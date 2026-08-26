"""Tests for FarmPi's deterministic question router."""

from __future__ import annotations

import unittest

from app.question_router import route_question


class QuestionRouterTests(unittest.TestCase):
    def test_driest(self) -> None:
        self.assertEqual(route_question("Which paddock is driest?").intent, "driest")
        self.assertEqual(
            route_question("Which has the lowest soil moisture?").intent,
            "driest",
        )

    def test_wettest(self) -> None:
        self.assertEqual(route_question("Which paddock is wettest?").intent, "wettest")

    def test_average(self) -> None:
        self.assertEqual(
            route_question("What is the average soil moisture?").intent,
            "average",
        )

    def test_single_paddock(self) -> None:
        route = route_question("What is Paddock B's soil moisture?")
        self.assertEqual(route.intent, "paddock")
        self.assertEqual(route.paddock_name, "Paddock B")

    def test_unsupported_measurement_wins_over_paddock(self) -> None:
        route = route_question("What is Paddock B's soil temperature?")
        self.assertEqual(route.intent, "unsupported")

    def test_ph_is_matched_as_a_word_not_inside_a_name(self) -> None:
        self.assertEqual(route_question("What is the pH?").intent, "unsupported")
        route = route_question("What is Paddock Alpha's soil moisture?")
        self.assertEqual(route.intent, "paddock")
        self.assertEqual(route.paddock_name, "Paddock Alpha")

    def test_multiple_paddocks_use_broad_fallback(self) -> None:
        route = route_question("Compare Paddock A and Paddock B.")
        self.assertEqual(route.intent, "moisture-fallback")


if __name__ == "__main__":
    unittest.main()
