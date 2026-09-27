"""Canonical configuration and pure node-state rules shared by API, firmware and tests."""
from __future__ import annotations

import hashlib
import json

from .measurements import BY_KEY

SCHEMA_VERSION = 2
SENSOR_MODES = ("OFF", "SIMULATED", "LIVE")


def configuration(node_uid: str, modes: dict[str, str], capabilities: list[str]) -> dict:
    """Return one complete desired state for every firmware-supported measurement."""
    if len(capabilities) != len(set(capabilities)) or set(capabilities) - set(BY_KEY):
        raise ValueError("Unknown or duplicate capability.")
    if set(modes) - set(capabilities):
        raise ValueError("Measurement is not supported by this firmware.")
    unknown_modes = {value for value in modes.values() if value not in SENSOR_MODES}
    if unknown_modes:
        raise ValueError("Sensor mode must be OFF, SIMULATED, or LIVE.")
    normalized = {key: modes.get(key, "OFF") for key in sorted(capabilities)}
    return {"modes": normalized, "node_uid": node_uid, "schema_version": SCHEMA_VERSION}


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
    if not isinstance(config.get("modes"), dict):
        raise ValueError("Configuration must contain measurement modes.")
    checked = configuration(node_uid, config["modes"], capabilities)
    if checked != config or fingerprint(checked) != expected:
        raise ValueError("Configuration fingerprint or structure mismatch.")
    return checked
