"""Canonical configuration and pure node-state rules shared by API and tests."""
from __future__ import annotations

import hashlib
import json

from .measurements import BY_KEY

SCHEMA_VERSION = 1


def configuration(node_uid: str, enabled: list[str], capabilities: list[str]) -> dict:
    if len(enabled) != len(set(enabled)) or set(enabled) - set(BY_KEY):
        raise ValueError("Unknown or duplicate measurement.")
    if set(enabled) - set(capabilities):
        raise ValueError("Measurement is not supported by this firmware.")
    return {"enabled": sorted(enabled), "node_uid": node_uid, "schema_version": SCHEMA_VERSION}


def canonical(config: dict) -> str:
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(config: dict) -> str:
    return hashlib.sha256(canonical(config).encode("ascii")).hexdigest()


def sync_state(desired: str | None, applied: str | None, failed: str | None) -> str:
    if desired and desired == applied:
        return "IN SYNC"
    if desired and failed == desired:
        return "UPDATE FAILED"
    return "UPDATE PENDING"


def validate_config(config: dict, node_uid: str, capabilities: list[str], expected: str) -> dict:
    if config.get("schema_version") != SCHEMA_VERSION or config.get("node_uid") != node_uid:
        raise ValueError("Unsupported schema or wrong node identity.")
    checked = configuration(node_uid, config.get("enabled", []), capabilities)
    if checked != config or fingerprint(checked) != expected:
        raise ValueError("Configuration fingerprint or structure mismatch.")
    return checked
