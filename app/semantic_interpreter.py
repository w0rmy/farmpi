"""LLM-assisted interpretation of learner language into reviewed FarmPi operations.

This module deliberately does not execute database queries or mutations.  It turns
natural learner language into a small structured intent which the application then
validates and executes through the existing deterministic FarmPi functions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any

from .measurements import AVERAGE, BY_KEY, CURRENT, MAXIMUM, MINIMUM, RANKING, TREND, measurement_for_text
from .question_router import QuestionRoute


@dataclass(frozen=True)
class SemanticInterpretation:
    """A constrained interpretation of what the learner appears to mean."""

    intent: str
    confidence: float
    paddock_name: str | None = None
    new_paddock_name: str | None = None
    measurement: str | None = None
    operation: str | None = None
    window_minutes: int | None = None
    topic: str | None = None
    reason: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


_MUTATION_HINT_RE = re.compile(
    r"\b(?:rename|renamed|call\s+(?:the\s+)?(?:paddock|field)|change\s+(?:the\s+)?(?:paddock|field)?.{0,20}\bname)\b",
    re.IGNORECASE,
)

_AMBIGUOUS_FAST_ROUTES = {
    "conversation",
    "interpretation-boundary",
    "measurement-fallback",
    "operational-decision",
    "forecast-boundary",
    "causal-boundary",
}

_ALLOWED_INTENTS = {
    "rename",
    "current",
    "average",
    "highest",
    "lowest",
    "comparison",
    "history",
    "trend",
    "summary",
    "list-paddocks",
    "count-paddocks",
    "capability",
    "irrigation-decision",
    "learning",
    "research",
    "clarify",
}


def needs_semantic_interpretation(question: str, route: QuestionRoute) -> bool:
    """Return whether the fast router should be supplemented by semantic interpretation.

    Obvious deterministic requests stay fast.  Ambiguous learner language, broad
    learning questions, and mutation-looking wording that missed the exact action
    grammar are interpreted by the LLM before any execution occurs.
    """
    if _MUTATION_HINT_RE.search(question) and route.intent != "rename-request":
        return True
    if route.intent in _AMBIGUOUS_FAST_ROUTES:
        return True
    if route.intent == "paddock" and route.measurement is None:
        return True
    return False


def _source_name(name: str | None) -> str | None:
    if not name:
        return None
    value = " ".join(str(name).strip().split())
    if not value:
        return None
    if value.casefold().startswith("field "):
        value = "Paddock " + value[6:].strip()
    if value.casefold().startswith("paddock "):
        suffix = value[8:].strip()
        if suffix.isalpha() and len(suffix) <= 3:
            suffix = suffix.upper()
        value = f"Paddock {suffix}"
    return value[:120]


def build_interpretation_payload(question: str, paddock_names: tuple[str, ...] = ()) -> dict[str, Any]:
    """Build a small JSON-only interpretation request for the reference model."""
    known = ", ".join(paddock_names) if paddock_names else "not supplied"
    measurements = ", ".join(BY_KEY.keys())
    system = f"""You are FarmPi's learner-intent interpreter, not the answering assistant.
Interpret ordinary, polite, colloquial, regional, accented/transcribed, or incomplete English by meaning rather than command grammar.
Do not execute anything and do not answer the learner's farming question.
Return ONE JSON object only, with these keys:
intent, confidence, paddock_name, new_paddock_name, measurement, operation, window_minutes, topic, reason.
Allowed intent values: rename, current, average, highest, lowest, comparison, history, trend, summary, list-paddocks, count-paddocks, capability, irrigation-decision, learning, research, clarify.
Allowed measurement values: {measurements}. Use null when no FarmPi measurement is requested.
Use field and paddock as conversational synonyms. Preserve a requested new paddock name exactly; words such as 'please' may legitimately be part of a name.
Use learning for general agricultural education, including cows, sheep, pasture, soils, animal health, farm systems and explanations such as 'why'.
Use research when the learner explicitly asks what an external organisation/source says, asks for current external information, or asks FarmPi to look something up.
Use irrigation-decision for a farm-specific question asking whether/when to irrigate; do not make the decision yourself.
For a farm-data request, extract only entities that are actually expressed or strongly implied. Known active paddocks: {known}.
Confidence is a number from 0 to 1. If meaning is genuinely ambiguous, use clarify rather than inventing details.
Examples:
'Could you please call field A North Flat?' -> rename, paddock_name='Paddock A', new_paddock_name='North Flat'.
'What's B sitting at temperature-wise?' -> current, paddock_name='Paddock B', measurement='air_temperature_c'.
'Which field is looking driest?' -> lowest, measurement='soil_moisture_pct'.
'Why do cows get milk fever?' -> learning, topic='milk fever in dairy cows'.
'What does DairyNZ say about irrigation scheduling?' -> research, topic='DairyNZ irrigation scheduling'.
"""
    return {
        "model": "FarmPi-reference",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        "temperature": 0.0,
        "max_tokens": 192,
        "stream": False,
    }


def _clean_json_text(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Semantic interpreter did not return a JSON object.")
    return text[start : end + 1]


def parse_semantic_interpretation(content: str) -> SemanticInterpretation:
    """Parse and validate model JSON without granting it execution authority."""
    raw = json.loads(_clean_json_text(content))
    if not isinstance(raw, dict):
        raise ValueError("Semantic interpretation must be a JSON object.")

    intent = str(raw.get("intent") or "clarify").strip().casefold().replace("_", "-")
    aliases = {
        "rename-request": "rename",
        "paddock-field": "current",
        "farm-average": "average",
        "ranking-high": "highest",
        "ranking-low": "lowest",
        "farm-inventory-list": "list-paddocks",
        "farm-inventory-count": "count-paddocks",
        "education": "learning",
        "agriculture-learning": "learning",
    }
    intent = aliases.get(intent, intent)
    if intent not in _ALLOWED_INTENTS:
        intent = "clarify"

    try:
        confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    measurement = raw.get("measurement")
    if measurement is not None:
        measurement_text = str(measurement).strip()
        if measurement_text in BY_KEY:
            measurement = measurement_text
        else:
            measurement = measurement_for_text(measurement_text)

    operation = str(raw.get("operation") or "").strip().casefold() or None
    if operation not in {None, "current", "average", "highest", "lowest", "comparison", "history", "trend"}:
        operation = None

    window = raw.get("window_minutes")
    try:
        window_minutes = int(window) if window is not None else None
    except (TypeError, ValueError):
        window_minutes = None
    if window_minutes is not None and not 5 <= window_minutes <= 10080:
        window_minutes = None

    topic = str(raw.get("topic") or "").strip()[:240] or None
    reason = str(raw.get("reason") or "").strip()[:240] or None
    new_name = str(raw.get("new_paddock_name") or "").strip()[:120] or None

    return SemanticInterpretation(
        intent=intent,
        confidence=confidence,
        paddock_name=_source_name(raw.get("paddock_name")),
        new_paddock_name=new_name,
        measurement=measurement if isinstance(measurement, str) else None,
        operation=operation,
        window_minutes=window_minutes,
        topic=topic,
        reason=reason,
    )


def route_from_interpretation(value: SemanticInterpretation) -> QuestionRoute:
    """Map an interpreted meaning onto existing deterministic application routes."""
    if value.intent == "clarify" or (value.confidence < 0.55 and value.intent not in {"learning", "research"}):
        return QuestionRoute("semantic-clarification", education_key=value.topic)

    if value.intent == "rename":
        if value.paddock_name and value.new_paddock_name and value.confidence >= 0.65:
            return QuestionRoute("rename-request", value.paddock_name, new_paddock_name=value.new_paddock_name)
        return QuestionRoute("semantic-clarification", education_key="rename")

    if value.intent == "list-paddocks":
        return QuestionRoute("farm_inventory_list")
    if value.intent == "count-paddocks":
        return QuestionRoute("farm_inventory_count")
    if value.intent == "capability":
        return QuestionRoute("capability")
    if value.intent == "summary":
        return QuestionRoute("paddock_summary", paddock_name=value.paddock_name)
    if value.intent == "irrigation-decision":
        return QuestionRoute("irrigation-decision", paddock_name=value.paddock_name)

    if value.intent in {"learning", "research"}:
        return QuestionRoute(
            "agriculture-research" if value.intent == "research" else "agriculture-learning",
            paddock_name=value.paddock_name,
            measurement=value.measurement,
            education_key=value.topic,
        )

    key = value.measurement
    if value.intent == "current":
        if value.paddock_name:
            return QuestionRoute("paddock-field" if key and key != "soil_moisture_pct" else "paddock", value.paddock_name, key)
        if key:
            return QuestionRoute("measurement-fallback", measurement=key)
        return QuestionRoute("semantic-clarification")

    if not key or key not in BY_KEY:
        return QuestionRoute("semantic-clarification", education_key=value.topic)

    if value.intent == "average":
        if AVERAGE not in BY_KEY[key].operations:
            return QuestionRoute("semantic-clarification", measurement=key)
        if value.window_minutes:
            return QuestionRoute("historical", value.paddock_name, key, AVERAGE, value.window_minutes)
        if value.paddock_name:
            return QuestionRoute("semantic-clarification", paddock_name=value.paddock_name, measurement=key)
        return QuestionRoute("farm-average", measurement=key, operation=AVERAGE)

    if value.intent in {"highest", "lowest"}:
        wanted = value.intent
        supported = RANKING in BY_KEY[key].operations or (MAXIMUM if wanted == "highest" else MINIMUM) in BY_KEY[key].operations
        return QuestionRoute("ranking", measurement=key, operation=wanted) if supported else QuestionRoute("semantic-clarification", measurement=key)

    if value.intent == "comparison":
        operation = AVERAGE if AVERAGE in BY_KEY[key].operations else CURRENT
        return QuestionRoute("comparison", value.paddock_name, key, operation, value.window_minutes or 60, comparison=True)

    if value.intent in {"history", "trend"}:
        operation = TREND if value.intent == "trend" and TREND in BY_KEY[key].operations else AVERAGE if AVERAGE in BY_KEY[key].operations else CURRENT
        return QuestionRoute("historical", value.paddock_name, key, operation, value.window_minutes or 1440)

    return QuestionRoute("semantic-clarification", education_key=value.topic)
