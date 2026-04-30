"""HTTP smoke tests with mocked MCP gateway."""

from meridian_api.schemas.mcp_inspection import (
    PromptPublic,
    PromptsListResponse,
    ResourcePublic,
    ResourcesListResponse,
    ResourceTemplatesListResponse,
    ToolPublic,
    ToolsListResponse,
)


class _FakeMcpGateway:
    async def list_tools(self, request_id: str | None) -> ToolsListResponse:
        return ToolsListResponse(
            tools=[
                ToolPublic(
                    name="demo_tool",
                    title="Demo",
                    description="Fake tool",
                    input_schema={"type": "object", "properties": {}},
                )
            ]
        )

    async def list_resources(self, request_id: str | None) -> ResourcesListResponse:
        return ResourcesListResponse(
            resources=[
                ResourcePublic(
                    uri="demo://resource/1",
                    name="r1",
                    title=None,
                    description=None,
                    mime_type="text/plain",
                    size=None,
                )
            ]
        )

    async def list_resource_templates(
        self, request_id: str | None
    ) -> ResourceTemplatesListResponse:
        return ResourceTemplatesListResponse(resource_templates=[])

    async def list_prompts(self, request_id: str | None) -> PromptsListResponse:
        return PromptsListResponse(
            prompts=[
                PromptPublic(
                    name="demo_prompt",
                    title=None,
                    description="Fake prompt",
                    arguments=None,
                )
            ]
        )

    async def read_resource(self, uri: str, request_id: str | None):
        from meridian_api.schemas.mcp_inspection import (
            ResourceContentBlockPublic,
            ResourceReadResponse,
        )

        return ResourceReadResponse(
            uri=uri,
            contents=[
                ResourceContentBlockPublic(
                    type="text",
                    mime_type="text/plain",
                    text="hello",
                    blob=None,
                )
            ],
        )


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_header(client) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc-12345"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "abc-12345"


def test_mcp_tools_mocked(client, app) -> None:
    app.state.mcp_gateway = _FakeMcpGateway()
    response = client.get("/api/mcp/tools")
    assert response.status_code == 200
    body = response.json()
    assert len(body["tools"]) == 1
    assert body["tools"][0]["name"] == "demo_tool"


def test_mcp_resources_read_mocked(client, app) -> None:
    app.state.mcp_gateway = _FakeMcpGateway()
    response = client.get("/api/mcp/resources/read", params={"uri": "demo://x"})
    assert response.status_code == 200
    data = response.json()
    assert data["uri"] == "demo://x"
    assert data["contents"][0]["type"] == "text"
