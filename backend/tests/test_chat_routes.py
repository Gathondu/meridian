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


def test_get_chat_session_returns_visible_transcript(chat_client: TestClient) -> None:
    created = chat_client.post("/api/chat/sessions")
    sid = created.json()["session_id"]
    from meridian_api.repositories.chat_session_json import ChatSessionJsonRepository

    repo = ChatSessionJsonRepository(get_settings())
    record = repo.load(sid)
    record.openai_messages = [
        {"role": "system", "content": "hidden"},
        {"role": "user", "content": "Where is my order?"},
        {"role": "assistant", "content": "I can help with that."},
        {"role": "tool", "content": "{\"status\":\"ok\"}"},
        {"role": "assistant", "content": None, "tool_calls": []},
    ]
    repo.save(record)

    response = chat_client.get(f"/api/chat/sessions/{sid}")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == sid
    assert body["user_session_id"] is None  # New field
    assert body["title"] is None  # New field
    assert body["messages"] == [
        {
            "role": "user",
            "content": "Where is my order?",
            "timestamp": record.created_at,
        },
        {
            "role": "assistant",
            "content": "I can help with that.",
            "timestamp": record.created_at,
        },
    ]


def test_get_chat_session_404_when_missing(chat_client: TestClient) -> None:
    response = chat_client.get("/api/chat/sessions/not-found")

    assert response.status_code == 404


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


def test_create_chat_with_user_session_id_and_title(chat_client: TestClient) -> None:
    """Test creating a chat with user_session_id and title."""
    response = chat_client.post(
        "/api/chat/chats",
        json={"user_session_id": "user123", "title": "My Chat Title"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert len(body["session_id"]) > 10


def test_get_chat_session_includes_new_fields(chat_client: TestClient) -> None:
    """Test that getting a chat session includes the new fields."""
    # Create a chat with user_session_id and title
    create_response = chat_client.post(
        "/api/chat/chats",
        json={"user_session_id": "user456", "title": "Test Chat"},
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    # Get the chat session
    response = chat_client.get(f"/api/chat/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["user_session_id"] == "user456"
    assert body["title"] == "Test Chat"


def test_list_chats_filter_by_user_session_id(chat_client: TestClient) -> None:
    """Test listing chats filtered by user_session_id."""
    # Create chats for different users
    chat_client.post("/api/chat/chats", json={"user_session_id": "user789", "title": "Chat 1"})
    chat_client.post("/api/chat/chats", json={"user_session_id": "user789", "title": "Chat 2"})
    chat_client.post("/api/chat/chats", json={"user_session_id": "user999", "title": "Chat 3"})

    # List chats for user789
    response = chat_client.get("/api/chat/chats?user_session_id=user789")
    assert response.status_code == 200
    body = response.json()
    assert len(body["chats"]) == 2
    for chat in body["chats"]:
        assert chat["user_session_id"] == "user789"

    # List chats for user999
    response = chat_client.get("/api/chat/chats?user_session_id=user999")
    assert response.status_code == 200
    body = response.json()
    assert len(body["chats"]) == 1
    assert body["chats"][0]["user_session_id"] == "user999"

    # List all chats (no filter)
    response = chat_client.get("/api/chat/chats")
    assert response.status_code == 200
    body = response.json()
    assert len(body["chats"]) == 3


def test_update_chat_title(chat_client: TestClient) -> None:
    """Test updating a chat's title."""
    # Create a chat
    create_response = chat_client.post(
        "/api/chat/chats",
        json={"user_session_id": "user111", "title": "Original Title"},
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    # Update the title
    update_response = chat_client.put(
        f"/api/chat/chats/{session_id}/title",
        json={"title": "Updated Title"},
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["session_id"] == session_id
    assert body["title"] == "Updated Title"
    assert body["user_session_id"] == "user111"

    # Verify the update persisted by getting the chat
    get_response = chat_client.get(f"/api/chat/sessions/{session_id}")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["title"] == "Updated Title"


def test_update_chat_title_from_plain_text_body(chat_client: TestClient) -> None:
    create_response = chat_client.post(
        "/api/chat/chats",
        json={"user_session_id": "user222", "title": "Original Title"},
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    update_response = chat_client.post(
        f"/api/chat/chats/{session_id}/title",
        content="Plain Text Title",
        headers={"Content-Type": "text/plain;charset=UTF-8"},
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["title"] == "Plain Text Title"


def test_update_chat_title_cors_preflight_allows_put(chat_client: TestClient) -> None:
    response = chat_client.options(
        "/api/chat/chats/session-id/title",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PUT" in response.headers["access-control-allow-methods"]
