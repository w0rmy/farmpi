"""Validated sensor-ingest helpers for FarmPi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .database import execute, fetch_one
from .measurements import BY_KEY, MEASUREMENTS


class UnknownSensor(RuntimeError):
    """Raised when a submitted sensor UID is not registered and active."""


@dataclass(frozen=True)
class StoredReading:
    """A sensor reading accepted and stored by FarmPi."""

    reading_id: int
    sensor_uid: str
    paddock_name: str
    values: dict[str, float]
    simulated: bool
    observed_at: datetime
    received_at: datetime
    clock_valid: bool
    clock_offset_seconds: float | None
    clock_out_of_tolerance: bool
    sample_seq: int | None
    deduplicated: bool = False

    @property
    def recorded_at(self) -> datetime:
        """Compatibility alias for callers from the server-timestamped alpha."""
        return self.received_at

    def __getattr__(self, key: str) -> float:
        """Keep convenient attribute access for each catalogued measurement."""
        if key in BY_KEY:
            return self.values[key]
        raise AttributeError(key)


SENSOR_LOOKUP_SQL = """
SELECT s.id AS sensor_node_id, s.node_uid, p.name AS paddock_name
FROM sensor_nodes AS s
JOIN paddocks AS p ON p.id = s.paddock_id
WHERE s.node_uid = %s AND s.active = 1 AND p.active = 1
LIMIT 1
"""

_COLUMNS = ",\n    ".join(item.key for item in MEASUREMENTS)
_PLACEHOLDERS = ", ".join("%s" for _ in MEASUREMENTS)
INSERT_READING_SQL = f"""
INSERT INTO readings (
    sensor_node_id,
    {_COLUMNS},
    simulated,
    observed_at,
    received_at,
    recorded_at,
    clock_valid,
    clock_offset_seconds,
    clock_out_of_tolerance,
    sample_seq,
    protocol_version
)
VALUES (%s, {_PLACEHOLDERS}, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

DUPLICATE_READING_SQL = f"""
SELECT id, {_COLUMNS}, simulated, observed_at, received_at, clock_valid,
       clock_offset_seconds, clock_out_of_tolerance, sample_seq
FROM readings
WHERE sensor_node_id = %s AND sample_seq = %s
LIMIT 1
"""


def _utc_datetime(value: Any) -> datetime:
    """Treat MariaDB DATETIME values as the documented UTC convention."""
    if not isinstance(value, datetime):
        raise ValueError("Stored reading has an invalid timestamp.")
    return value.replace(tzinfo=timezone.utc)


def validate_reading_values(values: dict[str, float]) -> dict[str, float]:
    """Validate all values against the reviewed measurement catalogue."""
    result: dict[str, float] = {}
    for item in MEASUREMENTS:
        if item.key not in values:
            raise ValueError(f"Missing required measurement: {item.key}")
        value = float(values[item.key])
        if not item.minimum <= value <= item.maximum:
            raise ValueError(f"{item.key} must be between {item.minimum} and {item.maximum}.")
        result[item.key] = round(value, item.decimal_places)
    return result


def store_sensor_reading(
    sensor_uid: str,
    simulated: bool,
    *,
    observed_at: datetime | None = None,
    received_at: datetime | None = None,
    clock_valid: bool = False,
    clock_offset_seconds: float | None = None,
    clock_out_of_tolerance: bool = True,
    sample_seq: int | None = None,
    protocol_version: int = 1,
    **values: Any,
) -> StoredReading:
    """Store a validated sample with explicit device and FarmPi time semantics.

    ``received_at`` is always FarmPi UTC.  An unset node clock never creates a
    1970 observation: it is represented by the receive time plus ``clock_valid``
    false.  A supplied sequence makes retries idempotent per sensor node.
    """
    sensor = fetch_one(SENSOR_LOOKUP_SQL, (sensor_uid,))
    if sensor is None:
        raise UnknownSensor(f"Unknown or inactive sensor: {sensor_uid}")
    validated = validate_reading_values({key: float(value) for key, value in values.items()})
    received_at_utc = (received_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    effective_clock_valid = bool(clock_valid and observed_at is not None)
    observed_at_utc = observed_at.astimezone(timezone.utc) if effective_clock_valid else received_at_utc

    if sample_seq is not None:
        duplicate = fetch_one(DUPLICATE_READING_SQL, (int(sensor["sensor_node_id"]), sample_seq))
        if duplicate is not None:
            return StoredReading(
                int(duplicate["id"]), str(sensor["node_uid"]), str(sensor["paddock_name"]),
                {item.key: float(duplicate[item.key]) for item in MEASUREMENTS}, bool(duplicate["simulated"]),
                _utc_datetime(duplicate["observed_at"]), _utc_datetime(duplicate["received_at"]),
                bool(duplicate["clock_valid"]),
                float(duplicate["clock_offset_seconds"]) if duplicate["clock_offset_seconds"] is not None else None,
                bool(duplicate["clock_out_of_tolerance"]),
                int(duplicate["sample_seq"]) if duplicate["sample_seq"] is not None else None,
                True,
            )

    received_at_db = received_at_utc.replace(tzinfo=None)
    observed_at_db = observed_at_utc.replace(tzinfo=None)
    reading_id = execute(
        INSERT_READING_SQL,
        (
            int(sensor["sensor_node_id"]), *(validated[item.key] for item in MEASUREMENTS), bool(simulated),
            observed_at_db, received_at_db, received_at_db, effective_clock_valid,
            round(clock_offset_seconds, 3) if clock_offset_seconds is not None else None,
            bool(clock_out_of_tolerance), sample_seq, protocol_version,
        ),
    )
    return StoredReading(
        reading_id, str(sensor["node_uid"]), str(sensor["paddock_name"]), validated, bool(simulated),
        observed_at_utc, received_at_utc, effective_clock_valid, clock_offset_seconds,
        bool(clock_out_of_tolerance), sample_seq,
    )
