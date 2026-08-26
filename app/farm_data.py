"""Deterministic farm-data functions backed by MariaDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean

from .database import fetch_all


class NoFarmData(RuntimeError):
    """Raised when a deterministic farm result cannot be produced."""


@dataclass(frozen=True)
class PaddockEnvironment:
    """Current deterministic environmental values for one paddock."""

    name: str
    soil_moisture_pct: float
    air_temperature_c: float
    relative_humidity_pct: float
    soil_ph: float
    light_lux: float
    recorded_at: datetime
    sensor_count: int
    contains_simulated: bool


@dataclass(frozen=True)
class GroundingData:
    """Structured deterministic facts to expose to the language model."""

    intent: str
    facts: tuple[str, ...]


LATEST_PADDOCK_ENVIRONMENT_SQL = """
SELECT
    p.name,
    ROUND(AVG(r.soil_moisture_pct), 2) AS soil_moisture_pct,
    ROUND(AVG(r.air_temperature_c), 2) AS air_temperature_c,
    ROUND(AVG(r.relative_humidity_pct), 2) AS relative_humidity_pct,
    ROUND(AVG(r.soil_ph), 2) AS soil_ph,
    ROUND(AVG(r.light_lux), 2) AS light_lux,
    MAX(r.recorded_at) AS recorded_at,
    COUNT(*) AS sensor_count,
    MAX(CASE WHEN r.simulated = 1 THEN 1 ELSE 0 END) AS contains_simulated
FROM paddocks AS p
JOIN sensor_nodes AS s
    ON s.paddock_id = p.id
   AND s.active = 1
JOIN readings AS r
    ON r.id = (
        SELECT r2.id
        FROM readings AS r2
        WHERE r2.sensor_node_id = s.id
          AND r2.soil_moisture_pct IS NOT NULL
          AND r2.air_temperature_c IS NOT NULL
          AND r2.relative_humidity_pct IS NOT NULL
          AND r2.soil_ph IS NOT NULL
          AND r2.light_lux IS NOT NULL
        ORDER BY r2.recorded_at DESC, r2.id DESC
        LIMIT 1
    )
WHERE p.active = 1
GROUP BY p.id, p.name
ORDER BY p.name
"""


def get_environment_snapshot() -> list[PaddockEnvironment]:
    """Return the latest complete environmental reading for each active paddock."""
    rows = fetch_all(LATEST_PADDOCK_ENVIRONMENT_SQL)

    snapshot: list[PaddockEnvironment] = []
    for row in rows:
        recorded_at = row["recorded_at"]
        if not isinstance(recorded_at, datetime):
            raise NoFarmData("A moisture reading has an invalid timestamp.")

        snapshot.append(
            PaddockEnvironment(
                name=str(row["name"]),
                soil_moisture_pct=float(row["soil_moisture_pct"]),
                air_temperature_c=float(row["air_temperature_c"]),
                relative_humidity_pct=float(row["relative_humidity_pct"]),
                soil_ph=float(row["soil_ph"]),
                light_lux=float(row["light_lux"]),
                recorded_at=recorded_at,
                sensor_count=int(row["sensor_count"]),
                contains_simulated=bool(row["contains_simulated"]),
            )
        )

    if not snapshot:
        raise NoFarmData("No current complete environmental readings are available.")

    return snapshot


def get_moisture_snapshot() -> list[PaddockEnvironment]:
    """Return the environmental snapshot used by the moisture operations."""
    return get_environment_snapshot()


def get_driest_paddock(
    snapshot: list[PaddockEnvironment] | None = None,
) -> PaddockEnvironment:
    """Return the paddock with the lowest current soil-moisture value."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return min(values, key=lambda item: item.soil_moisture_pct)


def get_wettest_paddock(
    snapshot: list[PaddockEnvironment] | None = None,
) -> PaddockEnvironment:
    """Return the paddock with the highest current soil-moisture value."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return max(values, key=lambda item: item.soil_moisture_pct)


def get_average_soil_moisture(
    snapshot: list[PaddockEnvironment] | None = None,
) -> float:
    """Return the mean of the current paddock soil-moisture values."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return round(fmean(item.soil_moisture_pct for item in values), 2)


def get_paddock_environment(
    paddock_name: str,
    snapshot: list[PaddockEnvironment] | None = None,
) -> PaddockEnvironment | None:
    """Return the current environmental reading for one named paddock, if present."""
    values = snapshot if snapshot is not None else get_environment_snapshot()
    wanted = paddock_name.casefold()
    for item in values:
        if item.name.casefold() == wanted:
            return item
    return None


def get_paddock_moisture(
    paddock_name: str,
    snapshot: list[PaddockEnvironment] | None = None,
) -> PaddockEnvironment | None:
    """Compatibility helper for the existing soil-moisture query path."""
    return get_paddock_environment(paddock_name, snapshot)


def _provenance_fact(items: list[PaddockEnvironment]) -> str:
    if any(item.contains_simulated for item in items):
        return "The result includes simulated test readings."
    return "The result uses non-simulated sensor readings."


MEASUREMENT_DETAILS = {
    "soil_moisture_pct": ("soil moisture", "%", 2),
    "air_temperature_c": ("air temperature", "°C", 2),
    "relative_humidity_pct": ("relative humidity", "%", 2),
    "soil_ph": ("soil pH", "", 2),
    "light_lux": ("light", "lux", 0),
}


def _measurement_fact(item: PaddockEnvironment, measurement: str) -> str:
    """Format one already-retrieved instantaneous measurement as a fact."""
    label, unit, places = MEASUREMENT_DETAILS[measurement]
    value = getattr(item, measurement)
    suffix = unit if unit == "%" else f" {unit}" if unit else ""
    return f"{item.name} {label}: {value:.{places}f}{suffix}."


def get_grounding_data(
    intent: str,
    paddock_name: str | None = None,
    measurement: str | None = None,
) -> GroundingData:
    """Return only the deterministic facts needed for the selected question route."""
    if intent == "unsupported":
        return GroundingData(
            intent=intent,
            facts=(
                "The requested information is unavailable.",
                "FarmPi supports current soil moisture, air temperature, relative humidity, soil pH, and light readings only.",
                "Daylight hours are not directly ingested; they should later be derived deterministically from historical light readings.",
            ),
        )

    if intent == "driest":
        item = get_driest_paddock()
        return GroundingData(
            intent=intent,
            facts=(
                f"Driest paddock: {item.name}.",
                f"Soil moisture: {item.soil_moisture_pct:.2f}%.",
                _provenance_fact([item]),
            ),
        )

    if intent == "wettest":
        item = get_wettest_paddock()
        return GroundingData(
            intent=intent,
            facts=(
                f"Wettest paddock: {item.name}.",
                f"Soil moisture: {item.soil_moisture_pct:.2f}%.",
                _provenance_fact([item]),
            ),
        )

    if intent == "average":
        snapshot = get_moisture_snapshot()
        average = get_average_soil_moisture(snapshot)
        return GroundingData(
            intent=intent,
            facts=(
                f"Farm average soil moisture: {average:.2f}%.",
                _provenance_fact(snapshot),
            ),
        )

    if intent in {"paddock", "paddock-field"}:
        if not paddock_name:
            return GroundingData(
                intent=intent,
                facts=("The requested paddock was not identified.",),
            )

        snapshot = get_environment_snapshot()
        item = get_paddock_environment(paddock_name, snapshot)
        if item is None:
            return GroundingData(
                intent=intent,
                facts=(f"No verified environmental reading is available for {paddock_name}.",),
            )

        selected_measurement = measurement if intent == "paddock-field" else "soil_moisture_pct"
        if selected_measurement not in MEASUREMENT_DETAILS:
            return GroundingData(
                intent="unsupported",
                facts=("The requested information is unavailable.",),
            )

        return GroundingData(
            intent=intent,
            facts=(
                _measurement_fact(item, selected_measurement),
                f"Reading time: {item.recorded_at.isoformat(sep=' ')} UTC.",
                _provenance_fact([item]),
            ),
        )

    if intent == "measurement-fallback":
        if measurement not in MEASUREMENT_DETAILS:
            return GroundingData(
                intent="unsupported",
                facts=("The requested information is unavailable.",),
            )
        snapshot = get_environment_snapshot()
        return GroundingData(
            intent=intent,
            facts=(
                *(_measurement_fact(item, measurement) for item in snapshot),
                _provenance_fact(snapshot),
            ),
        )

    # Fallback keeps the broad soil-moisture capability for questions that the
    # small deterministic router does not yet classify more narrowly.
    snapshot = get_moisture_snapshot()
    driest = get_driest_paddock(snapshot)
    wettest = get_wettest_paddock(snapshot)
    average = get_average_soil_moisture(snapshot)

    facts = [
        *(f"{item.name} soil moisture: {item.soil_moisture_pct:.2f}%." for item in snapshot),
        f"Farm average soil moisture: {average:.2f}%.",
        f"Driest paddock: {driest.name} at {driest.soil_moisture_pct:.2f}%.",
        f"Wettest paddock: {wettest.name} at {wettest.soil_moisture_pct:.2f}%.",
        _provenance_fact(snapshot),
    ]
    return GroundingData(intent="moisture-fallback", facts=tuple(facts))


def format_grounding_context(grounding: GroundingData) -> str:
    """Format structured deterministic facts into compact LLM context."""
    lines = ["VERIFIED FACTS"]
    lines.extend(f"- {fact}" for fact in grounding.facts)
    return "\n".join(lines)


def build_verified_moisture_context() -> str:
    """Build the complete deterministic moisture context for diagnostics/fallback use."""
    return format_grounding_context(get_grounding_data("moisture-fallback"))
