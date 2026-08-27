"""Bounded semantic classification for questions outside deterministic routes.

The interpreter is deliberately incapable of selecting database queries or
actions. It can only recognise a broad learning/research request, or ask the
caller to clarify. The deterministic router remains the authority for all
FarmPi facts, calculations, paddock identity, and mutations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from .question_router import QuestionRoute


class SemanticInterpretationError(ValueError):
    """The local model was unavailable or did not return the required JSON."""


@dataclass(frozen=True)
class SemanticInterpretation:
    """The only outcomes a semantic interpreter may contribute."""

    intent: str
    topic: str


_ALLOWED_INTENTS = frozenset({"agriculture-learning", "clarification"})
_MUTATION_OR_OPERATION_RE = re.compile(
    r"\b(?:rename|delete|remove|add|create|update|set|move|irrigat(?:e|ion)|water)\b",
    re.IGNORECASE,
)
_RESEARCH_RE = re.compile(
    r"\b(?:research|source|sources|citation|citations|latest|current guidance|dairynz|mpi|look up|find out)\b",
    re.IGNORECASE,
)

_INTERPRETER_PROMPT = """Classify a learner question for FarmPi. Return only one JSON object:
{"intent":"agriculture-learning"|"clarification","topic":"short topic"}
Use agriculture-learning only for a general, non-mutating agricultural explanation or research-style question. Use clarification for any action, rename, database change, farm-specific operational decision, or request for a FarmPi measurement/calculation. You cannot authorise actions or select data. Never include markdown or extra text."""


def needs_semantic_interpretation(question: str, fast_route: QuestionRoute) -> bool:
    """Limit semantic handling to questions without a deterministic operation."""
    # Approved deterministic action/decision routes never involve the model.
    if fast_route.intent in {"rename-request", "irrigation-decision", "operational-decision"}:
        return False
    # A complete rename request is already an approved deterministic route.
    # Incomplete action wording (for example, "Rename Paddock A") must be
    # interpreted only far enough to return a clarification.
    if _MUTATION_OR_OPERATION_RE.search(question) and fast_route.intent != "rename-request":
        return True
    if fast_route.intent == "conversation":
        return True
    # A general "why" question, such as animal-health learning, can look like
    # the legacy farm-cause boundary. A named paddock or known measurement is
    # still a farm-specific question and remains deterministic.
    return (
        fast_route.intent == "causal-boundary"
        and fast_route.paddock_name is None
        and fast_route.measurement is None
    )


def requires_clarification_on_failure(question: str, fast_route: QuestionRoute) -> bool:
    """Identify language that must never fail open into a possible action."""
    return bool(_MUTATION_OR_OPERATION_RE.search(question)) or fast_route.intent in {
        "rename-request",
        "irrigation-decision",
        "operational-decision",
    }


def is_research_question(question: str) -> bool:
    """Recognise requests whose answer must disclose research is unavailable."""
    return bool(_RESEARCH_RE.search(question))


async def interpret_semantically(question: str, client: httpx.AsyncClient | None, endpoint: str) -> SemanticInterpretation:
    """Ask the local model for a tightly validated, non-authoritative label."""
    if client is None:
        raise SemanticInterpretationError("local language-model client is unavailable")
    try:
        response = await client.post(
            endpoint,
            json={
                "model": "Qwen3-0.6B",
                "messages": [
                    {"role": "system", "content": _INTERPRETER_PROMPT},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.0,
                "max_tokens": 80,
                "stream": False,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        intent = parsed.get("intent")
        topic = parsed.get("topic")
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SemanticInterpretationError("invalid semantic-interpreter response") from exc
    if intent not in _ALLOWED_INTENTS or not isinstance(topic, str) or not topic.strip() or len(topic) > 160:
        raise SemanticInterpretationError("semantic-interpreter response is outside the approved schema")
    return SemanticInterpretation(intent, " ".join(topic.split()))
