"""Role-based rules before dispatching MCP tools from chat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChatAuthContext:
    """Actor authenticated at session bootstrap (email+PIN)."""

    actor_email: str
    actor_customer_id: str
    role: str  # buyer | support | admin


@dataclass(frozen=True)
class DelegationContext:
    """Buyer the staff member is assisting."""

    delegated_customer_id: str
    delegated_email: str


class ToolPolicyError(Exception):
    """Raised when a tool call violates session RBAC."""

    def __init__(self, message: str, *, code: str = "policy_violation") -> None:
        super().__init__(message)
        self.code = code


def _norm_uuid(value: str) -> str:
    return value.strip().lower()


def effective_customer_id(
    auth: ChatAuthContext,
    delegation: DelegationContext | None,
) -> str:
    """Customer UUID for scoped buyer/support flows (not used for unrestricted admin list)."""
    r = auth.role.lower()
    if r == "buyer":
        return _norm_uuid(auth.actor_customer_id)
    if r == "support":
        if delegation is None:
            msg = "Delegation required: verify the customer with verify_customer_pin first."
            raise ToolPolicyError(msg, code="delegation_required")
        return _norm_uuid(delegation.delegated_customer_id)
    if r == "admin":
        if delegation is not None:
            return _norm_uuid(delegation.delegated_customer_id)
        return _norm_uuid(auth.actor_customer_id)
    msg = f"Unsupported role: {auth.role}"
    raise ToolPolicyError(msg)


def assert_support_cannot_target_staff(
    auth: ChatAuthContext,
    target_role: str | None,
) -> None:
    """Support cannot act on behalf of or view other staff; admin bypass."""
    if auth.role.lower() != "support":
        return
    if target_role is None:
        return
    tr = target_role.lower()
    if tr in ("support", "admin"):
        msg = "Support cannot access other support or admin accounts."
        raise ToolPolicyError(msg, code="support_visibility")


def validate_tool_call(
    *,
    auth: ChatAuthContext,
    delegation: DelegationContext | None,
    tool_name: str,
    raw_arguments: dict[str, Any],
) -> dict[str, Any]:
    """Return sanitized arguments for MCP (may coerce customer_id). Raises ToolPolicyError."""
    args = dict(raw_arguments)
    role_l = auth.role.lower()

    if tool_name == "verify_customer_pin":
        if role_l == "buyer":
            email = str(args.get("email", "")).strip().lower()
            pin = str(args.get("pin", "")).strip()
            if not email or not pin:
                raise ToolPolicyError("email and pin are required")
            if email != auth.actor_email.strip().lower():
                raise ToolPolicyError("Buyers may only verify their own email.")
            return {"email": email, "pin": pin}
        if role_l in ("support", "admin"):
            return {
                "email": str(args.get("email", "")).strip().lower(),
                "pin": str(args.get("pin", "")).strip(),
            }
        raise ToolPolicyError(f"Cannot verify for role {auth.role}")

    if tool_name == "get_customer":
        cid = _norm_uuid(str(args.get("customer_id", "")))
        if not cid:
            raise ToolPolicyError("customer_id is required")
        if role_l == "admin":
            return {"customer_id": cid}
        if role_l == "buyer":
            if cid != _norm_uuid(auth.actor_customer_id):
                raise ToolPolicyError("Buyers may only load their own customer profile.")
            return {"customer_id": cid}
        if role_l == "support":
            if delegation is None:
                raise ToolPolicyError("Delegation required before get_customer.")
            eff = effective_customer_id(auth, delegation)
            if cid != eff:
                raise ToolPolicyError("Support may only load the delegated customer profile.")
            return {"customer_id": cid}
        raise ToolPolicyError(f"Unsupported role {auth.role}")

    if tool_name in ("list_orders", "get_order"):
        if tool_name == "list_orders":
            if role_l == "admin":
                return args
            eff = effective_customer_id(auth, delegation)
            raw_c = args.get("customer_id")
            if raw_c is None or raw_c == "":
                args = {**args, "customer_id": eff}
            else:
                cid = _norm_uuid(str(raw_c))
                if cid != eff:
                    raise ToolPolicyError("customer_id must match the active customer context.")
        return args

    if tool_name == "create_order":
        cid = _norm_uuid(str(args.get("customer_id", "")))
        if not cid:
            raise ToolPolicyError("customer_id is required")
        if role_l == "buyer":
            if cid != _norm_uuid(auth.actor_customer_id):
                raise ToolPolicyError("Buyers may only create orders for themselves.")
            return args
        if role_l == "support":
            eff = effective_customer_id(auth, delegation)
            if cid != eff:
                raise ToolPolicyError("Support must create orders for the delegated buyer only.")
            if cid == _norm_uuid(auth.actor_customer_id):
                raise ToolPolicyError("Support cannot place orders for their own account.")
            return args
        if role_l == "admin":
            return args
        raise ToolPolicyError(f"Unsupported role {auth.role}")

    if tool_name in ("list_products", "get_product", "search_products"):
        return args

    msg = f"Unknown tool: {tool_name}"
    raise ToolPolicyError(msg)
