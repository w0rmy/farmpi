"""Tests for the FarmPi sensor-ingest boundary."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.ingest_api import SensorReadingRequest, _require_ingest_token


class SensorIngestTests(unittest.TestCase):
    def test_valid_payload(self) -> None:
        request = SensorReadingRequest(
            sensor="test-moisture-a",
            soil_moisture_pct=18.25,
            air_temperature_c=16.5,
            relative_humidity_pct=72.0,
            soil_ph=6.3,
            light_lux=12000.0,
            simulated=True,
        )
        self.assertEqual(request.sensor, "test-moisture-a")
        self.assertEqual(request.soil_moisture_pct, 18.25)
        self.assertEqual(request.air_temperature_c, 16.5)
        self.assertEqual(request.relative_humidity_pct, 72.0)
        self.assertEqual(request.soil_ph, 6.3)
        self.assertEqual(request.light_lux, 12000.0)
        self.assertTrue(request.simulated)

    def test_moisture_range_is_validated(self) -> None:
        with self.assertRaises(ValidationError):
            SensorReadingRequest(
                sensor="test-moisture-a",
                soil_moisture_pct=101.0,
                air_temperature_c=16.0,
                relative_humidity_pct=70.0,
                soil_ph=6.2,
                light_lux=1000.0,
            )

    def test_environment_ranges_are_validated(self) -> None:
        valid = {
            "sensor": "test-moisture-a",
            "soil_moisture_pct": 20.0,
            "air_temperature_c": 16.0,
            "relative_humidity_pct": 70.0,
            "soil_ph": 6.2,
            "light_lux": 1000.0,
        }
        for field, invalid_value in (
            ("air_temperature_c", 61.0),
            ("relative_humidity_pct", -1.0),
            ("soil_ph", 14.1),
            ("light_lux", -0.1),
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SensorReadingRequest(**(valid | {field: invalid_value}))

    def test_sensor_uid_format_is_validated(self) -> None:
        with self.assertRaises(ValidationError):
            SensorReadingRequest(
                sensor="bad sensor uid",
                soil_moisture_pct=20.0,
                air_temperature_c=16.0,
                relative_humidity_pct=70.0,
                soil_ph=6.2,
                light_lux=1000.0,
            )

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
