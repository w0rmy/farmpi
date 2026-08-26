"""Canonical, database-backed resolution of human paddock references."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from .database import fetch_all


@dataclass(frozen=True)
class PaddockIdentity:
    """An active paddock and its stable configured position."""

    id: int
    name: str
    order: int
    active_sensor_count: int


@dataclass(frozen=True)
class PaddockResolution:
    """A resolved identity or an explainable deterministic failure."""

    reference: str
    paddock: PaddockIdentity | None
    status: str
    suggestions: tuple[str, ...] = ()


_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16,
}
_NUMBER_RE = re.compile(r"^(?:paddock\s+)?(?:number\s+)?(\d+|" + "|".join(_NUMBER_WORDS) + r")$", re.IGNORECASE)
_LETTER_RE = re.compile(r"^(?:paddock\s+)?([a-z])$", re.IGNORECASE)

_ACTIVE_PADDOCKS_SQL = """
SELECT p.id, p.name, COUNT(s.id) AS active_sensor_count
FROM paddocks AS p
LEFT JOIN sensor_nodes AS s ON s.paddock_id = p.id AND s.active = 1
WHERE p.active = 1
GROUP BY p.id, p.name
ORDER BY p.id
"""
_ALIASES_SQL = """
SELECT a.paddock_id, a.old_name
FROM paddock_admin_audit AS a
JOIN paddocks AS p ON p.id = a.paddock_id
WHERE p.active = 1
ORDER BY a.id DESC
"""


def normalise_paddock_reference(reference: str) -> str:
    return " ".join(reference.strip(" .?!,\"'").split()).casefold()


def active_paddocks() -> tuple[PaddockIdentity, ...]:
    """Return active configured paddocks in their stable database order."""
    return tuple(
        PaddockIdentity(
            id=int(row["id"]), name=str(row["name"]), order=index,
            active_sensor_count=int(row.get("active_sensor_count", 0)),
        )
        for index, row in enumerate(fetch_all(_ACTIVE_PADDOCKS_SQL), start=1)
    )


def historic_aliases() -> dict[str, tuple[int, ...]]:
    """Return audit-backed prior names without making names themselves stable IDs."""
    aliases: dict[str, list[int]] = {}
    for row in fetch_all(_ALIASES_SQL):
        if not row.get("old_name"):
            continue
        alias = normalise_paddock_reference(str(row["old_name"]))
        aliases.setdefault(alias, []).append(int(row["paddock_id"]))
    return {alias: tuple(dict.fromkeys(ids)) for alias, ids in aliases.items()}


def _number(reference: str) -> int | None:
    match = _NUMBER_RE.fullmatch(reference)
    if not match:
        letter = _LETTER_RE.fullmatch(reference)
        return ord(letter.group(1).upper()) - ord("A") + 1 if letter else None
    value = match.group(1).casefold()
    return int(value) if value.isdigit() else _NUMBER_WORDS[value]


def resolve_paddock(
    reference: str,
    paddocks: tuple[PaddockIdentity, ...] | None = None,
    aliases: dict[str, tuple[int, ...]] | None = None,
) -> PaddockResolution:
    """Resolve display names, audited aliases, letter and ordinal forms safely."""
    wanted = normalise_paddock_reference(reference)
    items = paddocks if paddocks is not None else active_paddocks()
    suggestions = tuple(item.name for item in items[:4])
    if not items:
        return PaddockResolution(reference, None, "no-active-paddocks")

    exact = [item for item in items if normalise_paddock_reference(item.name) == wanted]
    if len(exact) == 1:
        return PaddockResolution(reference, exact[0], "resolved")
    if len(exact) > 1:
        return PaddockResolution(reference, None, "ambiguous-paddock", suggestions)

    aliases = historic_aliases() if aliases is None else aliases
    alias_ids = aliases.get(wanted, ())
    alias_matches = [item for item in items if item.id in alias_ids]
    if len(alias_matches) == 1:
        return PaddockResolution(reference, alias_matches[0], "resolved")
    if len(alias_matches) > 1:
        return PaddockResolution(reference, None, "ambiguous-paddock", suggestions)

    number = _number(wanted)
    if number is not None:
        if 1 <= number <= len(items):
            return PaddockResolution(reference, items[number - 1], "resolved")
        return PaddockResolution(reference, None, "paddock-out-of-range", suggestions)

    # The final recovery stage is intentionally small and transparent.  It
    # never maps a weak resemblance to a paddock; medium similarity becomes a
    # learner-facing "Did you mean...?" prompt instead.
    candidates = sorted(
        ((SequenceMatcher(None, wanted, normalise_paddock_reference(item.name)).ratio(), item) for item in items),
        key=lambda pair: pair[0],
        reverse=True,
    )
    if candidates:
        confidence, candidate = candidates[0]
        runner_up = candidates[1][0] if len(candidates) > 1 else 0.0
        if confidence >= 0.88 and confidence - runner_up >= 0.08:
            return PaddockResolution(reference, candidate, "resolved-fuzzy")
        if confidence >= 0.64:
            return PaddockResolution(reference, None, "did-you-mean", tuple(dict.fromkeys((candidate.name, *suggestions))))
    return PaddockResolution(reference, None, "unknown-paddock", suggestions)
