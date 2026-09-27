"""Structured monitoring data for the native FarmPi dashboard.

This endpoint is deliberately deterministic. It exposes current validated
database state and application-generated chart data without routing through the
language model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean

from fastapi import APIRouter, HTTPException, Query

from .analytics import compare_paddocks
from .farm_data import NoFarmData, analytics_grounding, get_environment_snapshot, historical_rows_from, time_window_start
from .measurements import AVERAGE, BY_KEY, MEASUREMENTS, STANDARD_NODE_MEASUREMENTS, TREND, format_measurement
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
        oldest_received = min(environment.received_at for environment in contributors)
        oldest_observed = min(environment.observed_at for environment in contributors)
        simulated = any(environment.measurement_modes.get(item.key) == "SIMULATED" for environment in contributors)
        payload = _measurement_payload(
            item.key,
            value,
            "SIMULATED" if simulated else "LIVE",
            oldest_observed,
            oldest_received,
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


@router.get("/compare")
def monitoring_compare(
    left_id: int = Query(gt=0),
    right_id: int = Query(gt=0),
    measurement: str = Query(min_length=1, max_length=64),
    window_minutes: int = Query(default=1440, ge=5, le=10080),
) -> dict[str, object]:
    """Compare two explicitly selected configured locations without invoking the LLM."""
    if left_id == right_id:
        raise HTTPException(status_code=422, detail="Choose two different FarmPi locations.")
    if measurement not in BY_KEY:
        raise HTTPException(status_code=422, detail="Unknown FarmPi measurement.")

    identities = {item.id: item for item in active_paddocks()}
    left = identities.get(left_id)
    right = identities.get(right_id)
    if left is None or right is None:
        raise HTTPException(status_code=404, detail="One or both selected FarmPi locations are not active.")

    start, period = time_window_start(window_minutes, None)
    rows: list[dict[str, object]] = []
    for identity in (left, right):
        location_rows, _ = historical_rows_from(measurement, start, identity.name)
        rows.extend(location_rows)

    result = compare_paddocks(measurement, AVERAGE, rows, period)
    evidence = [
        {
            "paddock": item.paddock,
            "sensor": item.sensor,
            "timestamp": item.timestamp,
            "value": item.value,
            "simulated": item.simulated,
        }
        for item in result.evidence
    ]
    answer = "\n".join(result.facts)
    return {
        "answer": answer,
        "spoken_answer": answer,
        "suggestions": [],
        "intent": "comparison",
        "conversation_id": None,
        "chart": result.chart,
        "evidence": evidence,
        "provenance": [
            {"kind": "farm-observation", "source": "FarmPi validated telemetry / MariaDB"},
            {"kind": "deterministic-calculation", "source": "FarmPi application layer"},
        ],
        "source_tier": "first-class-trusted",
        "source_category": "calculated",
        "left_location": {"id": left.id, "name": left.name},
        "right_location": {"id": right.id, "name": right.name},
        "measurement": measurement,
        "window_minutes": window_minutes,
    }
