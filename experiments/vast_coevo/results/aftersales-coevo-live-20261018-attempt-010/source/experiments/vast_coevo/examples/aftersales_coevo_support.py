"""Shared native evidence and initial-library helpers for After-sales runs."""
from __future__ import annotations

import json
from pathlib import Path

from usami_aftersales import adapter as aftersales
from vast_coevo.evidence import EvidenceArchive
from vast_coevo.models import (
    ArtifactRef, Budget as EvidenceBudget, Consumption, EpisodeConfig, InjectionRecord,
    EpisodeEvidence, ModelCall, ModelSpec, ReplayResult, TaskDecision, VerifiedEvent,
)
from vast_coevo.schema import digest
from vast_coevo.skills import (
    DecisionSkill, DesignerSkill, LibrarySnapshot, Scope, SkillHit, Trigger, empty_snapshot,
)


def initial_skill_libraries(*, designer_provenance="aftersales-initial-designer-v1",
                            service_provenance="aftersales-initial-service-v1"):
    designer = LibrarySnapshot(role="designer", skills=(DesignerSkill(
        id="aftersales.discovery", version=1,
        scope=Scope(domains=("aftersales",)), trigger=Trigger(keywords=("order", "refund", "challenge")),
        description="Select grounded after-sales challenges from the frozen catalog.",
        selection=("Choose a customer profile and business objects that exist in the frozen catalog.",),
        transformations=("Vary one legitimate objective or business condition at a time.",),
        interpretation=("Keep verified outcomes separate from untested hypotheses.",),
        stop=("Stop when the construction budget or frozen scope is reached.",),
    ),), provenance=designer_provenance)
    service = LibrarySnapshot(role="service", skills=(DecisionSkill(
        id="aftersales.service-decision", version=1,
        scope=Scope(domains=("aftersales",), tools=tuple(aftersales.TOOLS)),
        trigger=Trigger(keywords=("order", "refund", "exchange", "reship"),
                        intents=("refund order resolution", "after-sales request")),
        description="General after-sales decision guidance.",
        preconditions=("Use the current authenticated customer request and ordinary business records.",),
        procedure=("Obtain required information and customer choice before a settlement.",),
        postconditions=("Report only the outcome returned by the business tools.",),
        recovery=("If a response is uncertain, inspect current records and explain the next required step.",),
    ),), provenance=service_provenance)
    return designer, service, empty_snapshot("customer")


def model_spec(settings):
    return ModelSpec(model=settings.model, base_url=settings.base_url, options=settings.options,
                     timeout_seconds=settings.timeout_seconds, trust_env=settings.trust_env)


def event_and_decision_evidence(root, task_row, customer_snapshot, service_snapshot,
                                *, customer_model=None, service_model=None,
                                config_id="aftersales-smoke-task-v1"):
    """Bind actual agent calls, native decisions, Skill injection and Replay as evidence."""
    execution = task_row["execution"]
    trace = execution.trace
    task_id = f"task-{task_row['task_number']}"
    trace_path = Path(task_row["trace_path"])
    trace_hash = digest(trace.model_dump(mode="json"))
    archive = EvidenceArchive(Path(root) / "evidence")
    calls, call_ids = [], {}
    for index, row in enumerate(execution.calls):
        model = execution.customer_model if row.role == "customer" else execution.service_model
        call_id = f"{task_id}.call.{index:03d}"
        call_ids[index] = call_id
        calls.append(ModelCall(id=call_id, role=row.role, model=model_spec(model),
            base_request=row.record.request, request=row.record.request, response=row.record.response,
            error=row.record.error or None))

    evidence_events = []
    decisions = {row["event_id"]: row for row in execution.oracle.get("service_decisions", [])}
    operations = {row["dialogue_event_id"]: row for row in execution.oracle.get("operations", [])}
    task_decisions, previous_customer_turn = [], "turn_0"
    for event in trace.events:
        if event.kind == "customer" and not event.payload.get("setup"):
            previous_customer_turn = event.payload["turn_id"]
            continue
        if event.kind == "service" and event.id in decisions:
            row = decisions[event.id]
            classification = row["classification"]
            evidence_events.append(VerifiedEvent(
                event_id=event.id, operation=row["operation"].get("name", "service_refusal"),
                classification="false_rejection" if classification == "false_rejection" else "unscored",
                reference_codes=tuple([row["reference_code"]] if row.get("reference_code") else ["FALSE_REJECTION"]),
                successful_execution=False, authorized=classification != "unattributed_refusal",
                operation_correct=False if classification in {"false_rejection", "incorrect_refusal_reason"} else True,
                before_hash=event.before_hash, after_hash=event.after_hash))
            if classification == "false_rejection":
                refused = event.payload.get("refused_operation")
                matched_call = None
                for index, call_row in enumerate(execution.calls):
                    if call_row.role != "service" or not isinstance(call_row.record.response, dict):
                        continue
                    for choice in call_row.record.response.get("choices", []):
                        for tool_call in choice.get("message", {}).get("tool_calls", []):
                            if tool_call.get("function", {}).get("name") != "respond_to_customer":
                                continue
                            args = json.loads(tool_call["function"]["arguments"])
                            if args.get("refused_operation") == refused:
                                matched_call = (index, call_row.record.response)
                                break
                if matched_call is None:
                    raise ValueError("Oracle false rejection cannot be linked to its actual model response")
                index, response = matched_call
                task_decisions.append(TaskDecision(operation=refused, before_hash=event.before_hash,
                    claimed_code=event.payload["refusal_code"], model_call_id=call_ids[index],
                    response_hash=digest(response), turn_id=previous_customer_turn))
        elif event.kind == "business" and event.id in operations:
            row = operations[event.id]
            evidence_events.append(VerifiedEvent(
                event_id=event.id, operation=row["operation"], classification=row["classification"],
                reference_codes=tuple(row["violations"]), successful_execution=bool(row["success"]),
                authorized=row["authorized"], operation_correct=row["operation_correct"],
                before_hash=event.before_hash, after_hash=event.after_hash))

    injection = execution.config.skill_contexts["service"]
    service_hits = tuple(SkillHit(id=skill.id, version=skill.version, content_hash=skill.content_hash)
                         for skill in service_snapshot.skills if skill.id in injection.skill_ids)
    injections = tuple(InjectionRecord(
        call_id=call_ids[index], role="service", snapshot_hash=service_snapshot.snapshot_hash,
        context_hash=injection.context_hash, hits=service_hits, rendered=injection.rendered,
        request_hash=calls[index].request_hash)
        for index, row in enumerate(execution.calls) if row.role == "service")
    episode_config = EpisodeConfig(
        id=task_id, config_id=config_id, domain="aftersales", partition="development",
        initial_world_hash=task_row["task_record"].frozen.world_hash,
        identity=trace.private.identity, mode="reference",
        customer_model=customer_model or model_spec(execution.customer_model),
        service_model=service_model or model_spec(execution.service_model),
        budget=EvidenceBudget(**execution.config.budget.model_dump()), tools=tuple(execution.config.tools))
    evidence = EpisodeEvidence(
        episode_id=task_id, config=episode_config, track="service_task",
        task_ref=task_row["task_record"].task_hash,
        customer_snapshot_hash=customer_snapshot.snapshot_hash,
        service_snapshot_hash=service_snapshot.snapshot_hash,
        model_calls=tuple(calls), injections=injections, events=tuple(evidence_events),
        task_decisions=tuple(task_decisions) if task_decisions else None,
        consumption=Consumption(customer_llm_calls=execution.cost["customer_calls"],
            service_llm_calls=execution.cost["service_calls"], reflection_calls=0,
            tool_calls=execution.cost["tool_calls"]), termination=execution.status,
        trace=ArtifactRef(path=str(trace_path.resolve()), sha256=trace_hash), native_trace_hash=trace.trace_hash,
        replay=ReplayResult(verified=task_row["agent_replay"]["verified"],
            request_count=task_row["agent_replay"]["model_calls"], native_trace_hash=trace.trace_hash),
        task_success=bool(task_row["score"]["success"]), legal_task_success=bool(task_row["score"]["success"]),
        goal_satisfied=task_row["final_goal_reached"], frame_preserved=task_row["score"].get("frame_preserved"))
    return evidence, archive.save(evidence)
