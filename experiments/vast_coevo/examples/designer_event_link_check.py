"""Offline event-query/Reference controls; optional ONE bounded real Designer session.

No Customer, Service, Reflection or skill selection is invoked. Control answers
are never supplied to the live Designer. Existing worlds and business rules are
unchanged. Each invocation requires a new output directory.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path

from usami.service.client import OpenAICompatibleClient, key_from_env, settings_from_env
from usami.service.models import strict_json
from usami_benchmark.designer import design_and_compile, verify_designer_execution
from usami_benchmark.designer_exploration import (
    PROTOCOL, DialogueDesignerProposal, DesignerBudget, DesignerFailure,
    compile_proposal, inspect_world, verify_failed_journal,
)
from usami_benchmark.tasks import ConstructionBudget, verify_task
from vast_coevo.schema import atomic_json
from experiments.vast_coevo.examples.aftersales_coevo_live import (
    BudgetedClient, CallLedger, _initial_world, _designer_context,
)
from experiments.vast_coevo.examples.aftersales_coevo_support import initial_skill_libraries

MAX_LIVE_MODEL_CALLS = 5


def _proposal_validation(journal):
    """Classify each recorded submission without conflating schema and proof."""
    rows = []
    for row in journal.get("exchanges", []):
        if row.get("stage") != "submission":
            continue
        response = row.get("response", {})
        choices = response.get("choices", []) if isinstance(response, dict) else []
        message = choices[0].get("message", {}) if choices else {}
        calls = message.get("tool_calls") or []
        result = {"attempt": len(rows) + 1, "proposal_schema_valid": None,
                  "native_constraints_valid": None, "reference_certified": None,
                  "stage": "submission_protocol", "detail": None}
        if "transport_error" in row:
            error = row["transport_error"]
            result.update(stage="provider_error", detail={"type": error.get("type"),
                "message": error.get("message")})
            rows.append(result)
            continue
        if len(calls) != 1 or calls[0].get("function", {}).get("name") != "submit_frozen_world_task":
            result["detail"] = "submission did not contain exactly one task proposal tool call"
            rows.append(result)
            continue
        try:
            raw = strict_json(calls[0]["function"]["arguments"])
            DialogueDesignerProposal.model_validate(raw)
        except (KeyError, TypeError, ValueError) as exc:
            result.update(proposal_schema_valid=False, stage="proposal_schema", detail=str(exc))
            rows.append(result)
            continue

        result["proposal_schema_valid"] = True
        tool_results = row.get("tool_results", [])
        if any(item.get("status") == "certified" for item in tool_results):
            result.update(native_constraints_valid=True, reference_certified=True,
                          stage="reference_certified")
        else:
            feedback = row.get("feedback", {})
            detail = feedback.get("detail", "")
            if feedback.get("category") == "search_unproven" or "bounded Reference search did not prove" in detail:
                result.update(native_constraints_valid=True, reference_certified=False,
                              stage="reference_search", detail=detail)
            else:
                result.update(native_constraints_valid=False, reference_certified=None,
                              stage="native_constraints", detail=detail)
        rows.append(result)
    return {
        "attempts": len(rows),
        "proposal_tool_submissions": sum(row["proposal_schema_valid"] is not None for row in rows),
        "schema_valid": sum(row["proposal_schema_valid"] is True for row in rows),
        "native_constraints_valid": sum(row["native_constraints_valid"] is True for row in rows),
        "reference_certified": sum(row["reference_certified"] is True for row in rows),
        "provider_errors": sum(row["stage"] == "provider_error" for row in rows),
        "stages": rows,
    }


def run_check(root, *, live=False):
    if root.exists():
        raise ValueError("output directory already exists; no record will be replaced")
    root.mkdir(parents=True)
    frozen = _initial_world(1)
    budget = ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1)
    designer_budget = DesignerBudget(max_exploration_calls=3, max_revisions=1,
                                     initial_exploration_calls=2, actionable_feedback=True,
                                     include_related_objects=True, include_profile_events=True,
                                     confirmation_guidance=True)
    manifest = {"protocol": "designer-event-link-check-v2-confirmation-optional", "status": "RUNNING",
        "git_base": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "live_authorized": live, "max_live_designer_sessions": int(live),
        "max_model_calls": MAX_LIVE_MODEL_CALLS if live else 0,
        "max_tokens_request_option": None if live else "offline",
        "output_token_limit": "omitted from request options" if live else "offline",
        "service_tasks": 0, "reflection_calls": 0, "skill_updates": 0,
        "frozen_world_hash": frozen.world_hash, "designer_budget": designer_budget.model_dump(mode="json"),
        "construction_budget": budget.model_dump(mode="json"),
        "control_answers_sent_to_designer": False}
    atomic_json(root / "manifest.json", manifest)
    atomic_json(root / "world.json", frozen)
    summary = []
    ledger = CallLedger(root, MAX_LIVE_MODEL_CALLS if live else 0)
    raw_client = None
    try:
        query = {"action": "read_profile", "profile_id": "profile_u1_order0_line1"}
        old = inspect_world(frozen, query, include_profile_events=False)
        fixed = inspect_world(frozen, query)
        assert old["registered_external_events"] == []
        assert {e["id"] for e in fixed["registered_external_events"]} == {
            "manager_review_u1_order0_line1", "return_received_u1_order0_line1"}
        atomic_json(root / "query-before-after.json", {"query": query, "legacy": old, "fixed": fixed})
        original = json.loads((Path(__file__).resolve().parents[1] /
            "results/designer-exploration-v2-validation-001/offline-positive-control-proposal.json").read_text())

        def check(label, proposal, expected):
            atomic_json(root / "controls" / label / "proposal.json", proposal)
            try:
                _, task = compile_proposal(frozen, proposal, budget)
            except ValueError as exc:
                if expected or "bounded Reference search did not prove" not in str(exc):
                    raise
                result = {"certified": False, "reason": str(exc), "interpretation": "bounded search unproven"}
            else:
                assert expected, "unexpected proof without required external event"
                assert verify_task(task) is True
                if label == "original-five-step":
                    assert compile_proposal(frozen, proposal, budget)[1] == task
                atomic_json(root / "controls" / label / "certificate.json", task)
                result = {"certified": True, "replay_verified": True, "task_hash": task.task_hash,
                    "business_steps": sum(e.kind == "business" for e in task.dialogue_witnesses[0].trace.events),
                    "external_events": [e.payload["event_id"] for e in task.dialogue_witnesses[0].trace.events if e.kind == "external"]}
            atomic_json(root / "controls" / label / "result.json", result)
            summary.append({"label": label, **result})

        check("original-five-step", original, True)
        no_events = copy.deepcopy(original)
        no_events["external_schedule"] = []
        check("original-without-unnecessary-events", no_events, True)
        for label, profile_id, event_id in (
            ("approval", "profile_u1_order1_line0", "manager_review_u1_order1_line0"),
            ("return", "profile_u1_order0_line0", "return_received_u1_order0_line0"),
        ):
            line_id = frozen.world["profiles"][profile_id]["facts"]["line_id"]
            proposal = {"profile_ids": [profile_id], "customer_request": "Please refund my damaged item.",
                "goals": [{"collection": "lines", "entity": line_id, "field": "status", "accepted_values": ["refunded"]}],
                "preference_requirements": [{"profile_id": profile_id, "preference": "resolution", "accepted_values": ["refund"]}],
                "external_schedule": [event_id]}
            check(label + "-present", proposal, True)
            proposal["external_schedule"] = []
            check(label + "-missing", proposal, False)
        manifest["offline_controls"] = summary
        manifest["offline_controls_passed"] = True
        atomic_json(root / "manifest.json", manifest)
        if not live:
            manifest["status"] = "OFFLINE_VERIFIED"
        else:
            settings = settings_from_env()
            if "max_tokens" in settings.options:
                raise ValueError("live Designer check requires max_tokens to be omitted; output length is not capped by this runner")
            manifest["model"] = settings.model_dump(mode="json")
            manifest["provider_check"] = "DeepSeek v4.1 Flash availability was verified in the preceding authorized run"
            d0, _, _ = initial_skill_libraries()
            context = _designer_context(d0, [], "task-1", exploration=True)
            atomic_json(root / "designer-snapshot.json", d0)
            atomic_json(root / "live-prompt-context.json", context)
            atomic_json(root / "manifest.json", manifest)
            raw_client = OpenAICompatibleClient(settings, key_from_env())
            client = BudgetedClient("designer", raw_client, settings, ledger)
            try:
                result = design_and_compile(frozen, client, budget, prompt_context=context, protocol=PROTOCOL,
                    designer_budget=designer_budget, journal_path=root / "designer-journal.json")
            except DesignerFailure as exc:
                manifest["status"] = "BLOCKED"
                manifest["failure"] = str(exc)
                atomic_json(root / "live-replay.json", verify_failed_journal(frozen, exc.journal))
            else:
                atomic_json(root / "designer-execution.json", result)
                atomic_json(root / "certified-task.json", result.task)
                atomic_json(root / "live-replay.json", verify_designer_execution(result))
                manifest["status"] = "DESIGNER_CERTIFIED"
                manifest["task_hash"] = result.task.task_hash
                manifest["metrics"] = result.metrics
            journal = json.loads((root / "designer-journal.json").read_text())
            validation = _proposal_validation(journal)
            atomic_json(root / "proposal-validation.json", validation)
            manifest["proposal_validation"] = validation
    except Exception as exc:
        manifest["status"] = "BLOCKED"
        manifest["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        if raw_client is not None:
            raw_client.close()
        manifest["model_calls"] = ledger.actual_calls
        manifest["usage"] = ledger.usage()
        manifest["offline_controls"] = summary
        atomic_json(root / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="one Designer session only, max 5 model calls; max_tokens omitted; no Service")
    args = parser.parse_args()
    result = run_check(args.output, live=args.live)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
