"""Initial FarmPi web service."""

from fastapi import FastAPI

app = FastAPI(title="FarmPi", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    """Return a simple confirmation that the service is available."""
    return {"service": "FarmPi", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    """Provide a lightweight health check for systemd and reverse proxies."""
    return {"status": "healthy"}
