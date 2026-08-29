"""FarmPi ASGI application composition root."""

from __future__ import annotations

from .app import app
from .conversation_context import install_conversation_context
from .ingest_api import router as ingest_router
from .llm_compat import install_llm_compat

# Keep a small, short-lived conversation window so natural educational
# follow-ups can refer to the immediately preceding exchange.  This middleware
# also removes developer-only research diagnostics from learner responses and
# guarantees that spoken_answer contains the actual displayed answer.
install_conversation_context(app)

# Normalise outgoing OpenAI-compatible chat requests at the integration
# boundary.  This keeps FarmPi's reviewed prompt/grounding architecture intact
# while supporting stricter chat templates such as Qwen3.5 in LM Studio.
install_llm_compat(app)

# Keep feature-specific API routes outside the main UI/LLM module while the
# alpha grows. Uvicorn loads this composed application.
app.include_router(ingest_router)

__all__ = ["app"]
