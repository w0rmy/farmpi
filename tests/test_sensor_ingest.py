"""Tests for deterministic sensor-reading storage."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.sensor_ingest import UnknownSensor, store_sensor_reading


class SensorStorageTests(unittest.TestCase):
    @patch("app.sensor_ingest.execute", return_value=42)
    @patch("app.sensor_ingest.fetch_one")
    def test_registered_sensor_is_stored(self, fetch_one, execute) -> None:
        fetch_one.return_value = {
            "sensor_node_id": 7,
            "node_uid": "test-moisture-a",
            "paddock_name": "Paddock A",
        }

        stored = store_sensor_reading(
            "test-moisture-a",
            17.826,
            16.284,
            73.945,
            6.278,
            12345.678,
            True,
        )

        self.assertEqual(stored.reading_id, 42)
        self.assertEqual(stored.sensor_uid, "test-moisture-a")
        self.assertEqual(stored.paddock_name, "Paddock A")
        self.assertEqual(stored.soil_moisture_pct, 17.83)
        self.assertEqual(stored.air_temperature_c, 16.28)
        self.assertEqual(stored.relative_humidity_pct, 73.94)
        self.assertEqual(stored.soil_ph, 6.28)
        self.assertEqual(stored.light_lux, 12345.68)
        self.assertTrue(stored.simulated)
        execute.assert_called_once()

    @patch("app.sensor_ingest.fetch_one", return_value=None)
    def test_unknown_sensor_is_rejected(self, fetch_one) -> None:
        with self.assertRaises(UnknownSensor):
            store_sensor_reading("not-registered", 20.0, 16.0, 70.0, 6.2, 1000.0, True)


if __name__ == "__main__":
    unittest.main()
