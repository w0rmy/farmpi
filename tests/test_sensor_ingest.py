"""Tests for deterministic sensor-reading storage."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.measurements import MEASUREMENTS, OPTIONAL_MEASUREMENT_KEYS, STANDARD_NODE_KEYS
from app.sensor_ingest import UnknownSensor, store_sensor_reading, validate_reading_values


BASELINE_VALUES = {
    "soil_moisture_pct": 17.826, "soil_temperature_c": 13.284,
    "air_temperature_c": 16.284, "relative_humidity_pct": 73.945,
    "light_lux": 12345.678, "barometric_pressure_hpa": 1012.34,
}
VALUES = BASELINE_VALUES | {
    "soil_ph": 6.278, "soil_ec_ms_cm": 0.456,
    "rainfall_mm": 0.25, "wind_speed_kmh": 12.34,
    "wind_direction_deg": 225.5, "pasture_height_cm": 14.56,
    "leaf_wetness_pct": 23.45,
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

    @patch("app.sensor_ingest.execute", return_value=43)
    @patch("app.sensor_ingest.fetch_one")
    def test_standard_node_stores_nulls_for_uninstalled_add_ons(self, fetch_one, execute) -> None:
        fetch_one.return_value = {"sensor_node_id": 8, "node_uid": "standard-node", "paddock_name": "Paddock B"}
        stored = store_sensor_reading("standard-node", False, **BASELINE_VALUES)
        self.assertEqual(set(stored.values), set(STANDARD_NODE_KEYS))
        self.assertTrue(all(key not in stored.values for key in OPTIONAL_MEASUREMENT_KEYS))
        params = execute.call_args.args[1]
        measurement_params = params[1:1 + len(MEASUREMENTS)]
        by_key = dict(zip((item.key for item in MEASUREMENTS), measurement_params))
        self.assertTrue(all(by_key[key] is not None for key in STANDARD_NODE_KEYS))
        self.assertTrue(all(by_key[key] is None for key in OPTIONAL_MEASUREMENT_KEYS))

    @patch("app.sensor_ingest.execute")
    @patch("app.sensor_ingest.fetch_one")
    def test_retry_sequence_returns_existing_row_with_missing_add_ons(self, fetch_one, execute) -> None:
        duplicate = {
            "id": 41,
            **{item.key: (VALUES[item.key] if item.key in VALUES else None) for item in MEASUREMENTS},
            "simulated": True,
            "observed_at": __import__("datetime").datetime(2026, 1, 1),
            "received_at": __import__("datetime").datetime(2026, 1, 1),
            "clock_valid": True,
            "clock_offset_seconds": 1.0,
            "clock_out_of_tolerance": False,
            "sample_seq": 123,
        }
        duplicate["soil_ph"] = None
        fetch_one.side_effect = [
            {"sensor_node_id": 7, "node_uid": "test-moisture-a", "paddock_name": "Paddock A"},
            duplicate,
        ]
        stored = store_sensor_reading("test-moisture-a", True, sample_seq=123, **VALUES)
        self.assertTrue(stored.deduplicated)
        self.assertEqual(stored.reading_id, 41)
        self.assertNotIn("soil_ph", stored.values)
        execute.assert_not_called()

    def test_catalogue_validates_supplied_optional_field(self) -> None:
        invalid = VALUES | {"pasture_height_cm": 301.0}
        with self.assertRaises(ValueError):
            validate_reading_values(invalid)

    def test_missing_standard_measurement_is_rejected(self) -> None:
        missing = dict(BASELINE_VALUES)
        missing.pop("air_temperature_c")
        with self.assertRaises(ValueError):
            validate_reading_values(missing)

    def test_optional_measurements_may_be_omitted(self) -> None:
        validated = validate_reading_values(BASELINE_VALUES)
        self.assertEqual(set(validated), set(STANDARD_NODE_KEYS))

    @patch("app.sensor_ingest.fetch_one", return_value=None)
    def test_unknown_sensor_is_rejected(self, fetch_one) -> None:
        with self.assertRaises(UnknownSensor):
            store_sensor_reading("not-registered", True, **VALUES)


if __name__ == "__main__":
    unittest.main()
