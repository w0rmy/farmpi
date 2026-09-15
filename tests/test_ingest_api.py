"""Tests for the FarmPi sensor-ingest boundary."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.ingest_api import SensorReadingRequest, TIME_SYNC_THRESHOLD_SECONDS, _device_observation, _require_ingest_token
from app.measurements import MEASUREMENTS, OPTIONAL_MEASUREMENT_KEYS, STANDARD_NODE_KEYS


BASELINE = {
    "sensor": "test-moisture-a", "soil_moisture_pct": 18.25,
    "soil_temperature_c": 13.0, "air_temperature_c": 16.5,
    "relative_humidity_pct": 72.0, "light_lux": 12000.0,
    "barometric_pressure_hpa": 1013.2, "simulated": True,
}
VALID = BASELINE | {
    "soil_ph": 6.3, "soil_ec_ms_cm": 0.5, "rainfall_mm": 0.1,
    "wind_speed_kmh": 8.0, "wind_direction_deg": 225.0,
    "pasture_height_cm": 14.0, "leaf_wetness_pct": 12.0,
}


class SensorIngestTests(unittest.TestCase):
    def test_valid_payload_with_all_capabilities(self) -> None:
        request = SensorReadingRequest(**VALID)
        self.assertEqual(request.sensor, "test-moisture-a")
        self.assertTrue(request.simulated)
        self.assertEqual(request.soil_ph, 6.3)

    def test_standard_node_payload_does_not_require_add_ons(self) -> None:
        request = SensorReadingRequest(**BASELINE)
        self.assertEqual(
            {key for key in STANDARD_NODE_KEYS if getattr(request, key) is not None},
            set(STANDARD_NODE_KEYS),
        )
        self.assertTrue(all(getattr(request, key) is None for key in OPTIONAL_MEASUREMENT_KEYS))

    def test_missing_standard_measurement_is_rejected(self) -> None:
        payload = dict(BASELINE)
        payload.pop("soil_moisture_pct")
        with self.assertRaises(ValidationError):
            SensorReadingRequest(**payload)

    def test_invalid_clock_requests_sync_without_a_1970_observation(self) -> None:
        request = SensorReadingRequest(**(VALID | {"clock_valid": False, "device_time_unix": 0, "sample_seq": 9}))
        observed, valid, offset, sync = _device_observation(request, datetime(2026, 8, 27, tzinfo=timezone.utc))
        self.assertIsNone(observed)
        self.assertFalse(valid)
        self.assertIsNone(offset)
        self.assertTrue(sync)

    def test_large_clock_offset_requests_sync(self) -> None:
        received = datetime(2026, 8, 27, tzinfo=timezone.utc)
        request = SensorReadingRequest(**(VALID | {"clock_valid": True, "device_time_unix": int(received.timestamp()) - TIME_SYNC_THRESHOLD_SECONDS - 1}))
        _, valid, offset, sync = _device_observation(request, received)
        self.assertTrue(valid)
        self.assertEqual(offset, TIME_SYNC_THRESHOLD_SECONDS + 1)
        self.assertTrue(sync)

    def test_catalogue_ranges_are_validated_when_values_are_supplied(self) -> None:
        for item in MEASUREMENTS:
            with self.subTest(field=item.key), self.assertRaises(ValidationError):
                SensorReadingRequest(**(VALID | {item.key: item.maximum + 0.1}))

    def test_optional_null_is_allowed(self) -> None:
        request = SensorReadingRequest(**(BASELINE | {"rainfall_mm": None}))
        self.assertIsNone(request.rainfall_mm)

    def test_sensor_uid_format_is_validated(self) -> None:
        with self.assertRaises(ValidationError):
            SensorReadingRequest(**(VALID | {"sensor": "bad sensor uid"}))

    def test_valid_bearer_token(self) -> None:
        with patch.dict(os.environ, {"FARMPI_INGEST_TOKEN": "alpha-token"}):
            _require_ingest_token("Bearer alpha-token")

    def test_invalid_bearer_token_is_rejected(self) -> None:
        with patch.dict(os.environ, {"FARMPI_INGEST_TOKEN": "alpha-token"}):
            with self.assertRaises(HTTPException) as captured:
                _require_ingest_token("Bearer wrong-token")
        self.assertEqual(captured.exception.status_code, 401)

    def test_missing_server_token_reports_unconfigured(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as captured:
                _require_ingest_token("Bearer anything")
        self.assertEqual(captured.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
