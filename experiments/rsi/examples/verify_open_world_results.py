"""Offline native verification of the recorded open-World integration evidence.

The Customer binding is an explicitly supplied trusted factory. Artifacts never
select executable code. Model responses are replayed as records, not new calls.
"""
import argparse
import importlib
import json
from pathlib import Path

from pydantic import ValidationError

from rsi_core.archive import Archive
from integrations.rsi_usami.adapter import UsamiAdapter
from integrations.rsi_usami.open_world import WorldPopulation, OpenChallengeBridge
from integrations.rsi_usami.packages import NativePackageVerifier
from usami_v2.runtime.agents import AgentCall, _one_tool_call, _json_arguments
from usami_v2.scenarios.distribution import DistributionSpec
from usami_v2.scenarios.schema import BuildBudget
from usami_v2.scenarios.grounding import AbstractChallenge


def verify(root, customer_binding):
    root = Path(root)
    summary = json.loads((root / "summary.json").read_text())
    world_count, response_count, grounding_count = 0, 0, 0
    for label in ("existing-worlds", "generated-worlds"):
        evidence = root / "evidence" / label
        records = Archive(evidence / "worlds/records")
        state = json.loads((evidence / "worlds/state.json").read_text())
        identity = records.load(state["state_ref"])["identity"]
        budget = BuildBudget.model_validate(identity["build_budget"]) if identity["build_budget"] else None
        pool = WorldPopulation(evidence / "worlds", DistributionSpec.model_validate(identity["distribution"]),
            None, seed=identity["seed"], build_budget=budget, max_attempts=identity["max_attempts"])
        for ref in pool.period_refs:
            world_count += len(pool.worlds(ref))
        archive = Archive(evidence / "archive")
        for row in summary["live_designer"]:
            if row["population"] != label:
                continue
            record = archive.load(row["archive_ref"])
            call = AgentCall.model_validate(record["call"]).checked()
            message = _one_tool_call(call.response)
            raw = _json_arguments(message["tool_calls"][0]["function"]["arguments"])
            if record["status"] == "FAILED":
                if record["error_code"] != "DESIGNER_SCHEMA_INVALID":
                    raise ValueError("this evidence verifier expects an actual structured response")
                try:
                    AbstractChallenge.model_validate(raw)
                except ValidationError:
                    pass
                else:
                    raise ValueError("recorded schema rejection now passes")
            else:
                parsed = AbstractChallenge.model_validate(raw)
                if parsed.model_dump(mode="json") != record["proposal"]:
                    raise ValueError("recorded Designer proposal differs from original tool arguments")
                bridge = OpenChallengeBridge(pool, record["period_ref"], UsamiAdapter({}, evidence / "replay-native"),
                    NativePackageVerifier({}, archive), customer_binding)
                bridge.verify_attempt(record["attempt_ref"])
                grounding_count += 1
            response_count += 1
    return {"verified": True, "worlds": world_count, "model_responses": response_count,
            "grounding_records": grounding_count, "new_model_calls": 0,
            "scope": "native World construction, recorded model schemas, Grounder and Reference certificates"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--binding", required=True, help="trusted module:function Customer binding used in this run")
    args = parser.parse_args()
    module, name = args.binding.split(":", 1)
    print(json.dumps(verify(args.root, getattr(importlib.import_module(module), name)), ensure_ascii=False))


if __name__ == "__main__":
    main()
