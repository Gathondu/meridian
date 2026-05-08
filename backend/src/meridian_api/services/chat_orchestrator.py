"""OpenAI chat streaming with MCP tools; yields JSON-serializable SSE events."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from meridian_api.core.settings import Settings
from meridian_api.repositories.chat_session_json import ChatSessionRepositoryError
from meridian_api.repositories.chat_session_protocol import ChatSessionPersistence
from meridian_api.schemas.chat_session import (
    AuthRecord,
    ChatSessionRecord,
    DelegationRecord,
)
from meridian_api.services.chat_local_tool_definitions import (
    SUBMIT_DELEGATION_CREDENTIALS,
    SUBMIT_ORDER_CREDENTIALS,
    submit_delegation_credentials_tool,
    submit_order_credentials_tool,
)
from meridian_api.services.chat_tool_policy import (
    ChatAuthContext,
    DelegationContext,
    ToolPolicyError,
    validate_tool_call,
)
from meridian_api.services.mcp_gateway import McpGatewayService
from meridian_api.services.mcp_text_parsers import (
    extract_customer_id_from_verify_text,
    extract_price_from_product_text,
    extract_role_from_verify_text,
    structured_to_assistant_visible_text,
    tool_result_to_text,
)
from meridian_api.services.openai_config import resolve_openai_api_key
from meridian_api.services.openai_tool_definitions import order_tool_definitions

logger = logging.getLogger(__name__)

_MAX_AGENT_ROUNDS = 12
_ORDER_ITEM_RE = re.compile(r"\b([A-Z]{3}-\d{4})\b\s*(?:x|X|qty\s*)\s*(\d+)\b")

_SYSTEM_PROMPT = (
    "You are Meridian, an order assistant backed by tools. "
    "Use tools for product, customer, and order facts. "
    "Respect access rules: buyers only see their own data; support acts for a delegated buyer."
)

_BOOTSTRAP_SYSTEM_PROMPT = (
    "You are Meridian, an order assistant. The user is not signed in yet. "
    "Briefly greet them, then ask for their order account email and 4-digit PIN as they would "
    "use them in chat (no separate form). When they have given you both, call submit_order_credentials "
    "with the exact email and PIN they provided. Do not invent credentials. "
    "Do not call other tools until sign-in succeeds."
)


def _openai_base_url(settings: Settings) -> str | None:
    raw = settings.openai_base_url
    if raw is None:
        return None
    url = str(raw).strip()
    return url or None


def _delegation_from_record(record: ChatSessionRecord) -> DelegationContext | None:
    d = record.delegation
    if d is None:
        return None
    return DelegationContext(
        delegated_customer_id=d.delegated_customer_id,
        delegated_email=d.delegated_email,
    )


def _extract_order_items(text: str) -> list[dict[str, Any]]:
    items: dict[str, int] = {}
    for sku, qty_raw in _ORDER_ITEM_RE.findall(text):
        qty = int(qty_raw)
        if qty < 1:
            continue
        sku = sku.upper()
        items[sku] = items.get(sku, 0) + qty
    return [{"sku": sku, "quantity": qty} for sku, qty in items.items()]


def _coerce_order_quantity(value: Any) -> int:
    try:
        quantity = int(value)
    except (TypeError, ValueError) as exc:
        raise ToolPolicyError("Order item quantity must be a positive integer.") from exc
    if quantity < 1:
        raise ToolPolicyError("Order item quantity must be a positive integer.")
    return quantity


async def _prepare_create_order_args(
    args: dict[str, Any],
    *,
    gateway: McpGatewayService,
    request_id: str | None,
) -> dict[str, Any]:
    items = args.get("items")
    if not isinstance(items, list) or not items:
        raise ToolPolicyError("items are required for create_order")

    prepared_items: list[dict[str, Any]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise ToolPolicyError("Each order item must be an object.")
        sku = str(raw_item.get("sku", "")).strip().upper()
        if not sku:
            raise ToolPolicyError("Each order item needs a sku.")
        quantity = _coerce_order_quantity(raw_item.get("quantity", 1))
        unit_price = raw_item.get("unit_price") or raw_item.get("price")
        currency = str(raw_item.get("currency") or "USD").strip().upper()

        if unit_price is None or str(unit_price).strip() == "":
            product_payload = await gateway.call_tool("get_product", {"sku": sku}, request_id)
            if product_payload.get("mcp_is_error"):
                detail = structured_to_assistant_visible_text(product_payload)
                raise ToolPolicyError(f"Could not load price for {sku}: {detail}")
            parsed_price = extract_price_from_product_text(tool_result_to_text(product_payload))
            if parsed_price is None:
                raise ToolPolicyError(f"Could not find unit price for {sku}.")
            unit_price, currency = parsed_price

        prepared_items.append(
            {
                **raw_item,
                "sku": sku,
                "quantity": quantity,
                "unit_price": str(unit_price).strip().replace("$", ""),
                "currency": currency or "USD",
            }
        )

    return {**args, "items": prepared_items}


def _system_content_for_record(record: ChatSessionRecord) -> str:
    if record.auth is None:
        return _BOOTSTRAP_SYSTEM_PROMPT
    base = _SYSTEM_PROMPT
    base += (
        f" Signed-in actor: {record.auth.actor_email}; role: {record.auth.role}; "
        f"actor customer UUID: {record.auth.actor_customer_id}."
    )
    role = record.auth.role.lower()
    if record.delegation is not None:
        base += (
            f" Active customer context: {record.delegation.delegated_email}; "
            f"customer UUID: {record.delegation.delegated_customer_id}. "
            "When creating orders, use this active customer context; do not ask the user for a UUID."
        )
    elif role == "buyer":
        base += (
            " Active customer context is the signed-in buyer. When creating orders or listing "
            "customer-scoped orders, use the actor customer UUID; do not ask the user for a UUID."
        )
    if record.pending_order_items:
        base += (
            " Pending order items remembered from this chat: "
            f"{json.dumps(record.pending_order_items, ensure_ascii=False)}. "
            "If the user confirms placing the order, call create_order with these items."
        )
    if role in ("support", "admin") and record.delegation is None:
        base += (
            " This user is staff. Before using customer-scoped or order tools, ask the buyer for "
            "their order email and 4-digit PIN in chat, then call submit_delegation_credentials "
            "with those values."
        )
    return base


def _messages_with_system(
    messages: list[dict[str, Any]],
    record: ChatSessionRecord,
) -> list[dict[str, Any]]:
    want = _system_content_for_record(record)
    if not messages:
        return [{"role": "system", "content": want}]
    if messages[0].get("role") == "system":
        out = list(messages)
        out[0] = {**out[0], "content": want}
        return out
    return [{"role": "system", "content": want}, *messages]


def _openai_tools(record: ChatSessionRecord) -> list[ChatCompletionToolParam]:
    if record.auth is None:
        return cast(list[ChatCompletionToolParam], [submit_order_credentials_tool()])
    tools: list[dict[str, Any]] = list(order_tool_definitions())
    if record.delegation is None and record.auth.role.lower() in ("support", "admin"):
        tools.append(submit_delegation_credentials_tool())
    return cast(list[ChatCompletionToolParam], tools)


async def stream_chat_turn(
    *,
    settings: Settings,
    record: ChatSessionRecord,
    user_text: str,
    gateway: McpGatewayService,
    repo: ChatSessionPersistence,
    request_id: str | None,
) -> AsyncIterator[dict[str, Any]]:
    api_key = resolve_openai_api_key(settings)
    if not api_key:
        yield {"type": "error", "message": "OpenAI is not configured.", "ok": False}
        yield {"type": "finished", "ok": False}
        return

    user_text_clean = user_text.strip()
    user_items = _extract_order_items(user_text_clean)
    if user_items:
        record.pending_order_items = user_items
        repo.save(record)

    messages = _messages_with_system(list(record.openai_messages), record)
    messages.append({"role": "user", "content": user_text_clean})

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    base_url = _openai_base_url(settings)
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)
    model = settings.openai_model

    try:
        for _ in range(_MAX_AGENT_ROUNDS):
            tools = _openai_tools(record)
            tool_calls_acc: dict[int, dict[str, str]] = {}
            content_parts: list[str] = []
            finish_reason: str | None = None

            stream = await client.chat.completions.create(
                model=model,
                messages=cast(list[ChatCompletionMessageParam], messages),
                tools=tools,
                stream=True,
                parallel_tool_calls=True,
            )

            async for chunk in stream:
                for choice in chunk.choices:
                    delta = choice.delta
                    if delta.content:
                        piece = delta.content
                        content_parts.append(piece)
                        yield {"type": "content_delta", "text": piece}
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_acc:
                                tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls_acc[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_acc[idx]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_acc[idx]["arguments"] += tc.function.arguments
                    fr = choice.finish_reason
                    if fr is not None:
                        finish_reason = fr

            assistant_text = "".join(content_parts) if content_parts else ""

            if finish_reason == "tool_calls":
                if not tool_calls_acc:
                    yield {
                        "type": "error",
                        "message": "Model requested tools but sent no tool call payload.",
                        "ok": False,
                    }
                    yield {"type": "finished", "ok": False}
                    return

                ordered_keys = sorted(tool_calls_acc)
                openai_tool_calls = [
                    {
                        "id": tool_calls_acc[i]["id"],
                        "type": "function",
                        "function": {
                            "name": tool_calls_acc[i]["name"],
                            "arguments": tool_calls_acc[i]["arguments"] or "{}",
                        },
                    }
                    for i in ordered_keys
                ]
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": assistant_text or None,
                    "tool_calls": openai_tool_calls,
                }
                messages.append(assistant_msg)

                for i in ordered_keys:
                    row = tool_calls_acc[i]
                    name = row["name"]
                    yield {"type": "tool_call_start", "name": name, "text": None}
                    raw_json = row["arguments"] or "{}"
                    try:
                        parsed = json.loads(raw_json)
                    except json.JSONDecodeError as exc:
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": False,
                            "text": f"Invalid tool arguments JSON: {exc}",
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": json.dumps(
                                    {"error": "invalid_arguments", "detail": str(exc)},
                                    ensure_ascii=False,
                                ),
                            }
                        )
                        continue

                    if not isinstance(parsed, dict):
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": False,
                            "text": "Tool arguments must be a JSON object.",
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": json.dumps(
                                    {"error": "invalid_arguments"},
                                    ensure_ascii=False,
                                ),
                            }
                        )
                        continue

                    if name == "create_order" and not parsed.get("items") and record.pending_order_items:
                        parsed = {**parsed, "items": record.pending_order_items}

                    if name == SUBMIT_ORDER_CREDENTIALS:
                        if record.auth is not None:
                            vis = "Already signed in."
                            yield {"type": "tool_call_done", "name": name, "ok": True, "text": None}
                            messages.append(
                                {"role": "tool", "tool_call_id": row["id"], "content": vis}
                            )
                            continue

                        email = str(parsed.get("email", "")).strip().lower()
                        pin = str(parsed.get("pin", "")).strip()
                        if not email or not pin:
                            detail = "email and pin are required."
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": json.dumps({"error": detail}, ensure_ascii=False),
                                }
                            )
                            continue

                        payload = await gateway.call_tool(
                            "verify_customer_pin",
                            {"email": email, "pin": pin},
                            request_id,
                        )
                        text = tool_result_to_text(payload)
                        cid = extract_customer_id_from_verify_text(text)
                        role = extract_role_from_verify_text(text)
                        if not cid or not role or payload.get("mcp_is_error"):
                            vis = (
                                "Sign-in failed. Ask the user to double-check email and PIN, then try again."
                            )
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": vis,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": vis,
                                }
                            )
                            continue

                        record.auth = AuthRecord(
                            actor_email=email,
                            actor_customer_id=cid,
                            role=role,
                        )
                        repo.save(record)
                        if messages and messages[0].get("role") == "system":
                            messages[0] = {
                                "role": "system",
                                "content": _system_content_for_record(record),
                            }
                        vis = (
                            f"Signed in successfully as {email} (role: {role}). "
                            "You may now use order and catalog tools as allowed for this role."
                        )
                        yield {"type": "tool_call_done", "name": name, "ok": True, "text": None}
                        messages.append(
                            {"role": "tool", "tool_call_id": row["id"], "content": vis}
                        )
                        continue

                    if name == SUBMIT_DELEGATION_CREDENTIALS:
                        if record.auth is None:
                            detail = "Sign in first before delegating."
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": detail,
                                }
                            )
                            continue

                        auth_role = record.auth.role.lower()
                        if auth_role not in ("support", "admin"):
                            detail = "Only support or admin may delegate."
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": detail,
                                }
                            )
                            continue

                        if record.delegation is not None:
                            vis = "Delegation is already set."
                            yield {"type": "tool_call_done", "name": name, "ok": True, "text": None}
                            messages.append(
                                {"role": "tool", "tool_call_id": row["id"], "content": vis}
                            )
                            continue

                        ce = str(parsed.get("customer_email", "")).strip().lower()
                        cp = str(parsed.get("customer_pin", "")).strip()
                        if not ce or not cp:
                            detail = "customer_email and customer_pin are required."
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": detail,
                                }
                            )
                            continue

                        try:
                            record = await repo.set_delegation_from_verify(
                                session_id=record.session_id,
                                customer_email=ce,
                                customer_pin=cp,
                                auth_role=record.auth.role,
                                gateway=gateway,
                                request_id=request_id,
                            )
                        except ChatSessionRepositoryError as exc:
                            logger.warning("Delegation failed: %s", exc)
                            detail = str(exc)
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": detail,
                                }
                            )
                            continue
                        except Exception as exc:
                            logger.exception("Delegation MCP failed")
                            detail = str(exc)
                            yield {
                                "type": "tool_call_done",
                                "name": name,
                                "ok": False,
                                "text": detail,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": row["id"],
                                    "content": detail,
                                }
                            )
                            continue

                        if messages and messages[0].get("role") == "system":
                            messages[0] = {
                                "role": "system",
                                "content": _system_content_for_record(record),
                            }
                        vis = f"Delegation set for {ce}. You may assist this customer with orders."
                        yield {"type": "tool_call_done", "name": name, "ok": True, "text": None}
                        messages.append(
                            {"role": "tool", "tool_call_id": row["id"], "content": vis}
                        )
                        continue

                    if record.auth is None:
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": False,
                            "text": "Sign in required before using this tool.",
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": '{"error":"not_signed_in"}',
                            }
                        )
                        continue

                    auth = ChatAuthContext(
                        actor_email=record.auth.actor_email,
                        actor_customer_id=record.auth.actor_customer_id,
                        role=record.auth.role,
                    )
                    delegation = _delegation_from_record(record)

                    try:
                        safe_args = validate_tool_call(
                            auth=auth,
                            delegation=delegation,
                            tool_name=name,
                            raw_arguments=parsed,
                        )
                        if name == "create_order":
                            safe_args = await _prepare_create_order_args(
                                safe_args,
                                gateway=gateway,
                                request_id=request_id,
                            )
                        payload = await gateway.call_tool(name, safe_args, request_id)
                        visible = structured_to_assistant_visible_text(payload)
                        ok = not bool(payload.get("mcp_is_error"))
                        if ok and name == "create_order":
                            record.pending_order_items = []
                            repo.save(record)
                        if ok and name == "verify_customer_pin":
                            cid = extract_customer_id_from_verify_text(visible)
                            target_role = extract_role_from_verify_text(visible)
                            email = str(parsed.get("email", "")).strip().lower()
                            if (
                                cid
                                and target_role == "buyer"
                                and record.auth.role.lower() in ("support", "admin")
                            ):
                                record.delegation = DelegationRecord(
                                    delegated_customer_id=cid,
                                    delegated_email=email,
                                )
                                repo.save(record)
                                if messages and messages[0].get("role") == "system":
                                    messages[0] = {
                                        "role": "system",
                                        "content": _system_content_for_record(record),
                                    }
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": ok,
                            "text": None if ok else visible[:4000],
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": visible,
                            }
                        )
                    except ToolPolicyError as exc:
                        detail = str(exc)
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": False,
                            "text": detail,
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": json.dumps(
                                    {"error": detail, "code": exc.code},
                                    ensure_ascii=False,
                                ),
                            }
                        )
                    except Exception as exc:
                        logger.exception("MCP tool %s failed", name)
                        detail = str(exc)
                        yield {
                            "type": "tool_call_done",
                            "name": name,
                            "ok": False,
                            "text": detail,
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": row["id"],
                                "content": json.dumps({"error": detail}, ensure_ascii=False),
                            }
                        )

                continue

            messages.append({"role": "assistant", "content": assistant_text})
            assistant_items = _extract_order_items(assistant_text)
            if assistant_items:
                record.pending_order_items = assistant_items
            break

        record.openai_messages = messages
        repo.save(record)
        yield {"type": "finished", "ok": True}

    except Exception as exc:
        logger.exception("stream_chat_turn failed")
        yield {"type": "error", "message": str(exc), "ok": False}
        yield {"type": "finished", "ok": False}
