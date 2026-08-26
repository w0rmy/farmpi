"""Regression coverage for deterministic learner-friendly paddock wording."""

from __future__ import annotations

import asyncio
from datetime import datetime
import unittest
from unittest.mock import patch

from app.app import AskRequest, _conversation_states, ask
from app.farm_data import GroundingData, farm_inventory_count, get_grounding_data, latest_paddock_summary
from app.paddock_resolver import PaddockIdentity, resolve_paddock
from app.question_router import route_question


class ConversationalPaddockTests(unittest.TestCase):
    def _paddocks(self) -> tuple[PaddockIdentity, ...]:
        return (
            PaddockIdentity(10, "Paddock A", 1, 1),
            PaddockIdentity(20, "North Flat", 2, 1),
            PaddockIdentity(30, "Paddock C", 3, 0),
        )

    def _reading(self, name: str = "Paddock B", paddock_id: int = 20) -> dict[str, object]:
        return {
            "id": paddock_id, "name": name, "soil_moisture_pct": 24.0,
            "soil_temperature_c": 14.0, "air_temperature_c": 17.2,
            "relative_humidity_pct": 69.0, "soil_ph": 6.5,
            "soil_ec_ms_cm": 0.55, "light_lux": 14500.0, "rainfall_mm": 0.0,
            "barometric_pressure_hpa": 1015.2, "wind_speed_kmh": 9.0,
            "wind_direction_deg": 225.0, "pasture_height_cm": 13.0,
            "leaf_wetness_pct": 6.0, "recorded_at": datetime(2026, 8, 27, 9),
            "sensor_count": 1, "contains_simulated": 1,
        }

    def test_inventory_summary_and_measurement_wording_route_to_approved_operations(self) -> None:
        cases = {
            "How many paddocks are we monitoring?": "farm_inventory_count",
            "How many sensor nodes are active?": "farm_inventory_count",
            "What stats are available on Paddock B?": "paddock_summary",
            "What data do we have for Paddock B?": "paddock_summary",
            "Tell me about Paddock B.": "paddock_summary",
            "What is the temperature in Paddock B?": "paddock-field",
            "What is the soil moisture in Paddock B?": "paddock",
            "How wet is Paddock B?": "paddock",
        }
        for question, intent in cases.items():
            with self.subTest(question=question):
                self.assertEqual(route_question(question).intent, intent)
        self.assertEqual(route_question("What is the temperature in Paddock B?").measurement, "air_temperature_c")
        self.assertEqual(route_question("What is the temperature in Paddock number 2?").paddock_name, "Paddock number 2")

    def test_numeric_word_and_previous_name_aliases_keep_the_same_identity(self) -> None:
        paddocks = self._paddocks()
        aliases = {"paddock b": (20,)}
        for reference in ("Paddock 2", "Paddock two", "Paddock number 2", "Paddock B", "number 2"):
            with self.subTest(reference=reference):
                result = resolve_paddock(reference, paddocks, aliases)
                self.assertEqual((result.status, result.paddock.id, result.paddock.name), ("resolved", 20, "North Flat"))

    def test_out_of_range_ordinal_is_explainable(self) -> None:
        result = resolve_paddock("Paddock 17", self._paddocks(), {})
        self.assertEqual(result.status, "paddock-out-of-range")
        self.assertIn("Paddock A", result.suggestions)

    @patch("app.farm_data.fetch_all")
    def test_summary_lists_the_catalogue_current_values_and_provenance(self, fetch_all) -> None:
        fetch_all.return_value = [self._reading("Paddock A", 10), self._reading()]
        result = latest_paddock_summary("Paddock B")
        self.assertEqual(result.intent, "paddock_summary")
        self.assertIn("Paddock B air temperature: 17.20 °C.", result.facts)
        self.assertIn("Paddock B soil electrical conductivity: 0.55 mS/cm.", result.facts)
        self.assertTrue(any("Reading time:" in fact for fact in result.facts))

    @patch("app.farm_data.fetch_one", return_value={"total_paddocks": 4})
    @patch("app.farm_data.active_paddocks")
    def test_inventory_distinguishes_active_from_historical_records(self, active, _) -> None:
        active.return_value = (PaddockIdentity(1, "Paddock A", 1, 1), PaddockIdentity(2, "Paddock B", 2, 1))
        self.assertEqual(
            farm_inventory_count().facts,
            ("Active monitored paddocks: 2.", "Active sensor nodes: 2.", "Total paddock records, including inactive/historical paddocks: 4."),
        )

    @patch("app.app.get_grounding_data")
    def test_contextual_follow_up_reuses_the_previous_measurement(self, grounding) -> None:
        _conversation_states.clear()
        grounding.return_value = GroundingData("paddock-field", ("verified",))
        first = asyncio.run(ask(AskRequest(question="What is the temperature in Paddock A?")))
        second = asyncio.run(ask(AskRequest(question="What about Paddock 2?", conversation_id=first.conversation_id)))
        self.assertEqual(second.intent, "paddock-field")
        self.assertEqual(grounding.call_args.args[:3], ("paddock-field", "Paddock 2", "air_temperature_c"))

    def test_existing_patek_and_stopword_regressions_remain_safe(self) -> None:
        self.assertEqual(route_question("Which paddock is currently the most dry?").paddock_name, None)
        self.assertEqual(route_question("What about Paddock 2?").intent, "contextual-follow-up")


if __name__ == "__main__":
    unittest.main()
