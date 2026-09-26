"""HTTP ingest API used by FarmPi sensor nodes."""

from __future__ import annotations

import asyncio
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .database import DatabaseUnavailable
from .measurements import BY_KEY, MEASUREMENTS
from .sensor_ingest import UnknownSensor, store_sensor_reading

router = APIRouter(prefix="/api", tags=["sensor-ingest"])


class SensorReadingRequest(BaseModel):
    """One instantaneous sample from a standard or expanded FarmPi node."""

    model_config = ConfigDict(extra="forbid", strict=True)

    hardware_uid: str | None = Field(default=None, pattern=r"^[0-9a-f]{12}$")
    device_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    applied_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    location_epoch: int | None = Field(default=None, ge=0)

    sensor: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")

    # All measurements are sparse; catalogue membership does not imply fitted.
    soil_moisture_pct: float | None = None
    soil_temperature_c: float | None = None
    air_temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    light_lux: float | None = None
    barometric_pressure_hpa: float | None = None

    # Add-on measurements are optional capabilities. Omission means the node
    # does not currently report that measurement; FarmPi never fabricates it.
    soil_ph: float | None = None
    soil_ec_ms_cm: float | None = None
    rainfall_mm: float | None = None
    wind_speed_kmh: float | None = None
    wind_direction_deg: float | None = None
    pasture_height_cm: float | None = None
    leaf_wetness_pct: float | None = None

    simulated: bool = True
    # Version 1 is deliberately transport-neutral so its semantics can be
    # carried in a future LoRa acknowledgement unchanged.
    protocol_version: int = Field(default=1, ge=1, le=1)
    device_time_unix: int | None = Field(default=None, ge=0)
    clock_valid: bool = False
    sample_seq: int | None = Field(default=None, ge=0, le=18446744073709551615)

    @model_validator(mode="after")
    def sparse_sample(self):
        supplied = self.model_fields_set & set(BY_KEY)
        if not supplied or any(getattr(self, key) is None for key in supplied):
            raise ValueError("Supply at least one measurement; omit absent measurements instead of null.")
        if self.hardware_uid and not self.device_key:
            raise ValueError("Device credential required.")
        return self

    @field_validator(*tuple(BY_KEY))
    @classmethod
    def value_in_catalogue_range(cls, value: float | None, info: Any) -> float | None:
        if value is None:
            return None
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
    observed_at: str
    received_at: str
    recorded_at: str
    clock_valid: bool
    clock_offset_seconds: float | None
    clock_out_of_tolerance: bool
    sample_seq: int | None
    deduplicated: bool = False
    time_sync_required: bool
    server_time: int


TIME_SYNC_THRESHOLD_SECONDS = 30


def _device_observation(request: SensorReadingRequest, received_at: datetime) -> tuple[datetime | None, bool, float | None, bool]:
    """Translate the transport-neutral node clock fields into UTC semantics."""
    if not request.clock_valid or request.device_time_unix is None or request.device_time_unix <= 0:
        return None, False, None, True
    try:
        observed_at = datetime.fromtimestamp(request.device_time_unix, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None, False, None, True
    offset = received_at.timestamp() - request.device_time_unix
    out_of_tolerance = abs(offset) > TIME_SYNC_THRESHOLD_SECONDS
    return observed_at, True, offset, out_of_tolerance


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
    """Accept a validated standard-node sample plus any installed add-ons."""
    if not request.hardware_uid:
        _require_ingest_token(authorization)
        if not request.simulated:
            raise HTTPException(422, "Physical telemetry requires registered hardware identity and device credentials.")
    received_at = datetime.now(timezone.utc)
    observed_at, clock_valid, clock_offset_seconds, clock_out_of_tolerance = _device_observation(request, received_at)
    supplied_values = {
        item.key: getattr(request, item.key)
        for item in MEASUREMENTS
        if getattr(request, item.key) is not None
    }
    try:
        if request.hardware_uid:
            from .managed_ingest import store_managed
            stored = await asyncio.to_thread(store_managed, request, received_at, observed_at, clock_valid, clock_offset_seconds, clock_out_of_tolerance)
        else:
            stored = await asyncio.to_thread(
                store_sensor_reading,
                request.sensor,
                request.simulated,
                observed_at=observed_at,
                received_at=received_at,
                clock_valid=clock_valid,
                clock_offset_seconds=clock_offset_seconds,
                clock_out_of_tolerance=clock_out_of_tolerance,
                sample_seq=request.sample_seq,
                protocol_version=request.protocol_version,
                **supplied_values,
            )
    except UnknownSensor as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or inactive sensor node.") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The FarmPi database is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SensorReadingResponse(
        reading_id=stored.reading_id, sensor=stored.sensor_uid, paddock=stored.paddock_name,
        values=stored.values, simulated=stored.simulated, observed_at=stored.observed_at.isoformat(),
        received_at=stored.received_at.isoformat(), recorded_at=stored.recorded_at.isoformat(),
        clock_valid=stored.clock_valid, clock_offset_seconds=stored.clock_offset_seconds,
        clock_out_of_tolerance=stored.clock_out_of_tolerance, sample_seq=stored.sample_seq,
        deduplicated=stored.deduplicated, time_sync_required=clock_out_of_tolerance,
        server_time=int(received_at.timestamp()),
    )
