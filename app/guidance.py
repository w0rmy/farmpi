"""Deterministic onboarding and follow-up guidance for FarmPi."""

from __future__ import annotations

WELCOME_TEXT = (
    "FarmPi can help you explore the current verified sensor readings. "
    "You can ask about soil moisture, temperature, humidity, pH, EC, light, rain, "
    "pressure, wind, pasture height, and leaf wetness. Tap Guide me for examples."
)

HELP_FACTS = (
    "FarmPi can answer current verified moisture, soil/air temperature, humidity, pH, EC, light, rainfall, pressure, wind, pasture height, and leaf wetness readings.",
    "FarmPi can deterministically identify the driest/wettest paddock, average moisture, approved rankings, rainfall totals, and limited historical change.",
    "Useful example questions include: Which paddock is tallest? What is Paddock A's soil EC? How much rainfall was there over the last 24 hours? What is the pasture height change in Paddock A over the last day?",
    "The current ESP32 readings are synthetic test telemetry and are marked as simulated in FarmPi.",
    "FarmPi does not currently provide weather forecasts, irrigation recommendations, or agronomic causes. Daylight is a deterministic historical light-derived value.",
    "If FarmPi does not have a verified fact for a question, it should say the information is unavailable rather than inventing an answer.",
)

INITIAL_SUGGESTIONS = (
    "Which paddock is driest?",
    "Which paddock is tallest?",
    "What is Paddock A's soil EC?",
    "How do I use FarmPi?",
)


def follow_up_suggestions(
    intent: str,
    paddock_name: str | None = None,
    measurement: str | None = None,
) -> tuple[str, ...]:
    """Return small deterministic next-question prompts for the user interface."""
    if intent == "help":
        return INITIAL_SUGGESTIONS[:3]

    if paddock_name:
        candidates = (
            f"What is {paddock_name}'s soil moisture?",
            f"What is {paddock_name}'s air temperature?",
            f"What is {paddock_name}'s soil EC?",
            f"What is the pasture height in {paddock_name}?",
            f"What is the rainfall in {paddock_name}?",
            f"How has {paddock_name} soil moisture changed over the last 24 hours?",
            f"What does {measurement or 'soil moisture'} mean?",
        )
        if measurement == "air_temperature_c":
            return (candidates[2], candidates[0], candidates[5])
        if measurement == "relative_humidity_pct":
            return (candidates[1], candidates[0], candidates[5])
        if measurement in {"soil_ph", "soil_ec_ms_cm"}:
            return (candidates[0], candidates[1], candidates[5])
        if measurement in {"light_lux", "pasture_height_cm"}:
            return (candidates[1], candidates[2], candidates[5])
        return (candidates[1], candidates[2], candidates[5])

    if intent in {"driest", "wettest", "average", "moisture-fallback"}:
        return (
            "Which paddock is tallest?",
            "What is Paddock A's soil EC?",
            "Compare soil EC across all paddocks.",
            "Show a graph of soil moisture over the last 24 hours.",
        )

    if intent == "measurement-fallback":
        return (
            "Which paddock is driest?",
            "What is Paddock A's soil moisture?",
            "How do I use FarmPi?",
        )

    if intent == "unsupported":
        return (
            "How do I use FarmPi?",
            "Which paddock is driest?",
            "What is Paddock A's air temperature?",
        )

    return INITIAL_SUGGESTIONS[:3]
