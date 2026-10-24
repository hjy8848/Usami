"""Public-tool-only deterministic integration fixture. No Reference/goal access."""
import json


def step(view, state):
    phase = state.get("phase", "orders")
    merchant = view["available_merchant_scope_ids"][0]
    tools = [row for row in view["conversation"] if row["role"] == "tool"]
    result = json.loads(tools[-1]["content"]) if tools else None
    if result is not None and not result["success"]:
        raise ValueError("native public operation rejected: " + str(result["error_code"]))
    data = result["data"] if result else None

    def operation(name, resource, params, next_phase):
        state["phase"] = next_phase
        return {"kind": "ACTION", "state": state, "action": {"kind": "operation", "operation": {
            "name": name, "scope_id": merchant, "resource_id": resource, "params": params}}}

    if phase == "orders":
        return operation("list_customer_orders", merchant, {}, "order_details")
    if phase == "order_details":
        state["orders"] = [row["id"] for row in data["orders"]]
        state["lines"] = []
        state["order_cursor"] = 0
        return operation("get_order_details", state["orders"][0], {}, "collect_lines")
    if phase == "collect_lines":
        state["lines"].extend(data["lines"])
        state["order_cursor"] += 1
        if state["order_cursor"] < len(state["orders"]):
            return operation("get_order_details", state["orders"][state["order_cursor"]], {}, "collect_lines")
        state["sku_cursor"], state["skus"] = 0, []
        return operation("get_sku_details", state["lines"][0]["sku_id"], {}, "collect_skus")
    if phase == "collect_skus":
        state["skus"].append(data["sku"])
        state["sku_cursor"] += 1
        if state["sku_cursor"] < len(state["lines"]):
            return operation("get_sku_details", state["lines"][state["sku_cursor"]]["sku_id"], {}, "collect_skus")
        requests = view["customer_request"].casefold().split(".")
        state["jobs"] = []
        for line, sku in zip(state["lines"], state["skus"]):
            clauses = [part for part in requests if sku["product_family"].casefold() in part]
            if clauses:
                clause = clauses[0]
                issue = "missing_parts" if "missing parts" in clause else "wrong_item" if "wrong item" in clause else "damaged"
                state["jobs"].append({"line": line["id"], "sku": sku["id"], "issue": issue,
                                      "remedy": "refund" if "refund" in clause else "reship"})
        state["job_cursor"] = 0
        phase = "open"
    if phase == "open":
        job = state["jobs"][state["job_cursor"]]
        return operation("open_remedy_case", job["line"], {"quantity": 1, "issue": job["issue"]}, "case_status")
    if phase == "case_status":
        state["case"] = data["case_id"]
        return operation("get_case_status", state["case"], {}, "verify")
    if phase == "verify":
        job = state["jobs"][state["job_cursor"]]
        evidence = next(row for row in data["evidence"] if row["issue"] == job["issue"])
        return operation("verify_submitted_evidence", state["case"], {"evidence_id": evidence["evidence_id"]}, "prepare")
    if phase == "prepare":
        job = state["jobs"][state["job_cursor"]]
        if job["remedy"] != "refund":
            return operation("get_inventory", job["sku"], {}, "warehouse")
        return operation("prepare_remedy_quote", state["case"], {"remedy": "refund", "target_sku_id": None,
                         "warehouse_id": None, "pickup_slot": None}, "present")
    if phase == "warehouse":
        state["warehouse"] = next(row["warehouse_id"] for row in data["inventory"] if row["available"] > 0)
        job = state["jobs"][state["job_cursor"]]
        return operation("estimate_delivery", job["sku"], {"warehouse_id": state["warehouse"], "quantity": 1}, "shipment_quote")
    if phase == "shipment_quote":
        job = state["jobs"][state["job_cursor"]]
        return operation("prepare_remedy_quote", state["case"], {"remedy": "reship", "target_sku_id": job["sku"],
                         "warehouse_id": state["warehouse"], "pickup_slot": None}, "present")
    if phase == "present":
        state["quote"], state["phase"] = data["quote"]["id"], "commit"
        return {"kind": "ACTION", "state": state, "action": {"kind": "reply", "message": "Please confirm this exact quote.",
                "present_quote_id": state["quote"], "present_for": "commit_accepted_quote"}}
    if phase == "commit":
        return operation("commit_accepted_quote", state["quote"], {}, "next_job")
    if phase == "next_job":
        state["job_cursor"] += 1
        if state["job_cursor"] < len(state["jobs"]):
            job = state["jobs"][state["job_cursor"]]
            return operation("open_remedy_case", job["line"], {"quantity": 1, "issue": job["issue"]}, "case_status")
        return {"kind": "ACTION", "state": state, "action": {"kind": "reply", "message": "All requested remedies are completed."}}
    raise ValueError("unregistered fixture phase: " + phase)
