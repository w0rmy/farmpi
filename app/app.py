"""FarmPi grounded local-LLM web service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
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
    NoFarmData,
    format_grounding_context,
    get_grounding_data,
)
from .question_router import route_question
from .paddock_admin import RenameProposal, RenameRejected, confirm_rename, prepare_rename
from .guidance import INITIAL_SUGGESTIONS, WELCOME_TEXT, follow_up_suggestions
from .speech_normalizer import SpeechAlternative, SpeechNormalization, current_paddock_names, normalize_speech

LLAMA_BASE_URL = os.getenv("FARMPI_LLAMA_URL", "http://127.0.0.1:8080")
LLAMA_CHAT_URL = f"{LLAMA_BASE_URL}/v1/chat/completions"
LLAMA_HEALTH_URL = f"{LLAMA_BASE_URL}/health"
LLAMA_TIMEOUT = httpx.Timeout(connect=3.0, read=120.0, write=10.0, pool=3.0)

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Keep one HTTP client open for local llama-server requests."""
    async with httpx.AsyncClient(timeout=LLAMA_TIMEOUT) as client:
        application.state.http_client = client
        yield


app = FastAPI(title="FarmPi", version="0.5.0", lifespan=lifespan)

SYSTEM_PROMPT = """You are FarmPi.
Use only VERIFIED FACTS supplied by FarmPi.
Never calculate or invent facts, causes, or recommendations.
If the answer is absent, say it is unavailable.
Answer briefly.
"""


class AskRequest(BaseModel):
    """Request body for a grounded FarmPi question."""

    question: str = Field(min_length=1, max_length=1000)
    confirmation_id: str | None = Field(default=None, min_length=16, max_length=128)
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
    database_ms: float
    context_ms: float
    llm_ms: float
    total_ms: float


class AskResponse(BaseModel):
    """Response returned to the FarmPi client."""

    answer: str
    grounding: str = "mariadb-deterministic"
    intent: str
    timings: AskTimings
    confirmation_id: str | None = None
    suggestions: list[str] = []
    speech_normalization: SpeechNormalizationResponse | None = None
    preferences: ClientPreferences = ClientPreferences()


class GuidanceResponse(BaseModel):
    """Deterministic onboarding content for the browser interface."""

    welcome: str
    suggestions: list[str]


# A confirmation is intentionally short-lived in process memory. It is not a
# durable command queue and cannot mutate anything unless the same browser
# explicitly returns its opaque token with a spoken/typed confirmation.
_pending_renames: dict[str, tuple[RenameProposal, float]] = {}
_CONFIRMATION_RE = re.compile(r"^\s*(?:yes|confirm|confirm rename|please confirm)\s*[!.]?\s*$", re.IGNORECASE)


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
<p class="hint">Ask the local farm-monitoring assistant a question.</p>

<div class="warning">
<strong>Prototype:</strong> MariaDB holds simulated 16-paddock telemetry.
FarmPi labels simulated results and does not provide farm advice.
</div>

<textarea id="question" autocomplete="off"
    placeholder="For example: Which paddock is driest?"></textarea>

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
            body: JSON.stringify({question: text, confirmation_id: pendingConfirmationId, speech: speechInput})
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || data.error || "FarmPi request failed");
        }

        answer.textContent = data.answer;
        pendingConfirmationId = data.confirmation_id || null;
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
            const utterance = new SpeechSynthesisUtterance(data.answer);
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
            status.textContent = "Local AI and farm database ready.";
        } else if (!data.database || !data.database.available) {
            status.textContent = "FarmPi is running, but the farm database is unavailable.";
        } else {
            status.textContent = "FarmPi is running, but the local AI is unavailable.";
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
    """Report application, database, and local LLM dependency status."""
    llm_ok = False
    llm_detail = "unavailable"

    try:
        client: httpx.AsyncClient = app.state.http_client
        response = await client.get(LLAMA_HEALTH_URL, timeout=3.0)
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
        },
        "database": {
            "available": database_ok,
            "status": database_detail,
        },
        "grounding": "mariadb-deterministic",
    }


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer a question using the smallest suitable deterministic grounding context."""
    total_start = time.perf_counter()
    question_text = request.question.strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="No question supplied.")

    preferences = request.preferences or ClientPreferences()
    speech_normalization: SpeechNormalizationResponse | None = None
    if request.speech is not None:
        try:
            paddock_names = await asyncio.to_thread(current_paddock_names)
        except DatabaseUnavailable:
            # The normalizer can still handle an explicit Paddock A-style
            # phrase.  The normal grounding request will report database
            # unavailability through its existing path if it needs data.
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

    def direct_action(answer: str, intent: str, confirmation_id: str | None = None) -> AskResponse:
        total_ms = (time.perf_counter() - total_start) * 1000
        return AskResponse(
            answer=answer,
            intent=intent,
            confirmation_id=confirmation_id,
            suggestions=list(follow_up_suggestions(intent)[:4 if preferences.guidance_level == "more" else 1 if preferences.guidance_level == "less" else 3]),
            speech_normalization=speech_normalization,
            preferences=preferences,
            timings=AskTimings(
                routing_ms=round(routing_ms, 2),
                database_ms=round(total_ms - routing_ms, 2),
                context_ms=0.0,
                llm_ms=0.0,
                total_ms=round(total_ms, 2),
            ),
        )

    # Confirmation is an explicit deterministic mutation boundary. Qwen is not
    # called to interpret, authorise, or execute the database update.
    now = time.monotonic()
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
        )

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
        )

    database_start = time.perf_counter()
    try:
        grounding_data = await asyncio.to_thread(
            get_grounding_data,
            route.intent,
            route.paddock_name,
            route.measurement,
            route.operation,
            route.window_minutes,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="The FarmPi database is unavailable.",
        ) from exc
    except NoFarmData as exc:
        raise HTTPException(
            status_code=503,
            detail="No current soil-moisture readings are available.",
        ) from exc
    database_ms = (time.perf_counter() - database_start) * 1000

    context_start = time.perf_counter()
    verified_farm_data = format_grounding_context(grounding_data)
    payload = {
        "model": "Qwen3-0.6B",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Explain verified facts at a {preferences.explanation_level} level. Do not add facts, calculations, advice, or causes."},
            {"role": "system", "content": verified_farm_data},
            {"role": "user", "content": question_text},
        ],
        "temperature": 0.1,
        "max_tokens": {"simple": 30, "normal": 40, "technical": 70}[preferences.explanation_level],
        "stream": False,
    }
    context_ms = (time.perf_counter() - context_start) * 1000

    llm_start = time.perf_counter()
    try:
        client: httpx.AsyncClient = app.state.http_client
        response = await client.post(LLAMA_CHAT_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="The local language model is unavailable or returned an invalid response.",
        ) from exc
    llm_ms = (time.perf_counter() - llm_start) * 1000

    if not answer:
        raise HTTPException(
            status_code=503,
            detail="The local language model returned an empty response.",
        )

    total_ms = (time.perf_counter() - total_start) * 1000
    timings = AskTimings(
        routing_ms=round(routing_ms, 2),
        database_ms=round(database_ms, 2),
        context_ms=round(context_ms, 2),
        llm_ms=round(llm_ms, 2),
        total_ms=round(total_ms, 2),
    )

    logger.info(
        "FarmPi ask intent=%s routing=%.2fms database=%.2fms context=%.2fms llm=%.2fms total=%.2fms",
        route.intent,
        routing_ms,
        database_ms,
        context_ms,
        llm_ms,
        total_ms,
    )

    return AskResponse(
        answer=answer,
        intent=route.intent,
        suggestions=list(follow_up_suggestions(route.intent, route.paddock_name, route.measurement)[:4 if preferences.guidance_level == "more" else 1 if preferences.guidance_level == "less" else 3]),
        speech_normalization=speech_normalization,
        preferences=preferences,
        timings=timings,
    )
