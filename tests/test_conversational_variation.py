"""Conversation-shape tests: polite, colloquial and culturally varied wording."""

from __future__ import annotations

import json
import unittest

from app.question_router import route_question
from app.semantic_interpreter import needs_semantic_interpretation, parse_semantic_interpretation, route_from_interpretation


class ConversationalVariationTests(unittest.TestCase):
    def test_polite_and_indirect_rename_forms_do_not_get_trapped_as_plain_paddock_queries(self) -> None:
        variants = (
            "Can you rename Paddock A to North Flat?",
            "Could you please rename Paddock A to North Flat?",
            "Please can you rename Paddock A to North Flat.",
            "I'd like Paddock A renamed North Flat please.",
            "Can we call field A North Flat?",
        )
        for question in variants:
            with self.subTest(question=question):
                fast = route_question(question)
                self.assertTrue(needs_semantic_interpretation(question, fast))

    def test_common_natural_data_phrases_are_either_direct_or_semantically_interpreted(self) -> None:
        variants = (
            "Could I have the temperature for Paddock B please?",
            "Give us the temp for field B.",
            "What's B looking like temperature-wise?",
            "How warm is number two at the moment?",
            "Which field is looking the driest?",
            "What's the mean temperature over all the fields please?",
        )
        useful_fast = {
            "paddock", "paddock-field", "ranking", "farm-average", "measurement-fallback",
            "conversation", "interpretation-boundary", "driest", "wettest", "average",
            "comparison", "historical",
        }
        for question in variants:
            with self.subTest(question=question):
                fast = route_question(question)
                self.assertTrue(fast.intent in useful_fast or needs_semantic_interpretation(question, fast))

    def test_structured_semantic_results_cover_value_ranking_average_and_learning(self) -> None:
        cases = (
            (
                {"intent": "current", "confidence": .93, "paddock_name": "field b", "measurement": "air_temperature_c"},
                ("paddock-field", "Paddock B", "air_temperature_c", None),
            ),
            (
                {"intent": "lowest", "confidence": .96, "measurement": "soil_moisture_pct"},
                ("ranking", None, "soil_moisture_pct", "lowest"),
            ),
            (
                {"intent": "average", "confidence": .95, "measurement": "air_temperature_c"},
                ("farm-average", None, "air_temperature_c", "average"),
            ),
            (
                {"intent": "learning", "confidence": .99, "topic": "facial eczema in sheep"},
                ("agriculture-learning", None, None, None),
            ),
        )
        for payload, expected in cases:
            payload.setdefault("paddock_name", None)
            payload.setdefault("new_paddock_name", None)
            payload.setdefault("operation", None)
            payload.setdefault("window_minutes", None)
            payload.setdefault("topic", None)
            payload.setdefault("reason", "test")
            route = route_from_interpretation(parse_semantic_interpretation(json.dumps(payload)))
            with self.subTest(payload=payload):
                self.assertEqual((route.intent, route.paddock_name, route.measurement, route.operation), expected)

    def test_follow_up_still_uses_conversation_context_route(self) -> None:
        route = route_question("What about Paddock 2?")
        self.assertEqual(route.intent, "contextual-follow-up")

    def test_general_why_question_is_marked_for_semantic_learning_instead_of_final_causal_refusal(self) -> None:
        question = "Why do dairy cows get milk fever?"
        fast = route_question(question)
        self.assertEqual(fast.intent, "causal-boundary")
        self.assertTrue(needs_semantic_interpretation(question, fast))

    def test_explicit_nz_source_question_is_open_to_research_interpretation(self) -> None:
        questions = (
            "Could you tell me what DairyNZ says about refill point please?",
            "What does MPI say about dairy cattle welfare?",
            "Can you look up Earth Sciences NZ information about drought?",
            "Research IrrigationNZ soil moisture monitoring for me.",
        )
        for question in questions:
            with self.subTest(question=question):
                fast = route_question(question)
                self.assertTrue(needs_semantic_interpretation(question, fast))


if __name__ == "__main__":
    unittest.main()
