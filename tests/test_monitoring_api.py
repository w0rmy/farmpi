from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.farm_data import GroundingData, NoFarmData, PaddockEnvironment
from app.monitoring_api import build_monitoring_overview, router
from app.paddock_resolver import PaddockIdentity


class MonitoringOverviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 27, 6, 30, tzinfo=timezone.utc)
        self.identities = (
            PaddockIdentity(1, "Bob's", 1, 1),
            PaddockIdentity(2, "Down by the Trough", 2, 1),
        )

    def environment(self, location_id: int, name: str, moisture: float, temperature: float, mode: str) -> PaddockEnvironment:
        observed = datetime(2026, 9, 27, 6, 28, tzinfo=timezone.utc)
        return PaddockEnvironment(
            id=location_id,
            name=name,
            values={"soil_moisture_pct": moisture, "air_temperature_c": temperature},
            received_at=observed,
            observed_at=observed,
            sensor_count=1,
            contains_simulated=mode == "SIMULATED",
            measurement_modes={"soil_moisture_pct": mode, "air_temperature_c": mode},
        )

    @patch("app.monitoring_api.analytics_grounding")
    @patch("app.monitoring_api.get_environment_snapshot")
    @patch("app.monitoring_api.active_paddocks")
    def test_overview_contains_structured_locations_farm_summary_and_chart(self, paddocks, snapshot, analytics) -> None:
        paddocks.return_value = self.identities
        snapshot.return_value = [
            self.environment(1, "Bob's", 30.0, 18.0, "SIMULATED"),
            self.environment(2, "Down by the Trough", 34.0, 20.0, "LIVE"),
        ]
        analytics.return_value = GroundingData(
            "historical",
            ("trend",),
            chart={"type": "line", "title": "Soil moisture", "series": []},
        )

        result = build_monitoring_overview(self.now)

        self.assertEqual(result["location_count"], 2)
        self.assertEqual(result["locations_with_readings_count"], 2)
        self.assertEqual(result["locations"][0]["name"], "Bob's")
        self.assertEqual(result["locations"][0]["measurements"][0]["age_seconds"], 120)
        moisture = next(item for item in result["farm_measurements"] if item["key"] == "soil_moisture_pct")
        self.assertEqual(moisture["value"], 32.0)
        self.assertEqual(moisture["source_mode"], "SIMULATED")
        self.assertEqual(moisture["contributing_locations"], 2)
        self.assertEqual(result["featured_chart"]["type"], "line")

    @patch("app.monitoring_api.analytics_grounding")
    @patch("app.monitoring_api.get_environment_snapshot", side_effect=NoFarmData("none"))
    @patch("app.monitoring_api.active_paddocks")
    def test_configured_location_remains_visible_without_current_reading(self, paddocks, snapshot, analytics) -> None:
        paddocks.return_value = self.identities
        analytics.return_value = GroundingData("historical", ("none",), chart=None)

        result = build_monitoring_overview(self.now)

        self.assertEqual(result["locations_with_readings_count"], 0)
        self.assertFalse(result["locations"][0]["has_reading"])
        self.assertEqual(result["locations"][0]["measurements"], [])
        self.assertEqual(result["farm_measurements"], [])
        self.assertIsNone(result["featured_chart"])

    @patch("app.monitoring_api.build_monitoring_overview")
    def test_endpoint_exposes_overview_contract(self, build) -> None:
        build.return_value = {
            "generated_at": self.now.isoformat(),
            "location_count": 0,
            "locations_with_readings_count": 0,
            "farm_measurements": [],
            "locations": [],
            "featured_chart": None,
        }
        app = FastAPI()
        app.include_router(router)

        response = TestClient(app).get("/api/monitoring/overview")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["location_count"], 0)
        build.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
