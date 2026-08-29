"""Compatibility adapter for OpenAI-compatible LLM servers.

FarmPi's application code keeps one reviewed prompt contract, while model
servers differ slightly in how strictly they interpret chat templates. This
adapter normalises the outgoing request at the integration boundary without
changing deterministic grounding or farm-data authority.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any, AsyncIterator

from .conversation_context import current_conversation_messages


CHAT_COMPLETIONS_SUFFIX = "/v1/chat/completions"

_OPEN_INFORMATION_POLICY = """INFORMATION ACCESS POLICY
Answer any safe and lawful informational question even when it is unrelated to farming. Relevance controls depth and evidence priority, not permission to answer. Some legacy routes may label ordinary conversation as agriculture-learning; that label is not a topic restriction. Give farm, agriculture and FarmPi-learning questions the most useful depth. Give unrelated questions a concise useful answer, then gently connect back to the application's learning context when that is natural. Do not invent current facts, retrieved facts, farm observations, or source attribution."""

_INTERPRETER_INFORMATION_POLICY = """INFORMATION ACCESS POLICY
Do not use farming relevance as a permission gate. A clear safe and lawful informational question may be about any topic. Treat learning as the general informational fallback as well as agricultural learning: classify a clear non-farm informational question as learning, with its topic, rather than clarify. Use clarify only when the learner's meaning is genuinely ambiguous or when an action/identity needs clarification. Use research when the learner explicitly asks what an external source says or asks for current external information."""


def _conversation_context_text(messages: tuple[dict[str, str], ...]) -> str:
    lines = [
        "CONVERSATION CONTEXT",
        "Use this short history only to resolve references such as 'that', 'it', 'more', 'simpler' or 'next'. The current learner request takes precedence.",
    ]
    for message in messages:
        role = "Learner" if message.get("role") == "user" else "FarmPi"
        content = str(message.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def normalise_chat_payload(
    payload: dict[str, Any],
    model_id: str | None = None,
) -> dict[str, Any]:
    """Return a server-compatible copy of one chat-completions payload.

    Qwen3.5 chat templates used by LM Studio require the system message to be
    the first message and reject multiple system messages. FarmPi therefore
    combines every system fragment into one initial system message while
    preserving all non-system messages in their original order.

    A bounded per-conversation history is injected only for FarmPi's learner
    interpreter and answering prompts. It is deliberately not a growing
    transcript, and it never changes deterministic farm-data authority.

    ``model_id`` overrides the request model when supplied. If it is absent,
    the payload's existing model value is preserved for backwards-compatible
    local llama.cpp operation.
    """

    adjusted = dict(payload)
    messages = adjusted.get("messages")

    if isinstance(messages, list):
        system_parts: list[str] = []
        non_system_messages: list[Any] = []

        for message in messages:
            if isinstance(message, dict) and message.get("role") == "system":
                content = message.get("content")
                if content is not None and str(content).strip():
                    system_parts.append(str(content).strip())
            else:
                non_system_messages.append(message)

        if system_parts:
            combined_system = "\n\n".join(system_parts)
            is_interpreter = "FarmPi's learner-intent interpreter" in combined_system
            is_answer_prompt = "You are FarmPi," in combined_system
            history = current_conversation_messages()

            if is_interpreter:
                combined_system = f"{combined_system}\n\n{_INTERPRETER_INFORMATION_POLICY}"
                if history:
                    combined_system = f"{combined_system}\n\n{_conversation_context_text(history)}"
            elif is_answer_prompt:
                combined_system = f"{combined_system}\n\n{_OPEN_INFORMATION_POLICY}"

            adjusted_messages: list[Any] = [
                {"role": "system", "content": combined_system},
            ]

            # The final answering model benefits from real conversational roles.
            # The interpreter instead receives the same history as compact system
            # context so its JSON-only response contract stays unambiguous.
            if is_answer_prompt and history and not any(
                isinstance(message, dict) and message.get("role") == "assistant"
                for message in non_system_messages
            ):
                adjusted_messages.extend(dict(message) for message in history)

            adjusted_messages.extend(non_system_messages)
            adjusted["messages"] = adjusted_messages

            # A short answer prompt controls verbosity; the token ceiling should
            # not be so small that a capable model is truncated before answering.
            if is_answer_prompt:
                try:
                    adjusted["max_tokens"] = max(256, int(adjusted.get("max_tokens") or 0))
                except (TypeError, ValueError):
                    adjusted["max_tokens"] = 256

    if model_id:
        adjusted["model"] = model_id

    return adjusted


class LLMCompatibleClient:
    """Delegate HTTP calls while normalising chat-completions requests."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, *args: Any, **kwargs: Any) -> Any:
        return await self._client.get(*args, **kwargs)

    async def post(self, url: Any, *args: Any, **kwargs: Any) -> Any:
        payload = kwargs.get("json")
        if (
            isinstance(payload, dict)
            and str(url).rstrip("/").endswith(CHAT_COMPLETIONS_SUFFIX)
        ):
            kwargs["json"] = normalise_chat_payload(
                payload,
                os.getenv("FARMPI_LLM_MODEL"),
            )
        return await self._client.post(url, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def install_llm_compat(application: Any) -> None:
    """Wrap FarmPi's lifespan HTTP client once at the ASGI composition root."""

    if getattr(application.state, "_farmpi_llm_compat_installed", False):
        return

    original_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def compatible_lifespan(app: Any) -> AsyncIterator[None]:
        async with original_lifespan(app):
            app.state.http_client = LLMCompatibleClient(app.state.http_client)
            yield

    application.router.lifespan_context = compatible_lifespan
    application.state._farmpi_llm_compat_installed = True
