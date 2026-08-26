"""Tests for deterministic sensor-reading storage."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.measurements import MEASUREMENTS
from app.sensor_ingest import UnknownSensor, store_sensor_reading, validate_reading_values


VALUES = {
    "soil_moisture_pct": 17.826, "soil_temperature_c": 13.284,
    "air_temperature_c": 16.284, "relative_humidity_pct": 73.945,
    "soil_ph": 6.278, "soil_ec_ms_cm": 0.456, "light_lux": 12345.678,
    "rainfall_mm": 0.25, "barometric_pressure_hpa": 1012.34,
    "wind_speed_kmh": 12.34, "wind_direction_deg": 225.5,
    "pasture_height_cm": 14.56, "leaf_wetness_pct": 23.45,
}


class SensorStorageTests(unittest.TestCase):
    @patch("app.sensor_ingest.execute", return_value=42)
    @patch("app.sensor_ingest.fetch_one")
    def test_registered_sensor_is_stored(self, fetch_one, execute) -> None:
        fetch_one.return_value = {"sensor_node_id": 7, "node_uid": "test-moisture-a", "paddock_name": "Paddock A"}
        stored = store_sensor_reading("test-moisture-a", True, **VALUES)
        self.assertEqual(stored.reading_id, 42)
        self.assertEqual(stored.sensor_uid, "test-moisture-a")
        self.assertEqual(stored.paddock_name, "Paddock A")
        self.assertEqual(stored.soil_moisture_pct, 17.83)
        self.assertEqual(stored.soil_ec_ms_cm, 0.46)
        self.assertEqual(stored.barometric_pressure_hpa, 1012.3)
        self.assertEqual(stored.wind_direction_deg, 226.0)
        self.assertTrue(stored.simulated)
        execute.assert_called_once()
        self.assertEqual(len(execute.call_args.args[1]), len(MEASUREMENTS) + 10)

    @patch("app.sensor_ingest.execute")
    @patch("app.sensor_ingest.fetch_one")
    def test_retry_sequence_returns_existing_row_without_second_insert(self, fetch_one, execute) -> None:
        fetch_one.side_effect = [
            {"sensor_node_id": 7, "node_uid": "test-moisture-a", "paddock_name": "Paddock A"},
            {"id": 41, **VALUES, "simulated": True, "observed_at": __import__("datetime").datetime(2026, 1, 1), "received_at": __import__("datetime").datetime(2026, 1, 1), "clock_valid": True, "clock_offset_seconds": 1.0, "clock_out_of_tolerance": False, "sample_seq": 123},
        ]
        stored = store_sensor_reading("test-moisture-a", True, sample_seq=123, **VALUES)
        self.assertTrue(stored.deduplicated)
        self.assertEqual(stored.reading_id, 41)
        execute.assert_not_called()

    def test_catalogue_validates_every_field(self) -> None:
        invalid = VALUES | {"pasture_height_cm": 301.0}
        with self.assertRaises(ValueError):
            validate_reading_values(invalid)

    @patch("app.sensor_ingest.fetch_one", return_value=None)
    def test_unknown_sensor_is_rejected(self, fetch_one) -> None:
        with self.assertRaises(UnknownSensor):
            store_sensor_reading("not-registered", True, **VALUES)


if __name__ == "__main__":
    unittest.main()
