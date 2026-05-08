"""OpenAI-compatible runtime configuration helpers."""

from __future__ import annotations

import logging
from functools import lru_cache

import boto3

from meridian_api.core.settings import Settings

logger = logging.getLogger(__name__)


def _direct_openai_api_key(settings: Settings) -> str | None:
    secret = settings.openai_api_key
    if secret is None:
        return None
    value = secret.get_secret_value().strip()
    return value or None


@lru_cache(maxsize=8)
def _secret_string(secret_arn: str) -> str | None:
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    value = response.get("SecretString")
    return value.strip() if isinstance(value, str) and value.strip() else None


def resolve_openai_api_key(settings: Settings) -> str | None:
    """Return OPENAI_API_KEY directly, or read it from Secrets Manager."""
    direct = _direct_openai_api_key(settings)
    if direct:
        return direct

    secret_arn = (settings.openai_api_key_secret_arn or "").strip()
    if not secret_arn:
        return None

    try:
        return _secret_string(secret_arn)
    except Exception:
        logger.exception("Failed to load OpenAI API key from Secrets Manager")
        return None
