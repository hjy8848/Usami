"""Translate native Oracle rows without inventing another business judge."""
from __future__ import annotations

from types import SimpleNamespace

from .domains import execution_of

CLASSIFICATIONS = ("successful_business_violation", "rejected_invalid_attempt", "authorization_only",
                   "false_rejection", "legal_execution", "unscored")


def operation_rows(domain, trace, track="discovery"):
    execution = execution_of(domain, trace, track)
    if domain != "saas":
        return [dict(row) for row in execution.oracle["operations"]]
    if track == "discovery":
        audits = trace.operation_audits
    else:
        from usami.interaction.runner import audit_operations
        turn = SimpleNamespace(prepared=SimpleNamespace(turn_id="initial"),
                               service=SimpleNamespace(tool_start=0, tool_end=len(execution.tool_records)))
        audits = audit_operations(execution, [turn])
    events = {event.event_id: event for event in execution.world_trace.events}
    rows = []
    for audit in audits:
        event = events[audit.event_id]
        op = audit.operation
        request = execution.trusted_requests[event.payload["request_id"]]
        rows.append(dict(event_id=audit.event_id, operation=op.name,
                         authorized=request.authorizes(event.payload["actor_id"], op),
                         reference_allowed=audit.reference_allowed,
                         reference_error_code=audit.reference_error_code,
                         success=event.payload["result"]["success"],
                         classification=audit.classification,
                         operation_correct=audit.oracle.operation_correct,
                         violations=[violation.code for violation in audit.oracle.violations],
                         before_hash=event.before.state_hash, after_hash=event.after.state_hash))
    return rows


def _cmp(left, right):
    return "lt" if left < right else "eq" if left == right else "gt"


def normalized_facts(domain, event):
    """Conservative ID-free features for known paths, exact fallback for others.

    The fallback is intentionally marked pending: an unknown causal relation is
    retained as separate evidence rather than falsely claiming semantic identity.
    These facts are privileged post-run verification input, never Agent context.
    """
    actor = event.payload.get("actor_id", event.payload.get("actor"))
    raw = event.payload["operation"]
    if domain == "saas":
        from usami.protocol import Operation
        from usami.audit.signatures import facts
        op, before = Operation.model_validate(raw), event.before
        try:
            result = facts(before, actor, op)
            result["policy_version"] = before.rules.version
            if op.name in {"activate_member", "deactivate_member", "remove_member", "invite_member"}:
                org = before.organizations.get(op.org_id)
                sub = before.subscriptions.get(org.subscription_id) if org else None
                if sub:
                    active = sum(member.org_id == op.org_id and member.status == "active" for member in before.memberships.values())
                    result["subscription_dependency"] = {"status": sub.status, "seats_vs_active": _cmp(sub.seats, active),
                                                         "seats_vs_plan": _cmp(sub.seats, before.rules.plans[sub.plan_id].max_seats)}
            return result, "policy_relative_features"
        except (KeyError, AttributeError, TypeError):
            return {"policy_version": before.rules.version, "exact_prestate_hash": before.state_hash}, "pending_causal_normalization"
    if domain == "cloudops":
        from usami_cloudops.models import Operation
        from usami_cloudops.signatures import facts
        result = facts(event.before, actor, Operation.model_validate(raw))
        result["policy_version"] = event.before.version
        return result, "policy_relative_features"
    import importlib
    module = importlib.import_module("usami_" + domain + ".models")
    rules = importlib.import_module("usami_" + domain + ".rules")
    before, op = module.World.model_validate(event.before), module.Operation.model_validate(raw)
    result = {"role": rules.role(before, actor, op.scope_id), "policy_version": before.version}
    if domain == "fulfillment":
        warehouse = before.warehouses.get(op.scope_id)
        order = before.orders.get(op.resource_id)
        lot = before.lots.get(op.params.get("lot_id", op.resource_id))
        reservation = before.reservations.get(op.resource_id)
        if reservation and order is None:
            order = before.orders.get(reservation.order_id)
        if reservation and lot is None:
            lot = before.lots.get(reservation.lot_id)
        if warehouse:
            result["warehouse"] = {"receiving": warehouse.receiving_enabled,
                                   "volume_vs_capacity": _cmp(rules.physical_volume(before, warehouse.id), warehouse.capacity_volume)}
        if order:
            result["order"] = {"status": order.status, "actor_is_buyer": order.customer_id == actor,
                               "scope_matches": order.warehouse_id == op.scope_id,
                               "paid_vs_price": _cmp(rules.paid(before, order.id), rules.price(order))}
            if "amount_cents" in op.params and op.name == "refund_order":
                result["refund_vs_eligible"] = _cmp(op.params["amount_cents"], rules.refund_limit(before, order))
            if op.name == "capture_payment":
                prior = next((payment for payment in before.payments.values() if payment.order_id == order.id and payment.key == op.params["key"]), None)
                result["payment_request"] = {"amount_vs_price": _cmp(op.params["amount_cents"], rules.price(order)),
                                             "token": op.params["token"], "key_repeated": prior is not None,
                                             "prior_amount_vs_request": _cmp(prior.amount_cents, op.params["amount_cents"]) if prior else None,
                                             "prior_token_matches": prior.token == op.params["token"] if prior else None,
                                             "prior_outcome": prior.outcome if prior else None}
        if lot:
            result["lot"] = {"quality": lot.quality, "scope_matches": lot.warehouse_id == op.scope_id,
                             "requested_vs_free": _cmp(op.params.get("quantity", 0), lot.on_hand - lot.reserved)}
        if reservation:
            result["reservation"] = {"status": reservation.status, "scope_matches": reservation.warehouse_id == op.scope_id}
        # These narrow paths have defined relevant dependency features. Other
        # operations retain their exact prestate until a causal normalizer exists.
        known = {"confirm_order", "reserve_inventory", "pick_reservation", "pack_reservation", "refund_order", "capture_payment"}
    else:
        reservation = before.reservations.get(op.resource_id)
        room = before.rooms.get(op.params.get("room_id", op.resource_id))
        if reservation:
            result["reservation"] = {"status": reservation.status, "scope_matches": reservation.property_id == op.scope_id,
                                     "actor_is_guest": before.guests[reservation.guest_id].user_id == actor,
                                     "paid_vs_deposit": _cmp(rules.net_paid(before, reservation.id), reservation.deposit_cents),
                                     "paid_vs_total": _cmp(rules.net_paid(before, reservation.id), reservation.total_cents),
                                     "clock_vs_expiry": _cmp(before.clock, reservation.hold_expires_at)}
            result["interval_capacity"] = [_cmp(rules.occupied(before, reservation.room_type_id, day, reservation.id),
                                                rules.calendar_capacity(before, reservation.room_type_id, day))
                                           for day in rules.days(reservation.arrival, reservation.departure)]
            if op.name == "refund_reservation":
                result["refund_vs_eligible"] = _cmp(op.params["amount_cents"], rules.refund_limit(before, reservation))
        if room:
            result["room"] = {"housekeeping": room.housekeeping, "maintenance": room.maintenance,
                              "occupied": room.current_stay_id is not None, "scope_matches": room.property_id == op.scope_id}
        known = {"confirm_reservation", "assign_room", "check_in", "check_out"}
    if op.name not in known:
        result["exact_prestate_hash"] = before.state_hash
        return result, "pending_causal_normalization"
    return result, "policy_relative_features"


def failure_details(domain, trace, track="discovery"):
    execution = execution_of(domain, trace, track)
    events = {getattr(event, "event_id", None) or getattr(event, "id"): event for event in execution.world_trace.events}
    previous = []
    details = []
    for row in operation_rows(domain, trace, track):
        event = events[row["event_id"]]
        if row["classification"] == "successful_business_violation":
            facts, scope = normalized_facts(domain, event)
            if previous:
                # An observed earlier write is not proof that it was necessary
                # for this failure. Preserve exact state for such paths until
                # a domain-specific counterfactual causal normalizer exists.
                facts["exact_prestate_hash"] = row["before_hash"]
                scope = "pending_causal_normalization"
            details.append(dict(row=row, operation=event.payload["operation"], relevant_prestate=facts,
                                normalization_scope=scope,
                                causal_prerequisites=list(previous),
                                permission_scope={"authorized": row["authorized"], "role": facts.get("role", facts.get("actor_role", facts.get("actor_membership")))},
                                expected={"allowed": row["reference_allowed"], "error_code": row["reference_error_code"],
                                          "transition": "reference_transition" if row["reference_allowed"] else "preserve_prestate"},
                                actual={"success": row["success"], "state_changed": row["before_hash"] != row["after_hash"]}))
        if row["success"] and row["before_hash"] != row["after_hash"]:
            previous.append({"operation": row["operation"], "classification": row["classification"],
                             "causal_status": "observed_prefix_not_counterfactually_verified"})
    return details
