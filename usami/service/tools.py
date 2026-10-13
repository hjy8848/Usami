"""Schemas from the core protocol; projection only, never business decisions."""
from __future__ import annotations

from usami.protocol import PARAMETERS, Operation
from usami.service.models import ServiceError, strict_json

DESCRIPTIONS = {
    "get_customer_context": "Get the fixed authenticated customer's own profile and organization memberships. No identity argument.",
    "get_organization": "Read an organization. On success also discover related invoice IDs; subscription ID is in the entity.",
    "list_members": "Read organization memberships and related public user profiles; resource_id must equal org_id.",
    "get_subscription": "Read the actual subscription, plan, seats, renewal and billing period.",
    "get_invoice": "Read a specific invoice, paid amount, original payment method and refund history. Permissions are enforced.",
    "change_plan": "Change the subscription plan requested by the customer; the current seats must fit the target plan.",
    "change_seats": "Change subscription seats. Respect plan capacity and active member count.",
    "cancel_renewal": "Disable automatic renewal without changing the current service period.",
    "refund_invoice": "Refund an invoice in full to its original payment method, within the reference refund window.",
    "change_member_role": "Change a member's role as requested. Only the owner can manage roles; owner transfer is unsupported.",
}


def tool_schemas(names):
    tools = []
    for name in names:
        props, required = {}, []
        if name != "get_customer_context":
            params = PARAMETERS[name].model_json_schema()
            props = {"org_id": {"type": "string", "description": "Target organization ID"},
                     "resource_id": {"type": "string", "description": "Target organization, subscription, invoice or membership ID"},
                     **params.get("properties", {})}
            required = ["org_id", "resource_id", *params.get("required", [])]
        tools.append({"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name],
            "parameters": {"type": "object", "properties": props, "required": required, "additionalProperties": False}}})
    return tools


def parse_operation(name, arguments):
    try:
        data = strict_json(arguments)
        if not isinstance(data, dict):
            raise ValueError("arguments must be an object")
        if name == "get_customer_context":
            if data:
                raise ValueError("identity is fixed; this tool takes no arguments")
            return None
        shape = PARAMETERS[name].model_json_schema().get("properties", {})
        if set(data) - {"org_id", "resource_id", *shape}:
            raise ValueError("unexpected argument")
        return Operation(name=name, org_id=data["org_id"], resource_id=data["resource_id"],
                         params={k: v for k, v in data.items() if k not in {"org_id", "resource_id"}})
    except (ValueError, KeyError, TypeError):
        raise ServiceError("INVALID_TOOL_ARGUMENTS", "Arguments must match the advertised tool schema; identity and authorization cannot be supplied") from None


def customer_context(world, identity):
    memberships = [m for m in world.memberships.values() if m.user_id == identity]
    return {"customer": world.users[identity].model_dump(mode="json"),
            "memberships": [m.model_dump(mode="json") for m in memberships],
            "organizations": [{"id": world.organizations[m.org_id].id, "name": world.organizations[m.org_id].name}
                              for m in memberships]}


def discovery(world, op, result):
    # Additional ID/name projections are gated by an actual successful core query.
    if not result["success"]:
        return {}
    if op.name == "get_organization":
        return {"invoice_ids": [i.id for i in world.invoices.values() if i.org_id == op.org_id]}
    if op.name == "list_members":
        members = result["data"]["memberships"]
        return {"users": [world.users[m["user_id"]].model_dump(mode="json") for m in members]}
    return {}
