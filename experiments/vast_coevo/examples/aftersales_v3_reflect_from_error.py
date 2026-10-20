"""One-shot Service Reflection from a replay-verified v3 After-sales failure.

The pilot source is explicitly consumed as training evidence. The evaluator
freezes three new certified worlds before the single Reflection call, then can
run a read-only S0/S1 pair without feeding results back into training.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any

from usami.service.client import OpenAICompatibleClient, key_from_env
from usami_benchmark.registry import default_spec
from usami_benchmark.tasks import (
    CertifiedTask, ConstructionBudget, OpenDialogueComposition, TaskSelection,
    compile_task, verify_task,
)
from usami_benchmark.worlds import FrozenWorld, freeze
from usami_aftersales import adapter as aftersales
from usami_aftersales import tasks as aftersales_tasks
from usami_aftersales.models import Operation
from usami_dialogue.agents import SkillPromptContext
from usami_dialogue.agents_v3 import AgentExecutionV3, replay_v3
from usami_dialogue.tasks import Goal, InformationRequirement, PreferenceRequirement
from usami_dialogue.user_scenario import scenario_from_task
from vast_coevo.evidence import EvidenceArchive
from vast_coevo.models import (
    ArtifactRef, Budget, Consumption, EpisodeConfig, EpisodeEvidence, ModelCall,
    ModelSpec, ReplayResult, VerifiedEvent, VerifiedFailure,
)
from vast_coevo.reflection.evidence import InteractionEvidenceView, native_view
from vast_coevo.reflection.reflector import ReflectionInput, ServiceReflector
from vast_coevo.reflection.scope import DomainPolicy
from vast_coevo.schema import atomic_json, digest
from vast_coevo.skills import LibrarySnapshot, StaticSkillGate, apply_patch, empty_snapshot

from experiments.vast_coevo.examples.aftersales_coevo_live import (
    BudgetedClient, CallLedger, _model_spec_for, _role_settings,
)
from experiments.vast_coevo.examples.aftersales_service_skill_ab_v3 import (
    _injection_evidence, _make_config, run_paired_evaluation_v3,
)


PROTOCOL = "aftersales-v3-verified-error-service-reflection-v3-trigger-aware"
SOURCE_RUN = Path("experiments/vast_coevo/results/aftersales-v3-first-pair-live-20261020-001")
PRIOR_REFLECTION_RUN = Path("experiments/vast_coevo/results/aftersales-v3-reflector-pilot-20261020-002")
PRIOR_DIAGNOSTIC_RUN = Path("experiments/vast_coevo/results/aftersales-v3-reflector-pilot-20261020-004")
DEFAULT_OUTPUT = Path("experiments/vast_coevo/results/aftersales-v3-reflector-pilot-20261020-006")
REPO_ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_EXCLUSIONS = SOURCE_RUN / "excluded-training-worlds"
TASK_PLAN = (
    {"seed": 20261046, "profile_id": "profile_u0_order1_line0", "resolution": "refund", "mixed": False},
    {"seed": 20261047, "profile_id": "profile_u0_order0_line0", "resolution": "exchange", "mixed": False},
    {"seed": 20261048, "profile_id": "profile_u0_order1_line0", "resolution": "refund", "mixed": True},
)
REPEATS = 2
CUSTOMER_TURNS = 12
SERVICE_CALLS = 20
SERVICE_TOOL_CALLS = 64
EVALUATION_CALL_BUDGET = 3 * 2 * REPEATS * SERVICE_CALLS


def _read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(root: Path, relative: str, value: Any, *, immutable: bool = True) -> Path:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    path = root / relative
    atomic_json(path, value, immutable=immutable)
    return path


def _native_operation(event: dict) -> dict | None:
    if event.get("kind") != "business":
        return None
    inner = event.get("payload", {}).get("trace", {})
    rows = [row for row in inner.get("events", []) if row.get("kind") == "operation"]
    if len(rows) != 1:
        return None
    return rows[0].get("payload", {}).get("operation")


def _make_source_evidence(root: Path, task_record: CertifiedTask,
                          execution: AgentExecutionV3, s0: LibrarySnapshot) -> tuple[EpisodeEvidence, InteractionEvidenceView]:
    episode_id = "pilot-s0-validation-consumed-as-training"
    trace = execution.trace.model_dump(mode="json")
    trace_path = _write(root, "source/trace.json", trace)
    execution_path = _write(root, "source/execution.json", execution)
    trace_ref = ArtifactRef(path=str(trace_path.relative_to(REPO_ROOT)), sha256=digest(trace))

    service_spec = _model_spec_for(execution.service_model)
    customer_spec = ModelSpec(
        model="local/fixed-compliant-customer-v1",
        base_url="http://127.0.0.1/usami-local-customer",
        options={}, timeout_seconds=60, trust_env=False,
    )
    model_calls = []
    for index, call in enumerate(execution.calls):
        if call.role != "service":
            continue
        record = call.record
        model_calls.append(ModelCall(
            id=f"{episode_id}.service.{index:03d}", role="service", model=service_spec,
            base_request=record.request, request=record.request,
            response=record.response, error=record.error or None,
        ))

    trace_events = {row["id"]: row for row in trace["events"]}
    event_positions = {row["id"]: index for index, row in enumerate(trace["events"])}
    events = []
    for row in execution.oracle.get("operations", []):
        event = trace_events[row["dialogue_event_id"]]
        events.append(VerifiedEvent(
            event_id=row["dialogue_event_id"], operation=row["operation"],
            classification=row["classification"],
            reference_codes=tuple(row.get("violations", [])),
            successful_execution=bool(row.get("success")),
            authorized=row.get("authorized"), operation_correct=row.get("operation_correct"),
            before_hash=event["before_hash"], after_hash=event["after_hash"],
        ))

    failures = []
    for row in execution.oracle.get("operations", []):
        if row.get("classification") != "successful_business_violation":
            continue
        event = trace_events[row["dialogue_event_id"]]
        native = event["payload"]["trace"]
        operation = _native_operation(event)
        if operation is None:
            raise ValueError("Oracle business failure has no unique native Engine operation")
        before = native["initial_state"]
        after = native["final_state"]
        params = operation.get("params", {})
        case_id = params.get("case_id")
        case = before.get("cases", {}).get(case_id) if case_id else None
        quote_id = params.get("quote_id") or (case or {}).get("agreement_quote")
        quote = before.get("quotes", {}).get(quote_id) if quote_id else None
        line_id = (case or {}).get("line_id") or (quote or {}).get("line_id")
        order_id = operation.get("resource_id")
        inner_request = next((row.get("payload", {}).get("request") for row in native.get("events", [])
                              if row.get("kind") == "request"), {})
        customer_event = next((candidate for candidate in reversed(trace["events"][:event_positions[event["id"]]])
                               if candidate["kind"] == "customer" and not candidate["payload"].get("setup")), None)
        grants = list(customer_event["payload"].get("grants", [])) if customer_event else []
        interaction = before.get("interaction", {})
        consents = list(interaction.get("consents", []))
        codes = tuple(sorted(row.get("violations", [])))
        exact_consent = any(consent.get("operation") == operation for consent in consents)
        failures.append(VerifiedFailure(
            episode_id=episode_id, event_id=row["dialogue_event_id"], domain="aftersales",
            operation=row["operation"], reference_codes=codes,
            relevant_prestate={
                "operation": operation,
                "order": before.get("orders", {}).get(order_id),
                "line": before.get("lines", {}).get(line_id) if line_id else None,
                "case": case,
                "quote": quote,
                "interaction": {"revision": interaction.get("revision"),
                                "commitments": interaction.get("commitments", {}),
                                "consents": consents},
            },
            permission_scope={
                "identity": trace["private"]["identity"],
                "customer_turn_id": customer_event["payload"].get("turn_id") if customer_event else None,
                "customer_grants_for_last_turn": grants,
                "operation_exactly_granted": operation in grants,
                "engine_request_granted": inner_request.get("granted"),
                "oracle_authorized": row.get("authorized"),
                "exact_current_consent_exists": exact_consent,
            },
            causal_prerequisites=(
                {"kind": "exact_customer_write_grant", "present": operation in grants},
                {"kind": "exact_current_consent", "present": exact_consent},
            ),
            expected={"reference_allowed": False, "reference_codes": list(codes),
                      "expected_execution": "do not execute this write"},
            actual={"engine_execution_succeeded": bool(row.get("success")),
                    "oracle_operation_correct": row.get("operation_correct"),
                    "before_hash": event["before_hash"], "after_hash": event["after_hash"],
                    "line_status_after": after.get("lines", {}).get(line_id, {}).get("status") if line_id else None,
                    "case_status_after": after.get("cases", {}).get(case_id, {}).get("status") if case_id else None},
            successful_business_violation=True, authorization_only=False,
            trace=trace_ref,
            fingerprint=digest({"domain": "aftersales", "operation": row["operation"], "reference_codes": list(codes)}),
            normalization_scope="pending_causal_normalization",
        ))

    source_world = aftersales.World.model_validate(task_record.frozen.world)
    source_task = task_record.dialogue_witnesses[0].certificate.task
    config = EpisodeConfig(
        id=episode_id, config_id=PROTOCOL, environment="usami-dialogue-v3", domain="aftersales",
        partition="validation", initial_world_hash=task_record.frozen.world_hash,
        identity=execution.trace.private.identity, mode=execution.config.mode,
        customer_model=customer_spec, service_model=service_spec,
        budget=Budget.model_validate(execution.config.budget.model_dump(mode="json")),
        tools=tuple(execution.config.tools),
    )
    evidence = EpisodeEvidence(
        episode_id=episode_id, config=config, track="service_task", task_ref=source_task.task_hash,
        customer_snapshot_hash=empty_snapshot("customer").snapshot_hash,
        service_snapshot_hash=s0.snapshot_hash,
        model_calls=tuple(model_calls), events=tuple(events), failures=tuple(failures),
        consumption=Consumption(customer_llm_calls=0,
            service_llm_calls=len(model_calls), reflection_calls=0,
            tool_calls=len(execution.tools)),
        termination=execution.status, trace=trace_ref, native_trace_hash=execution.trace.trace_hash,
        replay=ReplayResult(verified=True, reason="independent replay_v3 verified before Reflection",
                            request_count=len(model_calls), native_trace_hash=execution.trace.trace_hash),
        task_success=bool(execution.task_score.get("success")),
        legal_task_success=bool(execution.task_score.get("success")),
        goal_satisfied=all(execution.task_score.get("completion_subgoals", [])),
        frame_preserved=execution.task_score.get("frame_preserved"),
    )

    customer_rows = []
    visible = []
    for row in trace["events"]:
        if row["kind"] != "customer" or row["payload"].get("setup"):
            continue
        intent = row["payload"]["intent"]
        declared = list(intent.get("requested_operations", []))
        if intent.get("confirm_operation") is not None:
            declared.append(intent["confirm_operation"])
        customer_rows.append({
            "turn_id": row["payload"]["turn_id"], "message": intent["message"],
            "declared_write_intents": declared,
            "accepted_write_grants": row["payload"].get("grants", []),
            "authorization_source": "native_session_input",
            "source_refs": (f"source/trace.json#/events/{row['id']}/payload",),
        })
        visible.append({"event_id": row["id"], "turn_id": row["payload"]["turn_id"],
                        "message": intent["message"],
                        "source_ref": f"source/trace.json#/events/{row['id']}"})

    selected_tool_calls = {}
    for call in model_calls:
        response = call.response if isinstance(call.response, dict) else {}
        choices = response.get("choices", [])
        for choice in choices if isinstance(choices, list) else []:
            message = choice.get("message", {}) if isinstance(choice, dict) else {}
            for tool in message.get("tool_calls", []) if isinstance(message, dict) else []:
                function = tool.get("function", {}) if isinstance(tool, dict) else {}
                if isinstance(tool, dict) and isinstance(function, dict):
                    selected_tool_calls[tool.get("id")] = function

    business = [(row, _native_operation(row)) for row in trace["events"] if row["kind"] == "business"]
    used_events: set[str] = set()
    tool_rows = []
    for index, item in enumerate(execution.tools):
        selected = selected_tool_calls.get(item["call_id"])
        if not isinstance(selected, dict) or selected.get("name") != item["name"] or selected.get("arguments") != item["arguments"]:
            raise ValueError("archived v3 tool record does not match the Service-selected call")
        try:
            arguments = json.loads(item["arguments"])
        except (TypeError, ValueError):
            arguments = None
        matched = None
        if isinstance(arguments, dict):
            for event, operation in business:
                if event["id"] in used_events or not isinstance(operation, dict):
                    continue
                expected = {key: value for key, value in operation.items() if key != "name"}
                if (operation.get("name") == item["name"] and expected == arguments and
                        event["before_hash"] == item["before_hash"] and
                        event["after_hash"] == item["after_hash"]):
                    matched = event
                    used_events.add(event["id"])
                    break
        matched_position = event_positions[matched["id"]] if matched else len(trace["events"])
        turn_event = next((row for row in reversed(trace["events"][:matched_position])
                           if row["kind"] == "customer" and not row["payload"].get("setup")), None)
        refs = [f"source/execution.json#/tools/{index}"]
        if matched:
            refs.append(f"source/trace.json#/events/{matched['id']}")
        tool_rows.append({
            "call_id": item["call_id"], "name": item["name"], "arguments": item["arguments"],
            "response": item.get("result"),
            "turn_id": turn_event.get("payload", {}).get("turn_id") if turn_event else None,
            "event_id": matched["id"] if matched else None,
            "source_refs": tuple(refs),
        })

    replies = [{"event_id": row["id"], "message": row["payload"].get("message", ""),
                "offer": row["payload"].get("offer"),
                "source_ref": f"source/trace.json#/events/{row['id']}"}
               for row in trace["events"] if row["kind"] == "service"]
    view = native_view(evidence, customer_rows, tool_rows, replies, visible)
    return evidence, view


def _task_record(plan: dict) -> CertifiedTask:
    frozen = freeze(default_spec("aftersales", plan["seed"], partition="validation"))
    world = aftersales.World.model_validate(frozen.world)
    profile_id = plan["profile_id"]
    private = aftersales.private_state(world, profile_id)
    line = world.lines[private.facts["line_id"]]
    terminal = {"refund": "refunded", "exchange": "exchanged", "reship": "reshipped"}[plan["resolution"]]
    goal = Goal(collection="lines", entity=line.id, field="status", accepted_values=[terminal])
    refusal_operations = []
    if plan["mixed"]:
        order = world.orders[line.order_id]
        refusal_operations.append(Operation(
            name="open_case", scope_id=order.merchant_id, resource_id=order.id,
            params={"line_id": line.id, "issue": private.facts["issue"]},
        ).model_dump(mode="json"))
    frames = aftersales_tasks.frame_contract(world, private)
    composition = OpenDialogueComposition(
        protocol="open-dialogue-composition-v2", profile_ids=[profile_id],
        customer_request=(f"I need a {plan['resolution']} for the {private.facts['issue']} item in this order. "
                          f"Please review the case and handle the {plan['resolution']} if it is eligible." +
                          (" If this item is already resolved, do not open a duplicate case." if plan["mixed"] else "")),
        goals=[goal], frames=frames,
        external_schedule=[event.id for event in world.external_events.values() if event.line_id == line.id],
        information_requirements=[InformationRequirement(profile_id=profile_id,
            fact_keys=["order_id", "line_id", "issue", "evidence_id"])],
        preference_requirements=[PreferenceRequirement(profile_id=profile_id,
            preference="resolution", accepted_values=[plan["resolution"]])],
        refusal_operations=refusal_operations,
    )
    selection = TaskSelection(kind="dialogue", family="open_composition_v1",
                              profile_id=profile_id, composition=composition)
    record = compile_task(frozen, selection,
        ConstructionBudget(max_nodes=20000, max_depth=16, max_paths=1))
    verify_task(record)
    return record


def _collect_ids(value: Any) -> set[str]:
    keys = {"id", "order_id", "line_id", "scope_id", "case_id", "quote_id", "return_id", "refund_id", "evidence_id"}
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str):
                found.add(item)
            found.update(_collect_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_ids(item))
    return found


def prepare(root: Path) -> dict:
    root = Path(root).resolve()
    if root.exists():
        if any(root.iterdir()):
            raise FileExistsError("pre-registration is append-only; choose a new result directory")
    else:
        root.mkdir(parents=True)
    source = SOURCE_RUN.resolve()
    source_manifest = _read(source / "manifest.json")
    if source_manifest.get("status") != "EXECUTED" or not source_manifest.get("all_completed_episodes_replay_verified"):
        raise ValueError("pilot source is not a replay-verified completed pair")
    source_episode = source / "episodes/task-01-repeat-01/S0"
    source_task = CertifiedTask.model_validate(_read(source / "tasks/task-01.json"))
    verify_task(source_task)
    execution = AgentExecutionV3.model_validate(_read(source_episode / "execution.json"))
    if execution.execution_hash != execution.computed_hash() or execution.trace.trace_hash != execution.trace.computed_hash():
        raise ValueError("pilot source execution or trace hash mismatch")
    source_world = aftersales.World.model_validate(source_task.frozen.world)
    source_replay = replay_v3(aftersales, execution, world=source_world, config=execution.config)
    if not source_replay.get("verified"):
        raise ValueError("pilot source independent v3 replay failed")
    s0 = LibrarySnapshot.model_validate(_read(source / "snapshots/S0.json"))
    source_context = execution.config.skill_contexts.get("service")
    if (s0.skills or source_context is None or source_context.snapshot_hash != s0.snapshot_hash
            or source_context.rendered or source_context.skill_ids):
        raise ValueError("training source must be a true no-Service-Skill S0 run")
    business_failures = [row for row in execution.oracle.get("operations", [])
                         if row.get("classification") == "successful_business_violation"]
    if len(business_failures) != 1 or business_failures[0].get("operation") != "release_refund" or \
            "EXPLICIT_CONSENT_REQUIRED" not in business_failures[0].get("violations", []):
        raise ValueError("source does not contain the pre-registered consent failure")

    records = [_task_record(plan) for plan in TASK_PLAN]
    if len({row.task_hash for row in records}) != len(records) or \
            len({row.frozen.world_hash for row in records}) != len(records) or \
            len({row.frozen.structure_signature for row in records}) != len(records):
        raise ValueError("pre-registered validation tasks are not independently distinct")
    for record in records:
        if record.frozen.world_hash == source_task.frozen.world_hash or \
                record.frozen.structure_signature == source_task.frozen.structure_signature:
            raise ValueError("validation set reuses the consumed source world")
        world = aftersales.World.model_validate(record.frozen.world)
        scenario = scenario_from_task(aftersales, world, record.task)
        config, _ = _make_config(record, s0, mode="sandbox", turns=CUSTOMER_TURNS,
            service_calls=SERVICE_CALLS, service_tool_calls=SERVICE_TOOL_CALLS,
            customer_mode="deterministic")
        if config.user_scenario != scenario:
            raise ValueError("frozen v3 scenario differs from the task")

    _write(root, "source/pilot-manifest.json", source_manifest)
    _write(root, "source/pilot-task.json", source_task)
    _write(root, "source/pilot-world.json", source_task.frozen)
    _write(root, "snapshots/S0.json", s0)
    _write(root, "snapshots/customer-fixed.json", empty_snapshot("customer"))
    evidence, view = _make_source_evidence(root, source_task, execution, s0)
    _write(root, "evidence/episode.json", evidence)
    _write(root, "evidence/interaction-view.json", view)
    EvidenceArchive(root / "evidence/archive").save(evidence)
    reflection_input = ReflectionInput(
        schema_version=2, generation=1, role="service", library=s0, evidence=(evidence,),
        consumed_validation_evidence_ids=(evidence.episode_id,),
        allowed_tools=tuple(aftersales.TOOLS),
        domain_policy=DomainPolicy(add_domains=("aftersales",)),
        interaction_views=(view,),
        public_policy=json.dumps(aftersales.POLICY, ensure_ascii=False, sort_keys=True),
        boundaries=("This source validation task is consumed as training data and may never be reused in evaluation. "
                    "Only a current exact Customer grant authorizes a write. A settlement such as release_refund "
                    "also requires exact current structured consent to the operation and quote. Do not refuse legal "
                    "operations by default; preserve successful completion and correct refusals."),
    )
    _write(root, "reflection/input.json", reflection_input)

    previous_exclusions = []
    for path in sorted(PREVIOUS_EXCLUSIONS.glob("*.json")):
        frozen = FrozenWorld.model_validate(_read(path)).checked()
        previous_exclusions.append(frozen)
    seen_exclusions = {row.world_hash for row in previous_exclusions}
    for path in sorted((PRIOR_DIAGNOSTIC_RUN / "tasks").glob("*.json")):
        prior_task = CertifiedTask.model_validate(_read(path))
        frozen = FrozenWorld.model_validate(prior_task.frozen.model_dump(mode="json")).checked()
        if frozen.world_hash not in seen_exclusions:
            previous_exclusions.append(frozen)
            seen_exclusions.add(frozen.world_hash)
    all_exclusions = list(previous_exclusions) + [source_task.frozen]
    if len({row.world_hash for row in all_exclusions}) != len(all_exclusions):
        raise ValueError("source world duplicates a pre-existing training exclusion")
    excluded_hashes = {(row.spec.domain, row.world_hash) for row in all_exclusions}
    excluded_structures = {(row.spec.domain, row.structure_signature) for row in all_exclusions}
    for record in records:
        if (record.frozen.spec.domain, record.frozen.world_hash) in excluded_hashes or \
                (record.frozen.spec.domain, record.frozen.structure_signature) in excluded_structures:
            raise ValueError("pre-registered task overlaps a known training world or structure")
    for index, frozen in enumerate(previous_exclusions, 1):
        _write(root, f"excluded-training-worlds/known-{index:02d}-{frozen.world_hash}.json", frozen)
    _write(root, f"excluded-training-worlds/consumed-source-{source_task.frozen.world_hash}.json", source_task.frozen)
    for index, record in enumerate(records, 1):
        _write(root, f"tasks/task-{index:02d}.json", record)
        _write(root, f"worlds/{record.frozen.world_hash}.json", record.frozen)
    settings = _role_settings("service")
    preregistration = {
        "protocol": PROTOCOL, "status": "PRE_REGISTERED",
        "protocol_change": {
            "prior_http_error_attempt": str(PRIOR_REFLECTION_RUN),
            "prior_http_error_status": "REFLECTION_FAILED_HTTP_400",
            "prior_http_error_actual_calls": 1,
            "prior_http_error_body_retained": False,
            "prior_diagnostic_run": str(PRIOR_DIAGNOSTIC_RUN),
            "prior_diagnostic_status": "EXECUTED_BUT_CANDIDATE_SKILL_NOT_RETRIEVED",
            "prior_diagnostic_actual_episodes": 12,
            "prior_diagnostic_replays_verified": True,
            "prior_diagnostic_candidate_skill_injected": False,
            "provider_protocol_fix_already_in_place": "tool_choice=auto remains unchanged from protocol v2",
            "reflection_prompt_change": "explain deterministic SkillRetriever matching; select triggers from user-visible initial text",
            "new_validation_task_seeds": [row["seed"] for row in TASK_PLAN],
            "previous_diagnostic_worlds_excluded": True,
            "official_reference": "https://help.aliyun.com/zh/model-studio/qwen-function-calling",
            "this_is_a_new_preregistered_attempt_not_an_automatic_retry": True,
            "preserved_setup_failure": {
                "run": "experiments/vast_coevo/results/aftersales-v3-reflector-pilot-20261020-003",
                "status": "FAILED_BEFORE_PREREGISTRATION",
                "model_requests_sent": 0,
                "reason": "service model environment variables were absent from the prepare process",
            },
        },
        "source": {"run": str(SOURCE_RUN), "arm": "S0", "episode_id": evidence.episode_id,
            "world_hash": source_task.frozen.world_hash, "structure_signature": source_task.frozen.structure_signature,
            "task_hash": source_task.task_hash, "trace_hash": execution.trace.trace_hash,
            "execution_hash": execution.execution_hash, "oracle_failure": business_failures[0],
            "original_partition": "validation", "now_consumed_as_training": True,
            "source_replay_verified": True},
        "reflection": {"role": "service", "calls_max": 1, "automatic_retries": 0,
            "tool_choice": "auto",
            "model": _model_spec_for(settings).model_dump(mode="json"),
            "input_hash": digest(reflection_input.model_dump(mode="json")),
            "evidence_ids": [evidence.episode_id], "dynamic_gate": "not run; candidate remains diagnostic"},
        "evaluation": {"protocol": "aftersales-service-skill-paired-evaluation-v3-v1",
            "tasks": [{"task_hash": row.task_hash, "world_hash": row.frozen.world_hash,
                       "structure_signature": row.frozen.structure_signature,
                       "profile_id": row.task.profile_id,
                       "identity": row.frozen.world.get("profiles", {}).get(row.task.profile_id, {}).get("identity"),
                       "family": row.task.family,
                       "goal": row.task.goals[0].model_dump(mode="json"),
                       "refusal_count": len(row.task.refusals)} for row in records],
            "known_excluded_world_hashes": [row.world_hash for row in all_exclusions],
            "mode": "sandbox", "customer_mode": "deterministic", "customer_turns": CUSTOMER_TURNS,
            "service_calls_per_episode": SERVICE_CALLS, "service_tools_per_episode": SERVICE_TOOL_CALLS,
            "repeats": REPEATS, "episodes": len(records) * 2 * REPEATS,
            "service_model": _model_spec_for(settings).model_dump(mode="json"),
            "max_service_model_calls": EVALUATION_CALL_BUDGET,
            "skill_injection_must_be_verified_from_each_actual_request": True,
            "all_tasks_frozen_before_reflection": True,
            "no_result_feedback_to_reflector": True},
        "limits": {"reflection_calls": 1, "evaluation_max_model_calls": EVALUATION_CALL_BUDGET,
                   "parallel_workers": 1, "no_online_retry": True},
    }
    _write(root, "preregistration.json", preregistration)
    _write(root, "preparation-status.json", {"status": "READY_FOR_SINGLE_REFLECTION",
        "source_replay": source_replay, "certified_tasks": len(records),
        "all_world_hashes_unique": True, "all_task_certificates_verified": True})
    return preregistration


def reflect(root: Path) -> dict:
    root = Path(root).resolve()
    prereg = _read(root / "preregistration.json")
    if prereg.get("status") != "PRE_REGISTERED":
        raise ValueError("preregistration is missing or already consumed")
    reflection_dir = root / "reflection"
    calls_dir = reflection_dir / "model-calls"
    if calls_dir.exists() and any(calls_dir.glob("*.json")):
        raise RuntimeError("a Reflection request was already registered; automatic retry is forbidden")
    reflection_dir.mkdir(parents=True, exist_ok=True)
    settings = _role_settings("service")
    expected = prereg["reflection"]["model"]
    if _model_spec_for(settings).model_dump(mode="json") != expected:
        raise ValueError("Reflection model configuration differs from frozen preregistration")
    key = key_from_env()
    if not key:
        raise ValueError("LiteLLM credential resolution returned no API key")
    client = OpenAICompatibleClient(settings, key)
    ledger = CallLedger(reflection_dir, limit=1)
    wrapped = BudgetedClient("service_reflection", client, settings, ledger)
    value = ReflectionInput.model_validate(_read(root / "reflection/input.json"))
    tool_choice = prereg["reflection"].get("tool_choice")
    if tool_choice != "auto":
        raise ValueError("this Qwen thinking-mode pilot requires preregistered tool_choice=auto")
    _write(reflection_dir, "started.json", {"status": "IN_FLIGHT", "input_hash": digest(value.model_dump(mode="json")),
        "model": expected, "tool_choice": tool_choice, "retry_policy": "none"})
    try:
        record = ServiceReflector(wrapped, _model_spec_for(settings), tool_choice=tool_choice).reflect(value)
        _write(reflection_dir, "record.json", record)
        usage = {}
        if record.call and isinstance(record.call.response, dict):
            usage = record.call.response.get("usage", {}) or {}
        if record.patch is None:
            result = {"status": "REFLECTION_FAILED", "calls": ledger.actual_calls,
                      "error": record.error, "usage": usage}
            _write(reflection_dir, "status.json", result)
            return result
        _write(reflection_dir, "patch.json", record.patch)
        ids = _collect_ids(_read(root / "source/pilot-world.json"))
        for path in sorted((root / "tasks").glob("*.json")):
            ids.update(_collect_ids(_read(path)))
        static = StaticSkillGate(allowed_tools=aftersales.TOOLS,
            forbidden_identifiers=ids, allowed_domains=("aftersales",)).validate(value.library, record.patch)
        _write(reflection_dir, "static-gate.json", static)
        if not static.passed or record.patch.action == "NOOP":
            result = {"status": "STATIC_REJECTED" if not static.passed else "NOOP",
                      "calls": ledger.actual_calls, "patch_hash": digest(record.patch.model_dump(mode="json")),
                      "reasons": list(static.reasons), "usage": usage}
            _write(reflection_dir, "status.json", result)
            return result
        candidate = apply_patch(value.library, record.patch,
            "real-service-reflector-from-oracle-verified-v3-source")
        _write(root, "snapshots/S1-reflector-candidate.json", candidate)
        result = {"status": "STATIC_ACCEPTED_CANDIDATE", "calls": ledger.actual_calls,
            "patch_hash": digest(record.patch.model_dump(mode="json")),
            "parent_snapshot_hash": value.library.snapshot_hash,
            "candidate_snapshot_hash": candidate.snapshot_hash,
            "selected_formally": False, "dynamic_gate": "not run", "usage": usage,
            "skill_ids": [skill.id for skill in candidate.skills]}
        _write(reflection_dir, "status.json", result)
        return result
    finally:
        client.close()


def _retrieval_preflight(task_paths: list[Path], candidate: LibrarySnapshot) -> dict:
    target_ids = {skill.id for skill in candidate.skills}
    task_rows = []
    for path in sorted(task_paths):
        task_record = CertifiedTask.model_validate(_read(path))
        config, _ = _make_config(task_record, candidate, mode="sandbox", turns=CUSTOMER_TURNS,
            service_calls=SERVICE_CALLS, service_tool_calls=SERVICE_TOOL_CALLS,
            customer_mode="deterministic")
        context = config.skill_contexts.get("service")
        selected = list(context.skill_ids) if context else []
        task_rows.append({"task_hash": task_record.task_hash, "world_hash": task_record.frozen.world_hash,
            "skill_ids_selected": selected, "target_skill_ids_selected": sorted(target_ids & set(selected)),
            "rendered_chars": len(context.rendered) if context else 0})
    return {"status": "PASS" if any(row["target_skill_ids_selected"] for row in task_rows)
        else "FAIL_NO_CANDIDATE_SKILL_RETRIEVED", "candidate_snapshot_hash": candidate.snapshot_hash,
        "candidate_skill_ids": sorted(target_ids), "tasks": task_rows, "paid_evaluation_started": False}


def evaluate(root: Path) -> dict:
    root = Path(root).resolve()
    status = _read(root / "reflection/status.json")
    if status.get("status") != "STATIC_ACCEPTED_CANDIDATE":
        raise ValueError("independent evaluation requires a real Reflector patch accepted by the Static Gate")
    evaluation_dir = root / "evaluation"
    if evaluation_dir.exists():
        raise FileExistsError("evaluation is append-only; refusing to overwrite previous episodes")
    settings = _role_settings("service")
    if _model_spec_for(settings).model_dump(mode="json") != _read(root / "preregistration.json")["evaluation"]["service_model"]:
        raise ValueError("evaluation model configuration differs from preregistration")
    candidate = LibrarySnapshot.model_validate(_read(root / "snapshots/S1-reflector-candidate.json"))
    retrieval_preflight = _retrieval_preflight(sorted((root / "tasks").glob("*.json")), candidate)
    _write(root, "retrieval-preflight.json", retrieval_preflight)
    if retrieval_preflight["status"] != "PASS":
        result = {"status": "NOT_RUN_SKILL_NOT_RETRIEVED", "model_calls": 0,
            "reason": "The candidate Skill does not activate on any preregistered public task context.",
            "retrieval_preflight": retrieval_preflight}
        _write(root, "evaluation-status.json", result)
        return result
    result = run_paired_evaluation_v3(
        evaluation_dir,
        task_paths=sorted((root / "tasks").glob("*.json")),
        exclude_world_paths=sorted((root / "excluded-training-worlds").glob("*.json")),
        s0_path=root / "snapshots/S0.json", s1_path=root / "snapshots/S1-reflector-candidate.json",
        mode="sandbox", customer_mode="deterministic", repeats=REPEATS,
        turns=CUSTOMER_TURNS, service_calls=SERVICE_CALLS,
        service_tool_calls=SERVICE_TOOL_CALLS,
        max_model_calls=EVALUATION_CALL_BUDGET, order_seed=20261020,
    )
    _write(root, "evaluation-launch.json", result)
    return result


def audit(root: Path) -> dict:
    from usami_dialogue.agents_v3 import TaskRunConfigV3

    root = Path(root).resolve()
    eval_root = root / "evaluation"
    manifest = _read(eval_root / "manifest.json")
    rows = []
    total_calls = total_input = total_output = total_authorization_only = 0
    for episode_dir in sorted((eval_root / "episodes").glob("task-*-repeat-*/*")):
        if not episode_dir.is_dir():
            continue
        execution = AgentExecutionV3.model_validate(_read(episode_dir / "execution.json"))
        config = TaskRunConfigV3.model_validate(_read(episode_dir / "config.json"))
        world = aftersales.World.model_validate(execution.trace.initial_world)
        arm_snapshot = LibrarySnapshot.model_validate(_read(eval_root / "snapshots" / f"{episode_dir.name}.json"))
        replay = replay_v3(aftersales, execution, world=world, config=config)
        stored = _read(episode_dir / "replay.json")
        if not replay.get("verified") or replay != stored:
            raise ValueError(f"independent Replay mismatch in {episode_dir}")
        summary = _read(episode_dir / "summary.json")
        injection = _injection_evidence(execution, [skill.id for skill in arm_snapshot.skills])
        operation_rows = execution.oracle.get("operations", [])
        violation_codes = sorted({code for operation in operation_rows
            if operation.get("classification") == "successful_business_violation"
            for code in operation.get("violations", [])})
        authorization_only = sum(operation.get("classification") == "authorization_only"
            for operation in operation_rows)
        total_authorization_only += authorization_only
        cost = summary.get("cost", {})
        calls = cost.get("service_calls", 0)
        input_tokens = cost.get("input_tokens", 0)
        output_tokens = cost.get("output_tokens", 0)
        total_calls += calls
        total_input += input_tokens
        total_output += output_tokens
        rows.append({"episode": str(episode_dir.relative_to(root)), "replay_verified": True,
            "snapshot_hash": summary.get("service_skill_injection", {}).get("snapshot_hash"),
            "available_skill_ids": injection["available_skill_ids"],
            "selected_skill_ids": injection["selected_skill_ids"],
            "candidate_skill_injected": injection["candidate_skill_injected"],
            "skill_injection_status": injection["skill_injection_status"],
            "all_service_requests_contained_skill": injection["all_service_requests_contained_skill"],
            "execution_status": execution.status,
            "success": summary.get("task_success"), "final_goal_reached": summary.get("final_goal_reached"),
            "successful_business_violations": summary.get("successful_business_violations"),
            "authorization_only": authorization_only,
            "business_violation_codes": violation_codes,
            "false_rejections": summary.get("false_rejections"), "service_calls": calls,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "trace_hash": execution.trace.trace_hash, "execution_hash": execution.execution_hash})
    expected = 3 * 2 * REPEATS
    if len(rows) != expected:
        raise ValueError(f"expected {expected} evaluation episodes, found {len(rows)}")
    s0 = [row for row in rows if "/S0" in row["episode"]]
    s1 = [row for row in rows if "/S1" in row["episode"]]
    def group_summary(group_rows):
        return {"episodes": len(group_rows),
            "strict_successes": sum(bool(x["success"]) for x in group_rows),
            "final_goals": sum(bool(x["final_goal_reached"]) for x in group_rows),
            "violations": sum(x["successful_business_violations"] for x in group_rows),
            "authorization_only": sum(x["authorization_only"] for x in group_rows),
            "false_rejections": sum(x["false_rejections"] for x in group_rows),
            "protocol_error_episodes": sum(x["execution_status"] == "service_protocol_error" for x in group_rows),
            "budget_exhausted_episodes": sum("budget_exhausted" in x["execution_status"] for x in group_rows),
            "distinct_business_violation_codes": sorted({code for x in group_rows
                for code in x["business_violation_codes"]}),
            "candidate_skill_injected_episodes": sum(bool(x["candidate_skill_injected"]) for x in group_rows)}

    audit_result = {"protocol": "independent-v3-reflector-evaluation-replay-v2",
        "episodes": len(rows), "all_replay_verified": True,
        "s1_candidate_skill_injected_episodes": sum(bool(row["candidate_skill_injected"]) for row in s1),
        "authorization_only_events": total_authorization_only,
        "runner_status": manifest.get("status"), "model_calls": total_calls,
        "input_tokens": total_input, "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "S0": group_summary(s0),
        "S1": group_summary(s1),
        "rows": rows}
    _write(root, "postrun-replay-audit-v2.json", audit_result)
    return audit_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "reflect", "evaluate", "audit"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.phase == "prepare":
        result = prepare(args.output)
    elif args.phase == "reflect":
        result = reflect(args.output)
    elif args.phase == "evaluate":
        result = evaluate(args.output)
    else:
        result = audit(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
