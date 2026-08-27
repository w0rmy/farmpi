"""Regression tests for the broader language / deterministic authority boundary."""

from __future__ import annotations

import asyncio
from datetime import datetime
import unittest
from unittest.mock import patch

from app.app import AskRequest, ask
from app.farm_data import GroundingData, get_grounding_data, irrigation_decision_grounding
from app.question_router import route_question


class ConversationalArchitectureTests(unittest.TestCase):
    def _row(self, name: str, paddock_id: int, moisture: float) -> dict[str, object]:
        return {
            "id": paddock_id, "name": name, "soil_moisture_pct": moisture,
            "soil_temperature_c": 14.0, "air_temperature_c": 17.2,
            "relative_humidity_pct": 69.0, "soil_ph": 6.5,
            "soil_ec_ms_cm": 0.55, "light_lux": 14500.0, "rainfall_mm": 0.0,
            "barometric_pressure_hpa": 1015.2, "wind_speed_kmh": 9.0,
            "wind_direction_deg": 225.0, "pasture_height_cm": 13.0,
            "leaf_wetness_pct": 6.0, "recorded_at": datetime(2026, 8, 27, 9),
            "sensor_count": 1, "contains_simulated": 1,
        }

    @patch("app.paddock_resolver.fetch_all", return_value=[])
    @patch("app.farm_data.fetch_all")
    def test_irrigation_boundary_resolves_paddock_and_keeps_verified_value(self, fetch_all, _) -> None:
        fetch_all.return_value = [self._row("Paddock A", 1, 18.0), self._row("Paddock B", 2, 24.5)]
        result = irrigation_decision_grounding("Paddock 2")
        self.assertEqual(result.intent, "irrigation-decision")
        self.assertIn("Paddock B soil moisture: 24.50%.", result.facts)
        self.assertIn("cannot determine an irrigation decision", " ".join(result.facts))
        self.assertIn("field capacity", " ".join(result.facts).casefold())
        self.assertEqual(result.source_category, "combined")

    @patch("app.paddock_resolver.fetch_all", return_value=[])
    @patch("app.farm_data.fetch_all")
    def test_unknown_paddock_is_a_clarification_not_unavailable(self, fetch_all, _) -> None:
        fetch_all.return_value = [self._row("Paddock A", 1, 18.0)]
        result = irrigation_decision_grounding("Paddock 17")
        self.assertIn("outside the active configured paddock range", result.facts[0])
        self.assertNotIn("unavailable", result.facts[0].casefold())

    @patch("app.app.get_grounding_data")
    def test_capability_answer_is_curated_and_does_not_call_the_llm(self, grounding) -> None:
        grounding.return_value = GroundingData("capability", ("FarmPi can show verified measurements.",), source_category="educational")
        response = asyncio.run(ask(AskRequest(question="What else can you show me?")))
        self.assertEqual(response.intent, "capability")
        self.assertEqual(response.answer, "FarmPi can show verified measurements.")
        self.assertEqual(response.source_category, "educational")

    @patch("app.app.get_grounding_data")
    def test_irrigation_question_returns_a_teaching_boundary_not_a_generic_refusal(self, grounding) -> None:
        grounding.return_value = GroundingData(
            "irrigation-decision",
            (
                "FarmPi cannot determine an irrigation decision from its current measurements alone.",
                "Paddock B soil moisture: 24.50%.",
                "A decision normally also considers field capacity and refill point.",
                "Would you like me to explain refill point and field capacity?",
            ),
            source_category="combined",
        )
        response = asyncio.run(ask(AskRequest(question="Should I irrigate Paddock 2?")))
        self.assertEqual(response.intent, "irrigation-decision")
        self.assertIn("Paddock B soil moisture: 24.50%.", response.answer)
        self.assertNotIn("requested information is unavailable", response.answer.casefold())
        self.assertEqual(grounding.call_args.args[:3], ("irrigation-decision", "Paddock 2", None))

    def test_general_conversation_has_no_implicit_measurement_fallback(self) -> None:
        route = route_question("Can you help me understand the monitoring data?")
        self.assertEqual(route.intent, "conversation")
        context = get_grounding_data(route.intent)
        self.assertEqual(context.source_category, "educational")
        self.assertNotIn("soil moisture:", " ".join(context.facts).casefold())


if __name__ == "__main__":
    unittest.main()
