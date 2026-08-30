"""FarmPi grounded agricultural learning web service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
import logging
import os
import re
import secrets
import time
from typing import Any, AsyncIterator, Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .database import DatabaseUnavailable, ping_database
from .farm_data import (
    GroundingData,
    NoFarmData,
    analytics_grounding,
    format_grounding_context,
    get_grounding_data,
    paddock_summary,
)
from .education import CONCEPTS, concept_for_measurement, render_concept
from .guidance import INITIAL_SUGGESTIONS, WELCOME_TEXT, follow_up_suggestions
from .knowledge_sources import format_source_context, provenance_for_sources, source_hierarchy_contract
from .learning import activity_payload, course_payload, module_for_id
from .paddock_admin import RenameProposal, RenameRejected, confirm_rename, prepare_rename
from .question_router import route_question
from .semantic_interpreter import (
    build_interpretation_payload,
    is_research_question,
    needs_semantic_interpretation,
    parse_semantic_interpretation,
    requires_clarification_on_failure,
    route_from_interpretation,
)
from .speech_normalizer import SpeechAlternative, SpeechNormalization, current_paddock_names, normalize_speech

LLAMA_BASE_URL = os.getenv("FARMPI_LLAMA_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_CHAT_URL = f"{LLAMA_BASE_URL}/v1/chat/completions"
LLAMA_MODELS_URL = f"{LLAMA_BASE_URL}/v1/models"
LLAMA_TIMEOUT = httpx.Timeout(connect=3.0, read=120.0, write=10.0, pool=3.0)
LLM_MODEL = os.getenv("FARMPI_LLM_MODEL", "Qwen3-1.7B")

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Keep one HTTP client open for the configured LLM service."""
    async with httpx.AsyncClient(timeout=LLAMA_TIMEOUT) as client:
        application.state.http_client = client
        yield


app = FastAPI(title="FarmPi", version="0.7.0", lifespan=lifespan)

SYSTEM_PROMPT = """You are FarmPi, an open conversational agricultural learning assistant focused on practical New Zealand farming and the learner's FarmPi data.
Talk naturally and adapt to the learner's wording, background and requested explanation level. Questions about dairy farming, cows, sheep, pasture, soils, irrigation, weather, effluent, animal health, farm systems and related agriculture are legitimate learning questions.
FARMPI VERIFIED FACTS are authoritative for this farm: never invent, alter or replace sensor/database facts. DETERMINISTIC CALCULATIONS supplied by FarmPi are authoritative calculations over those facts; do not recalculate them.
CURATED NEW ZEALAND SOURCE material may be attributed to the named source only when a reviewed claim is supplied. Never claim that a source was searched live unless the context explicitly says live retrieval occurred.
You may use general agricultural knowledge to explain and teach. Clearly keep general knowledge separate from claims about this particular farm and from official NZ recommendations.
Do not make unsupported farm-specific diagnoses or operational decisions. Instead explain what is known, what factors are relevant, what is uncertain, and one useful next learning step.
Answer in 1–3 short sentences and at most one follow-up question unless the learner asks for more detail.
"""


SourceCategory = Literal[
    "observational",
    "calculated",
    "educational",
    "authoritative",
    "researched",
    "general",
    "combined",
]


class AskRequest(BaseModel):
    """Request body for a grounded FarmPi question."""

    question: str = Field(min_length=1, max_length=1000)
    confirmation_id: str | None = Field(default=None, min_length=16, max_length=128)
    conversation_id: str | None = Field(default=None, min_length=16, max_length=128)
    course_module_id: str | None = Field(default=None, min_length=1, max_length=64)
    speech: "SpeechInput | None" = None
    preferences: "ClientPreferences | None" = None


class SpeechInput(BaseModel):
    """Optional browser-speech metadata; typed questions deliberately omit it."""

    alternatives: list["SpeechAlternativeInput"] = Field(default_factory=list, max_length=5)


class SpeechAlternativeInput(BaseModel):
    transcript: str = Field(min_length=1, max_length=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SpeechNormalizationResponse(BaseModel):
    raw_transcript: str
    normalized_transcript: str
    correction_applied: bool
    correction_reason: str | None
    chosen_alternative_index: int | None
    chosen_alternative_confidence: float | None
    domain_score: int
    alternative_selected: bool


class ClientPreferences(BaseModel):
    """Presentation-only learning preferences; verified facts never vary."""

    explanation_level: Literal["simple", "normal", "technical"] = "normal"
    guidance_level: Literal["more", "normal", "less"] = "normal"


class SpeechNormalizeRequest(BaseModel):
    """Native clients can normalise STT before showing/routing a question."""

    transcript: str = Field(min_length=1, max_length=1000)
    alternatives: list["SpeechAlternativeInput"] = Field(default_factory=list, max_length=5)


class AskTimings(BaseModel):
    """Alpha performance timings for one FarmPi question."""

    routing_ms: float
    interpretation_ms: float = 0.0
    database_ms: float
    context_ms: float
    llm_ms: float
    total_ms: float


class AskResponse(BaseModel):
    """Response returned to the FarmPi client."""

    answer: str
    spoken_answer: str | None = None
    grounding: str = "hybrid-provenance"
    intent: str
    timings: AskTimings
    confirmation_id: str | None = None
    conversation_id: str | None = None
    suggestions: list[str] = Field(default_factory=list)
    speech_normalization: SpeechNormalizationResponse | None = None
    preferences: ClientPreferences = ClientPreferences()
    chart: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    source_category: SourceCategory = "observational"
    source_tier: str = "first-class-trusted"
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    semantic_interpretation: dict[str, Any] | None = None


class GuidanceResponse(BaseModel):
    """Deterministic onboarding content for the browser interface."""

    welcome: str
    suggestions: list[str]


@app.get("/api/learning/activities")
async def learning_activities() -> dict[str, list[dict[str, object]]]:
    """Serve the short activity catalogue; each activity invokes real routes."""
    return {"activities": activity_payload()}


@app.get("/api/learning/course")
async def learning_course() -> dict[str, object]:
    """Serve the versioned, deterministic flexible-course definition."""
    return course_payload()


# A confirmation is intentionally short-lived in process memory. It is not a
# durable command queue and cannot mutate anything unless the same browser
# explicitly returns its opaque token with a spoken/typed confirmation.
_pending_renames: dict[str, tuple[RenameProposal, float]] = {}
_CONFIRMATION_RE = re.compile(r"^\s*(?:yes|confirm|confirm rename|please confirm)\s*[!.]?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ConversationState:
    """The one small, non-durable state needed for an ordinal follow-up."""

    intent: str
    measurement: str | None
    operation: str | None
    expires_at: float


_conversation_states: dict[str, ConversationState] = {}
_CONVERSATION_TTL_SECONDS = 30 * 60


def _grounding_provenance(grounding: GroundingData, intent: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if grounding.evidence:
        entries.append({"kind": "farm-observation", "source": "FarmPi validated telemetry / MariaDB"})
    if intent in {"driest", "wettest", "average", "farm-average", "ranking", "historical", "comparison", "summary"}:
        entries.append({"kind": "deterministic-calculation", "source": "FarmPi application layer"})
    if grounding.source_category == "educational":
        entries.append({"kind": "curated-learning", "source": "FarmPi reviewed educational material"})
    return entries


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>FarmPi</title>
<style>
:root { color-scheme: dark; }
body {
    font-family: system-ui, sans-serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 20px;
    background: #111;
    color: #eee;
}
h1 { margin-bottom: 0.25rem; }
p { line-height: 1.45; }
.hint, #status, .footnote { color: #aaa; }
.warning {
    padding: 10px 12px;
    border: 1px solid #555;
    border-radius: 8px;
    margin: 16px 0;
}
textarea {
    box-sizing: border-box;
    width: 100%;
    min-height: 110px;
    font: inherit;
    font-size: 18px;
    padding: 12px;
    border-radius: 8px;
}
.controls { margin-top: 10px; }
button {
    font: inherit;
    font-size: 18px;
    padding: 11px 16px;
    margin: 0 8px 8px 0;
    border-radius: 8px;
}
label { display: inline-block; margin-top: 8px; }
#answer {
    margin-top: 22px;
    padding: 18px;
    background: #222;
    border-radius: 8px;
    font-size: 20px;
    min-height: 32px;
    white-space: pre-wrap;
}
#status { min-height: 1.5em; margin-top: 10px; }
#speech-transcript { min-height: 1.5em; margin-top: 8px; color: #aaa; font-size: 0.95rem; }
</style>
</head>
<body>
<h1>FarmPi</h1>
<p class="hint">Ask about your farm data or practical farming in your own words.</p>

<div class="warning">
<strong>Prototype:</strong> MariaDB holds simulated 16-paddock telemetry.
FarmPi labels simulated results and does not provide unsupported farm advice.
</div>

<textarea id="question" autocomplete="off"
    placeholder="For example: Why does soil moisture matter for pasture?"></textarea>

<div class="controls">
    <button id="ask" type="button">Ask FarmPi</button>
    <button id="guide" type="button">Guide me</button>
    <button id="speak" type="button">🎤 Speak</button>
</div>

<label>
    <input type="checkbox" id="speakAnswer" checked>
    Speak the answer on this device
</label>

<div id="status"></div>
<div id="speech-transcript" aria-live="polite"></div>
<div id="answer"></div>

<p class="footnote">
If browser speech recognition is unavailable or denied, tap the microphone on your phone keyboard and dictate into the question box.
</p>

<script>
const question = document.getElementById("question");
const answer = document.getElementById("answer");
const status = document.getElementById("status");
const speechTranscript = document.getElementById("speech-transcript");
const askButton = document.getElementById("ask");
const guideButton = document.getElementById("guide");
const speakButton = document.getElementById("speak");
const speakAnswer = document.getElementById("speakAnswer");
let pendingConfirmationId = null;
let conversationId = null;

async function askFarmPi(speechInput = null) {
    const text = question.value.trim();
    if (!text) {
        status.textContent = "Enter or speak a question first.";
        return;
    }

    askButton.disabled = true;
    guideButton.disabled = true;
    speakButton.disabled = true;
    answer.textContent = "";
    status.textContent = "Asking FarmPi…";
    if (!speechInput) speechTranscript.textContent = "";

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: text, confirmation_id: pendingConfirmationId, conversation_id: conversationId, speech: speechInput})
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || data.error || "FarmPi request failed");
        }

        answer.textContent = data.answer;
        pendingConfirmationId = data.confirmation_id || null;
        conversationId = data.conversation_id || conversationId;
        if (data.speech_normalization &&
                (data.speech_normalization.correction_applied || data.speech_normalization.alternative_selected)) {
            const interpreted = data.speech_normalization.normalized_transcript;
            speechTranscript.textContent = `Heard: “${text}” Interpreted: “${interpreted}”`;
            question.value = interpreted;
        } else if (speechInput) {
            speechTranscript.textContent = "";
        }
        if (data.suggestions && data.suggestions.length) {
            status.textContent = "Try next: " + data.suggestions[0];
        }
        if (data.timings) {
            const totalSeconds = (data.timings.total_ms / 1000).toFixed(2);
            const llmSeconds = (data.timings.llm_ms / 1000).toFixed(2);
            status.textContent =
                `Response received in ${totalSeconds}s (LLM ${llmSeconds}s, route ${data.intent}).`;
        } else {
            status.textContent = "Response received.";
        }

        if (speakAnswer.checked && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(data.spoken_answer || data.answer);
            utterance.lang = "en-NZ";
            window.speechSynthesis.speak(utterance);
        }
    } catch (error) {
        status.textContent = "Error: " + error.message;
    } finally {
        askButton.disabled = false;
        guideButton.disabled = false;
        speakButton.disabled = false;
    }
}

function startSpeech() {
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!window.isSecureContext) {
        status.textContent =
            "Speech recognition requires HTTPS. Use the phone keyboard microphone as a fallback.";
        return;
    }

    if (!SpeechRecognition) {
        status.textContent =
            "This browser does not provide speech recognition. Use the phone keyboard microphone instead.";
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-NZ";
    recognition.interimResults = false;
    recognition.maxAlternatives = 5;

    status.textContent = "Listening…";

    recognition.onresult = (event) => {
        const result = event.results[event.resultIndex];
        const text = result[0].transcript;
        const alternatives = Array.from(result, (alternative) => ({
            transcript: alternative.transcript,
            confidence: Number.isFinite(alternative.confidence) ? alternative.confidence : null
        }));
        question.value = text;
        status.textContent = "Heard: " + text;
        askFarmPi({alternatives});
    };

    recognition.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            status.textContent =
                "Microphone or speech recognition permission was denied. Allow microphone access for this site, or use the phone keyboard microphone.";
        } else {
            status.textContent = "Speech recognition error: " + event.error;
        }
    };

    recognition.onnomatch = () => {
        status.textContent = "Speech was not recognised. Try again.";
    };

    recognition.start();
}

askButton.addEventListener("click", askFarmPi);
guideButton.addEventListener("click", () => { question.value = "Guide me"; askFarmPi(); });
speakButton.addEventListener("click", startSpeech);
question.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        askFarmPi();
    }
});

async function checkFarmPiStatus() {
    try {
        const response = await fetch("/api/status");
        const data = await response.json();
        if (data.llm && data.llm.available && data.database && data.database.available) {
            status.textContent = "AI and farm database ready.";
        } else if (!data.database || !data.database.available) {
            status.textContent = "FarmPi is running, but the farm database is unavailable.";
        } else {
            status.textContent = "FarmPi is running, but the configured AI is unavailable.";
        }
    } catch {
        status.textContent = "Unable to check FarmPi status.";
    }
}

checkFarmPiStatus();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Serve the mobile-friendly FarmPi proof-of-concept interface."""
    return HTMLResponse(PAGE)


@app.get("/health")
async def health() -> dict[str, str]:
    """Cheap application health check for systemd and Caddy."""
    return {"status": "healthy"}


@app.get("/api/guidance", response_model=GuidanceResponse)
async def guidance(guidance_level: Literal["more", "normal", "less"] = "normal") -> GuidanceResponse:
    """Return deterministic onboarding text and example questions."""
    count = 4 if guidance_level == "more" else 1 if guidance_level == "less" else 3
    return GuidanceResponse(welcome=WELCOME_TEXT, suggestions=list(INITIAL_SUGGESTIONS[:count]))


@app.post("/api/speech/normalize", response_model=SpeechNormalizationResponse)
async def normalise_speech(request: SpeechNormalizeRequest) -> SpeechNormalizationResponse:
    """Apply the reviewed server-side domain correction without asking Qwen."""
    try:
        paddock_names = await asyncio.to_thread(current_paddock_names)
    except DatabaseUnavailable:
        paddock_names = ()
    normalization = normalize_speech(
        request.transcript,
        [SpeechAlternative(item.transcript, item.confidence) for item in request.alternatives],
        paddock_names,
    )
    return SpeechNormalizationResponse(**normalization.__dict__)


@app.get("/api/status")
async def status() -> dict[str, Any]:
    """Report application, database, and configured LLM dependency status."""
    llm_ok = False
    llm_detail = "unavailable"

    try:
        client: httpx.AsyncClient = app.state.http_client
        response = await client.get(LLAMA_MODELS_URL, timeout=3.0)
        llm_ok = response.is_success
        llm_detail = "ok" if llm_ok else f"http-{response.status_code}"
    except httpx.HTTPError:
        pass

    database_ok = False
    database_detail = "unavailable"
    try:
        database_ok = await asyncio.to_thread(ping_database)
        database_detail = "ok" if database_ok else "unavailable"
    except DatabaseUnavailable:
        pass

    return {
        "service": "FarmPi",
        "status": "running",
        "llm": {
            "available": llm_ok,
            "status": llm_detail,
            "url": LLAMA_BASE_URL,
            "model": LLM_MODEL,
        },
        "database": {
            "available": database_ok,
            "status": database_detail,
        },
        "grounding": "hybrid-provenance",
    }


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Interpret learner language, then use controlled FarmPi tools and learning context."""
    total_start = time.perf_counter()
    question_text = request.question.strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="No question supplied.")

    preferences = request.preferences or ClientPreferences()
    course_module = module_for_id(request.course_module_id) if request.course_module_id else None
    if request.course_module_id and course_module is None:
        raise HTTPException(status_code=422, detail="Unknown course_module_id.")
    course_provenance = (
        [{"kind": "reviewed-course-module", "source": "FarmPi controlled course material", "module": course_module.id}]
        if course_module else []
    )
    speech_normalization: SpeechNormalizationResponse | None = None
    semantic_interpretation: dict[str, Any] | None = None
    interpretation_ms = 0.0
    if request.speech is not None:
        try:
            paddock_names = await asyncio.to_thread(current_paddock_names)
        except DatabaseUnavailable:
            paddock_names = ()
        normalization: SpeechNormalization = normalize_speech(
            question_text,
            [SpeechAlternative(item.transcript, item.confidence) for item in request.speech.alternatives],
            paddock_names,
        )
        question_text = normalization.normalized_transcript
        speech_normalization = SpeechNormalizationResponse(**normalization.__dict__)

    route_start = time.perf_counter()
    route = route_question(question_text)
    routing_ms = (time.perf_counter() - route_start) * 1000
    conversation_id = request.conversation_id or secrets.token_urlsafe(18)

    now = time.monotonic()
    for token, state in tuple(_conversation_states.items()):
        if state.expires_at <= now:
            del _conversation_states[token]
    if route.intent == "contextual-follow-up":
        state = _conversation_states.get(conversation_id)
        if state is None:
            route = replace(route, intent="contextual-follow-up-missing")
        elif state.intent in {"paddock", "paddock-field"} and state.measurement:
            route = replace(
                route,
                intent="paddock-field" if state.measurement != "soil_moisture_pct" else "paddock",
                measurement=state.measurement,
                operation=state.operation,
            )
        elif state.intent == "paddock_summary":
            route = replace(route, intent="paddock_summary")
        else:
            route = replace(route, intent="contextual-follow-up-missing")

    def remember_conversation() -> None:
        if route.intent in {"paddock", "paddock-field", "paddock_summary"}:
            _conversation_states[conversation_id] = ConversationState(
                route.intent, route.measurement, route.operation, time.monotonic() + _CONVERSATION_TTL_SECONDS,
            )

    def direct_action(
        answer: str,
        intent: str,
        confirmation_id: str | None = None,
        *,
        spoken_answer: str | None = None,
        chart: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        source_category: SourceCategory = "observational",
        source_tier: str | None = None,
        provenance: list[dict[str, Any]] | None = None,
    ) -> AskResponse:
        remember_conversation()
        total_ms = (time.perf_counter() - total_start) * 1000
        database_ms = max(0.0, total_ms - routing_ms - interpretation_ms)
        return AskResponse(
            answer=answer,
            spoken_answer=spoken_answer or answer,
            intent=intent,
            confirmation_id=confirmation_id,
            conversation_id=conversation_id,
            suggestions=list(follow_up_suggestions(intent)[:4 if preferences.guidance_level == "more" else 1 if preferences.guidance_level == "less" else 3]),
            speech_normalization=speech_normalization,
            preferences=preferences,
            chart=chart,
            evidence=evidence or [],
            source_category=source_category,
            source_tier=source_tier or (
                "first-class-trusted" if source_category in {"observational", "calculated", "authoritative"}
                else "first-class-trusted" if source_category == "combined"
                else "model-knowledge"
            ),
            provenance=provenance or [],
            semantic_interpretation=semantic_interpretation,
            timings=AskTimings(
                routing_ms=round(routing_ms, 2),
                interpretation_ms=round(interpretation_ms, 2),
                database_ms=round(database_ms, 2),
                context_ms=0.0,
                llm_ms=0.0,
                total_ms=round(total_ms, 2),
            ),
        )

    # Confirmation remains an explicit deterministic mutation boundary. The
    # semantic model may interpret a rename request, but it never authorises or
    # executes the update.
    for token, (_, expires_at) in tuple(_pending_renames.items()):
        if expires_at <= now:
            del _pending_renames[token]
    if request.confirmation_id and _CONFIRMATION_RE.fullmatch(question_text):
        pending = _pending_renames.pop(request.confirmation_id, None)
        if pending is None:
            return direct_action("That rename confirmation is missing or expired. Please request the rename again.", "rename-confirmation")
        proposal, expires_at = pending
        if expires_at <= now:
            return direct_action("That rename confirmation has expired. Please request the rename again.", "rename-confirmation")
        try:
            confirmed = await asyncio.to_thread(confirm_rename, proposal)
        except (RenameRejected, DatabaseUnavailable) as exc:
            return direct_action(str(exc), "rename-confirmation")
        return direct_action(
            f'Renamed "{confirmed.old_name}" to "{confirmed.new_name}". Historical readings remain linked to this paddock.',
            "rename-confirmation",
            provenance=[{"kind": "deterministic-action", "source": "FarmPi paddock administration"}],
        )

    # The regex router is now a fast path, not the learner-language gatekeeper.
    # Ambiguous/open wording is interpreted semantically into a reviewed route.
    if needs_semantic_interpretation(question_text, route):
        interpretation_start = time.perf_counter()
        fast_route = route
        try:
            try:
                known_paddocks = await asyncio.to_thread(current_paddock_names)
            except DatabaseUnavailable:
                known_paddocks = ()
            payload = build_interpretation_payload(question_text, tuple(known_paddocks))
            payload["model"] = LLM_MODEL
            client: httpx.AsyncClient = app.state.http_client
            interpreted_response = await client.post(LLAMA_CHAT_URL, json=payload)
            interpreted_response.raise_for_status()
            interpreted_result = interpreted_response.json()
            interpretation = parse_semantic_interpretation(interpreted_result["choices"][0]["message"]["content"])
            semantic_interpretation = interpretation.public_dict()
            route = route_from_interpretation(interpretation)
            if route.intent == "semantic-clarification" and not requires_clarification_on_failure(question_text, fast_route):
                route = replace(
                    fast_route,
                    intent="agriculture-research" if is_research_question(question_text) else "agriculture-learning",
                    paddock_name=None,
                    measurement=None,
                    operation=None,
                    window_minutes=None,
                    new_paddock_name=None,
                    education_key=interpretation.topic or fast_route.education_key,
                )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            logger.warning("FarmPi semantic interpretation failed; using fast-route fallback: %s", exc)
            if requires_clarification_on_failure(question_text, fast_route):
                route = replace(fast_route, intent="semantic-clarification")
            elif is_research_question(question_text):
                route = replace(fast_route, intent="agriculture-research", paddock_name=None, measurement=None)
            elif fast_route.intent in {"conversation", "causal-boundary", "forecast-boundary", "interpretation-boundary"}:
                route = replace(fast_route, intent="agriculture-learning", paddock_name=None, measurement=None)
        interpretation_ms = (time.perf_counter() - interpretation_start) * 1000

    if route.intent == "rename-request":
        try:
            proposal = await asyncio.to_thread(prepare_rename, route.paddock_name or "", route.new_paddock_name or "")
        except (RenameRejected, DatabaseUnavailable) as exc:
            return direct_action(str(exc), "rename-request")
        confirmation_id = secrets.token_urlsafe(24)
        _pending_renames[confirmation_id] = (proposal, now + 300)
        return direct_action(
            f'Rename "{proposal.old_name}" to "{proposal.new_name}"? Reply “confirm” or “yes” within five minutes to apply this change.',
            "rename-request",
            confirmation_id,
            provenance=[{"kind": "deterministic-action", "source": "FarmPi paddock administration", "status": "awaiting-confirmation"}],
        )

    if route.intent == "semantic-clarification":
        return direct_action(
            "I’m not confident I understood that well enough to choose a FarmPi action. Could you say it another way or tell me what you want to learn or change?",
            "semantic-clarification",
            source_category="general",
            provenance=[{"kind": "interpretation", "source": "FarmPi semantic learner-intent layer", "confidence": "insufficient"}],
        )

    if route.intent == "contextual-follow-up-missing":
        return direct_action(
            "I need a little more context for that follow-up. Tell me the paddock, measurement, or farming topic you mean and I’ll continue from there.",
            "contextual-follow-up",
            source_category="general",
        )

    # Reviewed concept definitions remain useful high-confidence learning
    # material. A named current measurement can be added without letting the
    # language model invent the observation.
    if route.intent == "education":
        concept = CONCEPTS.get(route.education_key) or concept_for_measurement(route.measurement)
        lowered = question_text.casefold()
        if concept is None:
            concept = CONCEPTS.get("simulated_data" if "simulat" in lowered else "observed_received" if ("observed" in lowered or "received" in lowered) else "trend")
        facts = list(render_concept(concept, preferences.explanation_level))
        evidence: list[dict[str, Any]] = []
        provenance: list[dict[str, Any]] = [{"kind": "curated-learning", "source": "FarmPi reviewed educational material", "concept": concept.key}]
        if route.paddock_name and route.measurement:
            try:
                observed = await asyncio.to_thread(get_grounding_data, "paddock-field", route.paddock_name, route.measurement)
                facts.insert(0, observed.facts[0])
                evidence = [{"source": "observational", "fact": fact} for fact in observed.facts]
                provenance.insert(0, {"kind": "farm-observation", "source": "FarmPi validated telemetry / MariaDB"})
            except (DatabaseUnavailable, NoFarmData):
                facts.insert(0, "The requested current reading is unavailable, but the concept explanation is still available.")
        return direct_action(
            "\n".join(facts),
            "education",
            evidence=evidence + [{"source": "educational", "concept": concept.key}],
            source_category="combined" if evidence else "educational",
            provenance=provenance,
        )

    database_start = time.perf_counter()
    source_context = ""
    source_provenance: list[dict[str, Any]] = []
    try:
        if route.intent in {"agriculture-learning", "agriculture-research", "conversation"}:
            source_context, selected_sources = format_source_context(question_text)
            source_provenance = list(provenance_for_sources(selected_sources))
            if route.intent == "agriculture-research":
                source_provenance.append({
                    "kind": "research-status",
                    "status": "curated-source-directory-only",
                    "note": "Live external retrieval is not configured in this prototype; FarmPi must not imply that it searched the web.",
                })
            learning_facts = [
                "This is an agricultural learning question. General agricultural explanation is allowed, but general knowledge must not be presented as a verified fact about this farm.",
            ]
            evidence: tuple[dict[str, object], ...] = ()
            if route.paddock_name and route.measurement:
                try:
                    observed = await asyncio.to_thread(get_grounding_data, "paddock-field", route.paddock_name, route.measurement)
                    learning_facts = [*observed.facts, *learning_facts]
                    evidence = observed.evidence
                    source_provenance.insert(0, {"kind": "farm-observation", "source": "FarmPi validated telemetry / MariaDB"})
                except (DatabaseUnavailable, NoFarmData):
                    learning_facts.insert(0, "The related FarmPi reading is unavailable, so do not imply a current farm observation.")
            grounding_data = GroundingData(
                route.intent,
                tuple(learning_facts),
                evidence,
                source_category="general" if not evidence else "combined",
            )
        elif route.intent in {"historical", "comparison"} and route.measurement and route.operation:
            grounding_data = await asyncio.to_thread(analytics_grounding, route.measurement, route.operation, route.window_minutes, route.time_label, route.paddock_name, route.intent == "comparison")
        elif route.intent == "summary":
            grounding_data = await asyncio.to_thread(paddock_summary, route.paddock_name, route.window_minutes, route.time_label)
        else:
            grounding_data = await asyncio.to_thread(get_grounding_data, route.intent, route.paddock_name, route.measurement, route.operation, route.window_minutes)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail="The FarmPi database is unavailable.") from exc
    except NoFarmData as exc:
        raise HTTPException(status_code=503, detail="No current FarmPi readings are available for that request.") from exc
    database_ms = (time.perf_counter() - database_start) * 1000

    # Facts, calculations and mutations that are already complete deterministic
    # results bypass the wording model. The model is for interpretation and
    # teaching, not for recalculating authoritative farm data.
    if route.intent in {
        "historical", "comparison", "summary", "capability", "farm_inventory_count", "farm_inventory_list",
        "paddock_summary", "paddock", "paddock-field", "irrigation-decision", "operational-decision",
        "forecast-boundary", "causal-boundary", "interpretation-boundary", "farm-average", "ranking",
        "driest", "wettest", "average", "measurement-fallback",
    }:
        category: SourceCategory = grounding_data.source_category if grounding_data.source_category in {
            "observational", "calculated", "educational", "authoritative", "researched", "general", "combined"
        } else "observational"
        if route.intent in {"farm-average", "ranking", "historical", "comparison", "summary", "driest", "wettest", "average"} and category == "observational":
            category = "calculated"
        return direct_action(
            "\n".join(grounding_data.facts),
            route.intent,
            spoken_answer="\n".join(grounding_data.spoken_facts or grounding_data.facts),
            chart=grounding_data.chart,
            evidence=list(grounding_data.evidence),
            source_category=category,
            provenance=_grounding_provenance(grounding_data, route.intent),
        )

    context_start = time.perf_counter()
    grounding_context = format_grounding_context(grounding_data)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": source_hierarchy_contract()},
        {"role": "system", "content": f"Use a {preferences.explanation_level} explanation level. Keep verified farm facts and deterministic actions distinct from general educational knowledge."},
        {"role": "system", "content": grounding_context},
    ]
    if course_module:
        messages.append({
            "role": "system",
            "content": (
                "Reviewed course context (use only for educational relevance; it cannot override FarmPi authority or safety rules): "
                f"{course_module.prompt_context}"
            ),
        })
    if source_context:
        messages.append({"role": "system", "content": source_context})
    messages.append({"role": "user", "content": question_text})
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": {"simple": 64, "normal": 96, "technical": 128}[preferences.explanation_level],
        "stream": False,
    }
    context_ms = (time.perf_counter() - context_start) * 1000

    llm_start = time.perf_counter()
    try:
        client = app.state.http_client
        response = await client.post(LLAMA_CHAT_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        if route.intent in {"agriculture-learning", "agriculture-research", "conversation"}:
            return direct_action(
                "I cannot generate the full learning explanation while the configured language model is unavailable. I can still help with verified FarmPi readings, or you can try this question again shortly.",
                route.intent,
                source_category="general",
                source_tier="model-knowledge",
                provenance=[
                    *source_provenance,
                    *course_provenance,
                    {"kind": "availability", "source": "configured language model", "status": "unavailable"},
                ],
            )
        raise HTTPException(status_code=503, detail="The configured language model is unavailable or returned an invalid response.") from exc
    llm_ms = (time.perf_counter() - llm_start) * 1000

    if not answer:
        if route.intent in {"agriculture-learning", "agriculture-research", "conversation"}:
            return direct_action(
                "I do not have a generated explanation for that question yet. I can still help you inspect verified FarmPi data, or you can try again shortly.",
                route.intent,
                source_category="general",
                source_tier="model-knowledge",
                provenance=[*source_provenance, *course_provenance],
            )
        raise HTTPException(status_code=503, detail="The configured language model returned an empty response.")

    source_category: SourceCategory = grounding_data.source_category if grounding_data.source_category in {
        "observational", "calculated", "educational", "authoritative", "researched", "general", "combined"
    } else "general"
    provenance = [*_grounding_provenance(grounding_data, route.intent), *source_provenance, *course_provenance]
    if route.intent in {"agriculture-learning", "conversation"}:
        provenance.append({"kind": "general-explanation", "source": "configured language model", "scope": "educational; not a verified farm fact"})
        if source_provenance:
            source_category = "combined"
        else:
            source_category = "general"
    elif route.intent == "agriculture-research":
        provenance.append({"kind": "general-explanation", "source": "configured language model", "scope": "educational; curated source directory supplied"})
        source_category = "combined" if source_provenance else "general"
        answer = f"No live web research was performed. FarmPi used its curated source directory and configured model.\n\n{answer}"

    concept = concept_for_measurement(route.measurement)
    if concept and preferences.explanation_level in {"normal", "technical"} and route.intent not in {"agriculture-learning", "agriculture-research"}:
        note = concept.normal if preferences.explanation_level == "normal" else f"{concept.technical} Limitation: {concept.limitations}"
        answer = f"{answer}\n\nLearning note: {note}"
        source_category = "combined"
        provenance.append({"kind": "curated-learning", "source": "FarmPi reviewed educational material", "concept": concept.key})

    total_ms = (time.perf_counter() - total_start) * 1000
    timings = AskTimings(
        routing_ms=round(routing_ms, 2),
        interpretation_ms=round(interpretation_ms, 2),
        database_ms=round(database_ms, 2),
        context_ms=round(context_ms, 2),
        llm_ms=round(llm_ms, 2),
        total_ms=round(total_ms, 2),
    )

    logger.info(
        "FarmPi ask intent=%s routing=%.2fms interpretation=%.2fms database=%.2fms context=%.2fms llm=%.2fms total=%.2fms",
        route.intent,
        routing_ms,
        interpretation_ms,
        database_ms,
        context_ms,
        llm_ms,
        total_ms,
    )

    return AskResponse(
        answer=answer,
        intent=route.intent,
        conversation_id=conversation_id,
        suggestions=list(follow_up_suggestions(route.intent, route.paddock_name, route.measurement)[:4 if preferences.guidance_level == "more" else 1 if preferences.guidance_level == "less" else 3]),
        speech_normalization=speech_normalization,
        preferences=preferences,
        timings=timings,
        chart=grounding_data.chart,
        evidence=list(grounding_data.evidence),
        source_category=source_category,
        source_tier=(
            "first-class-trusted" if source_category in {"observational", "calculated", "authoritative"}
            else "first-class-trusted" if source_category == "combined"
            else "model-knowledge"
        ),
        provenance=provenance,
        semantic_interpretation=semantic_interpretation,
    )
