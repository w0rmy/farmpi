"""Small teach-by-doing activity catalogue, deliberately not an LMS."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LearningActivity:
    id: str
    title: str
    instruction: str
    example_question: str
    success_intents: tuple[str, ...]


ACTIVITIES = (
    LearningActivity("getting-started", "Getting started", "Use Guide me to see FarmPi's measurements, evidence, trends, and learning topics.", "What else can you show me?", ("capability",)),
    LearningActivity("one-paddock", "Ask about one paddock", "Ask for a current value in one paddock.", "What is Paddock A's soil EC?", ("paddock", "paddock-field")),
    LearningActivity("comparison", "Compare paddocks", "Compare a measurement across the paddocks and inspect the chart.", "Compare soil EC across all paddocks.", ("comparison", "ranking")),
    LearningActivity("driest", "Find a moisture extreme", "Find the driest or wettest paddock from verified readings.", "Which paddock is driest?", ("driest", "wettest")),
    LearningActivity("trend", "Inspect a 24-hour trend", "Ask for a deterministic trend over a time period.", "How has Paddock A soil moisture changed over the last 24 hours?", ("historical",)),
    LearningActivity("measurement", "Understand a measurement", "Ask what a measurement and its unit mean.", "What does soil EC mean?", ("education",)),
    LearningActivity("provenance", "Check provenance", "Explain the difference between simulated and real data.", "Explain simulated data.", ("education",)),
    LearningActivity("irrigation-factors", "Understand an irrigation decision", "See the current soil moisture, then learn why FarmPi cannot make the decision from that reading alone.", "Should I irrigate Paddock A?", ("irrigation-decision",)),
    LearningActivity("evidence", "View evidence", "Ask for a trend or comparison, then show its data/evidence.", "Show a graph of soil moisture over the last 24 hours.", ("historical", "comparison")),
)


def activity_payload() -> list[dict[str, object]]:
    return [asdict(activity) for activity in ACTIVITIES]
