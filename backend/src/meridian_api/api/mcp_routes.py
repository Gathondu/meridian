"""Read-only routes that proxy MCP inspection calls."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from mcp import McpError

from meridian_api.core.settings import get_settings
from meridian_api.limiter import limiter
from meridian_api.schemas.mcp_inspection import (
    PromptsListResponse,
    ResourceReadResponse,
    ResourcesListResponse,
    ResourceTemplatesListResponse,
    ToolsListResponse,
)
from meridian_api.services.mcp_gateway import McpGatewayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _gateway(request: Request) -> McpGatewayService:
    return request.app.state.mcp_gateway


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    return str(rid) if rid is not None else None


def _rate_limit_string() -> str:
    return get_settings().rate_limit_default


@router.get("/tools", response_model=ToolsListResponse)
@limiter.limit(_rate_limit_string)
async def list_tools(request: Request) -> ToolsListResponse:
    try:
        return await _gateway(request).list_tools(_request_id(request))
    except McpError as exc:
        logger.warning("Upstream MCP error on list_tools: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/resources", response_model=ResourcesListResponse)
@limiter.limit(_rate_limit_string)
async def list_resources(request: Request) -> ResourcesListResponse:
    try:
        return await _gateway(request).list_resources(_request_id(request))
    except McpError as exc:
        logger.warning("Upstream MCP error on list_resources: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/resource-templates", response_model=ResourceTemplatesListResponse)
@limiter.limit(_rate_limit_string)
async def list_resource_templates(request: Request) -> ResourceTemplatesListResponse:
    try:
        return await _gateway(request).list_resource_templates(_request_id(request))
    except McpError as exc:
        logger.warning("Upstream MCP error on list_resource_templates: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/prompts", response_model=PromptsListResponse)
@limiter.limit(_rate_limit_string)
async def list_prompts(request: Request) -> PromptsListResponse:
    try:
        return await _gateway(request).list_prompts(_request_id(request))
    except McpError as exc:
        logger.warning("Upstream MCP error on list_prompts: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/resources/read", response_model=ResourceReadResponse)
@limiter.limit(_rate_limit_string)
async def read_resource(
    request: Request,
    uri: Annotated[str, Query(min_length=1, max_length=4096)],
) -> ResourceReadResponse:
    try:
        McpGatewayService.validate_resource_uri(uri)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return await _gateway(request).read_resource(uri, _request_id(request))
    except McpError as exc:
        logger.warning("Upstream MCP error on read_resource: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
