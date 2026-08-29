"""Small explicit analytics and portable chart specifications for FarmPi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean, median, pstdev
from typing import Any, Iterable

from .measurements import DAYLIGHT, SUM, format_measurement, measurement


@dataclass(frozen=True)
class EvidenceItem:
    paddock: str
    sensor: str | None
    timestamp: str
    value: float
    simulated: bool


@dataclass(frozen=True)
class AnalyticsResult:
    facts: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]
    chart: dict[str, Any] | None = None


def _number(value: float) -> float:
    return round(float(value), 3)


def evidence_from_rows(rows: Iterable[dict[str, Any]]) -> tuple[EvidenceItem, ...]:
    """Produce a bounded, serialisable evidence trail from database rows."""
    result: list[EvidenceItem] = []
    for row in list(rows)[-24:]:
        timestamp = row.get("analysis_at") or row.get("received_at") or row.get("observed_at")
        result.append(EvidenceItem(
            paddock=str(row.get("name", "Farm")), sensor=str(row["sensor_uid"]) if row.get("sensor_uid") else None,
            timestamp=timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
            value=_number(float(row["value"])), simulated=bool(row.get("simulated", False)),
        ))
    return tuple(result)


def _farm_average_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse simultaneous paddock observations into one farm-average time series."""
    grouped: dict[object, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("analysis_at"), []).append(row)
    averaged: list[dict[str, Any]] = []
    for when, items in grouped.items():
        averaged.append({
            "name": "Farm average",
            "sensor_uid": None,
            "value": fmean(float(item["value"]) for item in items),
            "analysis_at": when,
            "simulated": any(bool(item.get("simulated")) for item in items),
        })
    averaged.sort(key=lambda row: row.get("analysis_at") or datetime.min)
    return averaged


def line_chart(key: str, rows: list[dict[str, Any]], period: str, title_scope: str) -> dict[str, Any] | None:
    if len(rows) < 2:
        return None
    item = measurement(key)
    series: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        when = row.get("analysis_at")
        label = when.isoformat() if isinstance(when, datetime) else str(when)
        series.setdefault(str(row.get("name", title_scope)), []).append({"x": label, "y": _number(float(row["value"]))})
    return {
        "type": "line", "title": f"{item.label.title()} — {title_scope}",
        "x_label": "Time (UTC)", "y_label": f"{item.label.title()} ({item.unit})".strip(),
        "unit": item.unit, "source_period": period, "provenance": "simulated" if any(bool(row.get("simulated")) for row in rows) else "non-simulated",
        "series": [{"name": name, "data": data} for name, data in series.items()],
    }


def comparison_chart(key: str, values: dict[str, float], period: str, operation: str) -> dict[str, Any]:
    item = measurement(key)
    return {
        "type": "bar", "title": f"{item.label.title()} comparison ({operation})",
        "x_label": "Paddock", "y_label": f"{item.label.title()} ({item.unit})".strip(),
        "unit": item.unit, "source_period": period, "provenance": "verified telemetry",
        "series": [{"name": operation, "data": [{"x": name, "y": _number(value)} for name, value in values.items()]}],
    }


def historical_analysis(key: str, operation: str, rows: list[dict[str, Any]], period: str, scope: str) -> AnalyticsResult:
    """Calculate approved descriptive facts from already validated rows."""
    if not rows:
        return AnalyticsResult((f"No verified {measurement(key).label} history is available for {scope} over {period}.",), ())

    # Generic history/graph questions with no named paddock represent the farm
    # as one readable average time series. The raw paddock rows remain the
    # evidence trail; only the visual/analytic presentation is aggregated.
    evidence = evidence_from_rows(rows)
    analysis_rows = _farm_average_rows(rows) if scope == "the farm" and len({str(row.get("name")) for row in rows}) > 1 else rows
    values = [float(row["value"]) for row in analysis_rows]
    item = measurement(key)
    chart = line_chart(key, analysis_rows, period, "farm average" if analysis_rows is not rows and scope == "the farm" else scope)

    if operation == SUM:
        value, name = sum(values), "total"
    elif operation == "average":
        value, name = fmean(values), "average"
    elif operation == "minimum":
        value, name = min(values), "minimum"
    elif operation == "maximum":
        value, name = max(values), "maximum"
    elif operation == "range":
        value, name = max(values) - min(values), "range"
    elif operation == "change":
        value, name = values[-1] - values[0], "change"
    elif operation == DAYLIGHT:
        times = [row.get("analysis_at") for row in analysis_rows if isinstance(row.get("analysis_at"), datetime)]
        intervals = [
            (later - earlier).total_seconds() / 60
            for earlier, later in zip(times, times[1:])
            if later > earlier
        ]
        sample_minutes = median(intervals) if intervals else 5.0
        daylight_hours = sum(1 for value in values if value >= 1000) * sample_minutes / 60
        return AnalyticsResult(
            (
                f"Recorded daylight for {scope} over {period}: about {daylight_hours:.2f} hours with light at or above 1,000 lux.",
                "This is derived from the recorded light profile, not an astronomical sunrise/sunset calculation.",
            ),
            evidence,
            chart,
        )
    elif operation == "trend":
        first, last = analysis_rows[0], analysis_rows[-1]
        first_time, last_time = first.get("analysis_at"), last.get("analysis_at")
        hours = ((last_time - first_time).total_seconds() / 3600) if isinstance(first_time, datetime) and isinstance(last_time, datetime) else 0
        rate = (values[-1] - values[0]) / hours if hours > 0 else 0.0
        direction = "rising" if rate > 0.0001 else "falling" if rate < -0.0001 else "stable"
        scope_label = "farm-average" if analysis_rows is not rows and scope == "the farm" else scope
        return AnalyticsResult((f"{scope_label} {item.label} trend over {period}: {direction} at {format_measurement(abs(rate), key)} per hour.", "This describes the selected observations; it is not a forecast or causal claim."), evidence, chart)
    elif operation == "anomaly":
        baseline = fmean(values)
        deviation = pstdev(values) if len(values) >= 2 else 0.0
        latest = values[-1]
        if deviation and abs(latest - baseline) > 2 * deviation:
            message = f"Latest {item.label} is an outlier against this period's simple baseline: {format_measurement(latest, key)} versus average {format_measurement(baseline, key)}."
        else:
            message = f"Latest {item.label} is not a simple two-standard-deviation outlier against this period's baseline."
        return AnalyticsResult((message, "This is descriptive anomaly flagging, not a diagnosis."), evidence, chart)
    else:
        return AnalyticsResult((f"I can show the recorded {item.label}, but that calculation is not available for this view.",), evidence, chart)
    scope_label = "farm-average" if analysis_rows is not rows and scope == "the farm" else scope
    return AnalyticsResult((f"{scope_label} {name} {item.label} over {period}: {format_measurement(value, key)}.",), evidence, chart)


def compare_paddocks(key: str, operation: str, rows: list[dict[str, Any]], period: str) -> AnalyticsResult:
    """Aggregate a selected period by paddock then return a bar-chart payload."""
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["name"]), []).append(float(row["value"]))
    if not grouped:
        return AnalyticsResult((f"No verified {measurement(key).label} data is available for that comparison.",), ())
    if operation == SUM:
        values = {name: sum(items) for name, items in grouped.items()}
    elif operation == "minimum":
        values = {name: min(items) for name, items in grouped.items()}
    elif operation == "maximum":
        values = {name: max(items) for name, items in grouped.items()}
    else:
        values = {name: fmean(items) for name, items in grouped.items()}
    ordered = dict(sorted(values.items(), key=lambda entry: entry[1], reverse=True))
    leader, leader_value = next(iter(ordered.items()))
    item = measurement(key)
    facts = (f"Highest {operation} {item.label} over {period}: {leader} at {format_measurement(leader_value, key)}.", "The chart compares verified values by paddock; it does not explain why they differ.")
    return AnalyticsResult(facts, evidence_from_rows(rows), comparison_chart(key, ordered, period, operation))