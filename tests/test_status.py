"""Dependency-status regression tests."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from app.app import LLAMA_MODELS_URL, app, status


class _HealthyResponse:
    is_success = True
    status_code = 200


class _RecordingClient:
    def __init__(self) -> None:
        self.last_url: str | None = None

    async def get(self, url: str, **_: object) -> _HealthyResponse:
        self.last_url = url
        return _HealthyResponse()


class StatusTests(unittest.TestCase):
    def test_status_uses_openai_compatible_models_endpoint(self) -> None:
        old_client = getattr(app.state, "http_client", None)
        client = _RecordingClient()
        app.state.http_client = client

        try:
            with patch("app.app.ping_database", return_value=True):
                result = asyncio.run(status())
        finally:
            app.state.http_client = old_client

        self.assertEqual(client.last_url, LLAMA_MODELS_URL)
        self.assertTrue(result["llm"]["available"])
        self.assertEqual(result["llm"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
