"""Chat session persistence as JSON files."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from meridian_api.core.settings import Settings, chat_sessions_path
from meridian_api.schemas.chat_session import AuthRecord, ChatSessionRecord, DelegationRecord
from meridian_api.services.mcp_gateway import McpGatewayService
from meridian_api.services.mcp_text_parsers import (
    extract_customer_id_from_verify_text,
    extract_role_from_verify_text,
    tool_result_to_text,
)

logger = logging.getLogger(__name__)


class ChatSessionRepositoryError(Exception):
    """Invalid session state or missing file."""


class ChatSessionJsonRepository:
    def __init__(self, settings: Settings) -> None:
        self._root = chat_sessions_path(settings)

    def _path(self, session_id: str) -> Path:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe or safe != session_id:
            msg = "Invalid session id"
            raise ChatSessionRepositoryError(msg)
        return self._root / f"{safe}.json"

    def _atomic_write(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        fd, tmp = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=".session-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    async def create_session_from_verify(
        self,
        *,
        email: str,
        pin: str,
        gateway: McpGatewayService,
        request_id: str | None,
    ) -> ChatSessionRecord:
        payload = await gateway.call_tool(
            "verify_customer_pin",
            {"email": email.strip().lower(), "pin": pin.strip()},
            request_id,
        )
        text = tool_result_to_text(payload)
        cid = extract_customer_id_from_verify_text(text)
        role = extract_role_from_verify_text(text)
        if not cid or not role:
            msg = "Could not parse customer id or role from verify_customer_pin response."
            raise ChatSessionRepositoryError(msg)
        session_id = str(uuid.uuid4())
        record = ChatSessionRecord(
            session_id=session_id,
            auth=AuthRecord(
                actor_email=email.strip().lower(),
                actor_customer_id=cid,
                role=role,
            ),
            openai_messages=[],
        )
        self._atomic_write(self._path(session_id), record.model_dump_for_disk())
        logger.info("Created chat session %s role=%s", session_id, role)
        return record

    def create_pending_session(self) -> ChatSessionRecord:
        """Create a session file before MCP verify (sign-in via chat tools)."""
        session_id = str(uuid.uuid4())
        record = ChatSessionRecord(session_id=session_id, auth=None, openai_messages=[])
        self._atomic_write(self._path(session_id), record.model_dump_for_disk())
        logger.info("Created pending chat session %s", session_id)
        return record

    def load(self, session_id: str) -> ChatSessionRecord:
        path = self._path(session_id)
        if not path.is_file():
            msg = "Session not found"
            raise ChatSessionRepositoryError(msg)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ChatSessionRecord.model_validate(raw)

    def save(self, record: ChatSessionRecord) -> None:
        self._atomic_write(self._path(record.session_id), record.model_dump_for_disk())

    async def set_delegation_from_verify(
        self,
        *,
        session_id: str,
        customer_email: str,
        customer_pin: str,
        auth_role: str,
        gateway: McpGatewayService,
        request_id: str | None,
    ) -> ChatSessionRecord:
        record = self.load(session_id)
        if record.auth is None:
            msg = "Sign in before delegating."
            raise ChatSessionRepositoryError(msg)
        if auth_role.lower() not in ("support", "admin"):
            msg = "Only support or admin may delegate."
            raise ChatSessionRepositoryError(msg)
        payload = await gateway.call_tool(
            "verify_customer_pin",
            {"email": customer_email.strip().lower(), "pin": customer_pin.strip()},
            request_id,
        )
        text = tool_result_to_text(payload)
        cid = extract_customer_id_from_verify_text(text)
        role = extract_role_from_verify_text(text)
        if not cid or not role:
            msg = "Could not parse delegation verify response."
            raise ChatSessionRepositoryError(msg)
        if auth_role.lower() == "support" and role.lower() in ("support", "admin"):
            msg = "Support cannot delegate to staff accounts."
            raise ChatSessionRepositoryError(msg)
        record.delegation = DelegationRecord(
            delegated_customer_id=cid,
            delegated_email=customer_email.strip().lower(),
        )
        self.save(record)
        return record
