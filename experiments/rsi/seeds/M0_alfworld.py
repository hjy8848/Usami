"""M0 for ALFWorld: select and ground task types, then adapt P/K and itself."""
import json


def _model(instruction, payload, schema, state):
    return {"action": "MODEL", "state": state,
            "request": {"instruction": instruction, "context": payload},
            "response_schema": schema}


def _p_schema():
    return {"type": "object", "required": ["policy_source", "experience"],
            "properties": {"policy_source": {"type": "string"},
                           "experience": {"type": "object"}},
            "additionalProperties": False}


def next_step(view, state):
    mode = view["mode"]
    phase = state.get("phase", 0)
    observations = view["observations"]
    target = view["target"]["ref"]

    if mode == "IMPROVE_SERVICE":
        if phase == 0:
            catalogue = view.get("challenge_catalogue", {}).get("task_types", [])
            types = [row["task_type"] for row in catalogue]
            schema = {"type": "object", "required": ["task_type", "hypothesis"],
                      "properties": {"task_type": {"type": "string", "enum": types},
                                     "hypothesis": {"type": "string"}},
                      "additionalProperties": False}
            return _model(
                "Choose one ALFWorld task type that will provide useful evidence for improving the "
                "current Service policy. The Host will bind your abstract task type to a registered "
                "training task. Do not invent task IDs or claim an answer.",
                {"task_catalogue": catalogue,
                 "service_experience": view["target"].get("experience", {})},
                schema, {"phase": 1})
        if phase == 1:
            proposal = observations[-1]["output"]
            return {"action": "PROPOSE_CHALLENGE", "state": {"phase": 2},
                    "proposal": proposal}
        if phase == 2:
            certified = observations[-1]
            if certified.get("kind") != "PROPOSE_CHALLENGE" or certified.get("status") != "CERTIFIED":
                return {"action": "SUBMIT", "state": {}, "candidate_ref": target}
            return {"action": "RUN_BASELINE", "state": {"phase": 3,
                    "challenge_ref": certified["task_ref"]},
                    "task_ref": certified["task_ref"]}
        if phase == 3:
            baseline = observations[-1].get("result", {})
            request = {"baseline": baseline,
                       "service_experience": view["target"].get("experience", {}),
                       "task_interface": view.get("environment_capabilities", {})}
            return _model(
                "Propose one executable ALFWorld Service improvement. Modify the full P policy and/or "
                "experience K using the public baseline trajectory. Keep the policy interface "
                "step(view, state); the Host will execute and compare it.",
                request, _p_schema(), {"phase": 4,
                                       "challenge_ref": state["challenge_ref"],
                                       "baseline_score": baseline.get("score", 0.0)})
        if phase == 4:
            candidate = observations[-1]["output"]
            return {"action": "STAGE", "state": {"phase": 5,
                    "candidate": target}, "kind": "SERVICE_BUNDLE",
                    "policy_source": candidate["policy_source"],
                    "experience": candidate["experience"],
                    "parent_ref": target}
        if phase == 5:
            staged = observations[-1]
            if staged.get("kind") != "STAGE" or staged.get("status") != "VALID":
                return {"action": "SUBMIT", "state": {}, "candidate_ref": target}
            return {"action": "PROBE", "state": {"phase": 6,
                    "candidate": staged["candidate_ref"], "parent_probe": None},
                    "candidate_ref": target,
                    "probe_ref": view["capabilities"]["probe_refs"][0]}
        if phase == 6:
            parent_result = observations[-1].get("result", {})
            return {"action": "PROBE", "state": {"phase": 7,
                    "candidate": state["candidate"],
                    "parent_score": parent_result.get("score", 0.0)},
                    "candidate_ref": state["candidate"],
                    "probe_ref": view["capabilities"]["probe_refs"][0]}
        candidate_result = observations[-1].get("result", {})
        chosen = state["candidate"] if candidate_result.get("score", 0.0) > state["parent_score"] else target
        return {"action": "SUBMIT", "state": {}, "candidate_ref": chosen}

    if mode == "EVALUATE_ADAPT":
        target_view = view["target"]
        parent_ref = target_view["ref"]
        if phase == 0:
            request = {
                "instruction": "Propose one complete ALFWorld Service update for this registered adaptation package. "
                              "The Service policy must implement step(view, state) and choose actions through "
                              "choose_alfworld_action. Use the parent policy, K and public task feedback below. "
                              "Return executable P source and a JSON-object K. Do not modify the Host or scoring.",
                "parent_policy": target_view["policy"]["source"],
                "parent_experience": target_view.get("experience", {}),
                "prior_service_research": view.get("prior_service_research", []),
                "environment_capabilities": view.get("environment_capabilities", {}),
            }
            return _model("Adapt the Service candidate for independent package probes.", request,
                          _p_schema(), {"phase": 1, "cursor": 0, "refs": [parent_ref],
                                        "scores": {}})
        if phase == 1:
            candidate = observations[-1]["output"]
            return {"action": "STAGE", "state": {**state, "phase": 2},
                    "kind": "SERVICE_BUNDLE", "policy_source": candidate["policy_source"],
                    "experience": candidate["experience"], "parent_ref": parent_ref}
        if phase == 2:
            previous = observations[-1]
            if previous.get("kind") == "STAGE":
                if previous.get("status") != "VALID":
                    return {"action": "SUBMIT", "state": {}, "candidate_ref": parent_ref}
                state["refs"].append(previous["candidate_ref"])
            elif previous.get("kind") == "PROBE":
                state["scores"].setdefault(previous["candidate_ref"], []).append(
                    previous["result"]["score"])
                state["cursor"] += 1
            probes = view["capabilities"]["probe_refs"]
            total = len(state["refs"]) * len(probes)
            if state["cursor"] < total:
                index = state["cursor"]
                return {"action": "PROBE", "state": state,
                        "candidate_ref": state["refs"][index // len(probes)],
                        "probe_ref": probes[index % len(probes)]}
            baseline = state["scores"].get(parent_ref, [])
            candidate_ref = state["refs"][-1]
            candidate_scores = state["scores"].get(candidate_ref, [])
            parent_score = sum(baseline) / max(1, len(baseline))
            candidate_score = sum(candidate_scores) / max(1, len(candidate_scores))
            winner = candidate_ref if candidate_score > parent_score else parent_ref
            return {"action": "SUBMIT", "state": {}, "candidate_ref": winner}

    if mode == "SELF_EDIT":
        if phase == 0:
            return _model(
                "Revise this ALFWorld research program only if the observed public evidence suggests a "
                "concrete improvement. Preserve the RSI Host protocol and ALFWorld challenge contract. "
                "Return one complete Python program with next_step(view, state).",
                {"current_program": view["target"].get("source", ""),
                 "prior_service_research": view.get("prior_service_research", [])},
                {"type": "object", "required": ["source"],
                 "properties": {"source": {"type": "string"}},
                 "additionalProperties": False}, {"phase": 1})
        if phase == 1:
            source = observations[-1]["output"]["source"]
            return {"action": "STAGE", "state": {"phase": 2}, "kind": "M",
                    "source": source, "parent_ref": target}
        if phase == 2:
            staged = observations[-1]
            if staged.get("kind") != "STAGE" or staged.get("status") != "VALID":
                return {"action": "SUBMIT", "state": {}, "candidate_ref": target}
            return {"action": "PROBE", "state": {"phase": 3,
                    "candidate": staged["candidate_ref"]},
                    "candidate_ref": staged["candidate_ref"],
                    "probe_ref": view["capabilities"]["probe_refs"][0]}
        return {"action": "SUBMIT", "state": {},
                "candidate_ref": state["candidate"]}

    return {"action": "SUBMIT", "state": {}, "candidate_ref": target}
