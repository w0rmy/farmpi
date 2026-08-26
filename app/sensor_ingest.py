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
    recorded_at: datetime

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
    recorded_at
)
VALUES (%s, {_PLACEHOLDERS}, %s, %s)
"""


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


def store_sensor_reading(sensor_uid: str, simulated: bool, **values: Any) -> StoredReading:
    """Validate a registered sensor and store one server-timestamped reading."""
    sensor = fetch_one(SENSOR_LOOKUP_SQL, (sensor_uid,))
    if sensor is None:
        raise UnknownSensor(f"Unknown or inactive sensor: {sensor_uid}")
    validated = validate_reading_values({key: float(value) for key, value in values.items()})
    recorded_at_utc = datetime.now(timezone.utc)
    recorded_at_db = recorded_at_utc.replace(tzinfo=None)
    reading_id = execute(
        INSERT_READING_SQL,
        (int(sensor["sensor_node_id"]), *(validated[item.key] for item in MEASUREMENTS), bool(simulated), recorded_at_db),
    )
    return StoredReading(reading_id, str(sensor["node_uid"]), str(sensor["paddock_name"]), validated, bool(simulated), recorded_at_utc)
