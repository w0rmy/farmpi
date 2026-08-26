"""Focused tests for calculations, chart payloads, educational content and routes."""

from __future__ import annotations

from datetime import datetime, timedelta
import asyncio
import unittest

from app.analytics import compare_paddocks, historical_analysis
from app.education import CONCEPTS, concept_for_measurement, render_concept
from app.learning import ACTIVITIES
from app.question_router import route_question
from app.app import AskRequest, ask


class AnalyticsAndLearningTests(unittest.TestCase):
    def _rows(self) -> list[dict[str, object]]:
        start = datetime(2026, 8, 27, 0, 0)
        return [
            {"name": "North Flat", "sensor_uid": "a", "value": 10.0, "analysis_at": start, "simulated": True},
            {"name": "North Flat", "sensor_uid": "a", "value": 14.0, "analysis_at": start + timedelta(hours=2), "simulated": True},
            {"name": "Back Hill", "sensor_uid": "b", "value": 8.0, "analysis_at": start, "simulated": True},
            {"name": "Back Hill", "sensor_uid": "b", "value": 12.0, "analysis_at": start + timedelta(hours=2), "simulated": True},
        ]

    def test_trend_chart_and_evidence_are_deterministic(self) -> None:
        result = historical_analysis("soil_moisture_pct", "trend", self._rows()[:2], "last 2 hours", "North Flat")
        self.assertIn("rising", result.facts[0])
        self.assertEqual(result.chart["type"], "line")
        self.assertEqual(len(result.evidence), 2)
        self.assertTrue(result.evidence[0].simulated)

    def test_comparison_makes_bar_payload(self) -> None:
        result = compare_paddocks("soil_moisture_pct", "average", self._rows(), "last 2 hours")
        self.assertEqual(result.chart["type"], "bar")
        self.assertIn("North Flat", result.facts[0])

    def test_education_is_static_and_has_levels(self) -> None:
        concept = concept_for_measurement("soil_ec_ms_cm")
        self.assertIs(concept, CONCEPTS["soil_ec"])
        self.assertNotEqual(render_concept(concept, "simple")[1], render_concept(concept, "technical")[1])
        self.assertIn("does not directly identify N, P, or K", render_concept(concept, "technical")[2])

    def test_new_question_shapes_normalise_to_controlled_routes(self) -> None:
        comparison = route_question("Compare soil EC across all paddocks.")
        self.assertEqual((comparison.intent, comparison.measurement, comparison.comparison), ("comparison", "soil_ec_ms_cm", True))
        graph = route_question("Show a graph of soil moisture over the last 24 hours.")
        self.assertEqual((graph.intent, graph.operation, graph.presentation), ("historical", "trend", "graph"))
        education = route_question("What does soil EC mean?")
        self.assertEqual((education.intent, education.measurement), ("education", "soil_ec_ms_cm"))
        summary = route_question("What has happened in North Flat today?")
        self.assertEqual((summary.intent, summary.paddock_name, summary.time_label), ("summary", "North Flat", "today"))
        range_question = route_question("What was today's temperature range?")
        self.assertEqual((range_question.intent, range_question.operation), ("historical", "range"))
        anomaly = route_question("Was soil EC unusual over the last 24 hours?")
        self.assertEqual((anomaly.intent, anomaly.operation), ("historical", "anomaly"))

    def test_activities_use_real_route_intents(self) -> None:
        self.assertGreaterEqual(len(ACTIVITIES), 8)
        self.assertTrue(all(activity.example_question and activity.success_intents for activity in ACTIVITIES))

    def test_educational_answer_does_not_depend_on_database_or_qwen(self) -> None:
        response = asyncio.run(ask(AskRequest(question="What does soil EC mean?")))
        self.assertEqual(response.intent, "education")
        self.assertEqual(response.source_category, "educational")
        self.assertIn("electrical conductivity", response.answer)
        self.assertEqual(response.timings.llm_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
