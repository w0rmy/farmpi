from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.app import app as base_app
from app.farm_data import GroundingData, NoFarmData, PaddockEnvironment
from app.monitoring_api import build_monitoring_overview, router
from app.main import app as composed_app
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

    @patch("app.monitoring_api.historical_rows_from")
    @patch("app.monitoring_api.active_paddocks")
    def test_compare_endpoint_uses_only_two_selected_locations(self, paddocks, historical_rows) -> None:
        paddocks.return_value = (
            PaddockIdentity(1, "Bob's paddock", 1, 1),
            PaddockIdentity(2, "Fred's paddock", 2, 1),
            PaddockIdentity(3, "Back Hill", 3, 1),
        )
        when = datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc)

        def rows_for(_key, _start, name):
            value = 30.0 if name == "Bob's paddock" else 36.0
            return ([{
                "name": name,
                "sensor_uid": "FP-001" if name == "Bob's paddock" else "FP-002",
                "analysis_at": when,
                "value": value,
                "simulated": True,
            }], name)

        historical_rows.side_effect = rows_for
        app = FastAPI()
        app.include_router(router)

        response = TestClient(app).get(
            "/api/monitoring/compare",
            params={
                "left_id": 1,
                "right_id": 2,
                "measurement": "soil_moisture_pct",
                "window_minutes": 1440,
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["intent"], "comparison")
        self.assertEqual(payload["left_location"]["name"], "Bob's paddock")
        self.assertEqual(payload["right_location"]["name"], "Fred's paddock")
        self.assertEqual({item["paddock"] for item in payload["evidence"]}, {"Bob's paddock", "Fred's paddock"})
        chart_names = {item["x"] for item in payload["chart"]["series"][0]["data"]}
        self.assertEqual(chart_names, {"Bob's paddock", "Fred's paddock"})
        self.assertNotIn("Back Hill", response.text)

    @patch("app.monitoring_api.active_paddocks")
    def test_compare_endpoint_rejects_same_or_missing_location(self, paddocks) -> None:
        paddocks.return_value = (
            PaddockIdentity(1, "Bob's paddock", 1, 1),
            PaddockIdentity(2, "Fred's paddock", 2, 1),
        )
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        same = client.get("/api/monitoring/compare", params={
            "left_id": 1, "right_id": 1, "measurement": "soil_moisture_pct", "window_minutes": 1440,
        })
        missing = client.get("/api/monitoring/compare", params={
            "left_id": 1, "right_id": 99, "measurement": "soil_moisture_pct", "window_minutes": 1440,
        })

        self.assertEqual(same.status_code, 422)
        self.assertEqual(missing.status_code, 404)

    def test_canonical_and_composed_applications_mount_monitoring_routes(self) -> None:
        for name, candidate in (("base", base_app), ("composed", composed_app)):
            with self.subTest(application=name):
                paths = {getattr(route, "path", None) for route in candidate.routes}
                self.assertIn("/api/monitoring/overview", paths)
                self.assertIn("/api/monitoring/compare", paths)

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
