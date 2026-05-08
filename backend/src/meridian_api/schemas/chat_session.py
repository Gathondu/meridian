"""On-disk chat session record (JSON file)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AuthRecord(BaseModel):
    actor_email: str
    actor_customer_id: str
    role: str


class DelegationRecord(BaseModel):
    delegated_customer_id: str
    delegated_email: str


class ChatSessionRecord(BaseModel):
    session_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(),
    )
    user_session_id: str | None = None
    title: str | None = None
    auth: AuthRecord | None = None
    delegation: DelegationRecord | None = None
    pending_order_items: list[dict[str, Any]] = Field(default_factory=list)
    openai_messages: list[dict[str, Any]] = Field(default_factory=list)

    def model_dump_for_disk(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SseEvent(BaseModel):
    """Wire format for SSE ``data:`` JSON lines."""

    type: Literal[
        "content_delta",
        "tool_call_start",
        "tool_call_done",
        "error",
        "finished",
    ]
    text: str | None = None
    name: str | None = None
    ok: bool | None = None
    message: str | None = None
