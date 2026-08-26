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
        cases = (
            ("What is the temperature in Paddock A?", "air_temperature_c"),
            ("What is Paddock A's humidity?", "relative_humidity_pct"),
            ("What is the soil pH in Paddock A?", "soil_ph"),
            ("What is the light level in Paddock A?", "light_lux"),
            ("What is the soil temperature in Paddock A?", "soil_temperature_c"),
            ("What is the EC in Paddock A?", "soil_ec_ms_cm"),
            ("What is the grass height in Paddock A?", "pasture_height_cm"),
        )

        for question, measurement in cases:
            with self.subTest(question=question):
                route = route_question(question)
                self.assertEqual(route.intent, "paddock-field")
                self.assertEqual(route.paddock_name, "Paddock A")
                self.assertEqual(route.measurement, measurement)

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

    def test_dynamic_names_history_rankings_and_rename_are_routed(self) -> None:
        route = route_question("What is the pasture height in North Flat?")
        self.assertEqual((route.intent, route.paddock_name, route.measurement), ("paddock-field", "North Flat", "pasture_height_cm"))
        route = route_question("How much rainfall was there over the last 24 hours?")
        self.assertEqual((route.intent, route.measurement, route.operation, route.window_minutes), ("historical", "rainfall_mm", "sum", 1440))
        route = route_question("What is the pasture height change in North Flat over the last day?")
        self.assertEqual((route.paddock_name, route.operation, route.window_minutes), ("North Flat", "change", 1440))
        self.assertEqual(route_question("Which paddock is tallest?").intent, "ranking")
        route = route_question("Rename Paddock A to North Flat")
        self.assertEqual((route.intent, route.paddock_name, route.new_paddock_name), ("rename-request", "Paddock A", "North Flat"))
        self.assertEqual(route_question("Guide me").intent, "help")

    def test_advice_and_causal_questions_are_unsupported(self) -> None:
        questions = (
            "What is tomorrow's weather forecast?",
            "Should I irrigate Paddock A?",
            "When should I water Paddock A?",
            "Why is the soil pH dropping in Paddock A?",
            "What caused Paddock A's humidity to change?",
        )
        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(route_question(question).intent, "unsupported")


if __name__ == "__main__":
    unittest.main()
