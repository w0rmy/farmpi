"""Deterministic routing for approved FarmPi questions and admin requests."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .measurements import AVERAGE, CHANGE, DAYLIGHT, MAXIMUM, MINIMUM, RANKING, SUM, BY_KEY, measurement_for_text


@dataclass(frozen=True)
class QuestionRoute:
    """Describe a reviewed application operation; it never contains SQL."""

    intent: str
    paddock_name: str | None = None
    measurement: str | None = None
    operation: str | None = None
    window_minutes: int | None = None
    new_paddock_name: str | None = None


_UNSUPPORTED_RE = re.compile(
    r"\b(?:weather|forecast|irrigat(?:e|ion|ing)?|water(?:ing)?|recommend(?:ation|ed)?|advi[cs]e|should|need\s+to|why|reason(?:s)?|cause(?:d|s|ing)?)\b",
    re.IGNORECASE,
)
_RENAME_RE = re.compile(r"^\s*rename\s+(.+?)\s+to\s+(.+?)[?.! ]*\s*$", re.IGNORECASE)
_PADDOCK_RE = re.compile(r"\b(paddock\s+[a-z0-9_-]+)\b", re.IGNORECASE)
_POSSESSIVE_RE = re.compile(r"\b([a-z][a-z0-9 '&-]{0,98}?)'s\s+(?:soil\s+)?(?:moisture|temperature|humidity|ph|ec|light|rainfall|pressure|wind|pasture|grass|leaf)", re.IGNORECASE)
_PREPOSITION_RE = re.compile(r"\b(?:in|for|at|of)\s+([a-z][a-z0-9 '&-]{0,98}?)(?=\s+(?:over|during|in)\s+(?:the\s+)?(?:last|past)\b|[?!.]|$)", re.IGNORECASE)
_WINDOW_RE = re.compile(r"\b(?:over|during|in)\s+(?:the\s+)?(?:last|past)\s+(?:(\d+)\s*)?(minutes?|mins?|hours?|hrs?|days?)\b", re.IGNORECASE)
_RANK_HIGH_RE = re.compile(r"\b(?:highest|most|wettest|tallest|hottest)\b", re.IGNORECASE)
_RANK_LOW_RE = re.compile(r"\b(?:lowest|least|driest|dryest|shortest|coldest)\b", re.IGNORECASE)
_AVERAGE_RE = re.compile(r"\b(?:average|mean)\b", re.IGNORECASE)
_MIN_RE = re.compile(r"\b(?:minimum|min|lowest|least)\b", re.IGNORECASE)
_MAX_RE = re.compile(r"\b(?:maximum|max|highest|most)\b", re.IGNORECASE)
_CHANGE_RE = re.compile(r"\b(?:change|changed|trend|trending|increase|decrease|difference)\b", re.IGNORECASE)
_HELP_RE = re.compile(r"\b(?:help|guide\s+me|what\s+can\s+(?:i|we)\s+ask|what\s+can\s+you\s+do|how\s+(?:can|do)\s+i\s+use\s+farmpi)\b", re.IGNORECASE)


def _canonical_paddock_name(name: str) -> str:
    name = " ".join(name.split())
    if name.casefold().startswith("paddock "):
        suffix = name[8:].strip()
        return f"Paddock {suffix.upper() if suffix.isalpha() and len(suffix) <= 3 else suffix}"
    return name


def _extract_paddock(question: str) -> str | None:
    """Extract only a candidate; dynamic resolution happens against MariaDB."""
    direct_matches = _PADDOCK_RE.findall(question)
    if len(direct_matches) > 1:
        return None
    direct = _PADDOCK_RE.search(question)
    if direct and direct.group(1).casefold() not in {"paddock is", "paddock are"}:
        return _canonical_paddock_name(direct.group(1))
    possessive = _POSSESSIVE_RE.search(question)
    if possessive:
        return _canonical_paddock_name(possessive.group(1))
    preposition = _PREPOSITION_RE.search(question)
    if preposition:
        candidate = preposition.group(1).strip(" '")
        if candidate.casefold() not in {"the farm", "farm", "a paddock", "paddock"} and not candidate.casefold().startswith(("last ", "past ")):
            return _canonical_paddock_name(candidate)
    return None


def _window_minutes(question: str) -> int | None:
    match = _WINDOW_RE.search(question)
    if not match:
        return None
    amount = int(match.group(1) or 1)
    unit = match.group(2).casefold()
    multiplier = 1440 if unit.startswith("day") else 60 if unit.startswith(("hour", "hr")) else 1
    minutes = amount * multiplier
    return minutes if 5 <= minutes <= 10080 else None


def route_question(question: str) -> QuestionRoute:
    """Select an approved deterministic operation, never an LLM-selected query."""
    rename = _RENAME_RE.match(question)
    if rename:
        return QuestionRoute("rename-request", _canonical_paddock_name(rename.group(1)), new_paddock_name=" ".join(rename.group(2).split()))
    if _HELP_RE.search(question):
        return QuestionRoute("help")
    if _UNSUPPORTED_RE.search(question):
        return QuestionRoute("unsupported")

    measurement = measurement_for_text(question)
    # Conversational ranking shorthand has no literal catalogue alias.
    if not measurement and re.search(r"\b(?:driest|dryest|wettest)\b", question, re.IGNORECASE):
        measurement = "soil_moisture_pct"
    if not measurement and re.search(r"\b(?:tallest|shortest)\b", question, re.IGNORECASE):
        measurement = "pasture_height_cm"
    if not measurement and re.search(r"\b(?:hottest|coldest)\b", question, re.IGNORECASE):
        measurement = "air_temperature_c"
    paddock = _extract_paddock(question)
    window = _window_minutes(question)

    if re.search(r"\bdaylight\s+hours?\b", question, re.IGNORECASE):
        return QuestionRoute("historical", paddock, "light_lux", DAYLIGHT, window or 1440)
    if window and measurement:
        if _CHANGE_RE.search(question) and CHANGE in BY_KEY[measurement].operations:
            operation = CHANGE
        elif measurement == "rainfall_mm" and SUM in BY_KEY[measurement].operations and not _AVERAGE_RE.search(question):
            operation = SUM
        elif _AVERAGE_RE.search(question) and AVERAGE in BY_KEY[measurement].operations:
            operation = AVERAGE
        elif _MIN_RE.search(question) and MINIMUM in BY_KEY[measurement].operations:
            operation = MINIMUM
        elif _MAX_RE.search(question) and MAXIMUM in BY_KEY[measurement].operations:
            operation = MAXIMUM
        else:
            return QuestionRoute("unsupported")
        return QuestionRoute("historical", paddock, measurement, operation, window)

    if measurement == "soil_moisture_pct" and re.search(r"\b(?:driest|dryest|lowest|least)\b", question, re.IGNORECASE):
        return QuestionRoute("driest")
    if measurement == "soil_moisture_pct" and re.search(r"\b(?:wettest|highest|most)\b", question, re.IGNORECASE):
        return QuestionRoute("wettest")
    if measurement == "soil_moisture_pct" and _AVERAGE_RE.search(question):
        return QuestionRoute("average")

    if measurement and RANKING in BY_KEY[measurement].operations:
        if _RANK_HIGH_RE.search(question):
            return QuestionRoute("ranking", measurement=measurement, operation="highest")
        if _RANK_LOW_RE.search(question):
            return QuestionRoute("ranking", measurement=measurement, operation="lowest")

    if measurement and (_RANK_HIGH_RE.search(question) or _RANK_LOW_RE.search(question) or _AVERAGE_RE.search(question)):
        return QuestionRoute("unsupported")

    if paddock:
        return QuestionRoute("paddock-field" if measurement and measurement != "soil_moisture_pct" else "paddock", paddock, measurement)
    if measurement and measurement != "soil_moisture_pct":
        return QuestionRoute("measurement-fallback", measurement=measurement)
    return QuestionRoute("moisture-fallback")
