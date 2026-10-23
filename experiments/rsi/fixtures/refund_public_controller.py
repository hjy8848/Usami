"""Deterministic contract fixture, not a learned policy or an effect result.

Every entity ID is discovered through the public tools. This source is never P0.
"""
import json


def step(view, state):
    n = state.get("n", 0)
    merchant = view["available_merchant_scope_ids"][0]
    tools = [row for row in view["conversation"] if row["role"] == "tool"]
    data = json.loads(tools[-1]["content"])["data"] if tools else None
    if n == 0:
        name, resource, params = "list_customer_orders", merchant, {}
    elif n == 1:
        name, resource, params = "get_order_details", data["orders"][0]["id"], {}
    elif n == 2:
        state["lines"] = data["lines"]
        name, resource, params = "get_sku_details", state["lines"][0]["sku_id"], {}
    elif n == 3:
        state["skus"] = [data["sku"]]
        name, resource, params = "get_sku_details", state["lines"][1]["sku_id"], {}
    elif n == 4:
        state["skus"].append(data["sku"])
        state["line"] = next(line["id"] for line, sku in zip(state["lines"], state["skus"])
                             if sku["product_family"] == "device")
        name, resource, params = "open_remedy_case", state["line"], {"quantity": 1, "issue": "damaged"}
    elif n == 5:
        state["case"] = data["case_id"]
        name, resource, params = "get_case_status", state["case"], {}
    elif n == 6:
        evidence = next(row for row in data["evidence"] if row["issue"] == "damaged")
        name, resource, params = "verify_submitted_evidence", state["case"], {"evidence_id": evidence["evidence_id"]}
    elif n == 7:
        name, resource, params = "prepare_remedy_quote", state["case"], {
            "remedy": "refund", "target_sku_id": None, "warehouse_id": None, "pickup_slot": None}
    elif n == 8:
        state["quote"] = data["quote"]["id"]
        state["n"] = n + 1
        return {"kind": "ACTION", "state": state, "action": {
            "kind": "reply", "message": "Please confirm this exact refund quote.",
            "present_quote_id": state["quote"], "present_for": "commit_accepted_quote"}}
    elif n == 9:
        name, resource, params = "commit_accepted_quote", state["quote"], {}
    else:
        return {"kind": "ACTION", "state": state, "action": {
            "kind": "reply", "message": state["line"] + ": refund status is released.",
            "subject_ids": [state["line"]]}}
    state["n"] = n + 1
    return {"kind": "ACTION", "state": state, "action": {"kind": "operation", "operation": {
        "name": name, "scope_id": merchant, "resource_id": resource, "params": params}}}
