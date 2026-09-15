"""Application prompts, optional course context, and dependency recovery."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.database import DatabaseUnavailable
from app.farm_data import GroundingData
from app.llm_compat import LLMCompatibleClient
from app.main import app


class RecordingClient:
    def __init__(self) -> None:
        self.payloads = []
        self.unavailable = False

    async def post(self, url, *, json):
        self.payloads.append(json)
        if self.unavailable:
            raise httpx.ConnectError("test model unavailable")
        system = json["messages"][0]["content"]
        if "FarmPi's user-intent interpreter" in system:
            content = '{"intent":"learning","confidence":0.95,"topic":"general information"}'
        else:
            content = "Here is a general explanation."
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "choices": [{"message": {"content": content}}],
        })


class ApplicationContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.model = RecordingClient()
        self.old_client = app.state.http_client
        self.addCleanup(setattr, app.state, "http_client", self.old_client)
        app.state.http_client = LLMCompatibleClient(self.model)
        patcher = patch("app.app.current_paddock_names", side_effect=DatabaseUnavailable("offline"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_nonfarm_question_uses_application_prompt_without_farm_reading(self) -> None:
        with patch("app.app.get_grounding_data") as readings:
            response = self.client.post("/api/ask", json={"question": "How do rainbows form?"})
        self.assertEqual(response.status_code, 200)
        readings.assert_not_called()
        payload = response.json()
        self.assertEqual(payload["intent"], "agriculture-learning")  # Existing API identifier.
        self.assertEqual(payload["source_tier"], "model-knowledge")
        self.assertEqual(payload["source_category"], "general")
        self.assertEqual(payload["spoken_answer"], payload["answer"])
        system = self.model.payloads[-1]["messages"][0]["content"]
        self.assertIn("farm-monitoring assistant", system)
        self.assertIn("it need not be agricultural", system)
        self.assertIn("never invent, alter or replace sensor/database facts", system)
        self.assertNotIn("This is an agricultural learning question", system)
        self.assertNotIn("Reviewed course context", system)

    def test_course_context_is_explicit_per_request_and_history_still_works(self) -> None:
        first = self.client.post("/api/ask", json={
            "question": "Explain how the assistant works.",
            "course_module_id": "using-the-ai-learning-assistant",
        }).json()
        self.assertIn("reviewed-course-module", [item["kind"] for item in first["provenance"]])
        self.assertIn("Reviewed course context", self.model.payloads[-1]["messages"][0]["content"])
        second = self.client.post("/api/ask", json={
            "question": "Explain that more simply.",
            "conversation_id": first["conversation_id"],
        }).json()
        messages = self.model.payloads[-1]["messages"]
        self.assertNotIn("Reviewed course context", messages[0]["content"])
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[-1]["content"], "Explain that more simply.")
        self.assertEqual(second["conversation_id"], first["conversation_id"])
        self.assertNotIn("reviewed-course-module", [item["kind"] for item in second["provenance"]])

    def test_model_failure_offers_recovery_and_graph_stays_deterministic(self) -> None:
        self.model.unavailable = True
        with patch("app.app.logger.warning"):
            response = self.client.post("/api/ask", json={"question": "How do rainbows form?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("readings and graphs", response.json()["answer"])
        self.assertIn("availability", [item["kind"] for item in response.json()["provenance"]])
        self.model.payloads.clear()
        chart = {"type": "line", "series": [{"name": "Farm average", "points": [{"label": "12:00", "value": 23.5}]}]}
        evidence = ({"source": "observational", "value": 23.5},)
        data = GroundingData("historical", ("Average soil moisture: 23.5%.",), evidence, chart=chart, source_category="calculated")
        with patch("app.app.analytics_grounding", return_value=data) as analytics:
            response = self.client.post("/api/ask", json={"question": "Show me the soil moisture over the last 24 hours."})
        self.assertEqual(response.status_code, 200)
        analytics.assert_called_once()
        self.assertEqual(response.json()["chart"], chart)
        self.assertEqual(response.json()["evidence"], list(evidence))
        self.assertEqual(response.json()["answer"], data.facts[0])
        self.assertEqual(self.model.payloads, [])


if __name__ == "__main__":
    unittest.main()
