"""OpenAI Chat Completions ``tools`` definitions aligned with order MCP."""

from __future__ import annotations

from typing import Any

_ORDER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List products with optional category and active filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter.",
                    },
                    "is_active": {
                        "type": "boolean",
                        "description": "Optional active flag filter.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get product details by SKU.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}},
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search products by name or description.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Get customer profile by UUID.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_customer_pin",
            "description": "Verify customer email and 4-digit PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "pin": {"type": "string"},
                },
                "required": ["email", "pin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "List orders with optional customer UUID and status filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Optional customer UUID filter.",
                    },
                    "status": {"type": "string", "description": "Optional order status filter."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get order details by order UUID.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": (
                "Create an order with line items. Omit customer_id to use the active verified "
                "customer stored in the current chat session."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Optional customer UUID; defaults to the active verified customer.",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "quantity": {"type": "integer", "minimum": 1},
                                "unit_price": {
                                    "type": "string",
                                    "description": "Optional. Backend fills current product price when omitted.",
                                },
                                "currency": {
                                    "type": "string",
                                    "description": "Optional. Defaults to USD.",
                                },
                            },
                            "required": ["sku", "quantity"],
                            "additionalProperties": True,
                        },
                    },
                },
                "required": ["items"],
            },
        },
    },
]


def order_tool_definitions() -> list[dict[str, Any]]:
    """Return a fresh list for mutability safety."""
    return list(_ORDER_TOOLS)
