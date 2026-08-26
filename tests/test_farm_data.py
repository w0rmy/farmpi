"""Tests for deterministic current environmental grounding facts."""

from __future__ import annotations

from datetime import datetime
import unittest
from unittest.mock import patch

from app.farm_data import get_environment_snapshot, get_grounding_data


class FarmDataTests(unittest.TestCase):
    def _row(self) -> dict[str, object]:
        return {
            "name": "Paddock A",
            "soil_moisture_pct": 18.25,
            "air_temperature_c": 16.5,
            "relative_humidity_pct": 72.0,
            "soil_ph": 6.3,
            "light_lux": 12345.0,
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
        self.assertEqual(reading.light_lux, 12345.0)

    @patch("app.farm_data.fetch_all")
    def test_named_temperature_uses_retrieved_fact(self, fetch_all) -> None:
        fetch_all.return_value = [self._row()]
        grounding = get_grounding_data(
            "paddock-field", "Paddock A", "air_temperature_c"
        )
        self.assertIn("Paddock A air temperature: 16.50 °C.", grounding.facts)
        self.assertIn("The result includes simulated test readings.", grounding.facts)

    def test_help_grounding_uses_declared_capabilities_without_database(self) -> None:
        grounding = get_grounding_data("help")
        self.assertEqual(grounding.intent, "help")
        self.assertTrue(any("air temperature" in fact for fact in grounding.facts))
        self.assertTrue(any("does not currently provide" in fact for fact in grounding.facts))


if __name__ == "__main__":
    unittest.main()
