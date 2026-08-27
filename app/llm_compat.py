"""Compatibility adapter for OpenAI-compatible LLM servers.

FarmPi's application code keeps one reviewed prompt contract, while model
servers differ slightly in how strictly they interpret chat templates.  This
adapter normalises the outgoing request at the integration boundary without
changing deterministic grounding or farm-data authority.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any, AsyncIterator


CHAT_COMPLETIONS_SUFFIX = "/v1/chat/completions"


def normalise_chat_payload(
    payload: dict[str, Any],
    model_id: str | None = None,
) -> dict[str, Any]:
    """Return a server-compatible copy of one chat-completions payload.

    Qwen3.5 chat templates used by LM Studio require the system message to be
    the first message and reject multiple system messages.  FarmPi therefore
    combines every system fragment into one initial system message while
    preserving all non-system messages in their original order.

    ``model_id`` overrides the request model when supplied.  If it is absent,
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
            adjusted["messages"] = [
                {"role": "system", "content": "\n\n".join(system_parts)},
                *non_system_messages,
            ]

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
