"""Contract tests for the controlled, embedded FarmPi course."""

from __future__ import annotations

import asyncio
import unittest

from fastapi.testclient import TestClient

from app.app import AskRequest, app, ask, learning_course
from app.learning import LEARNING_OUTCOMES, MODULES, OUTCOME_IDS, course_payload


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "A controlled learning explanation."}}]}


class _RecordingClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def post(self, _: str, **kwargs: object) -> _Response:
        self.payloads.append(kwargs["json"])
        return _Response()


class LearningCourseTests(unittest.TestCase):
    def test_course_has_unique_ids_and_valid_references(self) -> None:
        self.assertEqual(len(MODULES), 5)
        self.assertEqual(len({module.id for module in MODULES}), len(MODULES))
        self.assertEqual(len({outcome.id for outcome in LEARNING_OUTCOMES}), len(LEARNING_OUTCOMES))
        module_ids = {module.id for module in MODULES}
        allowed_intents = {
            "capability", "agriculture-learning", "conversation", "comparison", "ranking", "historical", "farm-average",
            "driest", "wettest", "education", "agriculture-research", "semantic-clarification", "contextual-follow-up",
        }
        for module in MODULES:
            self.assertTrue(module.learning_outcomes)
            self.assertTrue(set(module.learning_outcomes) <= OUTCOME_IDS)
            self.assertTrue(set(module.try_activity.success_intents) <= allowed_intents)
            self.assertTrue(set(module.response_intents) <= allowed_intents)
            self.assertTrue(module.try_activity.example_question)
            self.assertTrue(module.prompt_context)
            self.assertTrue(module.next_module_id is None or module.next_module_id in module_ids)

    def test_course_endpoint_is_deterministic_and_exposes_all_steps(self) -> None:
        first = asyncio.run(learning_course())
        second = asyncio.run(learning_course())
        self.assertEqual(first, second)
        self.assertEqual(first, course_payload())
        with TestClient(app) as client:
            response = client.get("/api/learning/course")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), first)
        self.assertEqual(len(first["modules"]), 5)
        for module in first["modules"]:
            self.assertIn("try", module)
            self.assertIn("understanding_check", module)
            self.assertIn("response_intents", module)

    def test_unknown_course_module_is_rejected(self) -> None:
        with TestClient(app) as client:
            response = client.post("/api/ask", json={"question": "Why do cows get milk fever?", "course_module_id": "not-a-course-module"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Unknown course_module_id.")

    def test_only_reviewed_module_context_reaches_the_model(self) -> None:
        old_client = getattr(app.state, "http_client", None)
        client = _RecordingClient()
        app.state.http_client = client
        try:
            response = asyncio.run(ask(AskRequest(
                question="Why do cows get milk fever?", course_module_id="using-the-ai-learning-assistant",
            )))
        finally:
            app.state.http_client = old_client
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertIn("reviewed-course-module", [entry["kind"] for entry in response.provenance])
        system_text = "\n".join(
            message["content"] for message in client.payloads[-1]["messages"] if message["role"] == "system"
        )
        self.assertIn("Reviewed course context", system_text)
        self.assertIn("AI support responsibly", system_text)
        self.assertNotIn("not-a-course-module", system_text)


if __name__ == "__main__":
    unittest.main()
