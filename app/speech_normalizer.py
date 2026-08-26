"""Small, deterministic interpretation layer for browser speech transcripts.

This module does not perform speech recognition and does not call the LLM.  It
only chooses between browser-provided alternatives and fixes a deliberately
small set of known farm-domain transcription mistakes when there is enough
FarmPi context to do so safely.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .database import fetch_all
from .measurements import measurement_for_text


@dataclass(frozen=True)
class SpeechAlternative:
    """One final alternative returned by the browser speech engine."""

    transcript: str
    confidence: float | None = None


@dataclass(frozen=True)
class SpeechNormalization:
    """Explainable result of deterministic speech interpretation."""

    raw_transcript: str
    normalized_transcript: str
    correction_applied: bool
    correction_reason: str | None
    chosen_alternative_index: int | None
    chosen_alternative_confidence: float | None
    domain_score: int
    alternative_selected: bool


# These are observed or very close phonetic spellings of "paddock".  They are
# intentionally not a general spelling-correction table.
_PADDOCK_CONFUSIONS = ("patek", "paddic", "paddik")
_PADDOCK_CONFUSION_RE = re.compile(
    r"\b(?:" + "|".join(_PADDOCK_CONFUSIONS) + r")\b", re.IGNORECASE
)
_PADDOCK_RE = re.compile(r"\bpaddock\s+[a-z0-9_-]+\b", re.IGNORECASE)
_FARM_CUE_RE = re.compile(
    r"\b(?:farm|paddock|soil|pasture|grass|driest|dryest|wettest|"
    r"tallest|shortest|hottest|coldest|rain|wind|daylight)\b",
    re.IGNORECASE,
)
_RENAME_CONFUSION_RE = re.compile(
    r"\brename\s+(?:" + "|".join(_PADDOCK_CONFUSIONS) + r")\s+[a-z0-9_-]+\b",
    re.IGNORECASE,
)


def current_paddock_names() -> tuple[str, ...]:
    """Read active display names so renamed paddocks contribute to speech bias."""
    rows = fetch_all("SELECT name FROM paddocks WHERE active = 1 ORDER BY id")
    return tuple(str(row["name"]).strip() for row in rows if str(row.get("name", "")).strip())


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(phrase.casefold()) + r"(?![a-z0-9])", text.casefold()))


def _mentions_paddock_name(text: str, paddock_names: Iterable[str]) -> bool:
    return any(_contains_phrase(text, name) for name in paddock_names)


def _has_farm_context(text: str, paddock_names: Iterable[str]) -> bool:
    """Require a FarmPi cue before changing a possible proper noun."""
    return bool(
        measurement_for_text(text)
        or _mentions_paddock_name(text, paddock_names)
        or _FARM_CUE_RE.search(text)
        or _RENAME_CONFUSION_RE.search(text)
    )


def _preserve_case(match: re.Match[str]) -> str:
    value = match.group(0)
    if value.isupper():
        return "PADDOCK"
    if value[:1].isupper():
        return "Paddock"
    return "paddock"


def _correct_known_confusions(text: str, paddock_names: Iterable[str]) -> tuple[str, bool]:
    if not _PADDOCK_CONFUSION_RE.search(text) or not _has_farm_context(text, paddock_names):
        return text, False
    return _PADDOCK_CONFUSION_RE.sub(_preserve_case, text), True


def _domain_score(text: str, paddock_names: Iterable[str], had_confusion: bool) -> int:
    """Use transparent vocabulary cues, not ML or fuzzy matching, to rank alternatives."""
    score = 0
    if measurement_for_text(text):
        score += 12
    if _PADDOCK_RE.search(text):
        score += 10
    if _mentions_paddock_name(text, paddock_names):
        score += 20
    if _FARM_CUE_RE.search(text):
        score += 2
    # Prefer a browser alternative that heard the known word correctly over a
    # transcript which had to be corrected locally, all else being equal.
    if had_confusion:
        score -= 2
    return score


def normalize_speech(
    raw_transcript: str,
    alternatives: Iterable[SpeechAlternative] = (),
    paddock_names: Iterable[str] = (),
) -> SpeechNormalization:
    """Return the safest domain-consistent transcript for deterministic routing.

    An alternative is selected only when it scores strictly better than the
    browser's top transcript.  A tie deliberately retains the top transcript,
    avoiding an unexplained change to ambiguous speech.
    """
    raw_transcript = raw_transcript.strip()
    names = tuple(name.strip() for name in paddock_names if name.strip())
    raw_normalized, raw_had_confusion = _correct_known_confusions(raw_transcript, names)
    raw_score = _domain_score(raw_normalized, names, raw_had_confusion)

    best_text = raw_normalized
    best_score = raw_score
    best_index: int | None = None
    best_confidence: float | None = None
    best_had_confusion = raw_had_confusion
    alternative_selected = False

    for index, alternative in enumerate(alternatives):
        candidate = alternative.transcript.strip()
        if not candidate:
            continue
        if candidate == raw_transcript:
            # Browser alternative zero is normally the raw top transcript.
            # Keep its metadata even when no different alternative is chosen.
            if best_index is None:
                best_index = index
                best_confidence = alternative.confidence
            continue
        normalized, had_confusion = _correct_known_confusions(candidate, names)
        score = _domain_score(normalized, names, had_confusion)
        if score > best_score:
            best_text = normalized
            best_score = score
            best_index = index
            best_confidence = alternative.confidence
            best_had_confusion = had_confusion
            alternative_selected = True

    correction_applied = best_text != raw_transcript
    if alternative_selected:
        reason = "domain-alternative"
    elif best_had_confusion:
        reason = "known-paddock-confusion"
    else:
        reason = None

    return SpeechNormalization(
        raw_transcript=raw_transcript,
        normalized_transcript=best_text,
        correction_applied=correction_applied,
        correction_reason=reason,
        chosen_alternative_index=best_index,
        chosen_alternative_confidence=best_confidence,
        domain_score=best_score,
        alternative_selected=alternative_selected,
    )
