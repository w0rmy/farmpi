"""Canonical configuration and pure node-state rules shared by API and tests."""
from __future__ import annotations

import hashlib
import json

from .measurements import BY_KEY

SCHEMA_VERSION = 2
MODES = ("OFF", "SIMULATED", "LIVE")


def configuration(
    node_uid: str,
    modes: dict[str, str] | None,
    capabilities: list[str],
    live_capabilities: list[str] | None = None,
) -> dict:
    capabilities = sorted(set(capabilities))
    live_capabilities = sorted(set(live_capabilities or []))
    if set(capabilities) - set(BY_KEY):
        raise ValueError("Unknown measurement capability.")
    if set(live_capabilities) - set(capabilities):
        raise ValueError("Live capability is not supported by this firmware.")

    requested = modes or {}
    if set(requested) - set(capabilities):
        raise ValueError("Measurement is not supported by this firmware.")

    normalised: dict[str, str] = {}
    for key in capabilities:
        mode = str(requested.get(key, "OFF")).upper()
        if mode not in MODES:
            raise ValueError("Measurement mode must be OFF, SIMULATED or LIVE.")
        if mode == "LIVE" and key not in live_capabilities:
            raise ValueError("Live acquisition is not available for this measurement.")
        normalised[key] = mode

    return {
        "modes": normalised,
        "node_uid": node_uid,
        "schema_version": SCHEMA_VERSION,
    }


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


def validate_config(
    config: dict,
    node_uid: str,
    capabilities: list[str],
    live_capabilities: list[str] | None,
    expected: str,
) -> dict:
    if config.get("schema_version") != SCHEMA_VERSION or config.get("node_uid") != node_uid:
        raise ValueError("Unsupported schema or wrong node identity.")
    modes = config.get("modes")
    if not isinstance(modes, dict):
        raise ValueError("Configuration modes are missing or invalid.")
    checked = configuration(node_uid, modes, capabilities, live_capabilities)
    if checked != config or fingerprint(checked) != expected:
        raise ValueError("Configuration fingerprint or structure mismatch.")
    return checked


def mode_for(config: dict, measurement: str) -> str:
    return str((config.get("modes") or {}).get(measurement, "OFF")).upper()
