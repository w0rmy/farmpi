"""Focused tests for deterministic FarmPi speech interpretation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.speech_normalizer import SpeechAlternative, current_paddock_names, normalize_speech


class SpeechNormalizerTests(unittest.TestCase):
    def test_patek_becomes_paddock_when_measurement_supplies_farm_context(self) -> None:
        result = normalize_speech("What is the moisture in Patek C?")
        self.assertEqual(result.normalized_transcript, "What is the moisture in Paddock C?")
        self.assertTrue(result.correction_applied)
        self.assertEqual(result.correction_reason, "known-paddock-confusion")

    def test_padlock_becomes_paddock_only_with_farm_context(self) -> None:
        result = normalize_speech("What is the temperature in padlock B?")
        self.assertEqual(result.normalized_transcript, "What is the temperature in paddock B?")
        self.assertTrue(result.correction_applied)
        unrelated = normalize_speech("The padlock is broken")
        self.assertEqual(unrelated.normalized_transcript, "The padlock is broken")
        self.assertFalse(unrelated.correction_applied)

    def test_patek_is_not_rewritten_without_farm_context(self) -> None:
        result = normalize_speech("Is Patek a good watch brand?")
        self.assertEqual(result.normalized_transcript, "Is Patek a good watch brand?")
        self.assertFalse(result.correction_applied)

    def test_top_alternative_confidence_is_retained_without_changing_text(self) -> None:
        result = normalize_speech(
            "What is the moisture in Paddock A?",
            [SpeechAlternative("What is the moisture in Paddock A?", 0.91)],
        )
        self.assertEqual(result.chosen_alternative_index, 0)
        self.assertEqual(result.chosen_alternative_confidence, 0.91)
        self.assertFalse(result.alternative_selected)

    def test_domain_consistent_alternative_beats_misrecognition(self) -> None:
        result = normalize_speech(
            "What is the moisture in Patek C?",
            [
                SpeechAlternative("What is the moisture in Patek C?", 0.80),
                SpeechAlternative("What is the moisture in Paddock C?", 0.64),
            ],
        )
        self.assertEqual(result.normalized_transcript, "What is the moisture in Paddock C?")
        self.assertTrue(result.alternative_selected)
        self.assertEqual(result.correction_reason, "domain-alternative")
        self.assertEqual(result.chosen_alternative_index, 1)

    def test_current_renamed_paddock_name_contributes_to_vocabulary(self) -> None:
        result = normalize_speech(
            "What is the pasture height in North Flight?",
            [SpeechAlternative("What is the pasture height in North Flat?")],
            paddock_names=("North Flat",),
        )
        self.assertEqual(result.normalized_transcript, "What is the pasture height in North Flat?")
        self.assertTrue(result.alternative_selected)

    def test_stats_states_confusion_is_corrected_only_for_known_location(self) -> None:
        corrected = normalize_speech(
            "What states are available on Fred's paddock?",
            paddock_names=("Bob's paddock", "Fred's paddock"),
        )
        self.assertEqual(corrected.normalized_transcript, "What stats are available on Fred's paddock?")
        self.assertTrue(corrected.correction_applied)

        unrelated = normalize_speech(
            "What states are available in Australia?",
            paddock_names=("Fred's paddock",),
        )
        self.assertEqual(unrelated.normalized_transcript, "What states are available in Australia?")
        self.assertFalse(unrelated.correction_applied)

    def test_spoken_possessive_name_without_apostrophe_uses_configured_name(self) -> None:
        result = normalize_speech(
            "Should I water Freds paddock now?",
            paddock_names=("Bob's paddock", "Fred's paddock"),
        )
        self.assertEqual(result.normalized_transcript, "Should I water Fred's paddock now?")
        self.assertTrue(result.correction_applied)

    def test_known_location_matching_accepts_smart_apostrophe(self) -> None:
        result = normalize_speech(
            "What states are available on Fred’s paddock?",
            paddock_names=("Fred's paddock",),
        )
        self.assertEqual(result.normalized_transcript, "What stats are available on Fred’s paddock?")

    def test_spoken_dairy_nz_is_canonicalised(self) -> None:
        result = normalize_speech("Can you search Dairy NZ live right now for irrigation scheduling advice?")
        self.assertEqual(
            result.normalized_transcript,
            "Can you search DairyNZ live right now for irrigation scheduling advice?",
        )
        self.assertTrue(result.correction_applied)

    @patch("app.speech_normalizer.fetch_all")
    def test_current_paddock_names_reads_active_database_names(self, fetch_all) -> None:
        fetch_all.return_value = [{"name": "North Flat"}, {"name": "Back Hill"}]
        self.assertEqual(current_paddock_names(), ("North Flat", "Back Hill"))
        self.assertIn("active = 1", fetch_all.call_args.args[0])

    def test_case_of_corrected_paddock_is_preserved(self) -> None:
        result = normalize_speech("RENAME PATEK A TO North Flat")
        self.assertEqual(result.normalized_transcript, "RENAME PADDOCK A TO North Flat")

    def test_rename_phrase_is_context_for_known_confusion(self) -> None:
        result = normalize_speech("Rename Patek A to North Flat")
        self.assertEqual(result.normalized_transcript, "Rename Paddock A to North Flat")
        self.assertTrue(result.correction_applied)


if __name__ == "__main__":
    unittest.main()
