"""Controlled paddock administration; natural language never becomes SQL."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .database import execute, fetch_one


class RenameRejected(ValueError):
    """Raised for an invalid, unknown, stale, or duplicate paddock rename."""


@dataclass(frozen=True)
class RenameProposal:
    paddock_id: int
    old_name: str
    new_name: str


_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '&-]{0,98}$")


def _normalise_name(name: str) -> str:
    return " ".join(name.split())


def _validate_new_name(name: str) -> str:
    name = _normalise_name(name)
    if not _NAME_RE.fullmatch(name):
        raise RenameRejected("A paddock name must be 1–99 letters, numbers, spaces, apostrophes, ampersands, or hyphens.")
    return name


def prepare_rename(old_name: str, new_name: str) -> RenameProposal:
    """Resolve an active paddock identity and validate a proposed new display name."""
    old_name, new_name = _normalise_name(old_name), _validate_new_name(new_name)
    row = fetch_one("SELECT id, name FROM paddocks WHERE name = %s AND active = 1 LIMIT 1", (old_name,))
    if row is None:
        raise RenameRejected(f"No active paddock named {old_name} exists.")
    current_name = str(row["name"])
    if current_name.casefold() == new_name.casefold():
        raise RenameRejected("The new paddock name is already its current name.")
    duplicate = fetch_one("SELECT id FROM paddocks WHERE name = %s LIMIT 1", (new_name,))
    if duplicate is not None:
        raise RenameRejected(f"A paddock named {new_name} already exists.")
    return RenameProposal(int(row["id"]), current_name, new_name)


def confirm_rename(proposal: RenameProposal) -> RenameProposal:
    """Apply a previously confirmed rename and write a traceable audit record."""
    current = fetch_one("SELECT id, name FROM paddocks WHERE id = %s AND active = 1 LIMIT 1", (proposal.paddock_id,))
    if current is None or str(current["name"]) != proposal.old_name:
        raise RenameRejected("The paddock changed before confirmation; request the rename again.")
    duplicate = fetch_one("SELECT id FROM paddocks WHERE name = %s AND id <> %s LIMIT 1", (proposal.new_name, proposal.paddock_id))
    if duplicate is not None:
        raise RenameRejected(f"A paddock named {proposal.new_name} already exists.")
    execute("UPDATE paddocks SET name = %s WHERE id = %s", (proposal.new_name, proposal.paddock_id))
    execute(
        "INSERT INTO paddock_admin_audit (paddock_id, old_name, new_name, action) VALUES (%s, %s, %s, %s)",
        (proposal.paddock_id, proposal.old_name, proposal.new_name, "rename"),
    )
    return proposal
