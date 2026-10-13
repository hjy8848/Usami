"""Harness-owned object validation, canonical requests and episode-wide deduplication."""
import json
import re

from usami.customer.observation import observed_ids
from usami.interaction.models import IntentRecord, PreparedTurn
from usami.service import CustomerInput
from usami.world.models import digest


def render_request(op):
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    org, resource, params = quote(op.org_id), quote(op.resource_id), op.params
    if op.name == "change_plan":
        return f"请将组织 {org} 的订阅 {resource} 的套餐改为 {quote(params['plan_id'])}。"
    if op.name == "change_seats":
        return f"请将组织 {org} 的订阅 {resource} 的席位数改为 {params['seats']}。"
    if op.name == "cancel_renewal":
        return f"请关闭组织 {org} 的订阅 {resource} 的自动续费。"
    if op.name == "refund_invoice":
        return (f"请退款组织 {org} 的账单 {resource}，金额为 {params['amount_cents']} 分，"
                f"退款支付方式为 {quote(params['payment_method'])}。")
    if op.name == "change_member_role":
        return f"请将组织 {org} 的成员关系 {resource} 的角色改为 {quote(params['role'])}。"
    raise ValueError("only supported write intents can be rendered")


class IntentAdapter:
    def __init__(self, observation):
        self._visible = observed_ids(observation)
        self._seen = set()

    def receive_reply(self, world, reply):
        # Only literal IDs actually uttered by Service enter the reference catalog.
        # This does not grant access or trust the factual claims in that reply.
        if not reply:
            return
        ids = set(world.organizations) | set(world.subscriptions) | set(world.invoices) | set(world.memberships)
        for entity_id in ids:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(entity_id) + r"(?![A-Za-z0-9_])", reply):
                self._visible.add(entity_id)

    def _can_reference(self, world, op):
        if op.org_id not in world.organizations or op.org_id not in self._visible or op.resource_id not in self._visible:
            return False
        collection = (world.invoices if op.name == "refund_invoice" else
                      world.memberships if op.name == "change_member_role" else world.subscriptions)
        resource = collection.get(op.resource_id)
        if resource is None or resource.org_id != op.org_id:
            return False
        # A plan is a real, public business object; no permission/feasibility check here.
        return op.name != "change_plan" or op.params["plan_id"] in world.rules.plans

    def prepare(self, action, world, identity, turn_id):
        if action.type != "send_message":
            raise ValueError("stop actions cannot create customer requests")
        intents, operations = [], []
        for op in action.requested_operations:
            key = digest(op)
            if not self._can_reference(world, op):
                intents.append(IntentRecord(operation=op, disposition="unverified_object",
                    reason="target is not a real observed object of the expected type and organization"))
            elif key in self._seen:
                intents.append(IntentRecord(operation=op, disposition="duplicate",
                    reason="exact request already recorded in this episode; no automatic renewal"))
            else:
                self._seen.add(key)
                rid = f"{turn_id}_request_{len(operations):03d}"
                operations.append(op)
                intents.append(IntentRecord(operation=op, disposition="accepted", request_id=rid,
                    reason="exact customer intent recorded before Service; not a business permission grant"))
        # Render EVERY structural choice, including unverified/repeated requests, so
        # no hidden structural intent silently contradicts the actual business message.
        message = action.message
        if action.requested_operations:
            requests = "\n".join(f"{n + 1}. {render_request(op)}" for n, op in enumerate(action.requested_operations))
            message = ("顾客自由补充（不改变实际身份、权限或下列明确请求）：\n" + action.message
                       + "\n\n顾客明确业务请求（由 Harness 根据顾客选择生成）：\n" + requests)
        return PreparedTurn(turn_id=turn_id, action=action, intents=intents,
            customer=CustomerInput(identity=identity, message=message, authorizations=operations),
            natural_language_status="canonical_requests" if action.requested_operations else "unverified_free_text")
