"""Tests for deterministic current environmental grounding facts."""

from __future__ import annotations

from datetime import datetime
import unittest
from unittest.mock import patch

from app.farm_data import get_environment_snapshot, get_grounding_data, historical_grounding
from app.question_router import route_question


class FarmDataTests(unittest.TestCase):
    def _row(self) -> dict[str, object]:
        return {
            "id": 1,
            "name": "Paddock A",
            "soil_moisture_pct": 18.25,
            "soil_temperature_c": 13.5,
            "air_temperature_c": 16.5,
            "relative_humidity_pct": 72.0,
            "soil_ph": 6.3,
            "soil_ec_ms_cm": 0.52,
            "light_lux": 12345.0,
            "rainfall_mm": 0.25,
            "barometric_pressure_hpa": 1012.5,
            "wind_speed_kmh": 8.0,
            "wind_direction_deg": 225.0,
            "pasture_height_cm": 14.5,
            "leaf_wetness_pct": 24.0,
            "recorded_at": datetime(2026, 8, 26, 9, 0, 0),
            "sensor_count": 1,
            "contains_simulated": 1,
        }

    @patch("app.farm_data.fetch_all")
    def test_current_environment_snapshot_has_all_fields(self, fetch_all) -> None:
        fetch_all.return_value = [self._row()]
        reading = get_environment_snapshot()[0]
        self.assertEqual(reading.air_temperature_c, 16.5)
        self.assertEqual(reading.relative_humidity_pct, 72.0)
        self.assertEqual(reading.soil_ph, 6.3)
        self.assertEqual(reading.soil_ec_ms_cm, 0.52)
        self.assertEqual(reading.pasture_height_cm, 14.5)
        self.assertEqual(reading.light_lux, 12345.0)

    @patch("app.farm_data.fetch_all")
    def test_named_measurements_use_retrieved_latest_facts(self, fetch_all) -> None:
        fetch_all.return_value = [self._row()]
        cases = (
            ("What is the temperature in Paddock A?", "Paddock A air temperature: 16.50 °C."),
            ("What is Paddock A's humidity?", "Paddock A relative humidity: 72.00%."),
            ("What is the soil pH in Paddock A?", "Paddock A soil pH: 6.30."),
            ("What is the light level in Paddock A?", "Paddock A light: 12345 lux."),
            ("What is the soil EC in Paddock A?", "Paddock A soil electrical conductivity: 0.52 mS/cm."),
            ("What is the pasture height in Paddock A?", "Paddock A pasture height: 14.5 cm."),
        )
        for question, expected_fact in cases:
            with self.subTest(question=question):
                route = route_question(question)
                grounding = get_grounding_data(
                    route.intent,
                    route.paddock_name,
                    route.measurement,
                )
                self.assertIn(expected_fact, grounding.facts)
                self.assertIn("Reading time: 2026-08-26 09:00:00 UTC.", grounding.facts)
                self.assertIn("The result includes simulated test readings.", grounding.facts)

    @patch("app.farm_data.fetch_all")
    def test_renamed_paddock_query_resolves_current_database_name(self, fetch_all) -> None:
        row = self._row() | {"name": "North Flat"}
        fetch_all.return_value = [row]
        route = route_question("What is the pasture height in North Flat?")
        grounding = get_grounding_data(route.intent, route.paddock_name, route.measurement)
        self.assertIn("North Flat pasture height: 14.5 cm.", grounding.facts)

    @patch("app.farm_data._historical_rows")
    def test_historical_rain_and_pasture_change_are_deterministic(self, historical_rows) -> None:
        historical_rows.return_value = (
            [{"value": 0.2}, {"value": 0.3}, {"value": 0.0}],
            "North Flat",
        )
        rain = historical_grounding("rainfall_mm", "sum", 60, "North Flat")
        self.assertIn("North Flat total rainfall over the last 60 minutes: 0.50 mm.", rain.facts)
        historical_rows.return_value = (
            [{"value": 10.0}, {"value": 12.5}],
            "North Flat",
        )
        change = historical_grounding("pasture_height_cm", "change", 1440, "North Flat")
        self.assertIn("North Flat change pasture height over the last 1440 minutes: 2.5 cm", change.facts[0])

    def test_help_grounding_uses_declared_capabilities_without_database(self) -> None:
        grounding = get_grounding_data("help")
        self.assertEqual(grounding.intent, "help")
        self.assertTrue(any("air temperature" in fact for fact in grounding.facts))
        self.assertTrue(any("does not currently provide" in fact for fact in grounding.facts))


if __name__ == "__main__":
    unittest.main()
