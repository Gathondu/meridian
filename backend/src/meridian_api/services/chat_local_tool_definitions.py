"""OpenAI function tools handled in-app (not proxied to MCP)."""

from __future__ import annotations

from typing import Any

SUBMIT_ORDER_CREDENTIALS = "submit_order_credentials"
SUBMIT_DELEGATION_CREDENTIALS = "submit_delegation_credentials"


def submit_order_credentials_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": SUBMIT_ORDER_CREDENTIALS,
            "description": (
                "After the user has told you their order account email and 4-digit PIN in chat, "
                "call this once with those exact values to sign them in. Do not guess or invent values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Order account email."},
                    "pin": {"type": "string", "description": "4-digit PIN."},
                },
                "required": ["email", "pin"],
            },
        },
    }


def submit_delegation_credentials_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": SUBMIT_DELEGATION_CREDENTIALS,
            "description": (
                "For support or admin only: after the customer has given you their email and "
                "4-digit PIN in chat, call this to act on their behalf for orders and profile."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string"},
                    "customer_pin": {"type": "string", "description": "Customer 4-digit PIN."},
                },
                "required": ["customer_email", "customer_pin"],
            },
        },
    }
