"""HTTP ingest API used by FarmPi sensor nodes."""

from __future__ import annotations

import asyncio
import os
import secrets

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from .database import DatabaseUnavailable
from .sensor_ingest import UnknownSensor, store_soil_moisture_reading

router = APIRouter(prefix="/api", tags=["sensor-ingest"])


class SensorReadingRequest(BaseModel):
    """Small prototype payload submitted by an ESP32 sensor node."""

    sensor: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    soil_moisture_pct: float = Field(ge=0.0, le=100.0)
    simulated: bool = True


class SensorReadingResponse(BaseModel):
    """Acknowledgement returned after one reading is stored."""

    accepted: bool = True
    reading_id: int
    sensor: str
    paddock: str
    soil_moisture_pct: float
    simulated: bool
    recorded_at: str


def _require_ingest_token(authorization: str | None) -> None:
    """Apply deliberately lightweight bearer-token auth for the alpha test path."""
    expected = os.getenv("FARMPI_INGEST_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sensor ingest is not configured on this FarmPi.",
        )

    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing sensor ingest token.",
        )

    supplied = authorization[len(prefix) :].strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sensor ingest token.",
        )


@router.post(
    "/ingest",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_sensor_reading(
    request: SensorReadingRequest,
    authorization: str | None = Header(default=None),
) -> SensorReadingResponse:
    """Accept one validated sensor reading and store it in MariaDB."""
    _require_ingest_token(authorization)

    try:
        stored = await asyncio.to_thread(
            store_soil_moisture_reading,
            request.sensor,
            request.soil_moisture_pct,
            request.simulated,
        )
    except UnknownSensor as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown or inactive sensor node.",
        ) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The FarmPi database is unavailable.",
        ) from exc

    return SensorReadingResponse(
        reading_id=stored.reading_id,
        sensor=stored.sensor_uid,
        paddock=stored.paddock_name,
        soil_moisture_pct=stored.soil_moisture_pct,
        simulated=stored.simulated,
        recorded_at=stored.recorded_at.isoformat(),
    )
