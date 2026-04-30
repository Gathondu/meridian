"""Select chat session storage from settings."""

from __future__ import annotations

from meridian_api.core.settings import Settings
from meridian_api.repositories.chat_session_json import ChatSessionJsonRepository
from meridian_api.repositories.chat_session_protocol import ChatSessionPersistence
from meridian_api.repositories.chat_session_s3 import ChatSessionS3Repository


def chat_session_repository(settings: Settings) -> ChatSessionPersistence:
    """Return S3-backed storage when ``CHAT_SESSIONS_S3_BUCKET`` is set, else local JSON files."""
    if settings.chat_sessions_s3_bucket:
        return ChatSessionS3Repository(settings)
    return ChatSessionJsonRepository(settings)
