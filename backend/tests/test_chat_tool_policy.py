"""Unit tests for chat MCP tool RBAC."""

import pytest

from meridian_api.services.chat_tool_policy import (
    ChatAuthContext,
    DelegationContext,
    ToolPolicyError,
    validate_tool_call,
)


def _buyer() -> ChatAuthContext:
    return ChatAuthContext(
        actor_email="buyer@example.com",
        actor_customer_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        role="buyer",
    )


def _support() -> ChatAuthContext:
    return ChatAuthContext(
        actor_email="support@example.com",
        actor_customer_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        role="support",
    )


def _admin() -> ChatAuthContext:
    return ChatAuthContext(
        actor_email="admin@example.com",
        actor_customer_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        role="admin",
    )


def _delegation() -> DelegationContext:
    return DelegationContext(
        delegated_customer_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
        delegated_email="cust@example.com",
    )


def test_buyer_verify_own_email_ok() -> None:
    out = validate_tool_call(
        auth=_buyer(),
        delegation=None,
        tool_name="verify_customer_pin",
        raw_arguments={"email": "buyer@example.com", "pin": "1234"},
    )
    assert out["email"] == "buyer@example.com"


def test_buyer_verify_other_email_denied() -> None:
    with pytest.raises(ToolPolicyError):
        validate_tool_call(
            auth=_buyer(),
            delegation=None,
            tool_name="verify_customer_pin",
            raw_arguments={"email": "other@example.com", "pin": "1234"},
        )


def test_support_list_orders_requires_delegation() -> None:
    with pytest.raises(ToolPolicyError) as exc:
        validate_tool_call(
            auth=_support(),
            delegation=None,
            tool_name="list_orders",
            raw_arguments={},
        )
    assert exc.value.code == "delegation_required"


def test_support_list_orders_with_delegation_injects_customer_id() -> None:
    out = validate_tool_call(
        auth=_support(),
        delegation=_delegation(),
        tool_name="list_orders",
        raw_arguments={},
    )
    assert out["customer_id"] == "dddddddd-dddd-dddd-dddd-dddddddddddd"


def test_admin_list_orders_passes_filters() -> None:
    out = validate_tool_call(
        auth=_admin(),
        delegation=None,
        tool_name="list_orders",
        raw_arguments={"status": "pending"},
    )
    assert out["status"] == "pending"
