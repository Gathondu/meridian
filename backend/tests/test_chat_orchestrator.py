"""Unit coverage for chat orchestration helpers."""

from typing import Any

import pytest

from meridian_api.services.chat_orchestrator import (
    _extract_order_items,
    _prepare_create_order_args,
)
from meridian_api.services.chat_tool_policy import ToolPolicyError


def test_extract_order_items_from_sku_quantity_lines() -> None:
    items = _extract_order_items(
        """
        I can place an order for:
        - MON-0082 x1
        - ACC-0132 X2
        """
    )

    assert items == [
        {"sku": "MON-0082", "quantity": 1},
        {"sku": "ACC-0132", "quantity": 2},
    ]


def test_extract_order_items_combines_duplicate_skus() -> None:
    items = _extract_order_items("MON-0082 x1 and MON-0082 x3")

    assert items == [{"sku": "MON-0082", "quantity": 4}]


class _FakeProductGateway:
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        request_id: str | None,
    ) -> dict[str, Any]:
        assert name == "get_product"
        prices = {
            "MON-0082": "Product: Portable Monitor - Model B\nSKU: MON-0082\nPrice: $217.98 USD\nStock: 73 units",
            "ACC-0132": "Product: Wireless Keyboard - Model B\nSKU: ACC-0132\nPrice: $30.20 USD\nStock: 68 units",
        }
        return {"result": prices[str(arguments["sku"])]}


@pytest.mark.anyio
async def test_prepare_create_order_args_adds_unit_prices_from_products() -> None:
    out = await _prepare_create_order_args(
        {
            "customer_id": "1da9f01a-b8ea-461c-b6d4-27ae5b43cd9f",
            "items": [
                {"sku": "mon-0082", "quantity": "2"},
                {"sku": "ACC-0132", "quantity": 1},
            ],
        },
        gateway=_FakeProductGateway(),
        request_id="test",
    )

    assert out == {
        "customer_id": "1da9f01a-b8ea-461c-b6d4-27ae5b43cd9f",
        "items": [
            {"sku": "MON-0082", "quantity": 2, "unit_price": "217.98", "currency": "USD"},
            {"sku": "ACC-0132", "quantity": 1, "unit_price": "30.20", "currency": "USD"},
        ],
    }


@pytest.mark.anyio
async def test_prepare_create_order_args_keeps_existing_unit_price() -> None:
    out = await _prepare_create_order_args(
        {
            "customer_id": "1da9f01a-b8ea-461c-b6d4-27ae5b43cd9f",
            "items": [{"sku": "MON-0082", "quantity": 1, "unit_price": "199.99", "currency": "USD"}],
        },
        gateway=_FakeProductGateway(),
        request_id=None,
    )

    assert out["items"] == [
        {"sku": "MON-0082", "quantity": 1, "unit_price": "199.99", "currency": "USD"}
    ]


@pytest.mark.anyio
async def test_prepare_create_order_args_requires_items() -> None:
    with pytest.raises(ToolPolicyError):
        await _prepare_create_order_args(
            {"customer_id": "1da9f01a-b8ea-461c-b6d4-27ae5b43cd9f", "items": []},
            gateway=_FakeProductGateway(),
            request_id=None,
        )
