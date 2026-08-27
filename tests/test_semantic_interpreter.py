"""Tests for the open learner-language interpretation boundary."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from app.app import AskRequest, _pending_renames, app, ask
from app.knowledge_sources import format_source_context, provenance_for_sources
from app.paddock_admin import RenameProposal
from app.question_router import route_question
from app.semantic_interpreter import (
    build_interpretation_payload,
    needs_semantic_interpretation,
    parse_semantic_interpretation,
    route_from_interpretation,
)


class SemanticInterpreterTests(unittest.TestCase):
    def test_polite_and_exact_rename_are_sent_for_semantic_interpretation(self) -> None:
        for question in (
            "Rename Paddock A to North Flat",
            "Could you please rename Paddock A to North Flat please?",
            "Can we call field A North Flat?",
        ):
            with self.subTest(question=question):
                fast = route_question(question)
                self.assertTrue(needs_semantic_interpretation(question, fast))

    def test_rename_interpretation_maps_to_deterministic_rename_route(self) -> None:
        interpretation = parse_semantic_interpretation(json.dumps({
            "intent": "rename",
            "confidence": 0.96,
            "paddock_name": "field a",
            "new_paddock_name": "North Flat",
            "measurement": None,
            "operation": None,
            "window_minutes": None,
            "topic": None,
            "reason": "The learner wants a name change.",
        }))
        route = route_from_interpretation(interpretation)
        self.assertEqual(route.intent, "rename-request")
        self.assertEqual(route.paddock_name, "Paddock A")
        self.assertEqual(route.new_paddock_name, "North Flat")

    def test_colloquial_temperature_request_maps_to_current_data(self) -> None:
        interpretation = parse_semantic_interpretation(json.dumps({
            "intent": "current",
            "confidence": 0.91,
            "paddock_name": "Paddock B",
            "new_paddock_name": None,
            "measurement": "air_temperature_c",
            "operation": "current",
            "window_minutes": None,
            "topic": None,
            "reason": "B means Paddock B in the supplied farm context.",
        }))
        route = route_from_interpretation(interpretation)
        self.assertEqual((route.intent, route.paddock_name, route.measurement), ("paddock-field", "Paddock B", "air_temperature_c"))

    def test_general_farming_question_becomes_learning_not_a_boundary_refusal(self) -> None:
        interpretation = parse_semantic_interpretation(json.dumps({
            "intent": "learning",
            "confidence": 0.98,
            "paddock_name": None,
            "new_paddock_name": None,
            "measurement": None,
            "operation": None,
            "window_minutes": None,
            "topic": "milk fever in dairy cows",
            "reason": "General agricultural education.",
        }))
        route = route_from_interpretation(interpretation)
        self.assertEqual(route.intent, "agriculture-learning")
        self.assertEqual(route.education_key, "milk fever in dairy cows")

    def test_explicit_source_question_becomes_research_route(self) -> None:
        interpretation = parse_semantic_interpretation(json.dumps({
            "intent": "research",
            "confidence": 0.97,
            "paddock_name": None,
            "new_paddock_name": None,
            "measurement": None,
            "operation": None,
            "window_minutes": None,
            "topic": "DairyNZ irrigation scheduling",
            "reason": "The learner explicitly asked what DairyNZ says.",
        }))
        self.assertEqual(route_from_interpretation(interpretation).intent, "agriculture-research")

    def test_low_confidence_action_requires_clarification(self) -> None:
        interpretation = parse_semantic_interpretation('{"intent":"rename","confidence":0.31,"paddock_name":"Paddock A","new_paddock_name":"North Flat"}')
        self.assertEqual(route_from_interpretation(interpretation).intent, "semantic-clarification")

    def test_interpreter_prompt_is_json_only_and_language_tolerant(self) -> None:
        payload = build_interpretation_payload("Give us the temp for B please", ("Paddock A", "Paddock B"))
        system = payload["messages"][0]["content"]
        self.assertIn("colloquial", system)
        self.assertIn("accented/transcribed", system)
        self.assertIn("Return ONE JSON object only", system)
        self.assertIn("trailing 'please'", system)
        self.assertEqual(payload["max_tokens"], 192)

    def test_dairynz_irrigation_source_has_reviewed_claims(self) -> None:
        context, sources = format_source_context("What does DairyNZ say about irrigation scheduling?")
        self.assertTrue(any(source.organisation == "DairyNZ" for source in sources))
        self.assertIn("refill point", context)
        self.assertIn("Do not say they were searched live", context)
        provenance = provenance_for_sources(sources)
        self.assertTrue(any(item["use"] == "reviewed-claim-support" for item in provenance))


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": self._content}}]}


class _SequenceClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls = 0

    async def post(self, _url: str, json: dict[str, object]) -> _FakeResponse:
        self.calls += 1
        if not self.responses:
            raise AssertionError("Unexpected extra model request")
        return _FakeResponse(self.responses.pop(0))


class OpenLearningAskTests(unittest.TestCase):
    @patch("app.app.current_paddock_names", return_value=())
    def test_broad_dairy_question_uses_semantic_learning_path(self, _names) -> None:
        client = _SequenceClient([
            '{"intent":"learning","confidence":0.99,"paddock_name":null,"new_paddock_name":null,"measurement":null,"operation":null,"window_minutes":null,"topic":"milk fever in dairy cows","reason":"general dairy learning"}',
            "Milk fever is a metabolic disorder around calving involving low blood calcium. Would you like me to explain why calcium demand rises around calving?",
        ])
        old_client = getattr(app.state, "http_client", None)
        app.state.http_client = client
        try:
            response = asyncio.run(ask(AskRequest(question="Why do cows get milk fever?")))
        finally:
            if old_client is None:
                delattr(app.state, "http_client")
            else:
                app.state.http_client = old_client
        self.assertEqual(response.intent, "agriculture-learning")
        self.assertIn("metabolic disorder", response.answer)
        self.assertEqual(response.semantic_interpretation["topic"], "milk fever in dairy cows")
        self.assertTrue(any(item.get("kind") == "general-explanation" for item in response.provenance))
        self.assertEqual(client.calls, 2)

    @patch("app.app.prepare_rename")
    @patch("app.app.current_paddock_names", return_value=("Paddock A",))
    def test_polite_rename_is_interpreted_then_enters_deterministic_confirmation(self, _names, prepare) -> None:
        _pending_renames.clear()
        prepare.return_value = RenameProposal(7, "Paddock A", "North Flat")
        client = _SequenceClient([
            '{"intent":"rename","confidence":0.98,"paddock_name":"Paddock A","new_paddock_name":"North Flat","measurement":null,"operation":null,"window_minutes":null,"topic":null,"reason":"polite rename request"}',
        ])
        old_client = getattr(app.state, "http_client", None)
        app.state.http_client = client
        try:
            response = asyncio.run(ask(AskRequest(question="Could you please rename Paddock A to North Flat please?")))
        finally:
            if old_client is None:
                delattr(app.state, "http_client")
            else:
                app.state.http_client = old_client
        self.assertEqual(response.intent, "rename-request")
        self.assertIsNotNone(response.confirmation_id)
        prepare.assert_called_once_with("Paddock A", "North Flat")
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
