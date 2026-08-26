"""Deterministic onboarding and follow-up guidance for FarmPi."""

from __future__ import annotations

WELCOME_TEXT = (
    "FarmPi can help you explore the current verified sensor readings. "
    "You can ask about soil moisture, air temperature, relative humidity, "
    "soil pH, and light. You can also ask which paddock is driest or wettest, "
    "or ask for the average soil moisture. Tap Guide me for a short introduction."
)

HELP_FACTS = (
    "FarmPi can answer current verified soil moisture, air temperature, relative humidity, soil pH, and light readings.",
    "FarmPi can deterministically identify the driest paddock, the wettest paddock, and the average soil moisture.",
    "Useful example questions include: Which paddock is driest? What is Paddock A's air temperature? What is Paddock A's relative humidity? What is Paddock A's soil pH? What is the light level in Paddock A?",
    "The current ESP32 readings are synthetic test telemetry and are marked as simulated in FarmPi.",
    "FarmPi does not currently provide weather forecasts, irrigation recommendations, agronomic causes, or daylight-hour calculations unless a deterministic application rule is added for them.",
    "If FarmPi does not have a verified fact for a question, it should say the information is unavailable rather than inventing an answer.",
)

INITIAL_SUGGESTIONS = (
    "Which paddock is driest?",
    "What is Paddock A's air temperature?",
    "What is Paddock A's relative humidity?",
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
            f"What is {paddock_name}'s relative humidity?",
            f"What is {paddock_name}'s soil pH?",
            f"What is the light level in {paddock_name}?",
        )
        if measurement == "air_temperature_c":
            return (candidates[2], candidates[0], candidates[3])
        if measurement == "relative_humidity_pct":
            return (candidates[1], candidates[0], candidates[4])
        if measurement == "soil_ph":
            return (candidates[0], candidates[1], candidates[4])
        if measurement == "light_lux":
            return (candidates[1], candidates[2], candidates[0])
        return (candidates[1], candidates[2], candidates[3])

    if intent in {"driest", "wettest", "average", "moisture-fallback"}:
        return (
            "What is Paddock A's air temperature?",
            "What is Paddock A's relative humidity?",
            "What is Paddock A's soil pH?",
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
