"""Bounded real-model After-sales Designer–Service–Skill loop.

Unlike ``aftersales_coevo_smoke``, this runner contains no preselected task,
dialogue plan, expected model response, or hand-authored SkillPatch. Models make
each decision; native compilation, Engine, Oracle, Static Skill Gate and Replay
remain deterministic boundaries. The run is a small integration experiment,
not evidence of general learning.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from usami.service.client import OpenAICompatibleClient, key_from_env, settings_from_env
from usami.service.models import ModelSettings, ServiceError
from usami_aftersales import adapter as aftersales
from usami_aftersales import tasks as aftersales_tasks
from usami_benchmark.designer import design_and_compile, verify_designer_execution
from usami_benchmark.registry import default_spec
from usami_benchmark.tasks import ConstructionBudget, verify_task
from usami_benchmark.worlds import FrozenWorld, freeze
from usami_dialogue.agents import (
    SkillPromptContext, TaskRunConfig, replay as replay_execution, run,
)
from usami_dialogue.tasks import score
from usami_harness.models import Budget, digest
from vast_coevo.designer.reflection import reflect as reflect_designer
from vast_coevo.models import ModelSpec
from vast_coevo.reflection.reflector import ReflectionInput, ServiceReflector
from vast_coevo.reflection.scope import DomainPolicy
from vast_coevo.schema import atomic_json
from vast_coevo.skills import (
    LibrarySnapshot, LibraryStore, SkillPatch, SkillRenderer, SkillRetriever, SkillContext,
    StaticSkillGate, apply_patch,
)
from experiments.vast_coevo.examples.aftersales_coevo_support import (
    event_and_decision_evidence, initial_skill_libraries, model_spec,
)


PROTOCOL = "aftersales-real-model-coevolution-v1"
MAX_SERVICE_TASKS = 3
DEFAULT_MAX_MODEL_CALLS = 41  # 3 task proposals + 2 reflections + 3*(4 Customer + 8 Service)


def _role_settings(role: str) -> ModelSettings:
    """Read role overrides without placing credentials in public model settings."""
    env = dict(os.environ)
    env.setdefault("USAMI_LLM_OPTIONS", '{"max_tokens":2048,"temperature":0}')
    prefix = "USAMI_" + role.upper() + "_"
    for name in ("MODEL", "BASE_URL", "OPTIONS", "TIMEOUT", "TRUST_ENV"):
        value = os.environ.get(prefix + name)
        if value is not None:
            env["USAMI_LLM_" + name] = value
    return settings_from_env(env)


class CallLedger:
    """Write each actual request before sending it and seal its response after."""
    def __init__(self, root: Path, limit: int):
        self.root = root
        self.limit = limit
        self.rows: list[dict[str, Any]] = []
        self.denied = 0
        self.denied_events: list[dict[str, Any]] = []

    @property
    def actual_calls(self):
        return sum(row.get("sent", False) for row in self.rows)

    def complete(self, role: str, inner, settings: ModelSettings, request: dict):
        if self.actual_calls >= self.limit:
            self.denied += 1
            event = {"role": role, "request_hash": digest(request), "sent": False,
                     "reason": "pre-registered total model-call budget exhausted"}
            self.denied_events.append(event)
            atomic_json(self.root / "model-calls" / f"budget-denied-{self.denied:03d}.json", event)
            raise ServiceError("GLOBAL_MODEL_BUDGET_EXHAUSTED", "pre-registered total model-call budget exhausted; no request sent")
        index = len(self.rows) + 1
        row: dict[str, Any] = {
            "protocol": "usami-live-model-call-v1", "call_index": index,
            "role": role, "model": model_spec(settings).model_dump(mode="json"),
            "request": copy.deepcopy(request), "status": "in_flight", "sent": True,
        }
        self.rows.append(row)
        path = self.root / "model-calls" / (f"{index:04d}-{role}.json")
        atomic_json(path, row)
        try:
            response = inner.complete(copy.deepcopy(request))
        except Exception as exc:
            row.update(status="error", error={"type": type(exc).__name__,
                "code": getattr(exc, "code", "PROVIDER_ERROR"), "message": str(exc)})
            row["response"] = copy.deepcopy(getattr(exc, "response", None))
            atomic_json(path, row)
            raise
        row.update(status="completed", response=copy.deepcopy(response))
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        row["usage"] = usage if isinstance(usage, dict) else {}
        atomic_json(path, row)
        return response

    def usage(self):
        totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "usage_complete": True}
        by_role: dict[str, dict[str, int]] = {}
        for row in self.rows:
            role = row["role"]
            target = by_role.setdefault(role, {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                                               "total_tokens": 0, "usage_complete": True})
            target["calls"] += int(row.get("sent", False))
            usage = row.get("usage") or {}
            keys = (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"),
                    ("total_tokens", "total_tokens"))
            if not all(type(usage.get(source)) is int and usage[source] >= 0 for _, source in keys):
                target["usage_complete"] = False
                totals["usage_complete"] = False
                continue
            for field, source in keys:
                target[field] += usage[source]
                totals[field] += usage[source]
        return {**totals, "by_role": by_role}


class BudgetedClient:
    def __init__(self, role: str, inner, settings: ModelSettings, ledger: CallLedger):
        self.role, self.inner, self.settings, self.ledger = role, inner, settings, ledger

    def complete(self, request):
        return self.ledger.complete(self.role, self.inner, self.settings, request)


def _model_spec_for(settings: ModelSettings) -> ModelSpec:
    return model_spec(settings)


def _initial_world(seed: int) -> FrozenWorld:
    row = freeze(default_spec("aftersales", seed, partition="train"))
    world = aftersales.World.model_validate(row.world)
    if any(aftersales.invariants(world)):
        raise ValueError("generated After-sales world violates native invariants")
    if not world.profiles:
        raise ValueError("generated After-sales world has no Customer profiles")
    return row


def _save(root: Path, relative: str, value: Any, *, immutable=True):
    path = root / relative
    atomic_json(path, value.model_dump(mode="json") if hasattr(value, "model_dump") else value,
                immutable=immutable)
    return path


def _designer_context(snapshot: LibrarySnapshot, rows: list[dict], stage: str):
    # No task family, profile, objective, expected error, or operation is fixed
    # here. The model receives registered facts and prior verified outcomes.
    rendered = SkillRenderer().render(snapshot.skills)
    schema = aftersales.World.model_json_schema()
    field_enums = {}
    for collection, definition in schema["properties"].items():
        reference = definition.get("additionalProperties", {}).get("$ref", "")
        entity_schema = schema.get("$defs", {}).get(reference.rsplit("/", 1)[-1], {})
        enums = {field: value["enum"] for field, value in entity_schema.get("properties", {}).items()
                 if "enum" in value}
        if enums:
            field_enums[collection] = enums
    return {
        "skill_snapshot_hash": snapshot.snapshot_hash,
        "skill_rendered": rendered,
        "stage": stage,
        "native_field_enums": field_enums,
        "verified_prior_trials": copy.deepcopy(rows),
        "instruction": "Independently identify an informative, legal next challenge from this frozen world and the evidence above. State your own test hypothesis in the task request; do not invent facts or supply answers.",
        "proposal_contract": {
            "goals": "Each completion goal must reference an entity already present in the frozen world, its actual collection and an existing field. A future case/refund/quote cannot be a goal entity when it does not yet exist. Choose desired field values from the native business model; the compiler independently proves reachability.",
            "frames": "Copy applicable native_frame_contract rows exactly, including selector_field, selector_value, mutable_fields and allow_create. Omitting selector_field changes its meaning to id. Combine only rows belonging to selected profiles of the same identity; do not expand their permissions.",
            "information": "Use only fact_keys actually present in each selected profile's private_facts. An information requirement is a requirement for Customer disclosure, not permission to invent a fact.",
            "confirmations": "confirmation_requirements contains exact native operation objects, never prose descriptions. Omit it unless a concrete operation can be specified from frozen facts.",
            "events": "external_schedule may contain only registered event IDs for the selected business objects. The Designer cannot create events or provide a reference witness.",
        },
    }


def _summary(row: dict) -> dict:
    execution = row["execution"]
    trace = execution.trace
    return {
        "episode_id": f"task-{row['task_number']}",
        "task_hash": row["task_record"].task_hash,
        "selection": row["task_record"].selection.model_dump(mode="json"),
        "trace_hash": trace.trace_hash,
        "task_success": bool(row["score"].get("success")),
        "final_goal_reached": row["final_goal_reached"],
        "process_errors": row["process_errors"],
        "oracle": execution.oracle,
        "customer_and_service_events": [event.model_dump(mode="json") for event in trace.events],
        "service_tools": copy.deepcopy(execution.tools),
        "cost": copy.deepcopy(execution.cost),
    }


def _make_task_config(frozen: FrozenWorld, task_record, service_snapshot: LibrarySnapshot, *, turns: int):
    witness = task_record.dialogue_witnesses[0]
    task = witness.certificate.task
    world = aftersales.World.model_validate(frozen.world)
    if task.composition is not None:
        task_brief = task.composition.customer_request
    else:
        private = aftersales.private_state(world, task.profile_id)
        task_brief = aftersales_tasks.customer_task_brief(world, private, task)
    retrieval = SkillRetriever("service").retrieve(service_snapshot, SkillContext(
        domain="aftersales", public_text=task_brief,
        intents=("refund order resolution", "after-sales request"), available_tools=tuple(aftersales.TOOLS)))
    rendered = SkillRenderer().render(retrieval.skills)
    context = SkillPromptContext(snapshot_hash=service_snapshot.snapshot_hash,
        skill_ids=[hit.id for hit in retrieval.hits], rendered=rendered)
    return TaskRunConfig(
        profile_id=task.profile_id, initial_world_hash=frozen.world_hash, mode="reference",
        tools=list(aftersales.TOOLS),
        budget=Budget(max_customer_turns=turns, max_customer_llm_calls=turns,
            max_service_llm_calls=8, max_service_tool_calls=12, max_format_recoveries=0),
        external_schedule=task.external_schedule, task=task,
        certificate=witness.certificate, witness=witness.trace,
        skill_contexts={"service": context},
    )


def _execute_task(root: Path, number: int, frozen: FrozenWorld, task_record,
                  service_snapshot: LibrarySnapshot, customers, services,
                  *, turns: int):
    world = aftersales.World.model_validate(frozen.world)
    config = _make_task_config(frozen, task_record, service_snapshot, turns=turns)
    _save(root, f"tasks/task-{number}/status.json", {
        "status": "RUNNING", "task_hash": task_record.task_hash,
        "initial_world_hash": frozen.world_hash,
        "service_snapshot_hash": service_snapshot.snapshot_hash,
    })
    execution = run(aftersales, world, config, customers, services)
    trace_path = _save(root, f"tasks/task-{number}/trace.json", execution.trace)
    _save(root, f"tasks/task-{number}/execution.json", execution)
    _save(root, f"tasks/task-{number}/certified_task.json", task_record)
    evaluation_error = None
    try:
        replay = replay_execution(aftersales, execution, world=world, config=config)
        task = task_record.dialogue_witnesses[0].certificate.task
        actual_score = score(aftersales, world, task, execution.trace)
        final_world = aftersales.World.model_validate(execution.trace.final_world)
        goals = task.goals
        final_goal_reached = bool(goals) and all(goal.satisfied(final_world) for goal in goals)
        process_errors = [row for row in execution.oracle.get("service_decisions", [])
            if row.get("classification") in {"false_rejection", "incorrect_refusal_reason"}]
        process_errors += [row for row in execution.oracle.get("operations", [])
            if row.get("classification") == "successful_business_violation"]
        if replay.get("verified") is not True:
            evaluation_error = "exact offline Replay returned unverified"
    except Exception as exc:
        replay = {"verified": False, "reason": "post-run score/Replay failed: " + str(exc)}
        actual_score = {"success": False, "evaluation_error": str(exc)}
        final_goal_reached = False
        process_errors = []
        evaluation_error = replay["reason"]
    _save(root, f"tasks/task-{number}/score.json", {
        "protocol": "aftersales-live-task-outcome-v1", "task_success": bool(actual_score["success"]),
        "final_goal_reached": final_goal_reached, "process_errors": process_errors,
        "strict_score": actual_score, "oracle": execution.oracle, "replay": replay,
        "evaluation_error": evaluation_error,
        "customer_snapshot": "fixed; no Customer Skill update in this protocol",
        "service_snapshot_hash": service_snapshot.snapshot_hash,
    })
    _save(root, f"tasks/task-{number}/status.json", {
        "status": "COMPLETED" if evaluation_error is None else "COMPLETED_WITH_EVALUATION_ERROR",
        "task_hash": task_record.task_hash, "initial_world_hash": frozen.world_hash,
        "trace_hash": execution.trace.trace_hash, "replay_verified": replay.get("verified") is True,
        "evaluation_error": evaluation_error,
    }, immutable=False)
    return {
        "task_number": number, "execution": execution, "task_record": task_record,
        "score": actual_score, "final_goal_reached": final_goal_reached,
        "process_errors": process_errors, "agent_replay": replay,
        "evaluation_error": evaluation_error,
        "trace_path": str(trace_path.resolve()),
        "execution_path": str((root / f"tasks/task-{number}/execution.json").resolve()),
        "task_path": str((root / f"tasks/task-{number}/certified_task.json").resolve()),
    }


def _select_patch(root: Path, role: str, parent: LibrarySnapshot, patch,
                  *, allowed_tools, forbidden_ids):
    if patch is None:
        result = {"status": "no_candidate", "selected_snapshot_hash": parent.snapshot_hash,
                  "reason": "reflection returned no valid SkillPatch"}
        _save(root, f"reflections/{role}_selection.json", result)
        return parent, result
    gate = StaticSkillGate(allowed_tools=allowed_tools, allowed_domains=("aftersales",),
                           forbidden_identifiers=forbidden_ids)
    validation = gate.validate(parent, patch)
    if not validation.passed:
        result = {"status": "static_rejected", "selected_snapshot_hash": parent.snapshot_hash,
                  "parent_snapshot_hash": parent.snapshot_hash,
                  "patch": patch.model_dump(mode="json"),
                  "static_gate": validation.model_dump(mode="json")}
        _save(root, f"reflections/{role}_selection.json", result)
        return parent, result
    if patch.action == "NOOP":
        result = {"status": "noop", "selected_snapshot_hash": parent.snapshot_hash,
                  "parent_snapshot_hash": parent.snapshot_hash,
                  "patch": patch.model_dump(mode="json"),
                  "static_gate": validation.model_dump(mode="json")}
        _save(root, f"reflections/{role}_selection.json", result)
        return parent, result
    candidate = apply_patch(parent, patch, "aftersales-real-model-live-reflection")
    store = LibraryStore(root / "libraries" / role)
    store.save(parent)
    store.save(candidate)
    result = {"status": "selected_after_static_gate_only",
        "selection_basis": "static structural and safety validation; no dynamic performance claim",
        "selected_snapshot_hash": candidate.snapshot_hash, "parent_snapshot_hash": parent.snapshot_hash,
        "patch": patch.model_dump(mode="json"), "static_gate": validation.model_dump(mode="json"),
        "skill_versions": [{"id": skill.id, "version": skill.version, "content_hash": skill.content_hash}
                            for skill in candidate.skills]}
    _save(root, f"reflections/{role}_selection.json", result)
    return candidate, result


def _forbidden_ids(world):
    ids = set()
    for name, value in world.model_dump(mode="json").items():
        if isinstance(value, dict):
            ids.update(key for key in value if isinstance(key, str))
    return tuple(sorted(ids))


def run_live(output_dir: Path, *, seed: int = 1, max_calls: int = DEFAULT_MAX_MODEL_CALLS,
             turns: int = 4, construction_nodes: int = 4096, construction_depth: int = 16):
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError("Live runs are append-only; select a new output directory")
    if not 1 <= max_calls <= 100:
        raise ValueError("max model calls must be between 1 and 100")
    if not 1 <= turns <= 8:
        raise ValueError("customer turns must be between 1 and 8")
    settings = {role: _role_settings(role) for role in ("designer", "customer", "service", "reflector")}
    # Credential lookup validates a configured API key/Keychain reference before
    # creating a run registration or sending world data anywhere.
    api_key = key_from_env()
    d0, s0, c0 = initial_skill_libraries()
    frozen = _initial_world(seed)
    world = aftersales.World.model_validate(frozen.world)
    ledger = CallLedger(root, max_calls)
    raw_clients = {role: OpenAICompatibleClient(settings[role], api_key) for role in settings}
    clients = {role: BudgetedClient(role, raw_clients[role], settings[role], ledger) for role in settings}
    root.mkdir(parents=True)
    for role, snapshot in (("designer", d0), ("service", s0), ("customer", c0)):
        _save(root, f"libraries/{role}/initial.json", snapshot)
        if role != "customer":
            LibraryStore(root / "libraries" / role).save(snapshot)
    _save(root, "world/frozen_world.json", frozen)
    manifest = {
        "protocol": PROTOCOL, "status": "RUNNING", "seed": seed,
        "service_tasks_max": MAX_SERVICE_TASKS, "service_tasks_completed": 0,
        "max_total_model_calls": max_calls, "per_task_budget": {
            "customer_turns": turns, "customer_model_calls": turns,
            "service_model_calls": 8, "service_tool_calls": 12, "format_recoveries": 0},
        "construction_budget": {"max_nodes": construction_nodes, "max_depth": construction_depth, "max_paths": 1},
        "frozen_world_hash": frozen.world_hash, "frozen_registration_hash": frozen.registration_hash,
        "partition": frozen.spec.partition, "generator_source_hash": frozen.generator_source_hash,
        "rules_source_hash": frozen.rules_source_hash,
        "initial_designer_snapshot_hash": d0.snapshot_hash,
        "initial_service_snapshot_hash": s0.snapshot_hash,
        "fixed_customer_snapshot_hash": c0.snapshot_hash,
        "models": {role: _model_spec_for(value).model_dump(mode="json") for role, value in settings.items()},
        "dynamic_gate": "disabled_for_this_three-task_live_smoke_only",
        "task_choices": "model-generated; no fixed family, profile, operation, or expected outcome",
        "dialogue_responses": "live Customer and Service models; no scripted operation plan",
        "reflection": "one live call per role; no retries; NOOP/rejected patch preserves parent",
        "skill_update_claim_boundary": "Static acceptance is not a performance-improvement claim.",
    }
    _save(root, "manifest.json", manifest, immutable=False)

    task_rows = []
    d_selected, s_selected = d0, s0
    reflection_results = {}
    try:
        for number in (1, 2):
            previous = [_summary(row) for row in task_rows]
            context = _designer_context(d_selected, previous, f"task-{number}")
            designer_result = design_and_compile(frozen, clients["designer"],
                ConstructionBudget(max_nodes=construction_nodes, max_depth=construction_depth, max_paths=1),
                prompt_context=context)
            verify_designer_execution(designer_result)
            _save(root, f"designer/task-{number}-execution.json", designer_result)
            _save(root, f"designer/task-{number}-selection.json", {
                "selection": designer_result.selection.model_dump(mode="json"),
                "task_hash": designer_result.task.task_hash,
                "native_task_proof": verify_designer_execution(designer_result),
                "designer_snapshot_hash": d_selected.snapshot_hash,
                "prompt_context": designer_result.prompt_context,
            })
            row = _execute_task(root, number, frozen, designer_result.task, s_selected,
                                clients["customer"], clients["service"], turns=turns)
            task_rows.append(row)
            manifest["service_tasks_completed"] = len(task_rows)
            manifest["task_outcomes"] = [_summary(value) for value in task_rows]
            manifest["model_usage_so_far"] = ledger.usage()
            _save(root, "manifest.json", manifest, immutable=False)
            if row["evaluation_error"]:
                raise ValueError(f"Task {number} execution was preserved but validation failed: {row['evaluation_error']}")

        # The two Reflectors see actual, replay-verified Task 1/2 evidence only.
        evidence_rows, evidence_hashes = [], []
        service_sources = [s0, s0]
        for row, used_service in zip(task_rows, service_sources):
            evidence, evidence_hash = event_and_decision_evidence(
                root, row, c0, used_service,
                customer_model=_model_spec_for(settings["customer"]),
                service_model=_model_spec_for(settings["service"]),
                config_id=PROTOCOL)
            evidence_rows.append(evidence)
            evidence_hashes.append(evidence_hash)
        feedback = [_summary(row) | {"evidence_hash": evidence.evidence_hash}
                    for row, evidence in zip(task_rows, evidence_rows)]
        _save(root, "reflections/source-evidence.json", {
            "episode_ids": [value.episode_id for value in evidence_rows],
            "evidence_hashes": evidence_hashes,
            "source_task_hashes": [row["task_record"].task_hash for row in task_rows],
            "source_trace_hashes": [row["execution"].trace.trace_hash for row in task_rows],
        })

        designer_reflection = reflect_designer(clients["reflector"], _model_spec_for(settings["reflector"]),
            d_selected, feedback, "aftersales-live-g1", domain_policy=DomainPolicy(add_domains=("aftersales",)))
        _save(root, "reflections/designer_reflection.json", designer_reflection)
        d_selected, reflection_results["designer"] = _select_patch(
            root, "designer", d_selected,
            SkillPatch.model_validate(designer_reflection["patch"]) if designer_reflection.get("patch") else None,
            allowed_tools=(), forbidden_ids=_forbidden_ids(world))

        service_input = ReflectionInput(
            generation=1, role="service", library=s_selected, evidence=tuple(evidence_rows),
            allowed_tools=tuple(aftersales.TOOLS), domain_policy=DomainPolicy(add_domains=("aftersales",)),
            public_policy=json.dumps(aftersales.POLICY, ensure_ascii=False, sort_keys=True),
            boundaries="Only After-sales declarative Skill text may change; keep Engine, Reference, Oracle, tools and Customer authority fixed.",
        )
        service_reflection = ServiceReflector(clients["reflector"], _model_spec_for(settings["reflector"])).reflect(service_input)
        _save(root, "reflections/service_reflection.json", service_reflection)
        s_selected, reflection_results["service"] = _select_patch(
            root, "service", s_selected, service_reflection.patch,
            allowed_tools=aftersales.TOOLS, forbidden_ids=_forbidden_ids(world))
        manifest["reflection_evidence_hashes"] = evidence_hashes
        manifest["reflection_selections"] = reflection_results
        _save(root, "manifest.json", manifest, immutable=False)

        context = _designer_context(d_selected, [_summary(row) for row in task_rows], "task-3-after-reflection")
        context["reflection_selections"] = reflection_results
        designer_result = design_and_compile(frozen, clients["designer"],
            ConstructionBudget(max_nodes=construction_nodes, max_depth=construction_depth, max_paths=1),
            prompt_context=context)
        verify_designer_execution(designer_result)
        _save(root, "designer/task-3-execution.json", designer_result)
        _save(root, "designer/task-3-selection.json", {
            "selection": designer_result.selection.model_dump(mode="json"),
            "task_hash": designer_result.task.task_hash,
            "native_task_proof": verify_designer_execution(designer_result),
            "designer_snapshot_hash": d_selected.snapshot_hash,
            "prompt_context": designer_result.prompt_context,
        })
        row = _execute_task(root, 3, frozen, designer_result.task, s_selected,
                            clients["customer"], clients["service"], turns=turns)
        task_rows.append(row)
        manifest["service_tasks_completed"] = len(task_rows)
        manifest["task_outcomes"] = [_summary(value) for value in task_rows]
        if row["evaluation_error"]:
            raise ValueError(f"Task 3 execution was preserved but validation failed: {row['evaluation_error']}")

        # Verify actual Skill text in Task 3 requests. If the Service Retriever
        # does not select the new Skill, record that as an observed failure to use it.
        designer_system = designer_result.request["messages"][0]["content"]
        designer_rendered = SkillRenderer().render(d_selected.skills)
        service_context = row["execution"].config.skill_contexts["service"]
        service_request = next((call.record.request for call in row["execution"].calls if call.role == "service"), None)
        service_contains = bool(service_request and service_context.rendered and
            service_context.rendered in service_request["messages"][0]["content"])
        consumption = {
            "task_hash": designer_result.task.task_hash,
            "designer_snapshot_hash": d_selected.snapshot_hash,
            "designer_skill_versions": [{"id": skill.id, "version": skill.version,
                "content_hash": skill.content_hash} for skill in d_selected.skills],
            "designer_rendered_skill_in_actual_task_request": bool(designer_rendered and designer_rendered in designer_system),
            "service_snapshot_hash": s_selected.snapshot_hash,
            "service_skill_versions": [{"id": skill.id, "version": skill.version,
                "content_hash": skill.content_hash} for skill in s_selected.skills],
            "service_skill_context_hash": service_context.context_hash,
            "service_selected_skill_ids": service_context.skill_ids,
            "service_rendered_skill_in_actual_task_request": service_contains,
            "source_trace_hashes": [row["execution"].trace.trace_hash for row in task_rows[:2]],
        }
        _save(root, "verification/task-3-skill-consumption.json", consumption)
        replay_rows = [replay_execution(aftersales, row["execution"],
            world=aftersales.World.model_validate(frozen.world), config=row["execution"].config)
            for row in task_rows]
        _save(root, "verification/replay.json", {"all_verified": all(row.get("verified") for row in replay_rows),
            "tasks": replay_rows, "certificates_verified": [verify_task(row["task_record"]) for row in task_rows]})
        manifest.update({"status": "EXECUTED", "service_tasks_completed": len(task_rows),
            "final_designer_snapshot_hash": d_selected.snapshot_hash,
            "final_service_snapshot_hash": s_selected.snapshot_hash,
            "designer_skill_updated": d_selected.snapshot_hash != d0.snapshot_hash,
            "service_skill_updated": s_selected.snapshot_hash != s0.snapshot_hash,
            "task3_skill_consumption": consumption,
            "model_usage": ledger.usage(), "model_calls": ledger.actual_calls,
            "denied_over_budget_requests": ledger.denied,
            "denied_model_call_events": ledger.denied_events,
            "replay_verified": all(value.get("verified") for value in replay_rows),
            "claim_boundary": "Three-task real-model engineering run only; no statistical or general learning claim."})
    except KeyboardInterrupt:
        manifest.update({"status": "BLOCKED", "failure": {
            "type": "KeyboardInterrupt", "message": "run interrupted; completed model-call and task artifacts were preserved"},
            "service_tasks_completed": len(task_rows), "task_outcomes": [_summary(value) for value in task_rows],
            "model_usage": ledger.usage(), "model_calls": ledger.actual_calls,
            "denied_over_budget_requests": ledger.denied,
            "denied_model_call_events": ledger.denied_events})
        _save(root, "failure.json", manifest["failure"])
    except Exception as exc:
        manifest.update({"status": "BLOCKED", "failure": {"type": type(exc).__name__, "message": str(exc)},
            "service_tasks_completed": len(task_rows), "task_outcomes": [_summary(value) for value in task_rows],
            "model_usage": ledger.usage(), "model_calls": ledger.actual_calls,
            "denied_over_budget_requests": ledger.denied})
        manifest["denied_model_call_events"] = ledger.denied_events
        _save(root, "failure.json", manifest["failure"])
    finally:
        for client in raw_clients.values():
            client.close()
        _save(root, "manifest.json", manifest, immutable=False)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None, help="new output directory; existing output is never overwritten")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-model-calls", type=int, default=DEFAULT_MAX_MODEL_CALLS)
    parser.add_argument("--customer-turns", type=int, default=4)
    parser.add_argument("--construction-nodes", type=int, default=4096)
    parser.add_argument("--construction-depth", type=int, default=16)
    args = parser.parse_args(argv)
    output = args.output or Path("experiments/vast_coevo/results") / (
        "aftersales-coevo-live-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    result = run_live(output, seed=args.seed, max_calls=args.max_model_calls,
        turns=args.customer_turns, construction_nodes=args.construction_nodes,
        construction_depth=args.construction_depth)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
