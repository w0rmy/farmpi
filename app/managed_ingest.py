"""Transactional physical-node validation using existing reading storage columns."""
from __future__ import annotations

import json
from datetime import timedelta

from fastapi import HTTPException

from .database import transaction
from .measurements import MEASUREMENTS
from .node_api import authenticate
from .node_config import mode_for
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
        applied = json.loads(node["applied_config_json"] or "{}")
        desired = json.loads(node["desired_config_json"] or "{}")
        if request.applied_fingerprint != node["applied_fingerprint"] or not request.applied_fingerprint:
            raise ValueError("Telemetry must identify an acknowledged configuration.")
        capabilities = set(json.loads(node["capabilities_json"] or "[]"))
        for key in values:
            if key not in capabilities:
                raise ValueError("Telemetry contains an unsupported measurement.")
            applied_mode = mode_for(applied, key)
            desired_mode = mode_for(desired, key)
            if applied_mode != desired_mode or applied_mode == "OFF":
                raise ValueError("Telemetry contains a disabled or unapplied measurement.")
            expected = "SIMULATED" if request.simulated else "LIVE"
            if applied_mode != expected:
                raise ValueError(f"{key} is configured for {applied_mode}, not {expected}.")
        cursor.execute("SELECT name FROM paddocks WHERE id=%s AND active=1", (node["paddock_id"],))
        location = cursor.fetchone()
        if not location:
            raise ValueError("Location is inactive.")
        cursor.execute("SELECT * FROM readings WHERE sensor_node_id=%s AND sample_seq=%s", (node["id"], request.sample_seq))
        duplicate = cursor.fetchone()
        observed_db = observed_at.replace(tzinfo=None)
        received_db = received_at.replace(tzinfo=None)
        if duplicate:
            previous = {m.key: float(duplicate[m.key]) for m in MEASUREMENTS if duplicate.get(m.key) is not None}
            if previous != values or bool(duplicate["simulated"]) != bool(request.simulated) or duplicate["observed_at"] != observed_db or duplicate["paddock_id"] != node["paddock_id"]:
                raise ValueError("Sequence already exists with different sample content.")
            return StoredReading(duplicate["id"], node["node_uid"], location["name"], values, bool(request.simulated),
                observed_at, duplicate["received_at"].replace(tzinfo=received_at.tzinfo), True,
                duplicate["clock_offset_seconds"], bool(duplicate["clock_out_of_tolerance"]), request.sample_seq, True)
        columns = ["sensor_node_id", "paddock_id", *(m.key for m in MEASUREMENTS), "simulated", "observed_at", "received_at", "recorded_at", "clock_valid", "clock_offset_seconds", "clock_out_of_tolerance", "sample_seq", "protocol_version"]
        params = (node["id"], node["paddock_id"], *(values.get(m.key) for m in MEASUREMENTS), bool(request.simulated), observed_db, received_db, received_db, True, offset, out_of_tolerance, request.sample_seq, request.protocol_version)
        cursor.execute(f"INSERT INTO readings ({','.join(columns)}) VALUES ({','.join('%s' for _ in columns)})", params)
        reading_id = cursor.lastrowid
        cursor.execute("UPDATE sensor_nodes SET last_seen=UTC_TIMESTAMP(6) WHERE id=%s", (node["id"],))
        return StoredReading(reading_id, node["node_uid"], location["name"], values, bool(request.simulated),
            observed_at, received_at, True, offset, out_of_tolerance, request.sample_seq)
