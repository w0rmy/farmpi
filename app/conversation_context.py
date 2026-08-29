"""Per-conversation learning context and client-response cleanup.

FarmPi keeps only a tiny, short-lived conversational window. The deterministic
farm-data layer remains authoritative; this context exists so natural follow-ups
such as "explain that more simply" can refer to the previous exchange without
sending an ever-growing transcript to the local model.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
import json
import logging
import re
import time
from typing import Any

from fastapi import Request
from fastapi.responses import Response


logger = logging.getLogger("uvicorn.error")

_CONVERSATION_TTL_SECONDS = 30 * 60
_MAX_TURNS = 2
_MAX_QUESTION_CHARS = 600
_MAX_ANSWER_CHARS = 1400

_RESEARCH_DIAGNOSTIC_RE = re.compile(
    r"^\s*No live web research was performed\.\s*"
    r"FarmPi used its curated source directory and configured model\.\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConversationTurn:
    question: str
    answer: str


@dataclass
class ConversationHistory:
    turns: list[ConversationTurn]
    expires_at: float


_conversation_histories: dict[str, ConversationHistory] = {}
_current_conversation: ContextVar[tuple[dict[str, str], ...]] = ContextVar(
    "farmpi_current_conversation",
    default=(),
)


def current_conversation_messages() -> tuple[dict[str, str], ...]:
    """Return the bounded history available to the current request's LLM calls."""

    return _current_conversation.get()


def _purge_expired(now: float) -> None:
    for conversation_id, history in tuple(_conversation_histories.items()):
        if history.expires_at <= now:
            del _conversation_histories[conversation_id]


def _messages_for(conversation_id: str | None, now: float) -> tuple[dict[str, str], ...]:
    if not conversation_id:
        return ()
    history = _conversation_histories.get(conversation_id)
    if history is None or history.expires_at <= now:
        return ()

    messages: list[dict[str, str]] = []
    for turn in history.turns[-_MAX_TURNS:]:
        messages.append({"role": "user", "content": turn.question})
        messages.append({"role": "assistant", "content": turn.answer})
    return tuple(messages)


def _remember(conversation_id: str | None, question: str | None, answer: str | None, now: float) -> None:
    if not conversation_id or not question or not answer:
        return

    clean_question = " ".join(question.strip().split())[:_MAX_QUESTION_CHARS]
    clean_answer = answer.strip()[:_MAX_ANSWER_CHARS]
    if not clean_question or not clean_answer:
        return

    history = _conversation_histories.get(conversation_id)
    turns = list(history.turns) if history and history.expires_at > now else []
    turns.append(ConversationTurn(clean_question, clean_answer))
    _conversation_histories[conversation_id] = ConversationHistory(
        turns=turns[-_MAX_TURNS:],
        expires_at=now + _CONVERSATION_TTL_SECONDS,
    )


def prepare_client_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove developer diagnostics and guarantee usable speech text."""

    adjusted = dict(payload)
    answer = adjusted.get("answer")
    if isinstance(answer, str):
        clean_answer = _RESEARCH_DIAGNOSTIC_RE.sub("", answer).lstrip()
        adjusted["answer"] = clean_answer
    else:
        clean_answer = ""

    spoken = adjusted.get("spoken_answer")
    if not isinstance(spoken, str) or not spoken.strip() or spoken.strip().casefold() in {"null", "none"}:
        adjusted["spoken_answer"] = clean_answer
    else:
        adjusted["spoken_answer"] = _RESEARCH_DIAGNOSTIC_RE.sub("", spoken).lstrip()

    provenance = adjusted.get("provenance")
    if isinstance(provenance, list):
        # Research execution status is useful server-side diagnostic metadata,
        # not learner-facing evidence. Keep actual source provenance visible.
        adjusted["provenance"] = [
            item
            for item in provenance
            if not (isinstance(item, dict) and item.get("kind") == "research-status")
        ]

    return adjusted


def _response_from_bytes(response: Any, body: bytes) -> Response:
    headers = dict(response.headers)
    headers.pop("content-length", None)
    return Response(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type=None,
        background=response.background,
    )


def _json_response(response: Any, payload: Any) -> Response:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _response_from_bytes(response, body)


def install_conversation_context(application: Any) -> None:
    """Install bounded conversation memory and learner-facing response cleanup."""

    if getattr(application.state, "_farmpi_conversation_context_installed", False):
        return

    @application.middleware("http")
    async def conversation_context_middleware(request: Request, call_next: Any) -> Any:
        is_ask = request.method.upper() == "POST" and request.url.path == "/api/ask"
        is_guidance = request.method.upper() == "GET" and request.url.path == "/api/guidance"
        now = time.monotonic()
        token: Token[tuple[dict[str, str], ...]] | None = None
        incoming_conversation_id: str | None = None
        original_question: str | None = None

        if is_ask:
            _purge_expired(now)
            try:
                body = await request.json()
                if isinstance(body, dict):
                    raw_id = body.get("conversation_id")
                    incoming_conversation_id = str(raw_id).strip() if raw_id else None
                    raw_question = body.get("question")
                    original_question = str(raw_question).strip() if raw_question else None
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            token = _current_conversation.set(_messages_for(incoming_conversation_id, now))

        try:
            response = await call_next(request)
        finally:
            if token is not None:
                _current_conversation.reset(token)

        if not (is_ask or is_guidance):
            return response
        if "application/json" not in response.headers.get("content-type", ""):
            return response

        raw_body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return _response_from_bytes(response, raw_body)

        if not isinstance(payload, dict):
            return _json_response(response, payload)

        if is_guidance:
            welcome = payload.get("welcome")
            if isinstance(welcome, str):
                logger.info("FarmPi guidance client text chars=%d", len(welcome))
            return _json_response(response, payload)

        adjusted = prepare_client_payload(payload)
        answer = adjusted.get("answer") if isinstance(adjusted.get("answer"), str) else None
        spoken = adjusted.get("spoken_answer") if isinstance(adjusted.get("spoken_answer"), str) else None
        response_conversation_id = adjusted.get("conversation_id")
        conversation_id = str(response_conversation_id).strip() if response_conversation_id else incoming_conversation_id
        _remember(conversation_id, original_question, answer, time.monotonic())
        logger.info(
            "FarmPi client response answer_chars=%d spoken_chars=%d conversation=%s",
            len(answer or ""),
            len(spoken or ""),
            "present" if conversation_id else "missing",
        )
        return _json_response(response, adjusted)

    application.state._farmpi_conversation_context_installed = True
