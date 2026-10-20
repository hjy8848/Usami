"""Read-only paired After-sales evaluation of two Service Skill snapshots.

This entry point runs no Designer or Reflector. It reuses the certified task,
native dialogue Engine, independent Oracle, strict task scoring, and exact
request/response Replay from the existing After-sales stack. Each condition
starts from a fresh copy of the same frozen world and task.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path
from typing import Any

from usami.service.client import OpenAICompatibleClient, key_from_env
from usami_benchmark.tasks import CertifiedTask, verify_task
from usami_benchmark.splits import verified_world
from usami_benchmark.worlds import FrozenWorld
from usami_dialogue.agents import CUSTOMER_POLICY
from vast_coevo.schema import atomic_json, digest
from vast_coevo.skills import LibrarySnapshot

from experiments.vast_coevo.examples.aftersales_coevo_live import (
    BudgetedClient,
    CallLedger,
    _execute_task,
    _model_spec_for,
    _role_settings,
)


PROTOCOL = "aftersales-service-skill-paired-evaluation-v1"
MAX_TASKS = 5


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_certified_task(path: Path) -> CertifiedTask:
    """Accept a CertifiedTask file or the task nested in DesignerExecution."""
    raw = _read_json(path)
    if isinstance(raw, dict) and "task" in raw:
        raw = raw["task"]
    task = CertifiedTask.model_validate(raw)
    if task.frozen.spec.domain != "aftersales":
        raise ValueError(f"{path}: paired Service evaluator only accepts After-sales tasks")
    if task.frozen.spec.partition != "validation":
        raise ValueError(f"{path}: paired development tasks must use the validation partition")
    verify_task(task)
    return task


def _load_service_snapshot(path: Path) -> LibrarySnapshot:
    snapshot = LibrarySnapshot.model_validate(_read_json(path))
    if snapshot.role != "service":
        raise ValueError(f"{path}: expected a Service LibrarySnapshot")
    return snapshot


def _load_excluded_world(path: Path) -> FrozenWorld:
    raw = _read_json(path)
    if isinstance(raw, dict) and "task" in raw:
        raw = raw["task"]
    if isinstance(raw, dict) and "frozen" in raw and "world" not in raw:
        raw = raw["frozen"]
    return verified_world(FrozenWorld.model_validate(raw))


def _validate_world_disjointness(tasks: list[CertifiedTask], excluded: list[FrozenWorld]) -> None:
    if not excluded:
        raise ValueError("supply at least one known training world with --exclude-world")
    excluded_worlds = {(row.spec.domain, row.world_hash) for row in excluded}
    excluded_structures = {(row.spec.domain, row.structure_signature) for row in excluded}
    for task in tasks:
        frozen = task.frozen
        if (frozen.spec.domain, frozen.world_hash) in excluded_worlds:
            raise ValueError("validation task reuses an excluded training world hash")
        if (frozen.spec.domain, frozen.structure_signature) in excluded_structures:
            raise ValueError("validation task reuses an excluded training-world structure")


def _skill_changes(s0: LibrarySnapshot, s1: LibrarySnapshot) -> list[str]:
    before = {skill.id: skill.model_dump(mode="json") for skill in s0.skills}
    after = {skill.id: skill.model_dump(mode="json") for skill in s1.skills}
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


def _model_request_injection(execution) -> dict:
    context = execution.config.skill_contexts.get("service")
    service_calls = [call for call in execution.calls if call.role == "service"]
    verified_calls = []
    for call in service_calls:
        messages = call.record.request.get("messages", [])
        system = messages[0].get("content", "") if messages else ""
        verified_calls.append(bool(context and context.snapshot_hash in system and
            (not context.rendered or context.rendered in system)))
    return {
        "snapshot_hash": context.snapshot_hash if context else None,
        "context_hash": context.context_hash if context else None,
        "skill_ids": list(context.skill_ids) if context else [],
        "rendered_skill": context.rendered if context else "",
        "service_model_calls": len(service_calls),
        "actual_requests_contained_context": verified_calls,
        "all_service_requests_contained_context": bool(verified_calls) and all(verified_calls),
    }


def _episode_summary(result: dict | None, *, error: str | None = None) -> dict:
    if result is None:
        return {"status": "FAILED_BEFORE_RESULT", "error": error}
    execution = result["execution"]
    score = result["score"]
    operations = execution.oracle.get("operations", [])
    return {
        "execution_status": execution.status,
        "task_success": bool(score.get("success")),
        "native_task_success": bool(score.get("native_success")),
        "final_goal_reached": bool(result["final_goal_reached"]),
        "normal_completion": bool(score.get("normal_completion")),
        "budget_compliance": bool(score.get("budget_compliance")),
        "oracle_status": execution.oracle.get("status"),
        "successful_business_violations": sum(
            row.get("classification") == "successful_business_violation" for row in operations),
        "false_rejections": sum(
            row.get("classification") == "false_rejection" for row in execution.oracle.get("service_decisions", [])) +
            sum(row.get("classification") == "false_rejection" for row in operations),
        "rejected_invalid_attempts": sum(
            row.get("classification") == "rejected_invalid_attempt" for row in operations),
        "cost": copy.deepcopy(execution.cost),
        "replay": copy.deepcopy(result["agent_replay"]),
        "service_skill_injection": _model_request_injection(execution),
        "trace_hash": execution.trace.trace_hash,
        "execution_hash": execution.execution_hash,
        "evaluation_error": result.get("evaluation_error"),
    }


def _base_config(config) -> dict:
    value = config.model_dump(mode="json")
    value.pop("skill_contexts", None)
    return value


def run_paired_evaluation(
    output_dir: Path,
    *,
    task_paths: list[Path],
    exclude_world_paths: list[Path],
    s0_path: Path,
    s1_path: Path,
    mode: str,
    repeats: int = 3,
    turns: int = 4,
    service_calls: int = 8,
    service_tool_calls: int = 12,
    max_model_calls: int = 256,
    order_seed: int = 1,
) -> dict:
    """Run S0/S1 pairs on the exact same validation tasks; never updates Skills."""
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError("paired-evaluation outputs are append-only; choose a new directory")
    if mode not in {"reference", "sandbox"}:
        raise ValueError("mode must be explicitly selected as reference or sandbox")
    if not 1 <= len(task_paths) <= MAX_TASKS:
        raise ValueError(f"supply between 1 and {MAX_TASKS} paired development tasks")
    if not 1 <= repeats <= 20 or not 1 <= turns <= 8:
        raise ValueError("repeats must be 1..20 and customer turns 1..8")
    if not 1 <= service_calls <= 32 or not 1 <= service_tool_calls <= 64:
        raise ValueError("Service call/tool budgets are outside supported bounds")
    if not 1 <= max_model_calls <= 2000:
        raise ValueError("global model-call budget must be 1..2000")

    tasks = [load_certified_task(path) for path in task_paths]
    if len({row.task_hash for row in tasks}) != len(tasks):
        raise ValueError("paired task list contains duplicate task hashes")
    excluded_worlds = [_load_excluded_world(path) for path in exclude_world_paths]
    _validate_world_disjointness(tasks, excluded_worlds)
    s0, s1 = _load_service_snapshot(s0_path), _load_service_snapshot(s1_path)
    if s0.snapshot_hash == s1.snapshot_hash:
        raise ValueError("S0 and S1 are identical snapshots")
    if s1.parent_hash != s0.snapshot_hash:
        raise ValueError("S1 must be a direct child of the supplied S0 snapshot")
    changed_skill_ids = _skill_changes(s0, s1)
    if len(changed_skill_ids) != 1:
        raise ValueError("this evaluator isolates exactly one changed Service Skill")

    settings = {role: _role_settings(role) for role in ("customer", "service")}
    api_key = key_from_env()
    root.mkdir(parents=True)
    for role, snapshot in (("S0", s0), ("S1", s1)):
        atomic_json(root / "snapshots" / f"{role}.json", snapshot.model_dump(mode="json"), immutable=True)
    world_hashes = {}
    for index, task in enumerate(tasks, start=1):
        task.frozen.checked()
        world_hashes.setdefault(task.frozen.registration_hash, task.frozen)
        atomic_json(root / "tasks" / f"task-{index:02d}.json", task.model_dump(mode="json"), immutable=True)
    for registration_hash, frozen in world_hashes.items():
        atomic_json(root / "worlds" / f"{frozen.world_hash}.json", frozen.model_dump(mode="json"), immutable=True)

    task_configs = {}
    from experiments.vast_coevo.examples.aftersales_coevo_live import _make_task_config
    for task in tasks:
        configs = {
            label: _make_task_config(task.frozen, task, snapshot, turns=turns, mode=mode,
                service_calls=service_calls, service_tool_calls=service_tool_calls)
            for label, snapshot in (("S0", s0), ("S1", s1))
        }
        if _base_config(configs["S0"]) != _base_config(configs["S1"]):
            raise ValueError("paired conditions differ outside the Service Skill context")
        task_configs[task.task_hash] = configs

    manifest = {
        "protocol": PROTOCOL,
        "status": "RUNNING",
        "read_only": True,
        "reflection_or_skill_selection": "disabled",
        "execution_mode": mode,
        "mode_semantics": {
            "reference": "Disallowed writes are blocked by the Engine.",
            "sandbox": "Writes execute in the isolated simulated world; the independent Oracle audits them.",
        }[mode],
        "conditions": {
            "S0": {"snapshot_hash": s0.snapshot_hash},
            "S1": {"snapshot_hash": s1.snapshot_hash, "parent_hash": s1.parent_hash},
            "changed_skill_ids": changed_skill_ids,
        },
        "tasks": [{"task_hash": task.task_hash, "world_hash": task.frozen.world_hash,
                    "world_registration_hash": task.frozen.registration_hash,
                    "partition": task.frozen.spec.partition,
                    "profile_id": task.task.profile_id,
                    "identity": task.frozen.world.get("profiles", {}).get(task.task.profile_id, {}).get("identity")}
                   for task in tasks],
        "excluded_training_worlds": [{"world_hash": row.world_hash,
            "structure_signature": row.structure_signature,
            "registration_hash": row.registration_hash} for row in excluded_worlds],
        "models": {role: _model_spec_for(value).model_dump(mode="json") for role, value in settings.items()},
        "customer_policy_hash": digest(CUSTOMER_POLICY),
        "budget_per_episode": {"customer_turns": turns, "customer_model_calls": turns,
            "service_model_calls": service_calls, "service_tool_calls": service_tool_calls,
            "format_recoveries": 0},
        "paired_repetitions_per_task": repeats,
        "planned_episodes": len(tasks) * repeats * 2,
        "global_model_call_limit": max_model_calls,
        "pair_order_seed": order_seed,
        "pairing": "Each task/repetition runs S0 and S1 from a fresh copy of the same certified FrozenWorld and task; only the retrieved/injected Service Skill context differs.",
        "claim_boundary": "Small development diagnostic; not a performance Gate, statistical claim, or held-out generalization result.",
    }
    atomic_json(root / "manifest.json", manifest, immutable=False)

    rng = random.Random(order_seed)
    total_model_calls = 0
    episode_rows = []
    pair_rows = []
    episode_index = 0
    for task_index, task in enumerate(tasks, start=1):
        for repeat in range(1, repeats + 1):
            condition_order = ["S0", "S1"]
            rng.shuffle(condition_order)
            pair_id = f"task-{task_index:02d}-repeat-{repeat:02d}"
            conditions = {}
            pair_configs = task_configs[task.task_hash]
            for condition in condition_order:
                episode_index += 1
                episode_root = root / "episodes" / pair_id / condition
                row = {"episode_id": f"{pair_id}-{condition}", "pair_id": pair_id,
                       "condition": condition, "task_hash": task.task_hash,
                       "world_hash": task.frozen.world_hash, "run_order": len(conditions) + 1}
                if total_model_calls >= max_model_calls:
                    row.update(status="NOT_RUN_GLOBAL_BUDGET", model_calls=0)
                    atomic_json(episode_root / "status.json", row, immutable=True)
                    conditions[condition] = row
                    episode_rows.append(row)
                    continue
                ledger = CallLedger(episode_root, limit=max_model_calls - total_model_calls)
                raw_customer = raw_service = None
                try:
                    raw_customer = OpenAICompatibleClient(settings["customer"], api_key)
                    raw_service = OpenAICompatibleClient(settings["service"], api_key)
                    customer = BudgetedClient("customer", raw_customer, settings["customer"], ledger)
                    service = BudgetedClient("service", raw_service, settings["service"], ledger)
                    if _base_config(pair_configs[condition]) != _base_config(
                            _make_task_config(task.frozen, task, s0 if condition == "S0" else s1,
                                turns=turns, mode=mode, service_calls=service_calls,
                                service_tool_calls=service_tool_calls)):
                        raise ValueError("paired frozen config changed during execution")
                    result = _execute_task(episode_root, 1, task.frozen, task,
                        s0 if condition == "S0" else s1, customer, service, turns=turns,
                        mode=mode, service_calls=service_calls, service_tool_calls=service_tool_calls)
                    row.update(_episode_summary(result), status="COMPLETED",
                               model_calls=ledger.actual_calls,
                               config_hash=digest(result["execution"].config.model_dump(mode="json")))
                except Exception as exc:
                    row.update(status="FAILED", error={"type": type(exc).__name__, "message": str(exc)},
                               model_calls=ledger.actual_calls)
                    task_status = episode_root / "tasks" / "task-1" / "status.json"
                    if task_status.exists():
                        atomic_json(task_status, {"status": "FAILED", "error": row["error"]}, immutable=False)
                finally:
                    if raw_customer is not None:
                        raw_customer.close()
                    if raw_service is not None:
                        raw_service.close()
                total_model_calls += ledger.actual_calls
                atomic_json(episode_root / "status.json", row, immutable=False)
                conditions[condition] = row
                episode_rows.append(row)
            s0_row, s1_row = conditions.get("S0", {}), conditions.get("S1", {})
            pair_rows.append({"pair_id": pair_id, "task_hash": task.task_hash,
                "world_hash": task.frozen.world_hash, "condition_order": condition_order,
                "S0": s0_row, "S1": s1_row,
                "paired_task_success_delta_S1_minus_S0": (
                    int(bool(s1_row.get("task_success"))) - int(bool(s0_row.get("task_success")))
                    if "task_success" in s0_row and "task_success" in s1_row else None),
                "paired_violation_delta_S1_minus_S0": (
                    s1_row.get("successful_business_violations", 0) - s0_row.get("successful_business_violations", 0)
                    if "successful_business_violations" in s0_row and "successful_business_violations" in s1_row else None)})
            atomic_json(root / "pairs.json", pair_rows, immutable=False)
            manifest["model_calls_so_far"] = total_model_calls
            manifest["completed_or_failed_episodes"] = len(episode_rows)
            atomic_json(root / "manifest.json", manifest, immutable=False)

    fully_scheduled = len(episode_rows) == manifest["planned_episodes"] and all(
        row.get("status") == "COMPLETED" for row in episode_rows)
    manifest.update({
        "status": "EXECUTED" if fully_scheduled else "PARTIAL",
        "model_calls": total_model_calls,
        "episodes": episode_rows,
        "pairs": pair_rows,
        "all_started_episodes_replay_verified": bool(episode_rows) and all(
            row.get("status") == "COMPLETED" and row.get("replay", {}).get("verified") is True
            for row in episode_rows if row.get("status") != "NOT_RUN_GLOBAL_BUDGET"),
        "customer_model": _model_spec_for(settings["customer"]).model_dump(mode="json"),
        "service_model": _model_spec_for(settings["service"]).model_dump(mode="json"),
    })
    atomic_json(root / "manifest.json", manifest, immutable=False)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, action="append", required=True,
        help="certified After-sales task JSON or DesignerExecution JSON; use 1–5 validation-partition tasks")
    parser.add_argument("--exclude-world", type=Path, action="append", required=True,
        help="known training FrozenWorld JSON or task JSON containing one; excludes both exact worlds and structures")
    parser.add_argument("--s0", type=Path, required=True, help="original Service LibrarySnapshot JSON")
    parser.add_argument("--s1", type=Path, required=True, help="candidate Service LibrarySnapshot JSON")
    parser.add_argument("--mode", choices=["reference", "sandbox"], required=True,
        help="select Engine semantics explicitly; the chosen mode is frozen in the output manifest")
    parser.add_argument("--output", type=Path, required=True, help="new output directory; never overwritten")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--customer-turns", type=int, default=4)
    parser.add_argument("--service-model-calls", type=int, default=8)
    parser.add_argument("--service-tool-calls", type=int, default=12)
    parser.add_argument("--max-model-calls", type=int, default=256)
    parser.add_argument("--pair-order-seed", type=int, default=1)
    args = parser.parse_args(argv)
    result = run_paired_evaluation(args.output, task_paths=args.task,
        exclude_world_paths=args.exclude_world, s0_path=args.s0,
        s1_path=args.s1, mode=args.mode, repeats=args.repeats, turns=args.customer_turns,
        service_calls=args.service_model_calls, service_tool_calls=args.service_tool_calls,
        max_model_calls=args.max_model_calls, order_seed=args.pair_order_seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
