"""Validated sensor-ingest helpers for FarmPi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .database import execute, fetch_one


class UnknownSensor(RuntimeError):
    """Raised when a submitted sensor UID is not registered and active."""


@dataclass(frozen=True)
class StoredReading:
    """A sensor reading accepted and stored by FarmPi."""

    reading_id: int
    sensor_uid: str
    paddock_name: str
    soil_moisture_pct: float
    air_temperature_c: float
    relative_humidity_pct: float
    soil_ph: float
    light_lux: float
    simulated: bool
    recorded_at: datetime


SENSOR_LOOKUP_SQL = """
SELECT
    s.id AS sensor_node_id,
    s.node_uid,
    p.name AS paddock_name
FROM sensor_nodes AS s
JOIN paddocks AS p ON p.id = s.paddock_id
WHERE s.node_uid = %s
  AND s.active = 1
  AND p.active = 1
LIMIT 1
"""

INSERT_READING_SQL = """
INSERT INTO readings (
    sensor_node_id,
    soil_moisture_pct,
    air_temperature_c,
    relative_humidity_pct,
    soil_ph,
    light_lux,
    simulated,
    recorded_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def store_sensor_reading(
    sensor_uid: str,
    soil_moisture_pct: float,
    air_temperature_c: float,
    relative_humidity_pct: float,
    soil_ph: float,
    light_lux: float,
    simulated: bool,
) -> StoredReading:
    """Validate a registered sensor and store one server-timestamped reading."""
    sensor = fetch_one(SENSOR_LOOKUP_SQL, (sensor_uid,))
    if sensor is None:
        raise UnknownSensor(f"Unknown or inactive sensor: {sensor_uid}")

    # Store UTC in MariaDB as a naive DATETIME value. The UTC convention is
    # explicit here so ESP32 nodes do not need a real-time clock for this test.
    recorded_at_utc = datetime.now(timezone.utc)
    recorded_at_db = recorded_at_utc.replace(tzinfo=None)

    reading_id = execute(
        INSERT_READING_SQL,
        (
            int(sensor["sensor_node_id"]),
            round(float(soil_moisture_pct), 2),
            round(float(air_temperature_c), 2),
            round(float(relative_humidity_pct), 2),
            round(float(soil_ph), 2),
            round(float(light_lux), 2),
            bool(simulated),
            recorded_at_db,
        ),
    )

    return StoredReading(
        reading_id=reading_id,
        sensor_uid=str(sensor["node_uid"]),
        paddock_name=str(sensor["paddock_name"]),
        soil_moisture_pct=round(float(soil_moisture_pct), 2),
        air_temperature_c=round(float(air_temperature_c), 2),
        relative_humidity_pct=round(float(relative_humidity_pct), 2),
        soil_ph=round(float(soil_ph), 2),
        light_lux=round(float(light_lux), 2),
        simulated=bool(simulated),
        recorded_at=recorded_at_utc,
    )
