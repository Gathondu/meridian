"""MCP client wrapper (FastMCP + Streamable HTTP)."""

import json
import logging
from typing import Any

import mcp.types
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from mcp import McpError

from meridian_api.core.settings import Settings
from meridian_api.services.mcp_text_parsers import structured_from_call_tool_result

from meridian_api.schemas.mcp_inspection import (
    PromptPublic,
    PromptsListResponse,
    ResourceContentBlockPublic,
    ResourcePublic,
    ResourceReadResponse,
    ResourcesListResponse,
    ResourceTemplatePublic,
    ResourceTemplatesListResponse,
    ToolPublic,
    ToolsListResponse,
)

logger = logging.getLogger(__name__)

_MAX_URI_LEN = 4096


class McpGatewayService:
    """Per-request MCP sessions (inspection + ``call_tool`` for chat)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self, request_id: str | None) -> Client:
        headers = dict(self._settings.mcp_server_headers)
        if request_id:
            headers[self._settings.request_id_header] = request_id
        transport = StreamableHttpTransport(
            url=str(self._settings.mcp_server_url),
            headers=headers or None,
        )
        return Client(transport)

    @staticmethod
    def validate_resource_uri(uri: str) -> str:
        if not uri or not uri.strip():
            msg = "uri is required"
            raise ValueError(msg)
        cleaned = uri.strip()
        if len(cleaned) > _MAX_URI_LEN:
            msg = "uri exceeds maximum length"
            raise ValueError(msg)
        return cleaned

    @staticmethod
    def _map_resource_contents(
        blocks: list[mcp.types.TextResourceContents | mcp.types.BlobResourceContents],
    ) -> list[ResourceContentBlockPublic]:
        out: list[ResourceContentBlockPublic] = []
        for block in blocks:
            if isinstance(block, mcp.types.TextResourceContents):
                out.append(
                    ResourceContentBlockPublic(
                        type="text",
                        mime_type=block.mimeType,
                        text=block.text,
                        blob=None,
                    )
                )
            else:
                out.append(
                    ResourceContentBlockPublic(
                        type="blob",
                        mime_type=block.mimeType,
                        text=None,
                        blob=block.blob,
                    )
                )
        return out

    async def list_tools(self, request_id: str | None) -> ToolsListResponse:
        try:
            async with self._client(request_id) as client:
                raw = await client.list_tools()
        except McpError as exc:
            logger.warning("MCP list_tools failed: %s", exc)
            raise
        tools = [ToolPublic.model_validate(t.model_dump(mode="json")) for t in raw]
        return ToolsListResponse(tools=tools)

    async def list_resources(self, request_id: str | None) -> ResourcesListResponse:
        try:
            async with self._client(request_id) as client:
                raw = await client.list_resources()
        except McpError as exc:
            logger.warning("MCP list_resources failed: %s", exc)
            raise
        resources = [
            ResourcePublic.model_validate(r.model_dump(mode="json", by_alias=True))
            for r in raw
        ]
        return ResourcesListResponse(resources=resources)

    async def list_resource_templates(
        self, request_id: str | None
    ) -> ResourceTemplatesListResponse:
        try:
            async with self._client(request_id) as client:
                raw = await client.list_resource_templates()
        except McpError as exc:
            logger.warning("MCP list_resource_templates failed: %s", exc)
            raise
        templates = [
            ResourceTemplatePublic.model_validate(t.model_dump(mode="json", by_alias=True))
            for t in raw
        ]
        return ResourceTemplatesListResponse(resource_templates=templates)

    async def list_prompts(self, request_id: str | None) -> PromptsListResponse:
        try:
            async with self._client(request_id) as client:
                raw = await client.list_prompts()
        except McpError as exc:
            logger.warning("MCP list_prompts failed: %s", exc)
            raise
        prompts = [PromptPublic.model_validate(p.model_dump(mode="json")) for p in raw]
        return PromptsListResponse(prompts=prompts)

    async def read_resource(self, uri: str, request_id: str | None) -> ResourceReadResponse:
        validated = self.validate_resource_uri(uri)
        try:
            async with self._client(request_id) as client:
                blocks = await client.read_resource(validated)
        except McpError as exc:
            logger.warning("MCP read_resource failed for %s: %s", validated, exc)
            raise
        return ResourceReadResponse(
            uri=validated,
            contents=self._map_resource_contents(blocks),
        )

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        request_id: str | None,
    ) -> dict[str, Any]:
        """Invoke a single MCP tool and return structured JSON payload."""
        try:
            async with self._client(request_id) as client:
                result = await client.call_tool(name, arguments)
        except ToolError as exc:
            logger.warning("MCP call_tool %s tool error: %s", name, exc)
            return {"result": str(exc), "mcp_is_error": True}
        except McpError as exc:
            logger.warning("MCP call_tool %s failed: %s", name, exc)
            raise
        payload = structured_from_call_tool_result(result)
        if getattr(result, "is_error", False):
            logger.warning("MCP tool %s returned is_error=True", name)
            payload = {**payload, "mcp_is_error": True}
        return payload

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, Any],
        request_id: str | None,
    ) -> str:
        """Invoke tool and return a string suitable for OpenAI ``tool`` message content."""
        payload = await self.call_tool(name, arguments, request_id)
        return json.dumps(payload, ensure_ascii=False)
