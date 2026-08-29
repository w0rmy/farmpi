"""Deterministic onboarding and follow-up guidance for FarmPi."""

from __future__ import annotations

WELCOME_TEXT = (
    "FarmPi is a conversational agricultural learning assistant. Ask naturally about your monitored farm data "
    "or practical farming topics such as cows, sheep, pasture, soils, irrigation, weather, effluent, and animal health. "
    "FarmPi keeps verified farm observations separate from general explanations and sourced guidance."
)

HELP_FACTS = (
    "FarmPi can teach practical agricultural concepts and discuss dairy farming, cows, sheep, pasture, soils, irrigation, weather, effluent, animal health, farm systems, and related New Zealand agriculture.",
    "FarmPi can also answer current verified soil moisture, soil/air temperature, humidity, pH, EC, light, rainfall, pressure, wind, pasture height, and leaf wetness questions from its monitored data.",
    "FarmPi deterministically calculates supported farm averages, rankings, comparisons, rainfall totals, trends, and bounded historical analytics instead of asking the language model to invent or calculate those values.",
    "Curated New Zealand sources include DairyNZ, MPI, Earth Sciences New Zealand, and Irrigation New Zealand. FarmPi labels source provenance and must not claim live research unless retrieval actually occurred.",
    "The current ESP32 readings are synthetic test telemetry and are marked as simulated in FarmPi.",
    "For farm-specific decisions or diagnoses, FarmPi explains what is known, what other factors matter, and what can be learned next rather than pretending the available evidence proves an answer.",
    "You do not need to learn a FarmPi command grammar: polite, indirect, colloquial, and ordinary learner wording can be interpreted semantically before controlled FarmPi operations are executed.",
)

INITIAL_SUGGESTIONS = (
    "What can I learn about?",
    "Why does soil moisture matter for pasture?",
    "What does DairyNZ say about irrigation scheduling?",
    "What stats are available on Paddock B?",
    "Why do dairy cows get milk fever?",
)


def follow_up_suggestions(
    intent: str,
    paddock_name: str | None = None,
    measurement: str | None = None,
) -> tuple[str, ...]:
    """Return a small set of next learning directions for the user interface."""
    if intent in {"help", "capability"}:
        return INITIAL_SUGGESTIONS[:3]

    if intent in {"agriculture-learning", "agriculture-research", "conversation"}:
        return (
            "Can you explain that more simply?",
            "What should I learn about next?",
            "Is there a New Zealand source I can read about that?",
        )

    if intent == "farm_inventory_count":
        return (
            "What stats are available on Paddock B?",
            "Which paddock is driest?",
            "Why does soil moisture vary between paddocks?",
        )

    if intent == "farm_inventory_list":
        return (
            "What stats are available on Paddock 2?",
            "Which paddock is driest?",
            "What measurements are useful for understanding pasture conditions?",
        )

    if paddock_name:
        candidates = (
            f"What is {paddock_name}'s soil moisture?",
            f"What is {paddock_name}'s air temperature?",
            f"What is {paddock_name}'s soil EC?",
            f"What is the pasture height in {paddock_name}?",
            f"How has {paddock_name} soil moisture changed over the last 24 hours?",
            "Why does soil moisture matter for pasture growth?",
            "What does soil EC tell us and what can affect it?",
        )
        if measurement == "air_temperature_c":
            return (candidates[5], candidates[0], candidates[4])
        if measurement == "relative_humidity_pct":
            return ("How are humidity and temperature related?", candidates[0], candidates[4])
        if measurement in {"soil_ph", "soil_ec_ms_cm"}:
            return (candidates[6], candidates[0], candidates[4])
        if measurement in {"light_lux", "pasture_height_cm"}:
            return ("What factors affect pasture growth?", candidates[1], candidates[4])
        return (candidates[5], candidates[1], candidates[4])

    if intent in {"driest", "wettest", "average", "farm-average", "ranking", "comparison", "historical", "moisture-fallback"}:
        return (
            "Why might paddocks differ from each other?",
            "Show me another measurement that could help explain this.",
            "What should I be careful about when interpreting this data?",
        )

    if intent == "measurement-fallback":
        return (
            "Compare that measurement across the paddocks.",
            "What does that measurement mean?",
            "Why is that useful on a farm?",
        )

    if intent in {"irrigation-decision", "operational-decision"}:
        return (
            "Explain the other factors that matter for that decision.",
            "What does DairyNZ say about this topic?",
            "What information would I need before making that decision?",
        )

    if intent in {"forecast-boundary", "causal-boundary", "interpretation-boundary", "semantic-clarification"}:
        return (
            "Can you explain what you do know about this topic?",
            "What information would help answer this better?",
            "What should I learn about next?",
        )

    return INITIAL_SUGGESTIONS[:3]
