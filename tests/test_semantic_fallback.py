"""Regression coverage for the bounded semantic-interpreter failure policy."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from app.app import AskRequest, app, ask
from app.semantic_interpreter import SemanticInterpretationError


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

    @patch("app.app.interpret_semantically", side_effect=SemanticInterpretationError("bad JSON"))
    def test_general_animal_health_question_fails_open_to_learning(self, _) -> None:
        response = asyncio.run(ask(AskRequest(question="Why do cows get milk fever?")))
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertIn("General agricultural explanation:", response.answer)
        self.assertNotIn("cannot establish the cause", response.answer.casefold())

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


if __name__ == "__main__":
    unittest.main()
