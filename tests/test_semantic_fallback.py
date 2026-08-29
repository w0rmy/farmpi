"""Regression coverage for the bounded semantic-interpreter failure policy."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from app.app import AskRequest, app, ask
from app.question_router import route_question
from app.semantic_interpreter import SemanticInterpretation, SemanticInterpretationError
from app.semantic_interpreter import needs_semantic_interpretation


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "Milk fever usually follows a sudden demand for calcium around calving."}}]}


class _AnswerClient:
    async def post(self, *_: object, **__: object) -> _Response:
        return _Response()


class SemanticFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_client = getattr(app.state, "http_client", None)
        app.state.http_client = _AnswerClient()

    def tearDown(self) -> None:
        app.state.http_client = self._old_client

    def test_farm_wide_mean_temperature_is_semantically_eligible(self) -> None:
        question = "What's the mean temperature over all the fields please?"
        fast = route_question(question)
        self.assertEqual((fast.intent, fast.measurement), ("conversation", "air_temperature_c"))
        self.assertTrue(needs_semantic_interpretation(question, fast))

    @patch("app.app.interpret_semantically", side_effect=SemanticInterpretationError("bad JSON"))
    def test_general_animal_health_question_fails_open_to_learning(self, _) -> None:
        response = asyncio.run(ask(AskRequest(question="Why do cows get milk fever?")))
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertIn("General model-knowledge explanation:", response.answer)
        self.assertNotIn("cannot establish the cause", response.answer.casefold())
        self.assertEqual(response.source_tier, "model-knowledge")

    @patch("app.app.prepare_rename")
    @patch("app.app.interpret_semantically", side_effect=SemanticInterpretationError("bad JSON"))
    def test_ambiguous_rename_fails_closed_without_a_write(self, _, prepare_rename) -> None:
        response = asyncio.run(ask(AskRequest(question="Rename Paddock A")))
        self.assertEqual(response.intent, "clarification")
        self.assertIn("could not safely determine", response.answer.casefold())
        prepare_rename.assert_not_called()
        self.assertIsNone(response.confirmation_id)

    @patch("app.app.interpret_semantically", side_effect=SemanticInterpretationError("invalid JSON"))
    def test_research_request_is_labelled_without_claiming_live_research(self, _) -> None:
        response = asyncio.run(ask(AskRequest(question="Could you research current sources about milk fever in cows?")))
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertTrue(response.answer.startswith("No live web research was performed."))
        self.assertEqual(response.source_category, "educational")

    @patch("app.app.interpret_semantically", side_effect=SemanticInterpretationError("invalid JSON"))
    def test_general_question_does_not_require_the_farm_database(self, _) -> None:
        response = asyncio.run(ask(AskRequest(question="What is mastitis?")))
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertEqual(response.source_tier, "model-knowledge")

    @patch("app.app.interpret_semantically", return_value=SemanticInterpretation("clarification", "general question"))
    def test_non_action_classifier_uncertainty_still_gets_a_learning_response(self, _) -> None:
        response = asyncio.run(ask(AskRequest(question="How do rainbows form?")))
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertIn("General model-knowledge explanation:", response.answer)


if __name__ == "__main__":
    unittest.main()
