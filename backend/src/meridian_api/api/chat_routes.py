"""Chat session bootstrap and SSE message streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp import McpError
from pydantic import BaseModel, Field

from meridian_api.core.settings import get_settings
from meridian_api.limiter import limiter
from meridian_api.repositories.chat_session_json import ChatSessionRepositoryError
from meridian_api.repositories.chat_session_resolve import chat_session_repository
from meridian_api.services.openai_config import resolve_openai_api_key
from meridian_api.services.chat_orchestrator import stream_chat_turn
from meridian_api.services.mcp_gateway import McpGatewayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _gateway(request: Request) -> McpGatewayService:
    return request.app.state.mcp_gateway


def _settings(request: Request):
    return request.app.state.settings


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    return str(rid) if rid is not None else None


def _rate_limit_string() -> str:
    return get_settings().rate_limit_default


def _sse_data_line(obj: dict[str, object]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=True)}\n\n"


class CreateSessionResponse(BaseModel):
    session_id: str


class DelegateBody(BaseModel):
    customer_email: str = Field(..., min_length=3, max_length=320)
    customer_pin: str = Field(..., min_length=4, max_length=32)


class DelegateResponse(BaseModel):
    session_id: str
    delegated_customer_id: str
    delegated_email: str


class MessageBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=16000)


@limiter.limit(_rate_limit_string)
@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: Request) -> CreateSessionResponse:
    settings = _settings(request)
    repo = chat_session_repository(settings)
    record = repo.create_pending_session()
    return CreateSessionResponse(session_id=record.session_id)


@limiter.limit(_rate_limit_string)
@router.post("/sessions/{session_id}/delegate", response_model=DelegateResponse)
async def delegate_session(
    request: Request,
    session_id: str,
    body: DelegateBody,
) -> DelegateResponse:
    settings = _settings(request)
    repo = chat_session_repository(settings)
    try:
        record = repo.load(session_id)
        if record.auth is None:
            raise HTTPException(status_code=400, detail="Sign in before delegating.")
        role = record.auth.role
        record = await repo.set_delegation_from_verify(
            session_id=session_id,
            customer_email=body.customer_email,
            customer_pin=body.customer_pin,
            auth_role=role,
            gateway=_gateway(request),
            request_id=_request_id(request),
        )
    except ChatSessionRepositoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except McpError as exc:
        logger.warning("MCP error delegating chat session: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    d = record.delegation
    if d is None:
        raise HTTPException(status_code=500, detail="Delegation missing after save.")
    return DelegateResponse(
        session_id=record.session_id,
        delegated_customer_id=d.delegated_customer_id,
        delegated_email=d.delegated_email,
    )


@limiter.limit(_rate_limit_string)
@router.post("/sessions/{session_id}/messages")
async def stream_message(
    request: Request,
    session_id: str,
    body: MessageBody,
) -> StreamingResponse:
    settings = _settings(request)
    if not resolve_openai_api_key(settings):
        raise HTTPException(status_code=503, detail="OpenAI is not configured.")

    repo = chat_session_repository(settings)
    try:
        record = repo.load(session_id)
    except ChatSessionRepositoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def event_iterator() -> AsyncIterator[str]:
        async for ev in stream_chat_turn(
            settings=settings,
            record=record,
            user_text=body.text,
            gateway=_gateway(request),
            repo=repo,
            request_id=_request_id(request),
        ):
            yield _sse_data_line(ev)

    return StreamingResponse(
        event_iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
