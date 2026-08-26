"""Tests for the FarmPi sensor-ingest boundary."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.ingest_api import SensorReadingRequest, _require_ingest_token
from app.measurements import MEASUREMENTS


VALID = {
    "sensor": "test-moisture-a", "soil_moisture_pct": 18.25,
    "soil_temperature_c": 13.0, "air_temperature_c": 16.5,
    "relative_humidity_pct": 72.0, "soil_ph": 6.3, "soil_ec_ms_cm": 0.5,
    "light_lux": 12000.0, "rainfall_mm": 0.1, "barometric_pressure_hpa": 1013.2,
    "wind_speed_kmh": 8.0, "wind_direction_deg": 225.0,
    "pasture_height_cm": 14.0, "leaf_wetness_pct": 12.0, "simulated": True,
}


class SensorIngestTests(unittest.TestCase):
    def test_valid_payload(self) -> None:
        request = SensorReadingRequest(**VALID)
        self.assertEqual(request.sensor, "test-moisture-a")
        self.assertTrue(request.simulated)

    def test_catalogue_ranges_are_validated(self) -> None:
        for item in MEASUREMENTS:
            with self.subTest(field=item.key), self.assertRaises(ValidationError):
                SensorReadingRequest(**(VALID | {item.key: item.maximum + 0.1}))

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
