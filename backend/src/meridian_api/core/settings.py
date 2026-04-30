"""Application settings loaded from environment."""

from functools import lru_cache
from typing import Annotated

from pathlib import Path

from pydantic import AnyHttpUrl, BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv_or_json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            import json

            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                msg = "JSON list expected for origins"
                raise ValueError(msg)
            return [str(x).strip() for x in parsed if str(x).strip()]
        return [part.strip() for part in stripped.split(",") if part.strip()]
    msg = f"Unsupported origins value: {type(value)}"
    raise TypeError(msg)


_HEADER_VALUE_TRANSLATE = str.maketrans(
    {
        "\u2026": "...",  # ellipsis (common in pasted placeholders) → ASCII
        "\u201c": '"',
        "\u201d": '"',
        "\u2019": "'",
    }
)


def _http_safe_header_value(value: str) -> str:
    """Header field-values must be encodable as latin-1 for HTTP (RFC 9110)."""
    normalized = value.translate(_HEADER_VALUE_TRANSLATE)
    try:
        normalized.encode("latin-1")
    except UnicodeEncodeError as exc:
        msg = (
            "MCP_SERVER_HEADERS values must be HTTP-safe (latin-1). "
            "Replace non-ASCII characters in tokens or use percent-encoding."
        )
        raise ValueError(msg) from exc
    return normalized


def _parse_headers(value: object) -> dict[str, str]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        raw = {str(k): str(v) for k, v in value.items()}
    elif isinstance(value, str):
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            msg = "JSON object expected for MCP server headers"
            raise ValueError(msg)
        raw = {str(k): str(v) for k, v in parsed.items()}
    else:
        msg = f"Unsupported headers value: {type(value)}"
        raise TypeError(msg)
    return {k: _http_safe_header_value(v) for k, v in raw.items()}


class Settings(BaseSettings):
    """Runtime configuration (env + optional `.env` in cwd)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    mcp_server_url: Annotated[
        AnyHttpUrl,
        Field(description="Streamable HTTP MCP endpoint."),
    ] = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
    mcp_server_headers: Annotated[dict[str, str], BeforeValidator(_parse_headers)] = Field(
        default_factory=dict,
        description='Optional JSON object of outbound headers, e.g. `MCP_SERVER_HEADERS={"Authorization":"Bearer x"}`.',
    )

    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        description="Allowed browser origins (comma-separated list; use str to avoid JSON env parsing).",
    )

    log_level: str = Field(default="INFO", description="Root log level name.")
    log_json: bool = Field(default=False, description="Emit logs as JSON lines to stdout.")
    rate_limit_default: str = Field(
        default="120/minute",
        description="SlowAPI default limit for inspection routes.",
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        description="Header used for request correlation (inbound and outbound to MCP).",
    )

    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key for chat completions (SSE). If unset, chat endpoints return 503.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Chat completions model for the assistant.",
    )
    openai_base_url: str | None = Field(
        default=None,
        description=(
            "Optional OpenAI-compatible API base URL "
            "(e.g. https://openrouter.ai/api/v1). Omit to use the default OpenAI endpoint."
        ),
    )
    chat_sessions_dir: str = Field(
        default="data/chat_sessions",
        description="Directory for JSON chat session files (created on demand).",
    )
    chat_sessions_s3_bucket: str | None = Field(
        default=None,
        description="When set, store chat session JSON in this S3 bucket instead of ``CHAT_SESSIONS_DIR``.",
    )
    chat_sessions_s3_prefix: str = Field(
        default="sessions",
        description="Object key prefix under the chat sessions bucket (no leading slash).",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings (clear cache in tests if env changes)."""
    return Settings()


def cors_origins_list(settings: Settings) -> list[str]:
    """Parse ``Settings.cors_origins`` into a list for Starlette CORS."""
    return _parse_csv_or_json_list(settings.cors_origins)


def chat_sessions_path(settings: Settings) -> Path:
    """Absolute path to the chat session storage directory."""
    p = Path(settings.chat_sessions_dir)
    return p if p.is_absolute() else Path.cwd() / p
