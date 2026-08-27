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

    def test_farm_wide_current_average_and_rankings(self) -> None:
        route = route_question("What is the average temperature across all fields?")
        self.assertEqual((route.intent, route.measurement, route.operation), ("farm-average", "air_temperature_c", "average"))
        self.assertIsNone(route.paddock_name)

        route = route_question("What is the average air temperature across all paddocks?")
        self.assertEqual((route.intent, route.measurement), ("farm-average", "air_temperature_c"))

        route = route_question("What is the highest temperature?")
        self.assertEqual((route.intent, route.measurement, route.operation), ("ranking", "air_temperature_c", "highest"))

        route = route_question("Which field is coldest?")
        self.assertEqual((route.intent, route.measurement, route.operation), ("ranking", "air_temperature_c", "lowest"))

        route = route_question("Which field is hottest?")
        self.assertEqual((route.intent, route.measurement, route.operation), ("ranking", "air_temperature_c", "highest"))

    def test_field_is_a_paddock_alias(self) -> None:
        self.assertEqual(route_question("List all fields").intent, "farm_inventory_list")
        self.assertEqual(route_question("How many fields are we monitoring?").intent, "farm_inventory_count")

        route = route_question("What is the temperature in Field 2?")
        self.assertEqual((route.intent, route.paddock_name, route.measurement), ("paddock-field", "Paddock 2", "air_temperature_c"))

        route = route_question("What is Field B's humidity?")
        self.assertEqual((route.intent, route.paddock_name, route.measurement), ("paddock-field", "Paddock B", "relative_humidity_pct"))

    def test_help_and_onboarding(self) -> None:
        for question in (
            "How do I use FarmPi?",
            "What can I ask?",
            "What can you do?",
            "Guide me",
        ):
            self.assertEqual(route_question(question).intent, "help")

    def test_capability_paraphrases_never_become_paddock_candidates(self) -> None:
        for question in (
            "What sort of other information can you show me?",
            "What else can you show me?",
            "What can I learn about?",
            "What information is available?",
            "What else do you know?",
        ):
            with self.subTest(question=question):
                route = route_question(question)
                self.assertEqual(route.intent, "capability")
                self.assertIsNone(route.paddock_name)

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
        self.assertEqual(route.intent, "conversation")

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

    def test_decision_and_causal_questions_keep_safe_explicit_boundaries(self) -> None:
        self.assertEqual(route_question("Should I irrigate Paddock 2?").intent, "irrigation-decision")
        self.assertEqual(route_question("Should I irrigate Paddock 2?").paddock_name, "Paddock 2")
        self.assertEqual(route_question("When should I water Paddock A?").intent, "irrigation-decision")
        self.assertEqual(route_question("What is tomorrow's weather forecast?").intent, "forecast-boundary")
        self.assertEqual(route_question("Why is the soil pH dropping in Paddock A?").intent, "causal-boundary")
        self.assertEqual(route_question("What caused Paddock A's humidity to change?").intent, "causal-boundary")

    def test_ordinary_learning_prompt_uses_conversational_path(self) -> None:
        self.assertEqual(route_question("Can you help me make sense of this farm data?").intent, "conversation")
        self.assertEqual(route_question("Explain refill point and field capacity.").education_key, "irrigation_decision")


if __name__ == "__main__":
    unittest.main()
