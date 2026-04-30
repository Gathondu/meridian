"""Chat HTTP tests with mocked MCP and isolated session directory."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.testclient import TestClient

from meridian_api.core.settings import get_settings
from meridian_api.main import create_app


class _FakeMcpGatewayVerify:
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        request_id: str | None,
    ) -> dict[str, Any]:
        if name == "verify_customer_pin":
            email = str(arguments.get("email", "")).lower()
            if "fail" in email:
                return {"result": "Invalid PIN", "mcp_is_error": True}
            return {
                "result": (
                    "Verified.\nCustomer ID: 11111111-1111-1111-1111-111111111111\n"
                    "Role: buyer\n"
                )
            }
        return {"result": "{}"}


@pytest.fixture
def chat_app(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    sessions_root = tmp_path_factory.mktemp("chat_sessions")
    monkeypatch.setenv("CHAT_SESSIONS_DIR", str(sessions_root))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    get_settings.cache_clear()
    app = create_app()
    yield app
    get_settings.cache_clear()


@pytest.fixture
def chat_client(chat_app):
    """Install a fake MCP gateway after TestClient runs lifespan (which sets the real gateway)."""
    with TestClient(chat_app) as client:
        chat_app.state.mcp_gateway = _FakeMcpGatewayVerify()
        yield client


def test_create_pending_chat_session(chat_client: TestClient) -> None:
    response = chat_client.post("/api/chat/sessions")
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert len(body["session_id"]) > 10


def test_pending_session_has_no_auth_on_disk(chat_client: TestClient) -> None:
    created = chat_client.post("/api/chat/sessions")
    sid = created.json()["session_id"]
    from meridian_api.repositories.chat_session_json import ChatSessionJsonRepository

    repo = ChatSessionJsonRepository(get_settings())
    record = repo.load(sid)
    assert record.auth is None


def test_stream_message_503_without_openai_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    root = tmp_path_factory.mktemp("chat_sessions_2")
    monkeypatch.setenv("CHAT_SESSIONS_DIR", str(root))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        app.state.mcp_gateway = _FakeMcpGatewayVerify()
        created = client.post("/api/chat/sessions")
        assert created.status_code == 200
        sid = created.json()["session_id"]
        stream = client.post(
            "/api/chat/sessions/{sid}/messages".replace("{sid}", sid),
            json={"text": "hello"},
        )
        assert stream.status_code == 503
    get_settings.cache_clear()
