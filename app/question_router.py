"""Deterministic routing for FarmPi's currently supported question types."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QuestionRoute:
    """Describe which deterministic farm-data operation a question needs."""

    intent: str
    paddock_name: str | None = None
    measurement: str | None = None


_PADDOCK_RE = re.compile(r"\bpaddock\s+([a-z0-9_-]+)\b", re.IGNORECASE)
_UNSUPPORTED_RE = re.compile(
    r"\b(?:daylight\s+hours?|weather|rain|rainfall|irrigation|recommend(?:ation|ed)?|should\s+i|hottest|coldest)\b",
    re.IGNORECASE,
)
_HELP_RE = re.compile(
    r"\b(?:help|guide\s+me|what\s+can\s+(?:i|we)\s+ask|what\s+can\s+you\s+do|how\s+do\s+i\s+use\s+farmpi|show\s+me\s+what\s+farmpi\s+can\s+do)\b",
    re.IGNORECASE,
)
_MEASUREMENT_PATTERNS = (
    ("soil_moisture_pct", re.compile(r"\b(?:soil\s+)?moisture\b", re.IGNORECASE)),
    ("air_temperature_c", re.compile(r"\b(?:air\s+)?temp(?:erature)?\b", re.IGNORECASE)),
    ("relative_humidity_pct", re.compile(r"\b(?:relative\s+)?humid(?:ity)?\b", re.IGNORECASE)),
    ("soil_ph", re.compile(r"\b(?:soil\s+)?p\s*h\b", re.IGNORECASE)),
    ("light_lux", re.compile(r"\b(?:light|lux|illumination|bright(?:ness)?)\b", re.IGNORECASE)),
)
_NON_MOISTURE_COMPARISON_RE = re.compile(
    r"\b(?:driest|dryest|wettest|lowest|least|highest|most|average|mean)\b",
    re.IGNORECASE,
)
_DRIEST_RE = re.compile(
    r"\b(?:driest|dryest)\b|\b(?:lowest|least)\s+(?:soil\s+)?moisture\b",
    re.IGNORECASE,
)
_WETTEST_RE = re.compile(
    r"\bwettest\b|\b(?:highest|most)\s+(?:soil\s+)?moisture\b",
    re.IGNORECASE,
)
_AVERAGE_RE = re.compile(
    r"\baverage\b|\bmean\s+(?:soil\s+)?moisture\b",
    re.IGNORECASE,
)

# Words that commonly follow "paddock" in ordinary questions but are not
# paddock identifiers. Without this guard a phrase such as "which paddock is"
# can be misread as a request for a paddock literally named "Paddock IS" if an
# earlier intent recogniser does not match the user's wording.
_PADDOCK_STOPWORDS = {
    "an",
    "are",
    "can",
    "could",
    "do",
    "does",
    "has",
    "have",
    "is",
    "should",
    "that",
    "the",
    "was",
    "were",
    "which",
    "with",
    "would",
}


def _canonical_paddock_name(token: str) -> str:
    """Convert a paddock token from natural language into the stored display form."""
    if token.isalpha() and len(token) <= 3:
        token = token.upper()
    return f"Paddock {token}"


def _measurement_for_question(question: str) -> str | None:
    """Return the one supported instantaneous measurement named in a question."""
    for measurement, pattern in _MEASUREMENT_PATTERNS:
        if pattern.search(question):
            return measurement
    return None


def route_question(question: str) -> QuestionRoute:
    """Route a question without asking the LLM to select or execute database logic."""
    if _UNSUPPORTED_RE.search(question):
        return QuestionRoute(intent="unsupported")

    # Help/onboarding is an approved deterministic route. Qwen is allowed to
    # explain FarmPi's known capabilities, but the capability list itself comes
    # from application facts rather than model memory.
    if _HELP_RE.search(question):
        return QuestionRoute(intent="help")

    measurement = _measurement_for_question(question)

    # Ranking/aggregation is approved only for soil moisture. The application
    # must calculate any future environmental aggregates before they reach Qwen.
    if measurement not in {None, "soil_moisture_pct"} and _NON_MOISTURE_COMPARISON_RE.search(question):
        return QuestionRoute(intent="unsupported")

    if _DRIEST_RE.search(question):
        return QuestionRoute(intent="driest")

    if _WETTEST_RE.search(question):
        return QuestionRoute(intent="wettest")

    if _AVERAGE_RE.search(question):
        return QuestionRoute(intent="average")

    paddock_matches = [
        token
        for token in _PADDOCK_RE.findall(question)
        if token.casefold() not in _PADDOCK_STOPWORDS
    ]
    if len(paddock_matches) == 1:
        return QuestionRoute(
            intent="paddock-field" if measurement and measurement != "soil_moisture_pct" else "paddock",
            paddock_name=_canonical_paddock_name(paddock_matches[0]),
            measurement=measurement,
        )

    if measurement and measurement != "soil_moisture_pct":
        # Give Qwen retrieved values only; it must not calculate a comparison.
        return QuestionRoute(intent="measurement-fallback", measurement=measurement)

    # The fallback deliberately preserves broader soil-moisture Q&A, including
    # comparisons and conversational wording the small router does not classify
    # more narrowly. Importantly, it is safer to use the verified full snapshot
    # than to invent a paddock name from grammar such as "paddock is".
    return QuestionRoute(intent="moisture-fallback")
