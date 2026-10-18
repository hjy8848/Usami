#!/usr/bin/env python3
"""Independently rebuild and verify a saved offline Designer-subagent run.

This utility never calls a model. It reconstructs the registered frozen world,
recompiles the subagent's successful proposal with the native compiler, and
replays the certified task record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

from usami_benchmark.contracts import WorldSpec
from usami_benchmark.designer_exploration import compile_proposal
from usami_benchmark.tasks import ConstructionBudget, verify_task
from usami_benchmark.worlds import freeze
from usami_harness.models import digest


def main(directory: str) -> None:
    root = Path(directory)
    context = json.loads((root / "request-context.json").read_text())
    run = json.loads((root / "offline-run.json").read_text())
    frozen = freeze(WorldSpec.model_validate(context["world_spec"]))

    if run.get("external_api_calls") != 0 or any(
        run.get(key) != 0 for key in ("customer_executions", "service_executions", "reflection_calls")
    ):
        raise ValueError("offline diagnostic unexpectedly records an API, Customer, Service, or Reflection call")
    if len(run.get("queries", [])) > context["designer_budget"]["max_queries"]:
        raise ValueError("saved run exceeds its read-only query budget")
    if len(run.get("proposals", [])) > context["designer_budget"]["max_revisions"] + 1:
        raise ValueError("saved run exceeds its proposal correction budget")

    expected_hashes = {
        "world_hash": frozen.world_hash,
        "registration_hash": frozen.registration_hash,
        "exploration_request_hash": digest(context["exploration_request"]),
        "submission_request_hash": digest(context["submission_request_template"]),
    }
    for name, value in expected_hashes.items():
        if context[name] != value or run["hash_verification"][name] != value:
            raise ValueError(f"saved context hash mismatch: {name}")

    successful = [row for row in run["proposals"] if row["compiler_feedback"].get("success")]
    if len(successful) != 1:
        raise ValueError("offline run must contain exactly one successful proposal")
    proposal_row = successful[0]
    selection, task = compile_proposal(
        frozen,
        proposal_row["proposal"],
        ConstructionBudget.model_validate(context["construction_budget"]),
        protocol=context["designer_protocol"],
    )
    if not verify_task(task):
        raise ValueError("native task verification returned false")

    witness = task.dialogue_witnesses[0]
    certificate = witness.certificate.model_dump(mode="json")
    evaluation = certificate["evaluation"]
    profile_ids = selection.composition.profile_ids
    identities = {profile_id: frozen.world["profiles"][profile_id]["identity"] for profile_id in profile_ids}
    verification = {
        "protocol": "designer-subagent-independent-native-verification-v1",
        "verified": True,
        "provenance": "Root process rebuilt the frozen world and independently recompiled the saved offline proposal; this command makes no external model/API calls.",
        **expected_hashes,
        "proposal_attempt": proposal_row["attempt"],
        "proposal_profile_ids": profile_ids,
        "profile_identities": identities,
        "same_customer_identity": len(set(identities.values())) == 1,
        "created_completion_subgoals": evaluation.get("created_completion_subgoals", []),
        "completion_subgoals": evaluation["completion_subgoals"],
        "refusal_subgoals": evaluation["refusal_subgoals"],
        "oracle_status": evaluation["oracle_status"],
        "task_success": evaluation["success"],
        "replay_verified": evaluation["replay_verified"],
        "actual_business_operations_in_witness": evaluation["actual_business_operations"],
        "actual_customer_turns": evaluation["actual_customer_turns"],
        "record_hash": task.record_hash,
        "certificate_hash": certificate["certificate_hash"],
        "search_summary": task.search_summary,
        "note": "This certifies task reachability and objective scoring under the native evaluator; it does not execute Service or establish Service correctness.",
    }
    if not verification["same_customer_identity"]:
        raise ValueError("composed profiles do not share one authenticated identity")
    if evaluation["oracle_status"] != "pass" or not evaluation["replay_verified"]:
        raise ValueError("native Oracle or Replay verification failed")

    (root / "native-certified-task.json").write_text(task.model_dump_json(indent=2) + "\n")
    (root / "independent-verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(verification, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python verify_designer_subagent_run.py RUN_DIRECTORY")
    main(sys.argv[1])
