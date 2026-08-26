"""Reviewed educational grounding; this content is never model-generated."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EducationalConcept:
    key: str
    title: str
    unit: str
    simple: str
    normal: str
    technical: str
    limitations: str


_MEASUREMENT_CONTENT = {
    "soil_moisture": ("Soil moisture", "%", "how much water is held in the measured soil", "FarmPi uses it to compare wetness and change over time. It is a local sensor reading, not a watering instruction.", "Volumetric-style percentage is a sensor-specific proxy; readings are comparable only when placement and calibration are comparable."),
    "soil_temperature": ("Soil temperature", "°C", "how warm the soil is near the sensor", "It changes more slowly than air temperature and helps learners see lagged environmental data.", "One probe represents its immediate depth and location; it does not describe every soil layer."),
    "air_temperature": ("Air temperature", "°C", "how warm the air is at the sensor", "It supports daily ranges and comparisons between the simulated paddocks.", "Shelter, height, radiation and airflow affect a local air-temperature measurement."),
    "relative_humidity": ("Relative humidity", "%", "how close the air is to holding as much water vapour as it can at that temperature", "Rain and cooler conditions can coincide with higher humidity, but a reading alone does not prove why it changed.", "Relative humidity is temperature-dependent and is not the same thing as rainfall or soil moisture."),
    "soil_ph": ("Soil pH", "", "a scale describing acidity or alkalinity in the sampled soil", "FarmPi records a sensor value so learners can examine values and change without treating it as a fertiliser recommendation.", "pH is logarithmic and field interpretation needs sampling, calibration and context beyond this synthetic dataset."),
    "soil_ec": ("Soil electrical conductivity (EC)", "mS/cm", "how readily the measured soil conducts electricity", "It is a raw chemistry-related proxy included for comparison and data-literacy exercises.", "EC does not directly identify N, P, or K and does not by itself diagnose a nutrient problem."),
    "light_lux": ("Light / lux", "lux", "how much visible light reaches the sensor", "FarmPi uses it to show day/night and historical daylight patterns.", "Lux is a light-at-sensor measurement, not total solar energy or plant growth proof."),
    "rainfall": ("Rainfall", "mm per interval", "water recorded during one telemetry interval", "Totals are made by adding verified interval readings; FarmPi labels the selected period.", "Synthetic interval rain is test data and must not be treated as a local weather record."),
    "barometric_pressure": ("Barometric pressure", "hPa", "the pressure of the air at the sensor", "It is useful for practising trends and association summaries alongside rain and cloud.", "A pressure pattern can coincide with weather but does not provide a FarmPi forecast."),
    "wind_speed": ("Wind speed", "km/h", "how fast air is moving at the sensor", "It can be viewed as a current or historical measurement.", "A single simulated sensor does not represent all wind conditions across a farm."),
    "wind_direction": ("Wind direction", "°", "the compass direction recorded for wind", "Degrees make wind direction easy to store and compare consistently.", "Directions wrap at 360°, so ordinary averages need special circular statistics."),
    "pasture_height": ("Pasture height", "cm", "the measured height of simulated pasture", "FarmPi uses it for trends and comparisons, including synthetic grazing/cutting drops.", "It is not a pasture-mass estimate or grazing recommendation."),
    "leaf_wetness": ("Leaf wetness", "%", "a sensor proxy for how wet the leaf surface is", "It helps learners see how rainfall, humidity and light can move together in a synthetic model.", "It does not identify disease or prove a biological outcome."),
}

CONCEPTS = {
    key: EducationalConcept(key, title, unit, f"{title} is {simple}.", normal, f"Technical note: {technical}", technical)
    for key, (title, unit, simple, normal, technical) in _MEASUREMENT_CONTENT.items()
}
CONCEPTS.update({
    "simulated_data": EducationalConcept("simulated_data", "Simulated and real data", "", "Simulated data is deliberately generated test telemetry.", "FarmPi uses the same validated telemetry contract for simulated and future real devices, while clearly marking provenance.", "Synthetic values demonstrate system behaviour and data analysis; they are not field observations or an agronomic model.", "Never treat synthetic telemetry as evidence about a real farm."),
    "observed_received": EducationalConcept("observed_received", "Observed and received time", "UTC", "Observed time is when a sensor says it measured; received time is when FarmPi got the sample.", "FarmPi uses received time for freshness and keeps observed time for valid device-clock analysis.", "The two timestamps expose transport delay and clock quality. Invalid/out-of-tolerance clocks are retained with metadata rather than silently trusted.", "Neither timestamp proves that a sensor value is accurate."),
    "trend": EducationalConcept("trend", "Trend, comparison and average", "", "A trend is the direction values move over time; a comparison puts values side by side.", "FarmPi calculates trends, ranges and averages from selected verified readings and shows the period and evidence.", "A simple trend is a deterministic first-to-last rate, not a forecast or causal model; averages can hide variation.", "Association in a chart is not proof that one measurement caused another."),
})


def concept_for_measurement(measurement_key: str | None) -> EducationalConcept | None:
    if not measurement_key:
        return None
    from .measurements import BY_KEY
    item = BY_KEY.get(measurement_key)
    return CONCEPTS.get(item.educational_concept) if item else None


def render_concept(concept: EducationalConcept, level: str) -> tuple[str, ...]:
    detail = getattr(concept, level if level in {"simple", "normal", "technical"} else "normal")
    return (concept.simple, detail, f"Limitation: {concept.limitations}", "Educational grounding: curated FarmPi content (version-controlled), not a model-generated fact.")
