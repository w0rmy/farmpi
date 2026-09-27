"""Structured monitoring data for the native FarmPi dashboard.

This endpoint is deliberately deterministic. It exposes current validated
database state and application-generated chart data without routing through the
language model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean

from fastapi import APIRouter

from .farm_data import NoFarmData, analytics_grounding, get_environment_snapshot
from .measurements import MEASUREMENTS, STANDARD_NODE_MEASUREMENTS, TREND, format_measurement
from .paddock_resolver import active_paddocks

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _age_seconds(value: datetime, now: datetime) -> int:
    return max(0, int((now - _utc(value).astimezone(timezone.utc)).total_seconds()))


def _measurement_payload(key: str, value: float, mode: str | None, observed_at: datetime, received_at: datetime, now: datetime) -> dict[str, object]:
    item = next(measurement for measurement in MEASUREMENTS if measurement.key == key)
    return {
        "key": item.key,
        "label": item.label,
        "unit": item.unit,
        "value": float(value),
        "display_value": format_measurement(value, key),
        "source_mode": mode,
        "observed_at": _utc(observed_at).isoformat(),
        "received_at": _utc(received_at).isoformat(),
        "age_seconds": _age_seconds(received_at, now),
    }


def build_monitoring_overview(now: datetime | None = None) -> dict[str, object]:
    """Build current dashboard state without invoking the LLM."""
    current_time = _utc(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    identities = active_paddocks()

    try:
        snapshot = get_environment_snapshot()
    except NoFarmData:
        snapshot = []

    environments = {item.id: item for item in snapshot}
    locations: list[dict[str, object]] = []
    for identity in identities:
        environment = environments.get(identity.id)
        measurements: list[dict[str, object]] = []
        if environment is not None:
            measurements = [
                _measurement_payload(
                    item.key,
                    environment.values[item.key],
                    environment.measurement_modes.get(item.key),
                    environment.observed_at,
                    environment.received_at,
                    current_time,
                )
                for item in MEASUREMENTS
                if item.key in environment.values
            ]

        locations.append({
            "id": identity.id,
            "name": identity.name,
            "active_sensor_count": identity.active_sensor_count,
            "has_reading": environment is not None,
            "observed_at": _utc(environment.observed_at).isoformat() if environment else None,
            "received_at": _utc(environment.received_at).isoformat() if environment else None,
            "age_seconds": _age_seconds(environment.received_at, current_time) if environment else None,
            "contains_simulated": environment.contains_simulated if environment else False,
            "measurements": measurements,
        })

    farm_measurements: list[dict[str, object]] = []
    for item in STANDARD_NODE_MEASUREMENTS:
        contributors = [environment for environment in snapshot if item.key in environment.values]
        if not contributors:
            continue
        value = fmean(environment.values[item.key] for environment in contributors)
        latest_received = max(environment.received_at for environment in contributors)
        latest_observed = max(environment.observed_at for environment in contributors)
        simulated = any(environment.measurement_modes.get(item.key) == "SIMULATED" for environment in contributors)
        payload = _measurement_payload(
            item.key,
            value,
            "SIMULATED" if simulated else "LIVE",
            latest_observed,
            latest_received,
            current_time,
        )
        payload["contributing_locations"] = len(contributors)
        farm_measurements.append(payload)

    featured_chart = None
    try:
        featured_chart = analytics_grounding(
            "soil_moisture_pct",
            TREND,
            24 * 60,
            None,
            None,
        ).chart
    except NoFarmData:
        featured_chart = None

    return {
        "generated_at": current_time.isoformat(),
        "location_count": len(identities),
        "locations_with_readings_count": len(snapshot),
        "farm_measurements": farm_measurements,
        "locations": locations,
        "featured_chart": featured_chart,
    }


@router.get("/overview")
def monitoring_overview() -> dict[str, object]:
    return build_monitoring_overview()
