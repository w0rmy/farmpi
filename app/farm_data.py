"""Deterministic FarmPi data and small, bounded historical analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import fmean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .database import fetch_all, fetch_one
from .analytics import AnalyticsResult, comparison_chart, compare_paddocks, historical_analysis
from .measurements import AVERAGE, BY_KEY, CHANGE, CURRENT, DAYLIGHT, MAXIMUM, MINIMUM, RANKING, SUM, MEASUREMENTS, format_measurement, measurement
from .paddock_resolver import PaddockIdentity, PaddockResolution, active_paddocks, resolve_paddock as resolve_paddock_identity
from .education import irrigation_decision_material


class NoFarmData(RuntimeError):
    """Raised when a deterministic farm result cannot be produced."""


@dataclass(frozen=True)
class PaddockEnvironment:
    """Latest complete reading for one paddock, always linked by numeric IDs."""

    id: int
    name: str
    values: dict[str, float]
    received_at: datetime
    observed_at: datetime
    sensor_count: int
    contains_simulated: bool

    def __getattr__(self, key: str) -> float:
        if key in BY_KEY:
            return self.values[key]
        raise AttributeError(key)

    @property
    def recorded_at(self) -> datetime:
        """Compatibility alias; current/freshness uses received_at."""
        return self.received_at


@dataclass(frozen=True)
class GroundingData:
    """Structured facts that the LLM may phrase but never calculate."""

    intent: str
    facts: tuple[str, ...]
    evidence: tuple[dict[str, object], ...] = ()
    chart: dict[str, object] | None = None
    source_category: str = "observational"
    spoken_facts: tuple[str, ...] = ()


_SELECT_VALUES = ",\n    ".join(
    f"ROUND(AVG(r.{item.key}), {item.decimal_places}) AS {item.key}" for item in MEASUREMENTS
)
_COMPLETE_PREDICATE = "\n          AND ".join(f"r2.{item.key} IS NOT NULL" for item in MEASUREMENTS)
LATEST_PADDOCK_ENVIRONMENT_SQL = f"""
SELECT
    p.id,
    p.name,
    {_SELECT_VALUES},
    MAX(r.received_at) AS received_at,
    MAX(r.observed_at) AS observed_at,
    COUNT(*) AS sensor_count,
    MAX(CASE WHEN r.simulated = 1 THEN 1 ELSE 0 END) AS contains_simulated
FROM paddocks AS p
JOIN sensor_nodes AS s ON s.paddock_id = p.id AND s.active = 1
JOIN readings AS r ON r.id = (
    SELECT r2.id FROM readings AS r2
    WHERE r2.sensor_node_id = s.id
          AND {_COMPLETE_PREDICATE}
    ORDER BY r2.received_at DESC, r2.id DESC LIMIT 1
)
WHERE p.active = 1
GROUP BY p.id, p.name
ORDER BY p.id
"""


def get_environment_snapshot() -> list[PaddockEnvironment]:
    """Return the latest complete row for each active paddock."""
    snapshot: list[PaddockEnvironment] = []
    for row in fetch_all(LATEST_PADDOCK_ENVIRONMENT_SQL):
        # The fallback only supports callers/tests against the alpha projection;
        # the schema migration backfills both new columns before deployment.
        received_at = row.get("received_at", row.get("recorded_at"))
        observed_at = row.get("observed_at", received_at)
        if not isinstance(received_at, datetime) or not isinstance(observed_at, datetime):
            raise NoFarmData("A current reading has an invalid timestamp.")
        snapshot.append(PaddockEnvironment(
            id=int(row["id"]),
            name=str(row["name"]),
            values={item.key: float(row[item.key]) for item in MEASUREMENTS},
            received_at=received_at,
            observed_at=observed_at,
            sensor_count=int(row["sensor_count"]),
            contains_simulated=bool(row["contains_simulated"]),
        ))
    if not snapshot:
        raise NoFarmData("No current complete farm readings are available.")
    return snapshot


def get_moisture_snapshot() -> list[PaddockEnvironment]:
    """Compatibility helper for the original soil-moisture path."""
    return get_environment_snapshot()


def _snapshot_identities(snapshot: list[PaddockEnvironment]) -> tuple[PaddockIdentity, ...]:
    return tuple(PaddockIdentity(item.id, item.name, index, item.sensor_count) for index, item in enumerate(snapshot, start=1))


def resolve_paddock_reference(name: str, snapshot: list[PaddockEnvironment] | None = None) -> PaddockResolution:
    """Resolve every web/API client phrase through one canonical resolver."""
    return resolve_paddock_identity(name, _snapshot_identities(snapshot) if snapshot is not None else None)


def resolve_paddock(name: str, snapshot: list[PaddockEnvironment] | None = None) -> PaddockEnvironment | None:
    """Resolve a phrase to its latest reading, retaining its stable paddock ID."""
    readings = snapshot if snapshot is not None else get_environment_snapshot()
    resolution = resolve_paddock_reference(name, readings)
    if resolution.paddock is None:
        return None
    for item in readings:
        if item.id == resolution.paddock.id:
            return item
    return None


def _paddock_resolution_facts(resolution: PaddockResolution) -> tuple[str, ...]:
    if resolution.status == "no-active-paddocks":
        return ("There are no active paddocks configured for monitoring.",)
    suggestions = ", ".join(resolution.suggestions)
    if resolution.status == "paddock-out-of-range":
        count = len(resolution.suggestions)  # only used to select the empty-case message below
        return (f"{resolution.reference} is outside the active configured paddock range. Try one of: {suggestions}." if count else "There are no active paddocks configured for monitoring.",)
    if resolution.status == "ambiguous-paddock":
        return (f"I found more than one possible paddock for “{resolution.reference}”. Please choose one of: {suggestions}." if suggestions else f"I could not uniquely identify “{resolution.reference}”.",)
    if resolution.status == "did-you-mean":
        candidate = resolution.suggestions[0] if resolution.suggestions else None
        return (f"I could not confidently identify “{resolution.reference}”. Did you mean {candidate}?" if candidate else f"I could not confidently identify “{resolution.reference}”.",)
    return (f"I could not identify the paddock “{resolution.reference}”." + (f" Current active paddocks are: {suggestions}. Try, for example, “What is the temperature in {resolution.suggestions[0]}?”." if resolution.suggestions else ""),)


def farm_inventory_count() -> GroundingData:
    """Return active monitored inventory without inferring it from readings."""
    paddocks = active_paddocks()
    total_row = fetch_one("SELECT COUNT(*) AS total_paddocks FROM paddocks") or {"total_paddocks": len(paddocks)}
    total = int(total_row.get("total_paddocks", len(paddocks)))
    sensors = sum(item.active_sensor_count for item in paddocks)
    facts = [f"Active monitored paddocks: {len(paddocks)}.", f"Active sensor nodes: {sensors}."]
    if total != len(paddocks):
        facts.append(f"Total paddock records, including inactive/historical paddocks: {total}.")
    return GroundingData("farm_inventory_count", tuple(facts))


def farm_inventory_list() -> GroundingData:
    """Return deterministic active paddock names without inspecting readings."""
    paddocks = active_paddocks()
    if not paddocks:
        return GroundingData("farm_inventory_list", ("There are no active paddocks configured for monitoring.",))
    names = tuple(item.name for item in paddocks)
    joined = ", ".join(names)
    return GroundingData(
        "farm_inventory_list",
        (f"Active monitored paddocks ({len(names)}): {joined}.",),
        spoken_facts=(f"FarmPi is currently monitoring {len(names)} paddocks: {joined}.",),
    )


def _display_reading_time(received_at: datetime) -> str:
    """Human-friendly freshness for the main screen; evidence keeps UTC exactly."""
    timestamp = received_at if received_at.tzinfo else received_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = max(0, int((datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()))
    if elapsed_seconds < 60:
        return "Updated just now."
    if elapsed_seconds < 3600:
        minutes = elapsed_seconds // 60
        return f"Updated {minutes} minute{'s' if minutes != 1 else ''} ago."
    try:
        local = timestamp.astimezone(ZoneInfo("Pacific/Auckland"))
    except ZoneInfoNotFoundError:
        # Production Pi installations have the IANA zone database.  This
        # fallback keeps an offline Windows/dev environment readable until
        # requirements install `tzdata`; it does not affect evidence UTC.
        local = timestamp.astimezone()
    hour = local.hour % 12 or 12
    meridiem = "am" if local.hour < 12 else "pm"
    return f"Last reading: {hour}:{local.minute:02d} {meridiem} ({local.strftime('%d %b')})."


def _current_evidence(item: PaddockEnvironment) -> tuple[dict[str, object], ...]:
    return ({
        "paddock": item.name,
        "sensor_count": item.sensor_count,
        "observed_at": item.observed_at.isoformat(),
        "received_at": item.received_at.isoformat(),
        "simulated": item.contains_simulated,
        "source_category": "observational",
    },)


def latest_paddock_summary(paddock_name: str | None) -> GroundingData:
    """List the catalogue-backed current measurements for one paddock."""
    if not paddock_name:
        return GroundingData("paddock_summary", ("Please name a paddock, for example Paddock B or Paddock 2.",))
    try:
        snapshot = get_environment_snapshot()
    except NoFarmData:
        snapshot = []
    resolution = resolve_paddock_reference(paddock_name, snapshot if snapshot else None)
    if resolution.paddock is None:
        return GroundingData("paddock_summary", _paddock_resolution_facts(resolution))
    try:
        item = resolve_paddock(paddock_name, snapshot)
    except NoFarmData:
        item = None
    if item is None:
        return GroundingData("paddock_summary", (f"{resolution.paddock.name} is active, but has no current complete sensor reading yet.",))
    facts = [f"{item.name} currently has these monitored measurements:"]
    facts.extend(_measurement_fact(item, field.key) for field in MEASUREMENTS)
    facts.extend((_display_reading_time(item.received_at), f"Active sensor nodes for this paddock: {resolution.paddock.active_sensor_count}.", "Available analytics include current, minimum, maximum, average, range, change, trend, and supported comparisons over a selected time window."))
    spoken = (facts[0], facts[1], facts[2], "The screen shows the remaining current measurements. Ask Show evidence for exact timestamps and provenance.")
    return GroundingData("paddock_summary", tuple(facts), _current_evidence(item), spoken_facts=spoken)


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
    values = dict(sorted(((item.name, item.values[key]) for item in items), key=lambda entry: entry[1], reverse=highest))
    evidence = tuple({"paddock": item.name, "sensor": None, "timestamp": item.received_at.isoformat(), "value": item.values[key], "simulated": item.contains_simulated} for item in items)
    return GroundingData("ranking", (f"{direction} {measurement(key).label}: {winner.name}.", _measurement_fact(winner, key), _provenance_fact([winner])), evidence, comparison_chart(key, values, "current/latest", direction.casefold()))


def _historical_rows(key: str, minutes: int, paddock_name: str | None) -> tuple[list[dict[str, object]], str | None]:
    """Read a bounded historical window; key is catalogue-validated before SQL."""
    if key not in BY_KEY:
        raise ValueError("Unknown measurement.")
    params: list[object] = [minutes]
    analysis_time = "CASE WHEN r.clock_valid = 1 AND r.clock_out_of_tolerance = 0 THEN r.observed_at ELSE r.received_at END"
    where = [f"{analysis_time} >= UTC_TIMESTAMP() - INTERVAL %s MINUTE", f"r.{key} IS NOT NULL"]
    resolved_name = None
    if paddock_name:
        target = resolve_paddock(paddock_name)
        if target is None:
            return [], None
        where.append("p.id = %s")
        params.append(target.id)
        resolved_name = target.name
    sql = f"""
SELECT p.name, r.{key} AS value, {analysis_time} AS analysis_at, r.simulated
FROM readings AS r
JOIN sensor_nodes AS s ON s.id = r.sensor_node_id
JOIN paddocks AS p ON p.id = s.paddock_id
WHERE {" AND ".join(where)}
ORDER BY {analysis_time} ASC, r.id ASC
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


def time_window_start(window_minutes: int | None, window_label: str | None) -> tuple[datetime, str]:
    """Resolve presentation terms to an explicit UTC database boundary.

    ``today`` is a Pacific/Auckland local calendar day; all stored/query times
    remain UTC.  This prevents the old and subtle 'last 24 hours = today' bug.
    """
    now = datetime.now(timezone.utc)
    if window_label == "today":
        local = now.astimezone(ZoneInfo("Pacific/Auckland"))
        return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc), "today (Pacific/Auckland)"
    if window_label == "this morning":
        local = now.astimezone(ZoneInfo("Pacific/Auckland"))
        return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc), "this morning (Pacific/Auckland)"
    minutes = window_minutes or 1440
    return now - timedelta(minutes=minutes), f"the last {minutes} minutes"


def historical_rows_from(key: str, start_at: datetime, paddock_name: str | None = None) -> tuple[list[dict[str, object]], str | None]:
    """Read verified history from an explicit UTC start boundary."""
    if key not in BY_KEY:
        raise ValueError("Unknown measurement.")
    analysis_time = "CASE WHEN r.clock_valid = 1 AND r.clock_out_of_tolerance = 0 THEN r.observed_at ELSE r.received_at END"
    params: list[object] = [start_at.replace(tzinfo=None)]
    where = [f"{analysis_time} >= %s", f"r.{key} IS NOT NULL"]
    resolved_name = None
    if paddock_name:
        target = resolve_paddock(paddock_name)
        if target is None:
            return [], None
        where.append("p.id = %s")
        params.append(target.id)
        resolved_name = target.name
    sql = f"""
SELECT p.name, s.node_uid AS sensor_uid, r.{key} AS value, {analysis_time} AS analysis_at, r.simulated
FROM readings AS r JOIN sensor_nodes AS s ON s.id = r.sensor_node_id JOIN paddocks AS p ON p.id = s.paddock_id
WHERE {" AND ".join(where)} ORDER BY {analysis_time} ASC, r.id ASC
"""
    return fetch_all(sql, tuple(params)), resolved_name


def analytics_grounding(key: str, operation: str, window_minutes: int | None, window_label: str | None, paddock_name: str | None = None, comparison: bool = False) -> GroundingData:
    """Expose expanded analytics as facts plus optional evidence/chart payload."""
    start, period = time_window_start(window_minutes, window_label)
    rows, resolved = historical_rows_from(key, start, None if comparison else paddock_name)
    scope = "all paddocks" if comparison else (resolved or paddock_name or "the farm")
    result: AnalyticsResult = compare_paddocks(key, operation, rows, period) if comparison else historical_analysis(key, operation, rows, period, scope)
    evidence = tuple({"paddock": item.paddock, "sensor": item.sensor, "timestamp": item.timestamp, "value": item.value, "simulated": item.simulated} for item in result.evidence)
    return GroundingData("comparison" if comparison else "historical", result.facts, evidence, result.chart)


def paddock_summary(paddock_name: str | None, window_minutes: int | None, window_label: str | None) -> GroundingData:
    """A compact deterministic learning summary, assembled from real operations."""
    item = resolve_paddock(paddock_name) if paddock_name else None
    if paddock_name and item is None:
        return GroundingData("summary", (f"No verified current reading is available for {paddock_name}.",))
    name = item.name if item else "FarmPi"
    start, period = time_window_start(window_minutes, window_label)
    moisture_rows, _ = historical_rows_from("soil_moisture_pct", start, name if item else None)
    rain_rows, _ = historical_rows_from("rainfall_mm", start, name if item else None)
    moisture = historical_analysis("soil_moisture_pct", "change", moisture_rows, period, name)
    rain = historical_analysis("rainfall_mm", SUM, rain_rows, period, name)
    current = (f"Current soil moisture: {format_measurement(item.soil_moisture_pct, 'soil_moisture_pct')}." if item else "Use a named paddock for a current-value summary.")
    facts = (f"{name} summary for {period}.", current, *moisture.facts[:1], *rain.facts[:1], "Any rainfall/moisture sequence is an association in the selected telemetry, not proof of cause.")
    return GroundingData("summary", facts, moisture.evidence + rain.evidence, moisture.chart)


def irrigation_decision_grounding(paddock_name: str | None, level: str = "normal") -> GroundingData:
    """Explain the irrigation boundary with facts, never make an irrigation decision."""
    facts = list(irrigation_decision_material(level))
    if not paddock_name:
        return GroundingData("irrigation-decision", tuple(facts), source_category="educational")
    try:
        snapshot = get_environment_snapshot()
    except NoFarmData:
        snapshot = []
    resolution = resolve_paddock_reference(paddock_name, snapshot if snapshot else None)
    if resolution.paddock is None:
        return GroundingData("irrigation-decision", _paddock_resolution_facts(resolution), source_category="educational")
    try:
        item = resolve_paddock(paddock_name, snapshot)
    except NoFarmData:
        item = None
    if item is None:
        facts.insert(1, f"{resolution.paddock.name} is active, but has no current complete soil-moisture reading.")
        return GroundingData("irrigation-decision", tuple(facts), source_category="educational")
    facts.insert(1, _measurement_fact(item, "soil_moisture_pct"))
    return GroundingData(
        "irrigation-decision",
        tuple(facts),
        _current_evidence(item),
        source_category="combined",
    )


def get_grounding_data(intent: str, paddock_name: str | None = None, measurement_key: str | None = None, operation: str | None = None, window_minutes: int | None = None) -> GroundingData:
    """Return precisely the deterministic facts approved by a router route."""
    if intent in {"capability", "help"}:
        return GroundingData(intent, (
            "FarmPi can show current verified soil moisture, air temperature, humidity, pH, EC, light, rainfall, pressure, wind, pasture height, and leaf wetness, plus paddock comparisons, bounded history and trends, evidence/graphs, and explanations.",
            "It can also list or count active paddocks; renames require an explicit confirmation.",
            "FarmPi does not currently provide forecasts or irrigation recommendations. Try asking: What is Paddock 2's soil moisture? or How has soil moisture changed over the last 24 hours?",
        ), source_category="educational")
    if intent == "irrigation-decision":
        return irrigation_decision_grounding(paddock_name)
    if intent == "operational-decision":
        return GroundingData(intent, (
            "FarmPi cannot make that farm-operation decision from the information it has.",
            "It can show verified measurements and explain the factors that would normally need to be considered, without presenting a recommendation.",
            "Would you like to inspect a current paddock measurement or a trend?",
        ), source_category="educational")
    if intent == "forecast-boundary":
        return GroundingData(intent, (
            "FarmPi does not provide weather forecasts.",
            "It can show verified rainfall and other recorded measurements, but those readings are not a forecast.",
            "Would you like to inspect recent rainfall instead?",
        ), source_category="educational")
    if intent == "causal-boundary":
        return GroundingData(intent, (
            "FarmPi cannot establish the cause of a condition from its current measurements alone.",
            "It can show verified readings and explain general measurement limits without claiming what caused a change on this farm.",
            "Would you like to inspect a trend or explain the measurement?",
        ), source_category="educational")
    if intent == "interpretation-boundary":
        return GroundingData(intent, (
            "FarmPi understood the measurement, but that calculation or interpretation is not one of its reviewed deterministic analytics.",
            "It can show the current reading, a supported trend, or evidence instead of estimating a result.",
            "Would you like a current value or a trend?",
        ), source_category="educational")
    if intent in {"conversation", "agriculture-learning"}:
        return GroundingData(intent, (
            "FarmPi may provide a general agricultural explanation, not a claim about this farm.",
            "No live web research, current external guidance lookup, or external citation has been performed for this response.",
            "If a question needs a farm-specific value, calculation, paddock identity, or operation, FarmPi will use a deterministic route rather than guess it.",
        ), source_category="educational")
    if intent == "farm_inventory_count":
        return farm_inventory_count()
    if intent == "farm_inventory_list":
        return farm_inventory_list()
    if intent == "paddock_summary":
        return latest_paddock_summary(paddock_name)
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
        try:
            snapshot = get_environment_snapshot()
        except NoFarmData:
            snapshot = []
        resolution = resolve_paddock_reference(paddock_name, snapshot if snapshot else None)
        if resolution.paddock is None:
            return GroundingData(intent, _paddock_resolution_facts(resolution))
        try:
            item = resolve_paddock(paddock_name, snapshot)
        except NoFarmData:
            item = None
        if item is None:
            return GroundingData(intent, (f"{resolution.paddock.name} is active, but has no current complete reading for the requested measurement.",))
        key = measurement_key or "soil_moisture_pct"
        if key not in BY_KEY or CURRENT not in BY_KEY[key].operations:
            return GroundingData("interpretation-boundary", ("FarmPi does not have a reviewed current-reading operation for that measurement.",))
        screen_facts = (_measurement_fact(item, key), _display_reading_time(item.received_at))
        return GroundingData(intent, screen_facts, _current_evidence(item), spoken_facts=(_measurement_fact(item, key),))
    if intent == "measurement-fallback" and measurement_key in BY_KEY:
        snapshot = get_environment_snapshot()
        return GroundingData(intent, (*(_measurement_fact(item, measurement_key) for item in snapshot), _provenance_fact(snapshot)))
    snapshot = get_moisture_snapshot()
    driest, wettest = get_driest_paddock(snapshot), get_wettest_paddock(snapshot)
    facts = [*(f"{item.name} soil moisture: {format_measurement(item.soil_moisture_pct, 'soil_moisture_pct')}." for item in snapshot), f"Farm average soil moisture: {format_measurement(get_average_soil_moisture(snapshot), 'soil_moisture_pct')}.", f"Driest paddock: {driest.name} at {format_measurement(driest.soil_moisture_pct, 'soil_moisture_pct')}.", f"Wettest paddock: {wettest.name} at {format_measurement(wettest.soil_moisture_pct, 'soil_moisture_pct')}.", _provenance_fact(snapshot)]
    return GroundingData("moisture-fallback", tuple(facts))


def format_grounding_context(grounding: GroundingData) -> str:
    heading = "APPROVED LEARNING MATERIAL" if grounding.source_category == "educational" else "FARMPI GROUNDING"
    return "\n".join([heading, *(f"- {fact}" for fact in grounding.facts)])


def build_verified_moisture_context() -> str:
    return format_grounding_context(get_grounding_data("moisture-fallback"))
