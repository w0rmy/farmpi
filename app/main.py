"""FarmPi ASGI application composition root."""

from __future__ import annotations

from .app import app
from .ingest_api import router as ingest_router

# Keep feature-specific API routes outside the main UI/LLM module while the
# alpha grows. Uvicorn loads this composed application.
app.include_router(ingest_router)

__all__ = ["app"]
