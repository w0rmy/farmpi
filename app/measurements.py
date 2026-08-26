"""Single catalogue of FarmPi-supported instantaneous measurements.

This is deliberately application data rather than database- or model-generated
knowledge.  SQL column names, validation ranges, natural-language aliases and
allowed deterministic operations have one reviewed source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Measurement:
    """Metadata for one stored measurement."""

    key: str
    label: str
    unit: str
    aliases: tuple[str, ...]
    minimum: float
    maximum: float
    decimal_places: int
    operations: frozenset[str]


CURRENT = "current"
RANKING = "ranking"
AVERAGE = "average"
MINIMUM = "minimum"
MAXIMUM = "maximum"
SUM = "sum"
CHANGE = "change"
DAYLIGHT = "daylight"


MEASUREMENTS: tuple[Measurement, ...] = (
    Measurement("soil_moisture_pct", "soil moisture", "%", ("soil moisture", "moisture"), 0, 100, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("soil_temperature_c", "soil temperature", "°C", ("soil temperature", "ground temperature"), -10, 60, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("air_temperature_c", "air temperature", "°C", ("air temperature", "air temp", "temperature", "temp"), -30, 60, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("relative_humidity_pct", "relative humidity", "%", ("relative humidity", "humidity", "humid"), 0, 100, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("soil_ph", "soil pH", "", ("soil ph", "ph"), 0, 14, 2,
                frozenset({CURRENT, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("soil_ec_ms_cm", "soil electrical conductivity", "mS/cm", ("soil electrical conductivity", "soil ec", "electrical conductivity", "ec"), 0, 20, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("light_lux", "light", "lux", ("light level", "light", "lux", "illumination", "brightness"), 0, 200000, 0,
                frozenset({CURRENT, AVERAGE, MINIMUM, MAXIMUM, CHANGE, DAYLIGHT})),
    Measurement("rainfall_mm", "rainfall", "mm", ("rainfall", "rain"), 0, 100, 2,
                frozenset({CURRENT, RANKING, AVERAGE, MAXIMUM, SUM})),
    Measurement("barometric_pressure_hpa", "barometric pressure", "hPa", ("barometric pressure", "air pressure", "pressure"), 850, 1100, 1,
                frozenset({CURRENT, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("wind_speed_kmh", "wind speed", "km/h", ("wind speed", "wind"), 0, 250, 1,
                frozenset({CURRENT, AVERAGE, MAXIMUM})),
    Measurement("wind_direction_deg", "wind direction", "°", ("wind direction", "wind bearing"), 0, 360, 0,
                frozenset({CURRENT})),
    Measurement("pasture_height_cm", "pasture height", "cm", ("pasture height", "grass height", "grass length", "pasture", "grass"), 0, 300, 1,
                frozenset({CURRENT, RANKING, AVERAGE, MINIMUM, MAXIMUM, CHANGE})),
    Measurement("leaf_wetness_pct", "leaf wetness", "%", ("leaf wetness", "wet leaves"), 0, 100, 1,
                frozenset({CURRENT, AVERAGE, MAXIMUM, CHANGE})),
)

BY_KEY = {measurement.key: measurement for measurement in MEASUREMENTS}


def measurement_for_text(text: str) -> str | None:
    """Return the most specific supported measurement mentioned in text."""
    text_casefolded = text.casefold()
    candidates: list[tuple[int, str]] = []
    for measurement in MEASUREMENTS:
        for alias in measurement.aliases:
            if re.search(r"(?<![a-z0-9])" + re.escape(alias.casefold()) + r"(?![a-z0-9])", text_casefolded):
                candidates.append((len(alias), measurement.key))
    return max(candidates, default=(0, None))[1]


def measurement(key: str) -> Measurement:
    """Return known metadata or raise a clear error for internal callers."""
    return BY_KEY[key]


def format_measurement(value: float, key: str) -> str:
    """Format a deterministic numeric value using catalogue metadata."""
    item = measurement(key)
    number = f"{float(value):.{item.decimal_places}f}"
    if item.unit == "%":
        return f"{number}%"
    return f"{number} {item.unit}" if item.unit else number
