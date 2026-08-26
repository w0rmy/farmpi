"""FarmPi grounded local-LLM web service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import os
import time
from typing import Any, AsyncIterator

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


app = FastAPI(title="FarmPi", version="0.4.0", lifespan=lifespan)

SYSTEM_PROMPT = """You are FarmPi.
Use only VERIFIED FACTS supplied by FarmPi.
Never calculate or invent facts, causes, or recommendations.
If the answer is absent, say it is unavailable.
Answer briefly.
"""


class AskRequest(BaseModel):
    """Request body for a grounded FarmPi question."""

    question: str = Field(min_length=1, max_length=1000)


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
</style>
</head>
<body>
<h1>FarmPi</h1>
<p class="hint">Ask the local farm-monitoring assistant a question.</p>

<div class="warning">
<strong>Prototype:</strong> soil-moisture readings are retrieved from MariaDB.
The current rows are seeded test data until physical sensors are connected.
</div>

<textarea id="question" autocomplete="off"
    placeholder="For example: Which paddock is driest?"></textarea>

<div class="controls">
    <button id="ask" type="button">Ask FarmPi</button>
    <button id="speak" type="button">🎤 Speak</button>
</div>

<label>
    <input type="checkbox" id="speakAnswer" checked>
    Speak the answer on this device
</label>

<div id="status"></div>
<div id="answer"></div>

<p class="footnote">
If browser speech recognition is unavailable or denied, tap the microphone on your phone keyboard and dictate into the question box.
</p>

<script>
const question = document.getElementById("question");
const answer = document.getElementById("answer");
const status = document.getElementById("status");
const askButton = document.getElementById("ask");
const speakButton = document.getElementById("speak");
const speakAnswer = document.getElementById("speakAnswer");

async function askFarmPi() {
    const text = question.value.trim();
    if (!text) {
        status.textContent = "Enter or speak a question first.";
        return;
    }

    askButton.disabled = true;
    speakButton.disabled = true;
    answer.textContent = "";
    status.textContent = "Asking FarmPi…";

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: text})
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || data.error || "FarmPi request failed");
        }

        answer.textContent = data.answer;
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
    recognition.maxAlternatives = 1;

    status.textContent = "Listening…";

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        question.value = text;
        status.textContent = "Heard: " + text;
        askFarmPi();
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

    route_start = time.perf_counter()
    route = route_question(question_text)
    routing_ms = (time.perf_counter() - route_start) * 1000

    database_start = time.perf_counter()
    try:
        grounding_data = await asyncio.to_thread(
            get_grounding_data,
            route.intent,
            route.paddock_name,
            route.measurement,
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
            {"role": "system", "content": verified_farm_data},
            {"role": "user", "content": question_text},
        ],
        "temperature": 0.1,
        "max_tokens": 40,
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
        timings=timings,
    )
