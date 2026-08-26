"""Tests for FarmPi's deterministic question router."""

from __future__ import annotations

import unittest

from app.question_router import route_question


class QuestionRouterTests(unittest.TestCase):
    def test_driest(self) -> None:
        self.assertEqual(route_question("Which paddock is driest?").intent, "driest")
        self.assertEqual(route_question("Which paddock is the driest?").intent, "driest")
        self.assertEqual(route_question("Which paddock is dryest?").intent, "driest")
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

    def test_help_and_onboarding(self) -> None:
        for question in (
            "How do I use FarmPi?",
            "What can I ask?",
            "What can you do?",
            "Guide me",
        ):
            self.assertEqual(route_question(question).intent, "help")

    def test_single_paddock(self) -> None:
        route = route_question("What is Paddock B's soil moisture?")
        self.assertEqual(route.intent, "paddock")
        self.assertEqual(route.paddock_name, "Paddock B")

    def test_named_paddock_environment_measurement(self) -> None:
        route = route_question("What is Paddock B's air temperature?")
        self.assertEqual(route.intent, "paddock-field")
        self.assertEqual(route.paddock_name, "Paddock B")
        self.assertEqual(route.measurement, "air_temperature_c")

    def test_environment_measurement_fallback(self) -> None:
        route = route_question("What is the relative humidity?")
        self.assertEqual(route.intent, "measurement-fallback")
        self.assertEqual(route.measurement, "relative_humidity_pct")

    def test_ph_is_matched_as_a_word_not_inside_a_name(self) -> None:
        self.assertEqual(route_question("What is the pH?").measurement, "soil_ph")
        route = route_question("What is Paddock Alpha's soil moisture?")
        self.assertEqual(route.intent, "paddock")
        self.assertEqual(route.paddock_name, "Paddock Alpha")

    def test_multiple_paddocks_use_broad_fallback(self) -> None:
        route = route_question("Compare Paddock A and Paddock B.")
        self.assertEqual(route.intent, "moisture-fallback")

    def test_conversational_paddock_word_is_not_treated_as_name(self) -> None:
        route = route_question("Which paddock is currently the most dry?")
        self.assertEqual(route.intent, "moisture-fallback")
        self.assertIsNone(route.paddock_name)

    def test_daylight_hours_and_non_moisture_rankings_are_unsupported(self) -> None:
        self.assertEqual(route_question("How many daylight hours were there?").intent, "unsupported")
        self.assertEqual(route_question("Which paddock is hottest?").intent, "unsupported")
        self.assertEqual(route_question("Which paddock is most humid?").intent, "unsupported")


if __name__ == "__main__":
    unittest.main()
