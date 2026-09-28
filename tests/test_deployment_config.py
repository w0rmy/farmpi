"""Regression checks for checked-in deployment configuration."""

from __future__ import annotations

from pathlib import Path
import unittest


class DeploymentConfigTests(unittest.TestCase):
    def test_llm_service_identity_matches_configured_model(self) -> None:
        service = Path("config/systemd/farmpi-llm.service.template").read_text(encoding="utf-8")

        self.assertIn("Description=FarmPi Qwen3 0.6B local LLM server", service)
        self.assertIn("lmstudio-community/Qwen3-0.6B-GGUF:Q4_K_M", service)
        self.assertNotIn("Description=FarmPi Qwen3 1.7B local LLM server", service)


if __name__ == "__main__":
    unittest.main()
