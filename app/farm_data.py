"""Deterministic FarmPi data and small, bounded historical analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean

from .database import fetch_all
from .measurements import AVERAGE, BY_KEY, CHANGE, CURRENT, DAYLIGHT, MAXIMUM, MINIMUM, RANKING, SUM, MEASUREMENTS, format_measurement, measurement


class NoFarmData(RuntimeError):
    """Raised when a deterministic farm result cannot be produced."""


@dataclass(frozen=True)
class PaddockEnvironment:
    """Latest complete reading for one paddock, always linked by numeric IDs."""

    id: int
    name: str
    values: dict[str, float]
    recorded_at: datetime
    sensor_count: int
    contains_simulated: bool

    def __getattr__(self, key: str) -> float:
        if key in BY_KEY:
            return self.values[key]
        raise AttributeError(key)


@dataclass(frozen=True)
class GroundingData:
    """Structured facts that the LLM may phrase but never calculate."""

    intent: str
    facts: tuple[str, ...]


_SELECT_VALUES = ",\n    ".join(
    f"ROUND(AVG(r.{item.key}), {item.decimal_places}) AS {item.key}" for item in MEASUREMENTS
)
_COMPLETE_PREDICATE = "\n          AND ".join(f"r2.{item.key} IS NOT NULL" for item in MEASUREMENTS)
LATEST_PADDOCK_ENVIRONMENT_SQL = f"""
SELECT
    p.id,
    p.name,
    {_SELECT_VALUES},
    MAX(r.recorded_at) AS recorded_at,
    COUNT(*) AS sensor_count,
    MAX(CASE WHEN r.simulated = 1 THEN 1 ELSE 0 END) AS contains_simulated
FROM paddocks AS p
JOIN sensor_nodes AS s ON s.paddock_id = p.id AND s.active = 1
JOIN readings AS r ON r.id = (
    SELECT r2.id FROM readings AS r2
    WHERE r2.sensor_node_id = s.id
          AND {_COMPLETE_PREDICATE}
    ORDER BY r2.recorded_at DESC, r2.id DESC LIMIT 1
)
WHERE p.active = 1
GROUP BY p.id, p.name
ORDER BY p.name
"""


def get_environment_snapshot() -> list[PaddockEnvironment]:
    """Return the latest complete row for each active paddock."""
    snapshot: list[PaddockEnvironment] = []
    for row in fetch_all(LATEST_PADDOCK_ENVIRONMENT_SQL):
        recorded_at = row["recorded_at"]
        if not isinstance(recorded_at, datetime):
            raise NoFarmData("A current reading has an invalid timestamp.")
        snapshot.append(PaddockEnvironment(
            id=int(row["id"]),
            name=str(row["name"]),
            values={item.key: float(row[item.key]) for item in MEASUREMENTS},
            recorded_at=recorded_at,
            sensor_count=int(row["sensor_count"]),
            contains_simulated=bool(row["contains_simulated"]),
        ))
    if not snapshot:
        raise NoFarmData("No current complete farm readings are available.")
    return snapshot


def get_moisture_snapshot() -> list[PaddockEnvironment]:
    """Compatibility helper for the original soil-moisture path."""
    return get_environment_snapshot()


def resolve_paddock(name: str, snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment | None:
    """Resolve a user phrase against current database names, case-insensitively."""
    wanted = " ".join(name.split()).casefold()
    for item in snapshot if snapshot is not None else get_environment_snapshot():
        if item.name.casefold() == wanted:
            return item
    return None


def get_paddock_environment(paddock_name: str, snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment | None:
    return resolve_paddock(paddock_name, snapshot)


def get_paddock_moisture(paddock_name: str, snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment | None:
    return resolve_paddock(paddock_name, snapshot)


def get_driest_paddock(snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment:
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return min(values, key=lambda item: item.soil_moisture_pct)


def get_wettest_paddock(snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment:
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return max(values, key=lambda item: item.soil_moisture_pct)


def get_average_soil_moisture(snapshot: list[PaddockEnvironment] | None = None) -> float:
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return round(fmean(item.soil_moisture_pct for item in values), 2)


def _provenance_fact(items: list[PaddockEnvironment]) -> str:
    return "The result includes simulated test readings." if any(item.contains_simulated for item in items) else "The result uses non-simulated sensor readings."


def _measurement_fact(item: PaddockEnvironment, key: str) -> str:
    return f"{item.name} {measurement(key).label}: {format_measurement(item.values[key], key)}."


def _current_ranking(key: str, highest: bool) -> GroundingData:
    items = get_environment_snapshot()
    winner = max(items, key=lambda item: item.values[key]) if highest else min(items, key=lambda item: item.values[key])
    direction = "Highest" if highest else "Lowest"
    return GroundingData("ranking", (f"{direction} {measurement(key).label}: {winner.name}.", _measurement_fact(winner, key), _provenance_fact([winner])))


def _historical_rows(key: str, minutes: int, paddock_name: str | None) -> tuple[list[dict[str, object]], str | None]:
    """Read a bounded historical window; key is catalogue-validated before SQL."""
    if key not in BY_KEY:
        raise ValueError("Unknown measurement.")
    params: list[object] = [minutes]
    where = ["r.recorded_at >= UTC_TIMESTAMP() - INTERVAL %s MINUTE", f"r.{key} IS NOT NULL"]
    resolved_name = None
    if paddock_name:
        target = resolve_paddock(paddock_name)
        if target is None:
            return [], None
        where.append("p.id = %s")
        params.append(target.id)
        resolved_name = target.name
    sql = f"""
SELECT p.name, r.{key} AS value, r.recorded_at, r.simulated
FROM readings AS r
JOIN sensor_nodes AS s ON s.id = r.sensor_node_id
JOIN paddocks AS p ON p.id = s.paddock_id
WHERE {" AND ".join(where)}
ORDER BY r.recorded_at ASC, r.id ASC
"""
    return fetch_all(sql, tuple(params)), resolved_name


def historical_grounding(key: str, operation: str, minutes: int, paddock_name: str | None = None) -> GroundingData:
    """Calculate a small approved historical result without delegating math to Qwen."""
    item = measurement(key)
    rows, resolved_name = _historical_rows(key, minutes, paddock_name)
    if not rows:
        scope = resolved_name or paddock_name or "the requested period"
        return GroundingData("historical", (f"No verified {item.label} history is available for {scope}.",))
    values = [float(row["value"]) for row in rows]
    scope = resolved_name or "the farm"
    window = f"the last {minutes} minutes"
    if operation == SUM:
        value, description = sum(values), "total"
    elif operation == AVERAGE:
        value, description = fmean(values), "average"
    elif operation == MINIMUM:
        value, description = min(values), "minimum"
    elif operation == MAXIMUM:
        value, description = max(values), "maximum"
    elif operation == CHANGE:
        value, description = values[-1] - values[0], "change"
    elif operation == DAYLIGHT:
        # A five-minute sample at or above 1,000 lux counts as daylight. The
        # virtual nodes are intentionally sampled every five minutes; this is a
        # documented derived metric, not an ingested value or LLM estimate.
        daylight_hours = sum(1 for value in values if value >= 1000) * 5 / 60
        return GroundingData("historical", (f"Derived daylight for {scope} over {window}: {daylight_hours:.2f} hours (light ≥ 1,000 lux; 5-minute samples).", "The result is deterministically derived from historical light readings."))
    else:
        return GroundingData("unsupported", ("The requested information is unavailable.",))
    prefix = f"{scope} {description} {item.label} over {window}"
    if operation == CHANGE:
        return GroundingData("historical", (f"{prefix}: {format_measurement(value, key)} (last minus first sample).",))
    return GroundingData("historical", (f"{prefix}: {format_measurement(value, key)}.",))


def get_grounding_data(intent: str, paddock_name: str | None = None, measurement_key: str | None = None, operation: str | None = None, window_minutes: int | None = None) -> GroundingData:
    """Return precisely the deterministic facts approved by a router route."""
    if intent == "unsupported":
        return GroundingData(intent, (
            "The requested information is unavailable.",
            "FarmPi provides measured current values and limited deterministic historical summaries only; it does not provide forecasts, irrigation advice, agronomic causes, or recommendations.",
        ))
    if intent == "help":
        return GroundingData(intent, (
            "FarmPi can report current moisture, soil/air temperature, humidity, pH, EC, light, rainfall, pressure, wind, pasture height, and leaf wetness.",
            "Try: Which paddock is tallest?; What is the soil EC in Paddock C?; How much rainfall was there over the last 24 hours?; What is the pasture height change in Paddock A over the last day?",
            "It can rename a paddock only after an explicit confirmation. FarmPi does not currently provide forecasts, irrigation advice, or agronomic recommendations.",
        ))
    if intent == "driest":
        item = get_driest_paddock()
        return GroundingData(intent, (f"Driest paddock: {item.name}.", f"Soil moisture: {format_measurement(item.soil_moisture_pct, 'soil_moisture_pct')}.", _provenance_fact([item])))
    if intent == "wettest":
        item = get_wettest_paddock()
        return GroundingData(intent, (f"Wettest paddock: {item.name}.", f"Soil moisture: {format_measurement(item.soil_moisture_pct, 'soil_moisture_pct')}.", _provenance_fact([item])))
    if intent == "average":
        snapshot = get_moisture_snapshot()
        return GroundingData(intent, (f"Farm average soil moisture: {format_measurement(get_average_soil_moisture(snapshot), 'soil_moisture_pct')}.", _provenance_fact(snapshot)))
    if intent == "ranking" and measurement_key and operation in {"highest", "lowest"}:
        return _current_ranking(measurement_key, operation == "highest")
    if intent == "historical" and measurement_key and operation and window_minutes:
        return historical_grounding(measurement_key, operation, window_minutes, paddock_name)
    if intent in {"paddock", "paddock-field"}:
        if not paddock_name:
            return GroundingData(intent, ("The requested paddock was not identified.",))
        item = resolve_paddock(paddock_name)
        if item is None:
            return GroundingData(intent, (f"No verified current reading is available for {paddock_name}.",))
        key = measurement_key or "soil_moisture_pct"
        if key not in BY_KEY or CURRENT not in BY_KEY[key].operations:
            return GroundingData("unsupported", ("The requested information is unavailable.",))
        return GroundingData(intent, (_measurement_fact(item, key), f"Reading time: {item.recorded_at.isoformat(sep=' ')} UTC.", _provenance_fact([item])))
    if intent == "measurement-fallback" and measurement_key in BY_KEY:
        snapshot = get_environment_snapshot()
        return GroundingData(intent, (*(_measurement_fact(item, measurement_key) for item in snapshot), _provenance_fact(snapshot)))
    snapshot = get_moisture_snapshot()
    driest, wettest = get_driest_paddock(snapshot), get_wettest_paddock(snapshot)
    facts = [*(f"{item.name} soil moisture: {format_measurement(item.soil_moisture_pct, 'soil_moisture_pct')}." for item in snapshot), f"Farm average soil moisture: {format_measurement(get_average_soil_moisture(snapshot), 'soil_moisture_pct')}.", f"Driest paddock: {driest.name} at {format_measurement(driest.soil_moisture_pct, 'soil_moisture_pct')}.", f"Wettest paddock: {wettest.name} at {format_measurement(wettest.soil_moisture_pct, 'soil_moisture_pct')}.", _provenance_fact(snapshot)]
    return GroundingData("moisture-fallback", tuple(facts))


def format_grounding_context(grounding: GroundingData) -> str:
    return "\n".join(["VERIFIED FACTS", *(f"- {fact}" for fact in grounding.facts)])


def build_verified_moisture_context() -> str:
    return format_grounding_context(get_grounding_data("moisture-fallback"))
