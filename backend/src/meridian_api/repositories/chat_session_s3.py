"""Chat session persistence in a private S3 bucket (JSON per session)."""

from __future__ import annotations

import json
import logging
import uuid

import boto3
from botocore.exceptions import ClientError

from meridian_api.core.settings import Settings
from meridian_api.repositories.chat_session_json import ChatSessionRepositoryError
from meridian_api.schemas.chat_session import ChatSessionRecord, DelegationRecord
from meridian_api.services.mcp_gateway import McpGatewayService
from meridian_api.services.mcp_text_parsers import (
    extract_customer_id_from_verify_text,
    extract_role_from_verify_text,
    tool_result_to_text,
)

logger = logging.getLogger(__name__)


class ChatSessionS3Repository:
    """Store ``{prefix}/{session_id}.json`` objects in the configured bucket."""

    def __init__(self, settings: Settings) -> None:
        bucket = settings.chat_sessions_s3_bucket
        if not bucket or not bucket.strip():
            msg = "chat_sessions_s3_bucket is required for S3 storage"
            raise ValueError(msg)
        self._bucket = bucket.strip()
        self._prefix = settings.chat_sessions_s3_prefix.strip().strip("/")
        self._client = boto3.client("s3")

    def _key(self, session_id: str) -> str:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe or safe != session_id:
            msg = "Invalid session id"
            raise ChatSessionRepositoryError(msg)
        if self._prefix:
            return f"{self._prefix}/{safe}.json"
        return f"{safe}.json"

    def _put_json(self, session_id: str, payload: dict[str, object]) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._key(session_id),
            Body=body,
            ContentType="application/json; charset=utf-8",
        )

    def _get_json(self, session_id: str) -> dict[str, object]:
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=self._key(session_id))
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                msg = "Session not found"
                raise ChatSessionRepositoryError(msg) from exc
            raise
        raw = obj["Body"].read()
        return json.loads(raw.decode("utf-8"))

    def create_pending_session(
        self,
        *,
        user_session_id: str | None = None,
        title: str | None = None,
    ) -> ChatSessionRecord:
        session_id = str(uuid.uuid4())
        record = ChatSessionRecord(
            session_id=session_id,
            user_session_id=user_session_id,
            title=title,
            auth=None,
            openai_messages=[],
        )
        self._put_json(session_id, record.model_dump_for_disk())
        logger.info("Created pending chat session %s (S3)", session_id)
        return record

    def load(self, session_id: str) -> ChatSessionRecord:
        raw = self._get_json(session_id)
        return ChatSessionRecord.model_validate(raw)

    def list_sessions(self, *, user_session_id: str | None = None) -> list[ChatSessionRecord]:
        prefix = f"{self._prefix}/" if self._prefix else ""
        records: list[ChatSessionRecord] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = str(item.get("Key", ""))
                if not key.endswith(".json"):
                    continue
                session_id = key.removeprefix(prefix).removesuffix(".json")
                if "/" in session_id or not session_id:
                    continue
                try:
                    record = self.load(session_id)
                except (ChatSessionRepositoryError, json.JSONDecodeError, ValueError):
                    logger.warning("Skipping unreadable chat session object %s", key)
                    continue
                if user_session_id is None or record.user_session_id == user_session_id:
                    records.append(record)
        return records

    def save(self, record: ChatSessionRecord) -> None:
        self._put_json(record.session_id, record.model_dump_for_disk())

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
