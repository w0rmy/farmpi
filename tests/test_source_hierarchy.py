"""Keep FarmPi's documented learning-evidence preference executable."""

from __future__ import annotations

import unittest

from app.source_hierarchy import SOURCE_HIERARCHY, learning_source_contract


class SourceHierarchyTests(unittest.TestCase):
    def test_five_tiers_are_ordered_from_trusted_evidence_to_model_knowledge(self) -> None:
        self.assertEqual(
            [tier.key for tier in SOURCE_HIERARCHY],
            [
                "first-class-trusted",
                "trusted-primary",
                "reputable-general",
                "general-unverified-web",
                "model-knowledge",
            ],
        )

    def test_nz_dairy_preference_and_no_refusal_rule_are_in_the_model_contract(self) -> None:
        contract = learning_source_contract()
        self.assertIn("DairyNZ", contract)
        self.assertIn("relevant New Zealand government", contract)
        self.assertIn("do not reject a useful general answer", contract)


if __name__ == "__main__":
    unittest.main()
