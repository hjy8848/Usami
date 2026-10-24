"""Generic v0.2 Designer seed. It proposes evidence-driven changes, never rules."""

P_INTERFACE_EXAMPLE = """def step(view, state):
    if "model_observation" not in view:
        return {"kind": "MODEL", "state": state,
                "request": view["baseline_request"]}
    return {"kind": "ACTION", "state": state,
            "action": view["model_observation"]}
"""

P_INTERFACE_CONTRACT = (
    "P is complete Python source with exactly one synchronous def step(view, state), with exactly two arguments. "
    "The view contains customer_id, customer_request, conversation, available_merchant_scope_ids, "
    "observed_subject_ids, baseline_request, service_experience and service_experience_ref. After a MODEL call, "
    "the Host adds model_observation, parsed as the native ServiceAction. The separate state argument is this "
    "task's JSON-object working memory. K is a JSON object supplied read-only as view['service_experience']; "
    "it stores reusable experience, not executable code, and is not automatically inserted into the B prompt. "
    "Use relevant K guidance when constructing the request. For a MODEL decision return exactly "
    "{kind:'MODEL', state:<JSON object>, request:<object>}; start from view['baseline_request'] and preserve its "
    "fixed business model B, native tools and parallel_tool_calls setting. Then return exactly "
    "{kind:'ACTION', state:<JSON object>, action:<native ServiceAction object>} when ready for the Host to execute "
    "one operation or reply. The action is either the Host-parsed model_observation or a valid native "
    "operation/reply. P may request another B response after inspecting model_observation; the Host returns to the "
    "native Engine only after ACTION, with at most eight P steps per Service decision. "
    "P does not call tools directly and cannot fabricate model-call evidence. "
    "The example shows only the interface, not a task-solving strategy:\n" + P_INTERFACE_EXAMPLE
)

M_ACTION_CONTRACT = (
    "M is complete Python source with exactly one synchronous def next_step(research_view, state), with exactly two "
    "arguments. research_view combines public campaign context with Host fields mode, target, capabilities and "
    "observations; state is M's JSON-object state across decisions. capabilities lists the permitted stage kind, "
    "probe references, current-root challenge references, candidate limit and whether probing has frozen staging. "
    "Each decision must be a dictionary with an object-valued state and exactly the fields required by "
    "its action. MODEL is {action:'MODEL', state, request:<object>, response_schema:<JSON Schema object>}; the "
    "Host returns {kind:'MODEL', output:<schema-valid value>} in the next observation (and marks "
    "format_corrected if it used the single schema-only correction). In IMPROVE_SERVICE only, "
    "PROPOSE_CHALLENGE is {action:'PROPOSE_CHALLENGE', state, proposal:<AbstractChallenge>}; the Host returns "
    "CERTIFIED with a task_ref or a rejection status/reason_code. RUN_BASELINE is {action:'RUN_BASELINE', state, "
    "task_ref}; it accepts only a task certified in this root and returns the parent's replay-verified execution "
    "feedback. STAGE for a P or M program is {action:'STAGE', state, kind, source, parent_ref}; STAGE for a "
    "SERVICE_BUNDLE is {action:'STAGE', state, kind, policy_source, experience, parent_ref}. The Host returns "
    "VALID with candidate_ref or INVALID with a reason. PROBE is {action:'PROBE', state, candidate_ref, probe_ref}; "
    "the reference must be in public capabilities or certified in this root, and the Host returns its registered "
    "result. SUBMIT is {action:'SUBMIT', state, candidate_ref}; it can select only the target or a candidate "
    "registered in this run. Actions are additionally limited by the Host's current mode and capabilities. A "
    "certified challenge must run on the parent before a candidate probe. In SELF_EDIT, prior_service_research "
    "contains only public challenge, baseline and candidate feedback from training roots. Use it to identify "
    "recurring failures; it contains no Reference witness or independent evaluation label. Return only registered "
    "actions. Do not "
    "change the Host, model snapshots, permissions, business rules, reward or evaluation protocol."
)


def _public_research_context(research_view):
    host_fields = {"target", "mode", "observations", "model_snapshot_refs", "open_world_catalogue",
                   "prior_service_research"}
    return {key: value for key, value in research_view.items() if key not in host_fields}


def _research_observation_summaries(observations):
    rows = []
    for observation in observations:
        row = {key: observation[key] for key in (
            "kind", "status", "reason_code", "reason", "task_ref", "candidate_ref", "probe_ref",
            "format_corrected") if key in observation}
        if observation.get("kind") == "PROBE":
            result = observation.get("result", {})
            row["result"] = {key: result[key] for key in (
                "score", "baseline_score", "status", "usable", "unknown_fraction") if key in result}
        elif observation.get("kind") == "MODEL":
            output = observation.get("output")
            row["output_shape"] = {"type": type(output).__name__,
                                   "keys": sorted(output) if isinstance(output, dict) else [],
                                   "source_count": len(output.get("sources", []))
                                   if isinstance(output, dict) and isinstance(output.get("sources"), list) else 0}
        rows.append(row)
    return rows


def _challenge_context(research_view):
    catalogue = research_view["open_world_catalogue"]
    public_catalogue = {key: value for key, value in catalogue.items() if key != "challenge_schema"}
    return {"domain": research_view["domain"], "open_world_catalogue": public_catalogue,
            "task_certification_capabilities": research_view["task_certification_capabilities"]}


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
            request = {"instruction": "Propose one abstract business challenge. Inspect world_topologies and choose "
                       "only customer/order/item relationships that are present there. Use the declared native "
                       "Challenge fields and currently supported certification capabilities. Do not invent World "
                       "facts, IDs, answers, proof witnesses or rules; the Host will ground and certify the intent.",
                       "research_context": _challenge_context(research_view)}
            schema = research_view["open_world_catalogue"]["challenge_schema"]
            return {"action": "MODEL", "state": {"phase": "challenge_submit", "attempt": attempt + 1},
                    "request": request, "response_schema": schema}
        if phase == "challenge_submit":
            proposal = observations[-1]["output"]
            return {"action": "PROPOSE_CHALLENGE", "state": {"phase": "challenge_result",
                    "attempt": state["attempt"]}, "proposal": proposal}
        if phase == "challenge_result":
            last = observations[-1]
            if last["status"] != "CERTIFIED":
                attempt = state["attempt"]
                if attempt >= 3:
                    return {"action": "SUBMIT", "state": {}, "candidate_ref": target["ref"]}
                prior = observations[-2]["output"]
                return {"action": "MODEL", "state": {"phase": "challenge_submit",
                        "attempt": attempt + 1},
                        "request": {"instruction": "Revise the prior structured challenge using the public Host "
                                    "rejection. Check world_topologies before changing customer/order relations; "
                                    "use only currently supported certification capabilities. Do not change the "
                                    "business objective unless the rejection says it cannot be certified.",
                                    "research_context": _challenge_context(research_view),
                                    "prior_proposal": prior, "rejection": last},
                        "response_schema": research_view["open_world_catalogue"]["challenge_schema"]}
            return {"action": "RUN_BASELINE", "state": {"phase": "patch_model",
                    "task_ref": last["task_ref"]}, "task_ref": last["task_ref"]}
        if phase == "patch_model":
            request = {"instruction": "Use the parent Service and this certified task's baseline evidence to propose "
                       "a complete replacement P and K. Follow the exact P interface contract and example below. "
                       "P must be full Python source; K must be a JSON object containing reusable experience. "
                       "Keep fixed model B, native tools, permissions, business rules and evaluation protocol unchanged.",
                       "P_interface_contract": P_INTERFACE_CONTRACT,
                       "parent_P_source": target["policy"]["source"],
                       "parent_K": target["experience"],
                       "parent_service_ref": target["ref"],
                       "challenge_ref": state["task_ref"],
                       "baseline_evidence": observations[-1]}
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
                prior_candidate = observations[-2]["output"]
                return {"action": "MODEL", "state": {**state, "stage_attempts": attempts},
                        "request": {"instruction": "Correct the previous P/K candidate only for the reported Host "
                                    "interface or static-validation error. Return complete P source and JSON-object K. "
                                    "Follow the exact interface contract; preserve its business intent and do not "
                                    "change fixed model B, tools, permissions or business rules.",
                                    "P_interface_contract": P_INTERFACE_CONTRACT,
                                    "parent_P_source": target["policy"]["source"],
                                    "parent_K": target["experience"],
                                    "previous_candidate": prior_candidate,
                                    "rejection": previous,
                                    "baseline_evidence": observations[-2]},
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
                    "request": {"instruction": "Adapt the complete Service copy (P,K) only for this registered "
                                "evaluation package. Follow the exact P interface contract and example. Keep fixed "
                                "model B, native tools, permissions, business rules and evaluation protocol unchanged; "
                                "do not self-edit M.",
                                "P_interface_contract": P_INTERFACE_CONTRACT,
                                "target_service": target,
                                "authorized_support": _public_research_context(research_view)},
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
            target_role = target["kind"]
            role_contract = P_INTERFACE_CONTRACT if target_role == "P" else M_ACTION_CONTRACT
            entrypoint = "step(view, state)" if target_role == "P" else "next_step(research_view, state)"
            return {"action": "MODEL", "state": {"phase": "stage", "index": 0, "refs": []},
                    "request": {"instruction": "Return up to two complete executable source strings for the "
                                "target role. Each source must define exactly one synchronous " + entrypoint +
                                " with exactly two arguments and obey the contract below. Host STAGE will validate "
                                "syntax and the fixed entrypoint; only independently probed candidates can be "
                                "selected. Preserve the Host, fixed model snapshots, permissions, business rules, "
                                "reward and evaluation protocol. Use the exact target role and preserve its purpose.",
                                "role_contract": role_contract,
                                "target_ref": target["ref"],
                                "target_role": target_role,
                                "current_program_source": target["source"],
                                "public_research_context": _public_research_context(research_view),
                                "prior_service_research": research_view["prior_service_research"],
                                "research_observations": _research_observation_summaries(observations),
                                "instruction_on_prior_research": "Use these root-visible challenge, baseline and "
                                "candidate results to identify recurring failures and revise M's research procedure. "
                                "Do not infer private Reference answers or independent evaluation labels.",
                                "instruction_on_observations": "Use only these Host-produced public observations to "
                                "identify what failed. Do not infer hidden Reference answers, held-out labels, or "
                                "unrecorded model actions."},
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
