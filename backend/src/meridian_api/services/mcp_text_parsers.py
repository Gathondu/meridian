"""Parse human-oriented MCP tool result text."""

from __future__ import annotations

import json
import re
from typing import Any

_UUID_RE = re.compile(
    r"Customer ID:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
    re.IGNORECASE,
)
_ROLE_RE = re.compile(r"Role:\s*(\S+)", re.IGNORECASE)
_PRICE_RE = re.compile(r"Price:\s*\$?([0-9]+(?:\.[0-9]+)?)\s*([A-Z]{3})?", re.IGNORECASE)


def extract_customer_id_from_verify_text(text: str) -> str | None:
    m = _UUID_RE.search(text)
    return m.group(1).lower() if m else None


def extract_role_from_verify_text(text: str) -> str | None:
    m = _ROLE_RE.search(text)
    return m.group(1).strip().lower() if m else None


def extract_price_from_product_text(text: str) -> tuple[str, str] | None:
    m = _PRICE_RE.search(text)
    if not m:
        return None
    currency = (m.group(2) or "USD").upper()
    return m.group(1), currency


def tool_result_to_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("result"), str):
        return str(payload["result"])
    return json.dumps(payload, ensure_ascii=False)


def structured_from_call_tool_result(result: object) -> dict[str, Any]:
    """Normalize FastMCP ``CallToolResult`` to a JSON-friendly dict."""
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        return dict(sc)
    data = getattr(result, "data", None)
    if data is not None and hasattr(data, "model_dump"):
        dumped = data.model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        t = getattr(block, "text", None)
        if t:
            parts.append(t)
    return {"result": "\n".join(parts) if parts else ""}


def structured_to_assistant_visible_text(payload: dict[str, Any]) -> str:
    """Single string for persistence / UI from structured payload."""
    if "result" in payload and isinstance(payload["result"], str):
        return payload["result"]
    return json.dumps(payload, ensure_ascii=False)
