"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from meridian_api.api.chat_routes import router as chat_router
from meridian_api.api.mcp_routes import router as mcp_router
from meridian_api.core.logging import configure_logging
from meridian_api.core.settings import cors_origins_list, get_settings
from meridian_api.limiter import limiter
from meridian_api.middleware.request_id import RequestIdMiddleware
from meridian_api.services.mcp_gateway import McpGatewayService


class HealthResponse(BaseModel):
    """Response body for the health check."""

    status: str = Field(..., description="Service health indicator")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    app.state.settings = settings
    app.state.mcp_gateway = McpGatewayService(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Meridian API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        RequestIdMiddleware,
        header_name=settings.request_id_header,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_list(settings),
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header],
    )

    app.include_router(mcp_router)
    app.include_router(chat_router)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Liveness probe for orchestration and local checks."""
        return HealthResponse(status="ok")

    return app


app = create_app()
