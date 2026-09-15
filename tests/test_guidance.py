"""Tests for deterministic FarmPi onboarding and follow-up guidance."""

from __future__ import annotations

import unittest

from app.guidance import INITIAL_SUGGESTIONS, WELCOME_TEXT, follow_up_suggestions


class GuidanceTests(unittest.TestCase):
    def test_welcome_and_initial_suggestions_describe_application_capabilities(self) -> None:
        self.assertIn("conversational farm-monitoring assistant", WELCOME_TEXT)
        self.assertIn("farm data", WELCOME_TEXT)
        self.assertGreaterEqual(len(INITIAL_SUGGESTIONS), 3)
        self.assertTrue(any("DairyNZ" in item or "soil moisture" in item for item in INITIAL_SUGGESTIONS))

    def test_named_paddock_follow_up_bridges_data_to_related_information(self) -> None:
        suggestions = follow_up_suggestions(
            "paddock-field",
            "Paddock B",
            "air_temperature_c",
        )
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(any("Paddock B" in item for item in suggestions))
        self.assertTrue(any("Why" in item or "what" in item.casefold() for item in suggestions))

    def test_general_information_route_offers_useful_continuation(self) -> None:
        suggestions = follow_up_suggestions("agriculture-learning")
        self.assertEqual(len(suggestions), 3)
        self.assertIn("Can you explain that more simply?", suggestions)
        self.assertIn("What related information can FarmPi show me?", suggestions)

    def test_decision_boundary_offers_missing_factors_and_source(self) -> None:
        suggestions = follow_up_suggestions("irrigation-decision")
        self.assertTrue(any("factors" in item.casefold() for item in suggestions))
        self.assertTrue(any("DairyNZ" in item for item in suggestions))


if __name__ == "__main__":
    unittest.main()
