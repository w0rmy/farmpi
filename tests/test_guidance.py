"""Tests for deterministic FarmPi onboarding and follow-up guidance."""

from __future__ import annotations

import unittest

from app.guidance import INITIAL_SUGGESTIONS, WELCOME_TEXT, follow_up_suggestions


class GuidanceTests(unittest.TestCase):
    def test_welcome_and_initial_suggestions_exist(self) -> None:
        self.assertIn("soil moisture", WELCOME_TEXT)
        self.assertGreaterEqual(len(INITIAL_SUGGESTIONS), 3)

    def test_named_paddock_follow_up_stays_on_same_paddock(self) -> None:
        suggestions = follow_up_suggestions(
            "paddock-field",
            "Paddock B",
            "air_temperature_c",
        )
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(all("Paddock B" in item for item in suggestions))

    def test_unsupported_route_offers_safe_supported_questions(self) -> None:
        suggestions = follow_up_suggestions("unsupported")
        self.assertIn("How do I use FarmPi?", suggestions)
        self.assertTrue(all("irrigat" not in item.casefold() for item in suggestions))


if __name__ == "__main__":
    unittest.main()
