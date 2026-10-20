"""Read-only paired After-sales Service Skill evaluation on dialogue protocol v3.

This is intentionally separate from ``aftersales_service_skill_ab`` (v2).
Both conditions load the same certified task, frozen world, Customer scenario,
models, budgets, Engine mode, and native Oracle; only the Service Skill context
changes. No Reflection, Gate, or Skill publication runs here.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

from usami.service.client import OpenAICompatibleClient, key_from_env, settings_from_env
from usami_harness.models import Budget, digest
from usami_benchmark.worlds import FrozenWorld
from usami_aftersales import adapter as aftersales
from usami_dialogue.agents import SkillPromptContext
from usami_dialogue.agents_v3 import (
    CUSTOMER_POLICY_V3,
    AgentExecutionV3,
    TaskRunConfigV3,
    replay_v3,
    run_v3,
)
from usami_dialogue.customer_fidelity import evaluate_customer_fidelity
from usami_dialogue.customer_simulator import ScenarioDrivenCustomer
from usami_dialogue.user_scenario import scenario_from_task
from vast_coevo.schema import atomic_json
from vast_coevo.skills import SkillContext, SkillRenderer, SkillRetriever

from experiments.vast_coevo.examples.aftersales_coevo_live import (
    BudgetedClient,
    CallLedger,
    _model_spec_for,
    _role_settings,
)
from experiments.vast_coevo.examples.aftersales_service_skill_ab import (
    _load_excluded_world,
    _load_service_snapshot,
    _skill_changes,
    _validate_world_disjointness,
    load_certified_task,
)
from experiments.vast_coevo.examples.after_sales_service_v3_diagnostic import (
    FixedCompliantCustomer,
    customer_environment,
)


PROTOCOL = "aftersales-service-skill-paired-evaluation-v3-v1"
MAX_TASKS = 5


def _make_config(task_record, snapshot, *, mode: str, turns: int,
                 service_calls: int, service_tool_calls: int,
                 customer_mode: str) -> tuple[TaskRunConfigV3, Any]:
    task = task_record.dialogue_witnesses[0].certificate.task
    if task.composition is None or task.composition.profile_ids != [task.profile_id]:
        raise ValueError("v3 paired evaluation requires one frozen Customer profile per task")
    witness = task_record.dialogue_witnesses[0]
    world = aftersales.World.model_validate(task_record.frozen.world)
    scenario = scenario_from_task(aftersales, world, task)
    retrieval = SkillRetriever("service").retrieve(snapshot, SkillContext(
        domain="aftersales", public_text=task.composition.customer_request,
        intents=("refund order resolution", "after-sales request"),
        available_tools=tuple(aftersales.TOOLS)))
    rendered = SkillRenderer().render(retrieval.skills)
    context = SkillPromptContext(snapshot_hash=snapshot.snapshot_hash,
        skill_ids=[hit.id for hit in retrieval.hits], rendered=rendered)
    config = TaskRunConfigV3(
        profile_id=task.profile_id,
        initial_world_hash=task_record.frozen.world_hash,
        mode=mode,
        tools=list(aftersales.TOOLS),
        budget=Budget(max_customer_turns=turns, max_customer_llm_calls=turns,
            max_service_llm_calls=service_calls, max_service_tool_calls=service_tool_calls,
            max_format_recoveries=0),
        external_schedule=task.external_schedule,
        customer_business_view="own-order-line-status-v1",
        customer_mode=customer_mode,
        user_scenario=scenario,
        skill_contexts={"service": context},
        task=task,
        certificate=witness.certificate,
        witness=witness.trace,
    )
    return config, scenario


def _config_without_skills(config: TaskRunConfigV3) -> dict:
    value = config.model_dump(mode="json")
    value.pop("skill_contexts", None)
    return value


def _strict_success(execution: AgentExecutionV3) -> dict:
    budget = execution.config.budget
    cost = execution.cost
    within = (
        cost.get("customer_calls", 0) <= budget.max_customer_llm_calls
        and cost.get("service_calls", 0) <= budget.max_service_llm_calls
        and cost.get("tool_calls", 0) <= budget.max_service_tool_calls
        and all(value <= budget.max_format_recoveries
                for value in cost.get("format_recoveries", {}).values())
    )
    normal = execution.status == "customer_finished"
    native = bool(execution.task_score.get("success"))
    return {
        **execution.task_score,
        "native_success": native,
        "normal_completion": normal,
        "budget_compliance": within,
        "success": native and normal and within,
    }


def _final_goal_reached(task, initial, final) -> bool:
    goals = [goal.satisfied(final) for goal in task.goals]
    created = [goal.satisfied(initial, final) for goal in task.created_goals]
    return bool(task.goals or task.created_goals) and all(goals + created)


def _injection_evidence(execution: AgentExecutionV3) -> dict:
    context = execution.config.skill_contexts.get("service")
    checked = []
    for call in execution.calls:
        if call.role != "service":
            continue
        messages = call.record.request.get("messages", [])
        system = messages[0].get("content", "") if messages else ""
        checked.append(bool(context and context.snapshot_hash in system and
                            (not context.rendered or context.rendered in system)))
    return {
        "snapshot_hash": context.snapshot_hash if context else None,
        "context_hash": context.context_hash if context else None,
        "skill_ids": list(context.skill_ids) if context else [],
        "rendered_skill": context.rendered if context else "",
        "service_model_calls": len(checked),
        "actual_requests_contained_context": checked,
        "all_service_requests_contained_context": bool(checked) and all(checked),
    }


def _summary(execution: AgentExecutionV3, strict: dict, replay: dict,
             fidelity: dict, final_goal: bool) -> dict:
    operations = execution.oracle.get("operations", [])
    decisions = execution.oracle.get("service_decisions", [])
    return {
        "execution_status": execution.status,
        "task_success": strict["success"],
        "native_task_success": strict["native_success"],
        "final_goal_reached": final_goal,
        "normal_completion": strict["normal_completion"],
        "budget_compliance": strict["budget_compliance"],
        "oracle_status": execution.oracle.get("status"),
        "successful_business_violations": sum(
            row.get("classification") == "successful_business_violation" for row in operations),
        "false_rejections": sum(
            row.get("classification") == "false_rejection" for row in decisions),
        "rejected_invalid_attempts": sum(
            row.get("classification") == "rejected_invalid_attempt" for row in operations),
        "cost": copy.deepcopy(execution.cost),
        "replay": copy.deepcopy(replay),
        "customer_fidelity_status": fidelity.get("customer_fidelity_status"),
        "customer_skill_injection": _injection_evidence(execution),
        "trace_hash": execution.trace.trace_hash,
        "execution_hash": execution.execution_hash,
    }


def _run_episode(root: Path, task_record, snapshot, *, mode: str,
                 turns: int, service_calls: int, service_tool_calls: int,
                 customer_mode: str, customer_settings, service_settings,
                 customer_key: str | None, service_key: str | None,
                 max_model_calls: int) -> tuple[dict, int]:
    world = aftersales.World.model_validate(task_record.frozen.world)
    config, scenario = _make_config(task_record, snapshot, mode=mode, turns=turns,
        service_calls=service_calls, service_tool_calls=service_tool_calls,
        customer_mode=customer_mode)
    atomic_json(root / "config.json", config.model_dump(mode="json"), immutable=True)
    atomic_json(root / "scenario.json", scenario.model_dump(mode="json"), immutable=True)
    ledger = CallLedger(root, max_model_calls)
    raw_customer = raw_service = None
    try:
        if customer_mode == "scenario-llm":
            raw_customer = OpenAICompatibleClient(customer_settings, customer_key)
            customer = ScenarioDrivenCustomer(
                BudgetedClient("customer", raw_customer, customer_settings, ledger), scenario)
        elif customer_mode == "deterministic":
            private = aftersales.private_state(world, task_record.dialogue_witnesses[0].certificate.task.profile_id)
            customer = FixedCompliantCustomer(private, scenario.reason_for_call)
        else:
            raise ValueError("customer_mode must be scenario-llm or deterministic")
        raw_service = OpenAICompatibleClient(service_settings, service_key)
        service = BudgetedClient("service", raw_service, service_settings, ledger)
        execution = run_v3(aftersales, world, config, customer, service)
        atomic_json(root / "execution.json", execution.model_dump(mode="json"), immutable=True)
        strict = _strict_success(execution)
        replay = replay_v3(aftersales, execution, world=world, config=config)
        fidelity = evaluate_customer_fidelity(execution)
        task = task_record.dialogue_witnesses[0].certificate.task
        final_world = aftersales.World.model_validate(execution.trace.final_world)
        final_goal = _final_goal_reached(task, world, final_world)
        summary = _summary(execution, strict, replay, fidelity, final_goal)
        atomic_json(root / "strict-score.json", strict, immutable=True)
        atomic_json(root / "oracle.json", execution.oracle, immutable=True)
        atomic_json(root / "replay.json", replay, immutable=True)
        atomic_json(root / "customer-fidelity.json", fidelity, immutable=True)
        atomic_json(root / "summary.json", summary, immutable=True)
        status = {"status": "COMPLETED" if replay.get("verified") else "REPLAY_FAILED",
                  "execution_status": execution.status,
                  "execution_hash": execution.execution_hash,
                  "model_calls": ledger.actual_calls}
        atomic_json(root / "status.json", status, immutable=False)
        return {**summary, "status": status["status"], "config_hash": digest(config.model_dump(mode="json"))}, ledger.actual_calls
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        atomic_json(root / "status.json", {"status": "FAILED", "error": failure,
            "model_calls": ledger.actual_calls}, immutable=False)
        return {"status": "FAILED", "error": failure}, ledger.actual_calls
    finally:
        if raw_customer is not None and hasattr(raw_customer, "close"):
            raw_customer.close()
        if raw_service is not None and hasattr(raw_service, "close"):
            raw_service.close()


def run_paired_evaluation_v3(
    output_dir: Path,
    *,
    task_paths: list[Path],
    exclude_world_paths: list[Path],
    s0_path: Path,
    s1_path: Path,
    mode: str,
    customer_mode: str,
    repeats: int = 3,
    turns: int = 8,
    service_calls: int = 20,
    service_tool_calls: int = 64,
    max_model_calls: int = 256,
    order_seed: int = 1,
) -> dict:
    """Run paired S0/S1 episodes on v3; never reflects or updates snapshots."""
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError("paired-evaluation outputs are append-only; choose a new directory")
    if mode not in {"reference", "sandbox"}:
        raise ValueError("mode must be explicitly selected as reference or sandbox")
    if customer_mode not in {"scenario-llm", "deterministic"}:
        raise ValueError("customer_mode must be scenario-llm or deterministic")
    if not 1 <= len(task_paths) <= MAX_TASKS:
        raise ValueError(f"supply between 1 and {MAX_TASKS} validation tasks")
    if not 1 <= repeats <= 20 or not 1 <= turns <= 30:
        raise ValueError("repeats must be 1..20 and customer turns 1..30")
    if not 1 <= service_calls <= 200 or not 1 <= service_tool_calls <= 2000:
        raise ValueError("Service call/tool budgets are outside supported bounds")
    if not 1 <= max_model_calls <= 2000:
        raise ValueError("global model-call budget must be 1..2000")

    from usami_benchmark.tasks import verify_task
    tasks = [load_certified_task(path) for path in task_paths]
    if len({task.task_hash for task in tasks}) != len(tasks):
        raise ValueError("validation task list contains duplicate task hashes")
    for task_record in tasks:
        if task_record.dialogue_witnesses[0].certificate.task.composition is None:
            raise ValueError("v3 evaluation requires a native open-composition task")
        verify_task(task_record)
    excluded = [_load_excluded_world(path) for path in exclude_world_paths]
    _validate_world_disjointness(tasks, excluded)
    s0 = _load_service_snapshot(s0_path)
    s1 = _load_service_snapshot(s1_path)
    if s0.snapshot_hash == s1.snapshot_hash:
        raise ValueError("S0 and S1 are identical snapshots")
    if s1.parent_hash != s0.snapshot_hash:
        raise ValueError("S1 must be a direct child of S0")
    changed_skill_ids = _skill_changes(s0, s1)
    if len(changed_skill_ids) != 1:
        raise ValueError("paired evaluation isolates exactly one changed Service Skill")

    service_settings = _role_settings("service")
    if customer_mode == "scenario-llm":
        customer_env = customer_environment()
        customer_settings = settings_from_env(customer_env)
        customer_key = key_from_env(customer_env)
    else:
        customer_settings = None
        customer_key = None
    service_key = key_from_env()
    if customer_mode == "deterministic":
        from usami.service.models import ModelSettings
        registered_customer_model = ModelSettings(model="local/fixed-customer-driver-v3",
            base_url="http://127.0.0.1/usami-local", options={})
    else:
        registered_customer_model = customer_settings

    root.mkdir(parents=True)
    for label, snapshot in (("S0", s0), ("S1", s1)):
        atomic_json(root / "snapshots" / f"{label}.json", snapshot.model_dump(mode="json"), immutable=True)
    world_rows = {}
    for index, task_record in enumerate(tasks, start=1):
        task_record.frozen.checked()
        world_rows[task_record.frozen.world_hash] = task_record.frozen
        atomic_json(root / "tasks" / f"task-{index:02d}.json",
            task_record.model_dump(mode="json"), immutable=True)
    for frozen in world_rows.values():
        atomic_json(root / "worlds" / f"{frozen.world_hash}.json",
            frozen.model_dump(mode="json"), immutable=True)

    configs = {}
    for record in tasks:
        configs[record.task_hash] = {
            label: _make_config(record, snapshot, mode=mode, turns=turns,
                service_calls=service_calls, service_tool_calls=service_tool_calls,
                customer_mode=customer_mode)[0]
            for label, snapshot in (("S0", s0), ("S1", s1))
        }
        if _config_without_skills(configs[record.task_hash]["S0"]) != _config_without_skills(configs[record.task_hash]["S1"]):
            raise ValueError("paired v3 configurations differ outside Service Skill context")

    manifest = {
        "protocol": PROTOCOL,
        "dialogue_protocol": "business-dialogue-task-agents-v3-finish-clarification-v1",
        "status": "RUNNING",
        "read_only": True,
        "reflection_or_skill_selection": "disabled",
        "execution_mode": mode,
        "customer_mode": customer_mode,
        "conditions": {"S0": {"snapshot_hash": s0.snapshot_hash},
            "S1": {"snapshot_hash": s1.snapshot_hash, "parent_hash": s1.parent_hash},
            "changed_skill_ids": changed_skill_ids},
        "tasks": [{"task_hash": row.task_hash, "record_hash": row.record_hash,
            "world_hash": row.frozen.world_hash, "world_registration_hash": row.frozen.registration_hash,
            "partition": row.frozen.spec.partition,
            "scenario_hash": scenario_from_task(aftersales,
                aftersales.World.model_validate(row.frozen.world),
                row.dialogue_witnesses[0].certificate.task).scenario_hash}
            for row in tasks],
        "excluded_training_worlds": [{"world_hash": row.world_hash,
            "structure_signature": row.structure_signature,
            "registration_hash": row.registration_hash} for row in excluded],
        "models": {"customer": _model_spec_for(registered_customer_model).model_dump(mode="json"),
            "service": _model_spec_for(service_settings).model_dump(mode="json")},
        "customer_policy_hash": digest(CUSTOMER_POLICY_V3),
        "budget_per_episode": {"customer_turns": turns, "customer_calls": turns,
            "service_model_calls": service_calls, "service_tool_calls": service_tool_calls,
            "format_recoveries": 0},
        "paired_repetitions_per_task": repeats,
        "planned_episodes": len(tasks) * repeats * 2,
        "global_remote_model_call_limit": max_model_calls,
        "pair_order_seed": order_seed,
        "pairing": "Each condition starts from the same certified task, frozen world and scenario. Only Service Skill context changes; Customer and Service models/configuration, protocol, budgets, tools, Oracle and Engine mode are fixed.",
        "claim_boundary": "V3 paired development diagnostic only; not a Dynamic Gate, statistical claim, or held-out generalization result.",
    }
    atomic_json(root / "manifest.json", manifest, immutable=False)

    rng = random.Random(order_seed)
    total_remote_calls = 0
    episode_rows = []
    pair_rows = []
    for task_index, record in enumerate(tasks, start=1):
        for repeat in range(1, repeats + 1):
            order = ["S0", "S1"]
            rng.shuffle(order)
            pair_id = f"task-{task_index:02d}-repeat-{repeat:02d}"
            conditions = {}
            for position, label in enumerate(order, start=1):
                episode_root = root / "episodes" / pair_id / label
                row = {"episode_id": f"{pair_id}-{label}", "pair_id": pair_id,
                    "condition": label, "task_hash": record.task_hash,
                    "world_hash": record.frozen.world_hash, "run_order": position}
                if total_remote_calls >= max_model_calls:
                    row.update(status="NOT_RUN_GLOBAL_BUDGET", model_calls=0)
                    atomic_json(episode_root / "status.json", row, immutable=True)
                else:
                    try:
                        summary, calls = _run_episode(episode_root, record,
                            s0 if label == "S0" else s1, mode=mode, turns=turns,
                            service_calls=service_calls, service_tool_calls=service_tool_calls,
                            customer_mode=customer_mode, customer_settings=customer_settings,
                            service_settings=service_settings, customer_key=customer_key,
                            service_key=service_key, max_model_calls=max_model_calls-total_remote_calls)
                        row.update(summary, model_calls=calls)
                    except Exception as exc:
                        row.update(status="FAILED", error={"type": type(exc).__name__, "message": str(exc)})
                        atomic_json(episode_root / "status.json", row, immutable=False)
                        calls = 0
                    total_remote_calls += calls
                conditions[label] = row
                episode_rows.append(row)
            before, after = conditions["S0"], conditions["S1"]
            pair_rows.append({"pair_id": pair_id, "task_hash": record.task_hash,
                "world_hash": record.frozen.world_hash, "scenario_hash": manifest["tasks"][task_index-1]["scenario_hash"],
                "condition_order": order, "S0": before, "S1": after,
                "paired_task_success_delta_S1_minus_S0": (
                    int(bool(after["task_success"])) - int(bool(before["task_success"]))
                    if "task_success" in before and "task_success" in after else None),
                "paired_violation_delta_S1_minus_S0": (
                    after.get("successful_business_violations", 0)-before.get("successful_business_violations", 0)
                    if "successful_business_violations" in before and "successful_business_violations" in after else None)})
            manifest.update({"model_calls_so_far": total_remote_calls,
                "episodes_completed_or_failed": len(episode_rows), "episodes": episode_rows, "pairs": pair_rows})
            atomic_json(root / "manifest.json", manifest, immutable=False)

    manifest.update({
        "status": "EXECUTED" if len(episode_rows) == manifest["planned_episodes"] and
            all(row.get("status") == "COMPLETED" for row in episode_rows) else "PARTIAL",
        "model_calls": total_remote_calls,
        "all_completed_episodes_replay_verified": bool(episode_rows) and
            all(row.get("status") == "COMPLETED" for row in episode_rows) and all(
                row.get("replay", {}).get("verified") is True for row in episode_rows),
    })
    atomic_json(root / "manifest.json", manifest, immutable=False)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, action="append", required=True,
        help="CertifiedTask/DesignerExecution JSON in validation partition; use 1–5 tasks")
    parser.add_argument("--exclude-world", type=Path, action="append", required=True,
        help="known training FrozenWorld or task JSON; exact hashes and structures are excluded")
    parser.add_argument("--s0", type=Path, required=True, help="initial Service LibrarySnapshot JSON")
    parser.add_argument("--s1", type=Path, required=True, help="candidate Service LibrarySnapshot JSON")
    parser.add_argument("--mode", choices=["reference", "sandbox"], required=True)
    parser.add_argument("--customer-mode", choices=["scenario-llm", "deterministic"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--customer-turns", type=int, default=8)
    parser.add_argument("--service-model-calls", type=int, default=20)
    parser.add_argument("--service-tool-calls", type=int, default=64)
    parser.add_argument("--max-model-calls", type=int, default=256)
    parser.add_argument("--pair-order-seed", type=int, default=1)
    args = parser.parse_args(argv)
    result = run_paired_evaluation_v3(args.output, task_paths=args.task,
        exclude_world_paths=args.exclude_world, s0_path=args.s0, s1_path=args.s1,
        mode=args.mode, customer_mode=args.customer_mode, repeats=args.repeats,
        turns=args.customer_turns, service_calls=args.service_model_calls,
        service_tool_calls=args.service_tool_calls,
        max_model_calls=args.max_model_calls, order_seed=args.pair_order_seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
