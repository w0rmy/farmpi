"""FarmPi ASGI application composition root."""

from __future__ import annotations

from .app import app
from .ingest_api import router as ingest_router
from .llm_compat import install_llm_compat

# Normalise outgoing OpenAI-compatible chat requests at the integration
# boundary.  This keeps FarmPi's reviewed prompt/grounding architecture intact
# while supporting stricter chat templates such as Qwen3.5 in LM Studio.
install_llm_compat(app)

# Keep feature-specific API routes outside the main UI/LLM module while the
# alpha grows. Uvicorn loads this composed application.
app.include_router(ingest_router)

__all__ = ["app"]
