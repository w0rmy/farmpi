"""HTTP ingest API used by FarmPi sensor nodes."""

from __future__ import annotations

import asyncio
import os
import secrets
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from .database import DatabaseUnavailable
from .measurements import BY_KEY, MEASUREMENTS
from .sensor_ingest import UnknownSensor, store_sensor_reading

router = APIRouter(prefix="/api", tags=["sensor-ingest"])


class SensorReadingRequest(BaseModel):
    """Complete instantaneous payload submitted by an ESP32 virtual node."""

    sensor: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    soil_moisture_pct: float
    soil_temperature_c: float
    air_temperature_c: float
    relative_humidity_pct: float
    soil_ph: float
    soil_ec_ms_cm: float
    light_lux: float
    rainfall_mm: float
    barometric_pressure_hpa: float
    wind_speed_kmh: float
    wind_direction_deg: float
    pasture_height_cm: float
    leaf_wetness_pct: float
    simulated: bool = True

    @field_validator(*tuple(BY_KEY))
    @classmethod
    def value_in_catalogue_range(cls, value: float, info: Any) -> float:
        item = BY_KEY[info.field_name]
        if not item.minimum <= value <= item.maximum:
            raise ValueError(f"must be between {item.minimum} and {item.maximum}")
        return value


class SensorReadingResponse(BaseModel):
    """Acknowledgement returned after one reading is stored."""

    accepted: bool = True
    reading_id: int
    sensor: str
    paddock: str
    values: dict[str, float]
    simulated: bool
    recorded_at: str


def _require_ingest_token(authorization: str | None) -> None:
    expected = os.getenv("FARMPI_INGEST_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sensor ingest is not configured on this FarmPi.")
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing sensor ingest token.")
    supplied = authorization[len(prefix):].strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sensor ingest token.")


@router.post("/ingest", response_model=SensorReadingResponse, status_code=status.HTTP_201_CREATED)
async def ingest_sensor_reading(request: SensorReadingRequest, authorization: str | None = Header(default=None)) -> SensorReadingResponse:
    """Accept a fully validated, server-timestamped virtual-node sample."""
    _require_ingest_token(authorization)
    try:
        stored = await asyncio.to_thread(
            store_sensor_reading,
            request.sensor,
            request.simulated,
            **{item.key: getattr(request, item.key) for item in MEASUREMENTS},
        )
    except UnknownSensor as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or inactive sensor node.") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The FarmPi database is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SensorReadingResponse(reading_id=stored.reading_id, sensor=stored.sensor_uid, paddock=stored.paddock_name, values=stored.values, simulated=stored.simulated, recorded_at=stored.recorded_at.isoformat())
