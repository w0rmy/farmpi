"""Tests for OpenAI-compatible LLM request normalization."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from app.llm_compat import LLMCompatibleClient, normalise_chat_payload


class _FakeClient:
    def __init__(self) -> None:
        self.last_url = None
        self.last_kwargs = None

    async def post(self, url, *args, **kwargs):
        self.last_url = url
        self.last_kwargs = kwargs
        return object()

    async def get(self, url, *args, **kwargs):
        self.last_url = url
        self.last_kwargs = kwargs
        return object()


class LLMCompatibilityTests(unittest.TestCase):
    def test_multiple_system_messages_become_one_initial_message(self) -> None:
        payload = {
            "model": "Qwen3-0.6B",
            "messages": [
                {"role": "system", "content": "FarmPi contract"},
                {"role": "system", "content": "Simple explanation"},
                {"role": "system", "content": "APPROVED LEARNING MATERIAL"},
                {"role": "user", "content": "let's go for a trend"},
            ],
        }

        result = normalise_chat_payload(payload)

        self.assertEqual(len(result["messages"]), 2)
        self.assertEqual(result["messages"][0]["role"], "system")
        self.assertEqual(
            result["messages"][0]["content"],
            "FarmPi contract\n\nSimple explanation\n\nAPPROVED LEARNING MATERIAL",
        )
        self.assertEqual(result["messages"][1], payload["messages"][3])

    def test_model_override_is_used_when_configured(self) -> None:
        payload = {
            "model": "Qwen3-0.6B",
            "messages": [{"role": "user", "content": "hello"}],
        }
        result = normalise_chat_payload(payload, "qwen/qwen3.5-9b")
        self.assertEqual(result["model"], "qwen/qwen3.5-9b")

    def test_existing_model_is_preserved_without_override(self) -> None:
        payload = {
            "model": "Qwen3-0.6B",
            "messages": [{"role": "user", "content": "hello"}],
        }
        result = normalise_chat_payload(payload)
        self.assertEqual(result["model"], "Qwen3-0.6B")

    def test_client_uses_environment_model_for_chat_completion(self) -> None:
        fake = _FakeClient()
        client = LLMCompatibleClient(fake)
        payload = {
            "model": "Qwen3-0.6B",
            "messages": [
                {"role": "system", "content": "one"},
                {"role": "system", "content": "two"},
                {"role": "user", "content": "hello"},
            ],
        }

        with patch.dict(os.environ, {"FARMPI_LLM_MODEL": "qwen/qwen3.5-9b"}, clear=False):
            asyncio.run(
                client.post(
                    "http://192.168.68.20:1234/v1/chat/completions",
                    json=payload,
                )
            )

        sent = fake.last_kwargs["json"]
        self.assertEqual(sent["model"], "qwen/qwen3.5-9b")
        self.assertEqual([message["role"] for message in sent["messages"]], ["system", "user"])


if __name__ == "__main__":
    unittest.main()
