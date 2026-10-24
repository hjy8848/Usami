"""Generic v0.2 Designer seed. It proposes evidence-driven changes, never rules."""


def next_step(research_view, state):
    observations = research_view["observations"]
    target = research_view["target"]
    mode = research_view["mode"]

    if mode == "IMPROVE_SERVICE":
        phase = state.get("phase", "challenge_model")
        if phase == "challenge_model":
            attempt = state.get("attempt", 0)
            if attempt >= 3:
                return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
            request = {"instruction": "Inspect the public research context and propose one frozen-world Service challenge. "
                       "Do not assert its answer, change a rule, or invent a task fact. The fixed Host will certify it.",
                       "research_view": research_view}
            schema = {"type": "object", "properties": {"proposal": {"type": "object"}},
                      "required": ["proposal"], "additionalProperties": False}
            return {"action": "MODEL", "state": {"phase": "challenge_submit", "attempt": attempt + 1},
                    "request": request, "response_schema": schema}
        if phase == "challenge_submit":
            proposal = observations[-1]["output"]["proposal"]
            return {"action": "PROPOSE_CHALLENGE", "state": {"phase": "challenge_result",
                    "attempt": state["attempt"]}, "proposal": proposal}
        if phase == "challenge_result":
            last = observations[-1]
            if last["status"] != "CERTIFIED":
                attempt = state["attempt"]
                if attempt >= 3:
                    return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
                return {"action": "MODEL", "state": {"phase": "challenge_submit",
                        "attempt": attempt + 1},
                        "request": {"instruction": "Revise the challenge using the Host rejection. "
                                    "Only use public facts and currently certifiable task types.",
                                    "rejection": last, "research_view": research_view},
                        "response_schema": {"type": "object", "properties": {
                            "proposal": {"type": "object"}}, "required": ["proposal"],
                            "additionalProperties": False}}
            return {"action": "RUN_BASELINE", "state": {"phase": "patch_model",
                    "task_ref": last["task_ref"]}, "task_ref": last["task_ref"]}
        if phase == "patch_model":
            request = {"instruction": "Use the certified task's parent Service execution evidence to propose a complete "
                       "(P,K) improvement. P must implement the two-argument step(view,state) contract. "
                       "K must be a JSON object with reusable experience. Do not change business rules or fixed model B.",
                       "parent_service": target, "challenge_ref": state["task_ref"],
                       "baseline_evidence": observations[-1], "research_view": research_view}
            schema = {"type": "object", "properties": {
                "policy_source": {"type": "string"}, "experience": {"type": "object"}},
                "required": ["policy_source", "experience"], "additionalProperties": False}
            return {"action": "MODEL", "state": {"phase": "patch_stage", "task_ref": state["task_ref"],
                    "stage_attempts": 0}, "request": request, "response_schema": schema}
        if phase == "patch_stage":
            previous = observations[-1]
            if previous.get("kind") == "STAGE" and previous["status"] == "VALID":
                return {"action": "PROBE", "state": {"phase": "patch_submit",
                        "candidate_ref": previous["candidate_ref"]},
                        "candidate_ref": previous["candidate_ref"], "probe_ref": state["task_ref"]}
            attempts = state["stage_attempts"]
            if previous.get("kind") == "STAGE" and previous["status"] == "INVALID":
                attempts += 1
                if attempts >= 2:
                    return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
                return {"action": "MODEL", "state": {**state, "stage_attempts": attempts},
                        "request": {"instruction": "Repair the rejected Service bundle using the exact Host error. "
                                    "Return a complete P source and JSON-object K.",
                                    "rejection": previous, "parent_service": target,
                                    "baseline_evidence": observations},
                        "response_schema": {"type": "object", "properties": {
                            "policy_source": {"type": "string"}, "experience": {"type": "object"}},
                            "required": ["policy_source", "experience"], "additionalProperties": False}}
            suggestion = previous["output"]
            return {"action": "STAGE", "state": {**state, "stage_attempts": attempts},
                    "kind": "SERVICE_BUNDLE", "policy_source": suggestion["policy_source"],
                    "experience": suggestion["experience"], "parent_ref": target["ref"]}
        if phase == "patch_submit":
            return {"action": "SUBMIT", "state": {},
                    "candidate_ref": observations[-1]["candidate_ref"]}

    if mode == "EVALUATE_ADAPT":
        phase = state.get("phase", "model")
        if phase == "model":
            schema = {"type": "object", "properties": {
                "policy_source": {"type": "string"}, "experience": {"type": "object"}},
                "required": ["policy_source", "experience"], "additionalProperties": False}
            return {"action": "MODEL", "state": {"phase": "stage"},
                    "request": {"instruction": "Adapt the complete Service copy (P,K) only for this registered package. "
                                "Keep fixed model B and all business rules unchanged. Do not self-edit M.",
                                "target_service": target, "allowed_support": research_view},
                    "response_schema": schema}
        if phase == "stage":
            previous = observations[-1]
            if previous.get("kind") == "STAGE" and previous["status"] == "INVALID":
                return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
            suggestion = previous["output"]
            return {"action": "STAGE", "state": {"phase": "probe", "candidate_ref": "",
                    "refs": [target["ref"]], "cursor": 0, "scores": {}},
                    "kind": "SERVICE_BUNDLE", "policy_source": suggestion["policy_source"],
                    "experience": suggestion["experience"], "parent_ref": target["ref"]}
        if phase == "probe":
            if observations[-1].get("kind") == "STAGE":
                if observations[-1]["status"] != "VALID":
                    return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
                state["candidate_ref"] = observations[-1]["candidate_ref"]
                state["refs"].append(state["candidate_ref"])
            elif observations[-1].get("kind") == "PROBE":
                previous = observations[-1]
                state["scores"].setdefault(previous["candidate_ref"], []).append(
                    previous["result"]["score"])
                state["cursor"] += 1
            probes = research_view["capabilities"]["probe_refs"]
            total = len(state["refs"]) * len(probes)
            if state["cursor"] < total:
                index = state["cursor"]
                return {"action": "PROBE", "state": state,
                        "candidate_ref": state["refs"][index // len(probes)],
                        "probe_ref": probes[index % len(probes)]}
            baseline = sum(state["scores"].get(target["ref"], []))
            proposed = sum(state["scores"].get(state["candidate_ref"], []))
            winner = state["candidate_ref"] if proposed > baseline else target["ref"]
            return {"action": "SUBMIT", "state": {}, "candidate_ref": winner}

    if mode in {"SELF_EDIT", "ADAPT_TASK"}:
        phase = state.get("phase", "generate")
        if phase == "generate":
            source_key = "sources"
            schema = {"type": "object", "properties": {
                source_key: {"type": "array", "maxItems": 2, "items": {"type": "string"}}},
                "required": [source_key], "additionalProperties": False}
            return {"action": "MODEL", "state": {"phase": "stage", "index": 0, "refs": []},
                    "request": {"instruction": "Propose up to two executable candidates of the target's role. "
                                "Keep the Host, model, permissions and evaluation protocol fixed.",
                                "target": target, "research_view": research_view},
                    "response_schema": schema}
        if phase == "stage":
            if "sources" not in state:
                state["sources"] = observations[-1]["output"]["sources"]
            elif observations[-1].get("kind") == "STAGE" and observations[-1]["status"] == "VALID":
                state["refs"].append(observations[-1]["candidate_ref"])
            if state["index"] < len(state["sources"]):
                source = state["sources"][state["index"]]
                state["index"] += 1
                return {"action": "STAGE", "state": state, "kind": target["kind"],
                        "source": source, "parent_ref": target["ref"]}
            state = {"phase": "probe", "refs": [target["ref"]] + state["refs"],
                     "cursor": 0, "scores": {}}
        if phase == "probe" or state["phase"] == "probe":
            if observations and observations[-1].get("kind") == "PROBE":
                previous = observations[-1]
                state["scores"].setdefault(previous["candidate_ref"], []).append(
                    previous["result"]["score"])
            probes = research_view["capabilities"]["probe_refs"]
            total = len(state["refs"]) * len(probes)
            if state["cursor"] < total:
                index = state["cursor"]
                state["cursor"] += 1
                return {"action": "PROBE", "state": state,
                        "candidate_ref": state["refs"][index // len(probes)],
                        "probe_ref": probes[index % len(probes)]}
            best = target["ref"]
            best_score = sum(state["scores"].get(best, [0])) / max(1, len(probes))
            for ref in state["refs"][1:]:
                value = sum(state["scores"].get(ref, [0])) / max(1, len(probes))
                if value > best_score:
                    best, best_score = ref, value
            return {"action": "SUBMIT", "state": state, "candidate_ref": best}

    return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
