"""Structural typing for chat session persistence backends."""

from __future__ import annotations

from typing import Protocol

from meridian_api.schemas.chat_session import ChatSessionRecord
from meridian_api.services.mcp_gateway import McpGatewayService


class ChatSessionPersistence(Protocol):
    """File or object storage for chat session JSON."""

    def create_pending_session(
        self,
        *,
        user_session_id: str | None = None,
        title: str | None = None,
    ) -> ChatSessionRecord: ...

    def load(self, session_id: str) -> ChatSessionRecord: ...

    def list_sessions(self, *, user_session_id: str | None = None) -> list[ChatSessionRecord]: ...

    def save(self, record: ChatSessionRecord) -> None: ...

    async def set_delegation_from_verify(
        self,
        *,
        session_id: str,
        customer_email: str,
        customer_pin: str,
        auth_role: str,
        gateway: McpGatewayService,
        request_id: str | None,
    ) -> ChatSessionRecord: ...
