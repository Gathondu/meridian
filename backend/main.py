"""FastAPI application entrypoint."""

from fastapi import FastAPI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for the health check."""

    status: str = Field(..., description="Service health indicator")


app = FastAPI(title="Meridian API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe for orchestration and local checks."""
    return HealthResponse(status="ok")
