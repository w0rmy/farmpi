"""Deterministic routing for FarmPi's currently supported question types."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QuestionRoute:
    """Describe which deterministic farm-data operation a question needs."""

    intent: str
    paddock_name: str | None = None


_PADDOCK_RE = re.compile(r"\bpaddock\s+([a-z0-9_-]+)\b", re.IGNORECASE)
_UNSUPPORTED_RE = re.compile(
    r"\b(?:temperature|temp|ph|humidity|weather|rain|rainfall|irrigation)\b",
    re.IGNORECASE,
)

_DRIEST_TERMS = (
    "driest",
    "lowest moisture",
    "least moisture",
    "lowest soil moisture",
    "least soil moisture",
)

_WETTEST_TERMS = (
    "wettest",
    "highest moisture",
    "most moisture",
    "highest soil moisture",
    "most soil moisture",
)

_AVERAGE_TERMS = (
    "average",
    "mean moisture",
    "mean soil moisture",
)


def _canonical_paddock_name(token: str) -> str:
    """Convert a paddock token from natural language into the stored display form."""
    if token.isalpha() and len(token) <= 3:
        token = token.upper()
    return f"Paddock {token}"


def route_question(question: str) -> QuestionRoute:
    """Route a question without asking the LLM to select or execute database logic."""
    normalized = " " + " ".join(question.casefold().split()) + " "

    # Unsupported measurement types are handled before moisture keywords so a
    # question such as "temperature of the driest paddock" cannot accidentally
    # be answered with a soil-moisture result.
    if _UNSUPPORTED_RE.search(question):
        return QuestionRoute(intent="unsupported")

    if any(term in normalized for term in _DRIEST_TERMS):
        return QuestionRoute(intent="driest")

    if any(term in normalized for term in _WETTEST_TERMS):
        return QuestionRoute(intent="wettest")

    if any(term in normalized for term in _AVERAGE_TERMS):
        return QuestionRoute(intent="average")

    paddock_matches = _PADDOCK_RE.findall(question)
    if len(paddock_matches) == 1:
        return QuestionRoute(
            intent="paddock",
            paddock_name=_canonical_paddock_name(paddock_matches[0]),
        )

    # The fallback deliberately preserves broader soil-moisture Q&A, including
    # comparisons involving multiple named paddocks, while the router is small.
    return QuestionRoute(intent="moisture-fallback")
