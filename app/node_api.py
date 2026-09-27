"""Registration and latest-state configuration for managed FarmPi sensor nodes."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .database import DatabaseUnavailable, fetch_all, transaction
from .measurements import BY_KEY, MEASUREMENTS
from .node_config import canonical, configuration, fingerprint, mode_for, sync_state, validate_config

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("FARMPI_ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Node management is not configured.")
    if not authorization or not secrets.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(401, "Administrator token required.")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Contact(StrictModel):
    hardware_uid: str = Field(pattern=r"^[0-9a-f]{12}$")
    device_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    firmware_version: str = Field(min_length=1, max_length=64)
    board_profile: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    capabilities: list[str] = Field(max_length=13)
    live_capabilities: list[str] = Field(default_factory=list, max_length=13)
    applied_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("capabilities", "live_capabilities")
    @classmethod
    def known_capabilities(cls, value):
        if set(value) - set(BY_KEY) or len(value) != len(set(value)):
            raise ValueError("Unknown or duplicate capability.")
        return sorted(value)

    @model_validator(mode="after")
    def live_is_subset(self):
        if set(self.live_capabilities) - set(self.capabilities):
            raise ValueError("Live capabilities must also be general capabilities.")
        return self


class DeviceAuth(StrictModel):
    hardware_uid: str = Field(pattern=r"^[0-9a-f]{12}$")
    device_key: str = Field(pattern=r"^[0-9a-f]{64}$")


class Approval(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    paddock_id: int | None = Field(default=None, gt=0)
    location_name: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def one_location_selector(self):
        if self.paddock_id is not None and self.location_name is not None:
            raise ValueError("Choose an existing location or provide a new location name, not both.")
        return self


class Desired(Approval):
    modes: dict[str, str] = Field(default_factory=dict)
    expected_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class Acknowledgement(DeviceAuth):
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    config: dict | None = None
    error: str | None = Field(default=None, max_length=240)


def decode(value, fallback):
    return json.loads(value) if value else fallback


def authenticate(cursor, request):
    cursor.execute("SELECT * FROM sensor_nodes WHERE hardware_uid=%s FOR UPDATE", (request.hardware_uid,))
    row = cursor.fetchone()
    if not row or not row.get("device_key_hash") or not secrets.compare_digest(row["device_key_hash"], token_hash(request.device_key)):
        raise HTTPException(401, "Device identity or credential not recognised.")
    return row


def status_for(row):
    return {
        "registered": row["registration_state"] == "registered" and bool(row.get("active", True)),
        "node_uid": row["node_uid"] if row["registration_state"] == "registered" else None,
        "desired_fingerprint": row.get("desired_fingerprint"),
        "applied_fingerprint": row.get("applied_fingerprint"),
        "sync_state": sync_state(row.get("desired_fingerprint"), row.get("applied_fingerprint"), row.get("failed_fingerprint")),
        "server_time": int(datetime.now(timezone.utc).timestamp()),
        "location_epoch": int(row.get("location_epoch", 0)),
    }


def resolve_location(cursor, paddock_id: int | None, location_name: str | None) -> int | None:
    if location_name is not None:
        cleaned = " ".join(location_name.strip().split())
        if not cleaned:
            raise HTTPException(422, "Location name cannot be blank.")
        cursor.execute(
            """INSERT INTO paddocks(name,active) VALUES(%s,1)
               ON DUPLICATE KEY UPDATE active=1""",
            (cleaned,),
        )
        cursor.execute("SELECT id FROM paddocks WHERE name=%s AND active=1", (cleaned,))
        row = cursor.fetchone()
        return int(row["id"])
    if paddock_id is not None:
        cursor.execute("SELECT id FROM paddocks WHERE id=%s AND active=1", (paddock_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(422, "Unknown or inactive location.")
        return int(row["id"])
    return None


@router.post("/contact")
def contact(request: Contact):
    try:
        with transaction() as cursor:
            cursor.execute(
                """INSERT INTO sensor_nodes
                (node_uid,name,hardware_uid,device_key_hash,registration_state,active)
                VALUES (%s,%s,%s,%s,'pending',0)
                ON DUPLICATE KEY UPDATE hardware_uid=hardware_uid""",
                ("pending-" + request.hardware_uid, "Unregistered ESP32-S3", request.hardware_uid, token_hash(request.device_key)),
            )
            row = authenticate(cursor, request)
            cursor.execute(
                """UPDATE sensor_nodes SET firmware_version=%s,board_profile=%s,
                capabilities_json=%s,live_capabilities_json=%s,last_seen=UTC_TIMESTAMP(6) WHERE id=%s""",
                (
                    request.firmware_version,
                    request.board_profile,
                    canonical(request.capabilities),
                    canonical(request.live_capabilities),
                    row["id"],
                ),
            )
            known = {row.get("desired_fingerprint"), row.get("applied_fingerprint")}
            if request.applied_fingerprint in known and request.applied_fingerprint:
                applied = row.get("desired_config_json") if request.applied_fingerprint == row.get("desired_fingerprint") else row.get("applied_config_json")
                cursor.execute(
                    "UPDATE sensor_nodes SET applied_fingerprint=%s,applied_config_json=%s WHERE id=%s",
                    (request.applied_fingerprint, applied, row["id"]),
                )
                row["applied_fingerprint"] = request.applied_fingerprint
            elif request.applied_fingerprint != row.get("applied_fingerprint"):
                cursor.execute("UPDATE sensor_nodes SET applied_fingerprint=NULL,applied_config_json=NULL WHERE id=%s", (row["id"],))
                row["applied_fingerprint"] = None
            return status_for(row)
    except DatabaseUnavailable as exc:
        raise HTTPException(503, "FarmPi database unavailable.") from exc


@router.post("/configuration")
def get_configuration(request: DeviceAuth):
    with transaction() as cursor:
        row = authenticate(cursor, request)
        if row["registration_state"] != "registered" or not row["active"]:
            raise HTTPException(403, "Node is not registered and active.")
        return {
            "config": decode(row["desired_config_json"], {}),
            "canonical": row["desired_config_json"],
            "fingerprint": row["desired_fingerprint"],
        }


@router.post("/ack")
def acknowledge(request: Acknowledgement):
    with transaction() as cursor:
        row = authenticate(cursor, request)
        if row["registration_state"] != "registered" or not row["active"]:
            raise HTTPException(403, "Node is not registered and active.")
        if request.error:
            cursor.execute(
                "UPDATE sensor_nodes SET failed_fingerprint=%s,config_error=%s WHERE id=%s",
                (request.fingerprint, request.error, row["id"]),
            )
            row["failed_fingerprint"] = request.fingerprint
        else:
            if request.fingerprint not in {row["desired_fingerprint"], row.get("applied_fingerprint")}:
                raise HTTPException(409, "Desired configuration changed; fetch latest configuration.")
            try:
                checked = validate_config(
                    request.config or {},
                    row["node_uid"],
                    decode(row["capabilities_json"], []),
                    decode(row.get("live_capabilities_json"), []),
                    request.fingerprint,
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            cursor.execute(
                """UPDATE sensor_nodes SET applied_fingerprint=%s,applied_config_json=%s,
                failed_fingerprint=NULL,config_error=NULL WHERE id=%s""",
                (request.fingerprint, canonical(checked), row["id"]),
            )
            row["applied_fingerprint"] = request.fingerprint
            row["failed_fingerprint"] = None
        return status_for(row)


@router.post("/{node_id}/approve", dependencies=[Depends(require_admin)])
def approve(node_id: int, request: Approval):
    with transaction() as cursor:
        cursor.execute("SELECT * FROM sensor_nodes WHERE id=%s FOR UPDATE", (node_id,))
        row = cursor.fetchone()
        if not row or not row.get("hardware_uid"):
            raise HTTPException(404, "Discovered node not found.")
        if row["registration_state"] == "registered":
            return status_for(row)
        location_id = resolve_location(cursor, request.paddock_id, request.location_name)
        uid = f"FP-{node_id:03d}"
        capabilities = decode(row["capabilities_json"], [])
        live_capabilities = decode(row.get("live_capabilities_json"), [])
        config = configuration(uid, {}, capabilities, live_capabilities)
        digest = fingerprint(config)
        cursor.execute(
            """UPDATE sensor_nodes SET node_uid=%s,name=%s,paddock_id=%s,
            registration_state='registered',active=1,desired_config_json=%s,desired_fingerprint=%s
            WHERE id=%s""",
            (uid, request.name.strip(), location_id, canonical(config), digest, node_id),
        )
        row.update(node_uid=uid, registration_state="registered", active=1, desired_fingerprint=digest)
        return status_for(row)


@router.put("/{node_id}/configuration", dependencies=[Depends(require_admin)])
def set_configuration(node_id: int, request: Desired):
    with transaction() as cursor:
        cursor.execute("SELECT * FROM sensor_nodes WHERE id=%s FOR UPDATE", (node_id,))
        row = cursor.fetchone()
        if not row or row["registration_state"] != "registered" or not row.get("hardware_uid"):
            raise HTTPException(404, "Registered physical node not found.")
        if request.expected_fingerprint != row["desired_fingerprint"]:
            raise HTTPException(409, "Configuration changed; refresh before saving.")
        location_id = resolve_location(cursor, request.paddock_id, request.location_name)
        try:
            config = configuration(
                row["node_uid"],
                request.modes,
                decode(row["capabilities_json"], []),
                decode(row.get("live_capabilities_json"), []),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        location_epoch = int(row.get("location_epoch", 0)) + int(location_id != row["paddock_id"])
        digest = fingerprint(config)
        cursor.execute(
            """UPDATE sensor_nodes SET name=%s,paddock_id=%s,location_epoch=%s,
            desired_config_json=%s,desired_fingerprint=%s WHERE id=%s""",
            (request.name.strip(), location_id, location_epoch, canonical(config), digest, node_id),
        )
        return {"fingerprint": digest}


@router.get("", dependencies=[Depends(require_admin)])
def list_nodes():
    rows = fetch_all(
        "SELECT s.*,p.name AS paddock_name FROM sensor_nodes s LEFT JOIN paddocks p ON p.id=s.paddock_id ORDER BY s.id"
    )
    result = []
    for row in rows:
        if not row.get("hardware_uid"):
            continue
        config = decode(row.get("desired_config_json"), {})
        capabilities = decode(row.get("capabilities_json"), [])
        live_capabilities = decode(row.get("live_capabilities_json"), [])
        stamps = fetch_all(
            "SELECT "
            + ",".join(f"MAX(CASE WHEN {m.key} IS NOT NULL THEN observed_at END) AS {m.key}" for m in MEASUREMENTS)
            + " FROM readings WHERE sensor_node_id=%s",
            (row["id"],),
        )
        last = stamps[0] if stamps else {}
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sensors = []
        for m in MEASUREMENTS:
            timestamp = last.get(m.key)
            reporting = isinstance(timestamp, datetime) and 0 <= (now - timestamp).total_seconds() <= 600
            mode = mode_for(config, m.key) if m.key in capabilities else "OFF"
            if m.key not in capabilities:
                state = "NOT SUPPORTED"
            elif mode == "OFF":
                state = "OFF"
            elif reporting:
                state = "REPORTING"
            else:
                state = f"{mode} / NOT REPORTING"
            sensors.append(
                {
                    "key": m.key,
                    "label": m.label,
                    "unit": m.unit,
                    "supported": m.key in capabilities,
                    "live_supported": m.key in live_capabilities,
                    "mode": mode,
                    "enabled": mode != "OFF",
                    "state": state,
                    "last_observed_at": timestamp,
                }
            )
        result.append(
            {
                **status_for(row),
                "id": row["id"],
                "name": row["name"],
                "hardware_uid": row["hardware_uid"],
                "paddock_id": row["paddock_id"],
                "paddock_name": row["paddock_name"],
                "firmware_version": row.get("firmware_version"),
                "last_seen": row.get("last_seen"),
                "config_error": row.get("config_error"),
                "sensors": sensors,
            }
        )
    return {
        "nodes": result,
        "locations": fetch_all("SELECT id,name FROM paddocks WHERE active=1 ORDER BY name,id"),
    }
