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
            simulated=True,
        )
        self.assertEqual(request.sensor, "test-moisture-a")
        self.assertEqual(request.soil_moisture_pct, 18.25)
        self.assertTrue(request.simulated)

    def test_moisture_range_is_validated(self) -> None:
        with self.assertRaises(ValidationError):
            SensorReadingRequest(
                sensor="test-moisture-a",
                soil_moisture_pct=101.0,
            )

    def test_sensor_uid_format_is_validated(self) -> None:
        with self.assertRaises(ValidationError):
            SensorReadingRequest(
                sensor="bad sensor uid",
                soil_moisture_pct=20.0,
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
