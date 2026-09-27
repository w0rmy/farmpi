"""FarmPi ASGI application composition root."""

from __future__ import annotations

from .app import app
from .conversation_context import install_conversation_context
from .ingest_api import router as ingest_router
from .node_api import router as node_router
from .monitoring_api import router as monitoring_router
from .database import DatabaseUnavailable
from fastapi.responses import JSONResponse
from .llm_compat import install_llm_compat

# Keep a small, short-lived conversation window so natural follow-ups can refer
# to the immediately preceding exchange. This middleware also removes
# developer-only research diagnostics from user-facing responses and guarantees
# that spoken_answer contains the actual displayed answer.
install_conversation_context(app)

# Normalise outgoing OpenAI-compatible chat requests at the integration
# boundary. This keeps FarmPi's reviewed prompt/grounding architecture intact
# while supporting stricter chat templates such as Qwen3.5 in LM Studio.
install_llm_compat(app)

# Keep feature-specific API routes outside the main UI/LLM module while the
# alpha grows. Uvicorn loads this composed application.
app.include_router(ingest_router)
app.include_router(node_router)
app.include_router(monitoring_router)


@app.exception_handler(DatabaseUnavailable)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "The FarmPi database is unavailable."})

__all__ = ["app"]
