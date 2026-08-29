"""Tests for bounded conversation continuity and learner-facing response cleanup."""

from __future__ import annotations

import unittest

from app import conversation_context
from app.conversation_context import prepare_client_payload
from app.llm_compat import normalise_chat_payload


class ConversationContextTests(unittest.TestCase):
    def test_client_payload_removes_research_diagnostic_and_repairs_spoken_answer(self) -> None:
        payload = {
            "answer": "No live web research was performed. FarmPi used its curated source directory and configured model.\n\nDairyNZ says irrigation scheduling uses several inputs.",
            "spoken_answer": None,
            "provenance": [
                {"kind": "research-status", "status": "curated-source-directory-only"},
                {"kind": "authoritative-curated", "organisation": "DairyNZ"},
            ],
        }

        result = prepare_client_payload(payload)

        self.assertEqual(result["answer"], "DairyNZ says irrigation scheduling uses several inputs.")
        self.assertEqual(result["spoken_answer"], result["answer"])
        self.assertEqual(result["provenance"], [{"kind": "authoritative-curated", "organisation": "DairyNZ"}])

    def test_final_answer_prompt_gets_open_information_policy_and_safe_token_floor(self) -> None:
        payload = {
            "model": "qwen/qwen3.5-9b",
            "messages": [
                {"role": "system", "content": "You are FarmPi, an open conversational agricultural learning assistant."},
                {"role": "user", "content": "Who wrote The Hobbit?"},
            ],
            "max_tokens": 64,
        }

        result = normalise_chat_payload(payload)

        self.assertIn("Relevance controls depth", result["messages"][0]["content"])
        self.assertIn("unrelated to farming", result["messages"][0]["content"])
        self.assertEqual(result["max_tokens"], 256)

    def test_bounded_history_is_injected_before_current_answer_request(self) -> None:
        history = (
            {"role": "user", "content": "What does DairyNZ say about irrigation scheduling?"},
            {"role": "assistant", "content": "DairyNZ describes several inputs to irrigation scheduling."},
        )
        token = conversation_context._current_conversation.set(history)
        try:
            result = normalise_chat_payload({
                "model": "qwen/qwen3.5-9b",
                "messages": [
                    {"role": "system", "content": "You are FarmPi, an open conversational agricultural learning assistant."},
                    {"role": "user", "content": "Can you explain that more simply?"},
                ],
                "max_tokens": 128,
            })
        finally:
            conversation_context._current_conversation.reset(token)

        self.assertEqual([message["role"] for message in result["messages"]], ["system", "user", "assistant", "user"])
        self.assertEqual(result["messages"][-1]["content"], "Can you explain that more simply?")

    def test_interpreter_uses_history_as_context_not_as_extra_chat_roles(self) -> None:
        history = (
            {"role": "user", "content": "What does DairyNZ say about irrigation scheduling?"},
            {"role": "assistant", "content": "DairyNZ describes several inputs to irrigation scheduling."},
        )
        token = conversation_context._current_conversation.set(history)
        try:
            result = normalise_chat_payload({
                "model": "qwen/qwen3.5-9b",
                "messages": [
                    {"role": "system", "content": "You are FarmPi's learner-intent interpreter, not the answering assistant."},
                    {"role": "user", "content": "Can you explain that more simply?"},
                ],
                "max_tokens": 192,
            })
        finally:
            conversation_context._current_conversation.reset(token)

        self.assertEqual([message["role"] for message in result["messages"]], ["system", "user"])
        self.assertIn("CONVERSATION CONTEXT", result["messages"][0]["content"])
        self.assertIn("DairyNZ", result["messages"][0]["content"])
        self.assertIn("clear non-farm informational question as learning", result["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
