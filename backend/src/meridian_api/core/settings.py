"""Application settings loaded from environment."""

from functools import lru_cache
from typing import Annotated, Any

from pydantic import AnyHttpUrl, BeforeValidator, Field
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


def _parse_headers(value: object) -> dict[str, str]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str):
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            msg = "JSON object expected for MCP server headers"
            raise ValueError(msg)
        return {str(k): str(v) for k, v in parsed.items()}
    msg = f"Unsupported headers value: {type(value)}"
    raise TypeError(msg)


class Settings(BaseSettings):
    """Runtime configuration (env + optional `.env` in cwd)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    mcp_server_url: AnyHttpUrl = Field(
        default="https://order-mcp-74afyau24q-uc.a.run.app/mcp",
        description="Streamable HTTP MCP endpoint.",
    )
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


@lru_cache
def get_settings() -> Settings:
    """Return cached settings (clear cache in tests if env changes)."""
    return Settings()


def cors_origins_list(settings: Settings) -> list[str]:
    """Parse ``Settings.cors_origins`` into a list for Starlette CORS."""
    return _parse_csv_or_json_list(settings.cors_origins)
