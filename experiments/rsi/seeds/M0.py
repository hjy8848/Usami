"""Generic seed researcher; deliberately no business fixes or disagreement rule."""


def next_step(research_view, state):
    observations = research_view["observations"]
    target = research_view["target"]
    phase = state.get("phase", "generate")
    if phase == "generate":
        return {"action": "MODEL", "state": {"phase": "stage", "index": 0, "refs": []},
                "request": {"instruction": "Propose at most two complete executable Python candidate sources. "
                            "Use the target's two-argument entrypoint and the supplied capabilities. "
                            "Do not change the Host, model, permissions, or evaluation protocol. "
                            "Return an object containing sources, a list of source strings.",
                            "target": target, "evidence": research_view,
                            "decision_contract": {
                                "MODEL": ["request", "response_schema"],
                                "STAGE": ["kind", "source", "parent_ref"],
                                "PROBE": ["candidate_ref", "probe_ref"],
                                "SUBMIT": ["candidate_ref"],
                                "all_actions_require": ["action", "state"]}},
                "response_schema": {"type": "object", "properties": {
                    "sources": {"type": "array", "maxItems": 2, "items": {"type": "string"}}},
                    "required": ["sources"], "additionalProperties": False}}
    if phase == "stage":
        if "sources" not in state:
            state["sources"] = observations[-1]["output"]["sources"]
        elif observations[-1]["kind"] == "STAGE" and observations[-1]["status"] == "VALID":
            state["refs"].append(observations[-1]["candidate_ref"])
        if state["index"] < len(state["sources"]):
            source = state["sources"][state["index"]]
            state["index"] += 1
            return {"action": "STAGE", "state": state, "kind": target["kind"],
                    "source": source, "parent_ref": target["ref"]}
        state = {"phase": "probe", "refs": [target["ref"]] + state["refs"],
                 "cursor": 0, "scores": {}}
    if phase == "probe" or state["phase"] == "probe":
        if observations and observations[-1]["kind"] == "PROBE":
            previous = observations[-1]
            ref = previous["candidate_ref"]
            state["scores"].setdefault(ref, []).append(previous["result"]["score"])
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
