"""Deterministic farm-data functions backed by MariaDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean

from .database import fetch_all


class NoFarmData(RuntimeError):
    """Raised when a deterministic farm result cannot be produced."""


@dataclass(frozen=True)
class PaddockMoisture:
    """Current deterministic soil-moisture value for one paddock."""

    name: str
    soil_moisture_pct: float
    recorded_at: datetime
    sensor_count: int


LATEST_PADDOCK_MOISTURE_SQL = """
SELECT
    p.name,
    ROUND(AVG(r.soil_moisture_pct), 2) AS soil_moisture_pct,
    MAX(r.recorded_at) AS recorded_at,
    COUNT(*) AS sensor_count
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
        ORDER BY r2.recorded_at DESC, r2.id DESC
        LIMIT 1
    )
WHERE p.active = 1
GROUP BY p.id, p.name
ORDER BY p.name
"""


def get_moisture_snapshot() -> list[PaddockMoisture]:
    """Return the latest deterministic soil-moisture value for each active paddock."""
    rows = fetch_all(LATEST_PADDOCK_MOISTURE_SQL)

    snapshot: list[PaddockMoisture] = []
    for row in rows:
        recorded_at = row["recorded_at"]
        if not isinstance(recorded_at, datetime):
            raise NoFarmData("A moisture reading has an invalid timestamp.")

        snapshot.append(
            PaddockMoisture(
                name=str(row["name"]),
                soil_moisture_pct=float(row["soil_moisture_pct"]),
                recorded_at=recorded_at,
                sensor_count=int(row["sensor_count"]),
            )
        )

    if not snapshot:
        raise NoFarmData("No current soil-moisture readings are available.")

    return snapshot


def get_driest_paddock(
    snapshot: list[PaddockMoisture] | None = None,
) -> PaddockMoisture:
    """Return the paddock with the lowest current soil-moisture value."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return min(values, key=lambda item: item.soil_moisture_pct)


def get_wettest_paddock(
    snapshot: list[PaddockMoisture] | None = None,
) -> PaddockMoisture:
    """Return the paddock with the highest current soil-moisture value."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return max(values, key=lambda item: item.soil_moisture_pct)


def get_average_soil_moisture(
    snapshot: list[PaddockMoisture] | None = None,
) -> float:
    """Return the mean of the current paddock soil-moisture values."""
    values = snapshot if snapshot is not None else get_moisture_snapshot()
    if not values:
        raise NoFarmData("No current soil-moisture readings are available.")
    return round(fmean(item.soil_moisture_pct for item in values), 2)


def build_verified_moisture_context() -> str:
    """Build compact model context only from deterministic database results."""
    snapshot = get_moisture_snapshot()
    driest = get_driest_paddock(snapshot)
    wettest = get_wettest_paddock(snapshot)
    average = get_average_soil_moisture(snapshot)

    lines = [
        "VERIFIED FARM INFORMATION",
        "Source: MariaDB current soil-moisture readings.",
        (
            "Rule: each paddock value is the average of the latest valid "
            "soil-moisture reading from each active sensor in that paddock."
        ),
        "",
        "Current soil moisture:",
    ]

    for item in snapshot:
        lines.append(
            f"- {item.name}: {item.soil_moisture_pct:.2f}% "
            f"(latest contributing reading {item.recorded_at.isoformat(sep=' ')})"
        )

    lines.extend(
        [
            "",
            "Verified deterministic results:",
            f"- Farm average soil moisture: {average:.2f}%",
            f"- Driest paddock: {driest.name} at {driest.soil_moisture_pct:.2f}%",
            f"- Wettest paddock: {wettest.name} at {wettest.soil_moisture_pct:.2f}%",
            "",
            "No temperature, pH, weather, irrigation, or agronomic recommendation data is supplied.",
        ]
    )

    return "\n".join(lines)
