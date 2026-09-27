"""Transactional managed-node validation using explicit OFF/SIMULATED/LIVE modes."""
from __future__ import annotations

import json
from datetime import timedelta

from fastapi import HTTPException

from .database import transaction
from .measurements import MEASUREMENTS
from .node_api import authenticate
from .sensor_ingest import StoredReading, validate_reading_values


def store_managed(request, received_at, observed_at, clock_valid, offset, out_of_tolerance):
    values = validate_reading_values({m.key: getattr(request, m.key) for m in MEASUREMENTS if getattr(request, m.key) is not None})
    if request.sample_seq is None or not clock_valid or observed_at is None:
        raise ValueError("Managed samples require a valid observation time and persistent sequence.")
    if observed_at > received_at + timedelta(seconds=30):
        raise ValueError("Observation time is in the future; synchronise the clock.")

    with transaction() as cursor:
        node = authenticate(cursor, request)
        if node["registration_state"] != "registered" or not node["active"] or node["node_uid"] != request.sensor:
            raise HTTPException(403, "Registered node identity required.")
        if node["paddock_id"] is None:
            raise ValueError("Assign a location before sending telemetry.")
        if request.location_epoch != node["location_epoch"]:
            raise ValueError("Location assignment changed; delayed sample requires explicit reconciliation.")
        if request.applied_fingerprint != node["applied_fingerprint"] or not request.applied_fingerprint:
            raise ValueError("Telemetry must identify an acknowledged configuration.")

        applied = json.loads(node["applied_config_json"] or "{}")
        desired = json.loads(node["desired_config_json"] or "{}")
        capabilities = set(json.loads(node["capabilities_json"] or "[]"))
        applied_modes = applied.get("modes", {})
        desired_modes = desired.get("modes", {})

        measurement_modes: dict[str, str] = {}
        for key in values:
            if key not in capabilities:
                raise ValueError("Telemetry contains an unsupported measurement.")
            applied_mode = applied_modes.get(key, "OFF")
            desired_mode = desired_modes.get(key, "OFF")
            if applied_mode == "OFF" or desired_mode == "OFF":
                raise ValueError("Telemetry contains a measurement that is switched off.")
            if applied_mode != desired_mode:
                raise ValueError("Telemetry mode does not match the latest desired configuration.")
            measurement_modes[key] = applied_mode

        contains_simulated = any(mode == "SIMULATED" for mode in measurement_modes.values())
        contains_live = any(mode == "LIVE" for mode in measurement_modes.values())
        # The transport boolean remains as a conservative row-level compatibility
        # flag. Per-measurement authority comes from measurement_modes_json.
        if request.simulated != contains_simulated:
            raise ValueError("Telemetry simulated flag does not match configured measurement modes.")

        cursor.execute("SELECT name FROM paddocks WHERE id=%s AND active=1", (node["paddock_id"],))
        location = cursor.fetchone()
        if not location:
            raise ValueError("Location is inactive.")

        cursor.execute("SELECT * FROM readings WHERE sensor_node_id=%s AND sample_seq=%s", (node["id"], request.sample_seq))
        duplicate = cursor.fetchone()
        observed_db = observed_at.replace(tzinfo=None)
        received_db = received_at.replace(tzinfo=None)
        modes_json = json.dumps(measurement_modes, sort_keys=True, separators=(",", ":"))

        if duplicate:
            previous = {m.key: float(duplicate[m.key]) for m in MEASUREMENTS if duplicate.get(m.key) is not None}
            previous_modes = json.loads(duplicate.get("measurement_modes_json") or "{}")
            if (previous != values or previous_modes != measurement_modes or
                    bool(duplicate["simulated"]) != contains_simulated or
                    duplicate["observed_at"] != observed_db or duplicate["paddock_id"] != node["paddock_id"]):
                raise ValueError("Sequence already exists with different sample content.")
            return StoredReading(
                duplicate["id"], node["node_uid"], location["name"], values, contains_simulated,
                observed_at, duplicate["received_at"].replace(tzinfo=received_at.tzinfo), True,
                duplicate["clock_offset_seconds"], bool(duplicate["clock_out_of_tolerance"]),
                request.sample_seq, True, measurement_modes,
            )

        columns = [
            "sensor_node_id", "paddock_id", *(m.key for m in MEASUREMENTS),
            "simulated", "measurement_modes_json", "observed_at", "received_at",
            "recorded_at", "clock_valid", "clock_offset_seconds",
            "clock_out_of_tolerance", "sample_seq", "protocol_version"
        ]
        params = (
            node["id"], node["paddock_id"], *(values.get(m.key) for m in MEASUREMENTS),
            contains_simulated, modes_json, observed_db, received_db, received_db,
            True, offset, out_of_tolerance, request.sample_seq, request.protocol_version
        )
        cursor.execute(
            f"INSERT INTO readings ({','.join(columns)}) VALUES ({','.join('%s' for _ in columns)})",
            params,
        )
        reading_id = cursor.lastrowid
        cursor.execute("UPDATE sensor_nodes SET last_seen=UTC_TIMESTAMP(6) WHERE id=%s", (node["id"],))
        return StoredReading(
            reading_id, node["node_uid"], location["name"], values, contains_simulated,
            observed_at, received_at, True, offset, out_of_tolerance,
            request.sample_seq, False, measurement_modes,
        )
