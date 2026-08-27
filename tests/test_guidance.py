"""Tests for deterministic FarmPi onboarding and follow-up guidance."""

from __future__ import annotations

import unittest

from app.guidance import INITIAL_SUGGESTIONS, WELCOME_TEXT, follow_up_suggestions


class GuidanceTests(unittest.TestCase):
    def test_welcome_and_initial_suggestions_describe_open_learning(self) -> None:
        self.assertIn("conversational agricultural learning assistant", WELCOME_TEXT)
        self.assertIn("farm data", WELCOME_TEXT)
        self.assertGreaterEqual(len(INITIAL_SUGGESTIONS), 3)
        self.assertTrue(any("DairyNZ" in item or "cows" in item for item in INITIAL_SUGGESTIONS))

    def test_named_paddock_follow_up_can_bridge_from_data_into_learning(self) -> None:
        suggestions = follow_up_suggestions(
            "paddock-field",
            "Paddock B",
            "air_temperature_c",
        )
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(any("Paddock B" in item for item in suggestions))
        self.assertTrue(any("Why" in item or "what" in item.casefold() for item in suggestions))

    def test_learning_route_offers_continuation_not_command_syntax(self) -> None:
        suggestions = follow_up_suggestions("agriculture-learning")
        self.assertEqual(len(suggestions), 3)
        self.assertIn("Can you explain that more simply?", suggestions)
        self.assertIn("What should I learn about next?", suggestions)

    def test_decision_boundary_offers_learning_about_missing_factors(self) -> None:
        suggestions = follow_up_suggestions("irrigation-decision")
        self.assertTrue(any("factors" in item.casefold() for item in suggestions))
        self.assertTrue(any("DairyNZ" in item for item in suggestions))


if __name__ == "__main__":
    unittest.main()
