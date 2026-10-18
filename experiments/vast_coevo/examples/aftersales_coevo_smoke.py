"""Three-Service-task After-sales coevolution plumbing smoke.

This is a deterministic integration check, not an LLM performance experiment.
Every interaction still passes through the native DialogueSession, Engine,
Reference, Oracle, task compiler, SkillPatch, StaticSkillGate and Replay.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any

from usami.service.models import ModelSettings
from usami_aftersales import adapter as aftersales
from usami_aftersales import tasks as aftersales_tasks
from usami_aftersales.models import Operation
from usami_aftersales.rules import case_key, quote_key
from usami_benchmark.designer import DesignerExecution, design_and_compile, verify_designer_execution
from usami_benchmark.registry import default_spec
from usami_benchmark.tasks import (
    ConstructionBudget, OpenDialogueComposition, TaskSelection, compile_task, verify_task,
)
from usami_benchmark.worlds import FrozenWorld, freeze
from usami_dialogue.agents import (
    AgentExecution, SkillPromptContext, TaskRunConfig, replay as replay_execution, run,
)
from usami_dialogue.tasks import Goal, InformationRequirement, PreferenceRequirement, score
from usami_harness.models import Budget, digest
from vast_coevo.designer.reflection import reflect as reflect_designer
from vast_coevo.models import ModelSpec
from vast_coevo.reflection.reflector import ReflectionInput, ServiceReflector
from vast_coevo.reflection.scope import DomainPolicy
from vast_coevo.schema import atomic_json
from vast_coevo.skills import (
    LibrarySnapshot, LibraryStore, SkillPatch, SkillRenderer, SkillRetriever,
    StaticSkillGate, apply_patch,
)


from experiments.vast_coevo.examples.aftersales_coevo_support import (
    event_and_decision_evidence as _event_and_decision_evidence,
    initial_skill_libraries,
)


def _skill_libraries():
    return initial_skill_libraries(
        designer_provenance="smoke-initial-designer-v1",
        service_provenance="smoke-initial-service-v1")


PROTOCOL = "aftersales-three-task-coevo-smoke-v1"
MODEL = ModelSpec(model="scripted-agent-fixture-v1", base_url="https://fixture.invalid/v1",
                  options={"temperature": 0})
CUSTOMER_MODEL = ModelSpec(model="scripted-customer-fixture-v1", base_url="https://fixture.invalid/v1",
                           options={"temperature": 0})
REFLECTOR_MODEL = ModelSpec(model="scripted-reflector-fixture-v1", base_url="https://fixture.invalid/v1",
                            options={"temperature": 0})
MODEL_SETTINGS = ModelSettings(model=MODEL.model, base_url=MODEL.base_url, options=MODEL.options)
CUSTOMER_SETTINGS = ModelSettings(model=CUSTOMER_MODEL.model, base_url=CUSTOMER_MODEL.base_url,
                                  options=CUSTOMER_MODEL.options)
DESIGNER_SETTINGS = ModelSettings(model="scripted-designer-fixture-v1", base_url=MODEL.base_url,
                                  options={"temperature": 0})
PRIMARY_PROFILE = "profile_u1_order0_line1"
COMPOSED_PROFILES = ("profile_u1_order0_line1", "profile_u1_order1_line0")
SERVICE_RECOVERY_SENTENCE = (
    "Before refusing an after-sales request, inspect the live order and case, verify the bound evidence and current "
    "eligibility, then continue when the native checks support the requested resolution."
)
DESIGNER_COMPOSITION_SENTENCE = (
    "For a useful challenge, combine distinct orders of one authenticated customer while keeping each order's facts "
    "and chosen remedy separately bound."
)


def _write(root: Path, relative: str, value: Any, *, immutable=True):
    path = root / relative
    atomic_json(path, value.model_dump(mode="json") if hasattr(value, "model_dump") else value,
                immutable=immutable)
    return path


def _write_append_only_attempt(root: Path, relative: str, value: Any):
    """Preserve earlier failed attempts while reusing byte-identical artifacts."""
    data = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    base = Path(relative)
    attempt = 1
    while True:
        candidate = base if attempt == 1 else base.with_name(
            f"{base.stem}_attempt_{attempt}{base.suffix}"
        )
        path = root / candidate
        if not path.exists():
            atomic_json(path, data, immutable=True)
            return path
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = None
        if previous == data:
            return path
        attempt += 1


def _call(call_id: str, name: str, args: dict) -> dict:
    return {"id": call_id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))}}


def _answer(*, calls=(), content=None, usage=None):
    result = {"choices": [{"finish_reason": "tool_calls" if calls else "stop",
                           "message": {"role": "assistant", "content": content,
                                       "tool_calls": list(calls)}}]}
    if usage is not None:
        result["usage"] = usage
    return result


def _operation_call(operation: Operation, call_id: str):
    return _call(call_id, operation.name, {
        "scope_id": operation.scope_id, "resource_id": operation.resource_id,
        "params": operation.params,
    })


class ScriptedClient:
    """Offline model endpoint: immutable requests, deterministic handlers."""
    def __init__(self, settings: ModelSettings, handler):
        self.settings = settings
        self.handler = handler
        self.requests = []

    def complete(self, request):
        row = copy.deepcopy(request)
        self.requests.append(row)
        return copy.deepcopy(self.handler(row))





def _single_task(frozen: FrozenWorld):
    selection = TaskSelection(kind="dialogue", family="dispute_resolution",
                              profile_id=PRIMARY_PROFILE, parameters={"resolutions": ["refund"]})
    record = compile_task(frozen, selection, ConstructionBudget(max_nodes=2048, max_depth=16, max_paths=1))
    if not verify_task(record):
        raise ValueError("native Reference could not certify Task 1 refund objective")
    return record


def _composition_selection(world, resolutions):
    frames, seen, goals, prefs, information, external = [], set(), [], [], [], []
    for profile_id, resolution in zip(COMPOSED_PROFILES, resolutions):
        private = world.profiles[profile_id]
        line = world.lines[private.facts["line_id"]]
        for frame in aftersales_tasks.frame_contract(world, private):
            key = digest(frame)
            if key not in seen:
                seen.add(key)
                frames.append(frame)
        goals.append(Goal(collection="lines", entity=line.id, field="status",
                          accepted_values=["refunded", "exchanged", "reshipped"]))
        prefs.append(PreferenceRequirement(profile_id=profile_id, preference="resolution",
                                           accepted_values=[resolution]))
        information.append(InformationRequirement(profile_id=profile_id, fact_keys=["line_id", "issue"]))
        external.extend(event.id for event in world.external_events.values() if event.line_id == line.id)
    composition = OpenDialogueComposition(
        profile_ids=list(COMPOSED_PROFILES),
        customer_request=("Resolve the actual issue on each of these two purchases separately. Use each order's own "
                          "facts and its selected remedy; do not transfer details between orders."),
        goals=goals, frames=frames, external_schedule=external,
        information_requirements=information, preference_requirements=prefs,
    )
    return TaskSelection(kind="dialogue", family="open_composition_v1", profile_id=COMPOSED_PROFILES[0],
                         composition=composition)


def _task_selection(frozen, resolutions):
    world = aftersales.World.model_validate(frozen.world)
    record = compile_task(frozen, _composition_selection(world, resolutions),
                          ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1))
    if not verify_task(record):
        raise ValueError("native Reference did not certify the two-order composition")
    return record


def _designer_response(selection):
    return _answer(calls=[_call("designer-task-selection", "submit_frozen_world_task",
                                 selection.model_dump(mode="json"))])


class TaskDesignerClient(ScriptedClient):
    def __init__(self, selection, *, expected_skill_hash, expected_version, expected_evidence_ids):
        self.selection = selection
        self.expected_skill_hash = expected_skill_hash
        self.expected_version = expected_version
        self.expected_evidence_ids = tuple(expected_evidence_ids)
        self.context_verified = False
        super().__init__(DESIGNER_SETTINGS, self._respond)

    def _respond(self, request):
        messages = request["messages"]
        system = messages[0]["content"]
        assert self.expected_skill_hash in system
        assert f'version="{self.expected_version}"' in system
        if self.expected_version == 2:
            assert DESIGNER_COMPOSITION_SENTENCE in system
        evidence_text = "\n".join(row["content"] for row in messages[1:] if row["role"] == "user")
        assert all(episode_id in evidence_text for episode_id in self.expected_evidence_ids)
        assert "process_errors" in evidence_text and "hypothesis" in evidence_text
        composition = self.selection.composition
        assert composition is not None and len(composition.profile_ids) == 2
        self.context_verified = True
        return _designer_response(self.selection)


def _private_operations(world, profile_id, resolution, quote_revision):
    private = aftersales.private_state(world, profile_id)
    line = world.lines[private.facts["line_id"]]
    order = world.orders[line.order_id]
    case_id = case_key(order.id, line.id, private.facts["issue"])
    opening = Operation(name="open_case", scope_id=order.merchant_id, resource_id=order.id,
                        params={"line_id": line.id, "issue": private.facts["issue"]})
    verify = Operation(name="verify_evidence", scope_id=order.merchant_id, resource_id=order.id,
                       params={"case_id": case_id, "evidence_id": private.facts["evidence_id"]})
    quote = Operation(name="quote_resolution", scope_id=order.merchant_id, resource_id=order.id,
                      params={"case_id": case_id, "option": resolution})
    quote_id = quote_key(case_id, resolution, quote_revision)
    commit = Operation(name="commit_resolution", scope_id=order.merchant_id, resource_id=order.id,
                       params={"quote_id": quote_id, "destination_channel": order.payment_channel})
    return {"profile_id": profile_id, "resolution": resolution, "private": private, "order": order, "line": line,
            "opening": opening, "verify": verify, "quote": quote, "commit": commit}


def _customer_intent(message, *, operations=(), preferences=None, disclosures=None, confirm=None, finish=False):
    body = {"message": message, "requested_operations": [op.model_dump(mode="json") for op in operations],
            "preferences": preferences or {}, "disclosures": disclosures or {}, "finish": finish}
    if confirm is not None:
        body["confirm_operation"] = confirm.model_dump(mode="json")
    return _answer(calls=[_call("customer-turn", "submit_customer_turn", body)])


def _task_customer_client(task_number, world, resolutions):
    plan = []
    if task_number == 1:
        p = _private_operations(world, PRIMARY_PROFILE, "refund", quote_revision=1)
        plan.extend([
            _customer_intent("Please refund this delivered item; the item and issue are in my request.",
                             operations=[p["opening"]], preferences={"resolution": "refund"}),
            _customer_intent("Please review my refund request again using the same order details.",
                             operations=[p["opening"]], preferences={"resolution": "refund"}),
            _customer_intent("I can provide the evidence; please verify it and quote the refund.",
                             operations=[p["verify"], p["quote"]], preferences={"resolution": "refund"},
                             disclosures={"deadline": p["private"].facts["deadline"]}),
            _customer_intent("I confirm the actual refund quote.", confirm=p["commit"]),
        ])
    else:
        profile_rows = [_private_operations(world, profile, resolution, quote_revision=1 + index)
                        for index, (profile, resolution) in enumerate(zip(COMPOSED_PROFILES, resolutions))]
        for item in profile_rows:
            plan.extend([
                _customer_intent("Please resolve this order's reported issue.", operations=[item["opening"]],
                                 preferences={"resolution": item["resolution"]}),
                _customer_intent("Here is the evidence; verify it and quote my chosen remedy.",
                                 operations=[item["verify"], item["quote"]],
                                 preferences={"resolution": item["resolution"]},
                                 disclosures={key: item["private"].facts[key]
                                              for key in ("line_id", "issue", "deadline")}),
                _customer_intent("I confirm the actual quote for this order.", confirm=item["commit"]),
            ])
    plan.append(_customer_intent("The requested business work is complete.", finish=True))
    cursor = {"index": 0}

    def respond(_request):
        index = cursor["index"]
        if index >= len(plan):
            raise AssertionError("scripted Customer exceeded its registered turns")
        cursor["index"] += 1
        return plan[index]

    client = ScriptedClient(CUSTOMER_SETTINGS, respond)
    client.plan = plan
    return client


def _parse_latest_grants(messages):
    prefix = "Customer-declared exact write intentions: "
    for message in reversed(messages):
        content = message.get("content")
        if message.get("role") == "user" and isinstance(content, str) and prefix in content:
            return json.loads(content.rsplit(prefix, 1)[1])
    return []


def _current_turn_tool_calls(messages):
    prefix = "Customer-declared exact write intentions: "
    start = max((i for i, m in enumerate(messages)
                 if m.get("role") == "user" and isinstance(m.get("content"), str) and prefix in m["content"]),
                default=-1)
    names = []
    for message in messages[start + 1:]:
        if message.get("role") == "assistant":
            names.extend(call.get("function", {}).get("name") for call in message.get("tool_calls", []))
    return [name for name in names if name]


def _tool_response_data(messages, operation_name):
    wanted_call = None
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls", []):
                if call.get("function", {}).get("name") == operation_name:
                    wanted_call = call.get("id")
    if wanted_call is None:
        return None
    for message in messages:
        if message.get("role") == "tool" and message.get("tool_call_id") == wanted_call:
            content = json.loads(message.get("content", "{}"))
            return content.get("data", {})
    return None


class ServiceScriptClient(ScriptedClient):
    """Uses only the actual Customer grant, native tool results and injected Skill."""
    def __init__(self, *, task_number, updated_skill_expected=False, force_seed_error=False):
        self.task_number = task_number
        self.updated_skill_expected = updated_skill_expected
        self.force_seed_error = force_seed_error
        self.seed_error_emitted = False
        self.query_before_open = False
        self.counter = 0
        self.skill_context_verified = False
        super().__init__(MODEL_SETTINGS, self._respond)

    def _id(self, stem):
        self.counter += 1
        return f"svc-{self.task_number}-{self.counter}-{stem}"

    def _respond(self, request):
        messages = request["messages"]
        system = messages[0]["content"]
        if self.updated_skill_expected:
            if SERVICE_RECOVERY_SENTENCE not in system:
                raise AssertionError("Task 3 Service Skill text was not injected")
            self.query_before_open = True
            self.skill_context_verified = True
        grants = [Operation.model_validate(raw) for raw in _parse_latest_grants(messages)]
        names = _current_turn_tool_calls(messages)
        if not grants:
            return _answer(content="The requested work is complete.")
        op_names = {op.name for op in grants}
        if op_names == {"open_case"}:
            op = grants[0]
            if self.force_seed_error and not self.seed_error_emitted:
                self.seed_error_emitted = True
                return _answer(calls=[_call(self._id("false-rejection"), "respond_to_customer", {
                    "message": "I cannot open this case under the current policy; I will review your request again.",
                    "offered_operation": None, "refused_operation": op.model_dump(mode="json"),
                    "refusal_code": "TEMPORARY_REVIEW_REQUIRED"})])
            if self.query_before_open and "get_order" not in names:
                query = Operation(name="get_order", scope_id=op.scope_id, resource_id=op.resource_id, params={})
                return _answer(calls=[_operation_call(query, self._id("preflight-order"))])
            if "open_case" not in names:
                return _answer(calls=[_operation_call(op, self._id("open-case"))])
            return _answer(calls=[_call(self._id("opened-reply"), "respond_to_customer", {
                "message": "The case has been opened against the selected order and item.",
                "offered_operation": None})])
        if op_names == {"verify_evidence", "quote_resolution"}:
            if "verify_evidence" not in names and "quote_resolution" not in names:
                ordered = sorted(grants, key=lambda op: (op.name != "verify_evidence", op.name))
                return _answer(calls=[_operation_call(op, self._id(op.name)) for op in ordered])
            if "get_order" not in names:
                quoted = next(op for op in grants if op.name == "quote_resolution")
                query = Operation(name="get_order", scope_id=quoted.scope_id,
                                  resource_id=quoted.resource_id, params={})
                return _answer(calls=[_operation_call(query, self._id("order-channel"))])
            quote_data = _tool_response_data(messages, "quote_resolution") or {}
            quote = quote_data.get("quote", {})
            order = _tool_response_data(messages, "get_order") or {}
            if not quote.get("id") or not order.get("payment_channel"):
                raise AssertionError("native quote/order tool results lack offer terms")
            operation = Operation(name="commit_resolution", scope_id=grants[0].scope_id,
                                  resource_id=grants[0].resource_id,
                                  params={"quote_id": quote["id"], "destination_channel": order["payment_channel"]})
            return _answer(calls=[_call(self._id("present-quote"), "respond_to_customer", {
                "message": "These are the actual terms returned for this order. Do you confirm?",
                "offered_operation": operation.model_dump(mode="json")})])
        if op_names == {"commit_resolution"}:
            op = grants[0]
            if "commit_resolution" not in names:
                return _answer(calls=[_operation_call(op, self._id("settle"))])
            return _answer(calls=[_call(self._id("settled-reply"), "respond_to_customer", {
                "message": "The selected remedy has been completed by the business system.",
                "offered_operation": None})])
        raise AssertionError("unexpected exact Customer grants: " + repr(sorted(op_names)))


def _task_config(frozen, task_record, profile_id, skill_snapshot):
    witness = task_record.dialogue_witnesses[0]
    task = witness.certificate.task
    prompt_text = task.composition.customer_request if task.composition else aftersales_tasks.customer_task_brief(
        aftersales.World.model_validate(frozen.world),
        aftersales.private_state(aftersales.World.model_validate(frozen.world), profile_id), task)
    retrieval = SkillRetriever("service").retrieve(skill_snapshot, SkillContext(
            domain="aftersales", public_text=prompt_text, intents=("refund order resolution", "after-sales request"),
            available_tools=tuple(aftersales.TOOLS)))
    rendered = SkillRenderer().render(retrieval.skills)
    if len(retrieval.hits) != 1 or not rendered:
        raise ValueError("registered Service Skill was not selected for the after-sales task")
    context = SkillPromptContext(snapshot_hash=skill_snapshot.snapshot_hash,
                                 skill_ids=[hit.id for hit in retrieval.hits], rendered=rendered)
    return TaskRunConfig(
        profile_id=profile_id, initial_world_hash=frozen.world_hash, mode="reference",
        tools=list(aftersales.TOOLS), budget=Budget(max_customer_turns=10, max_customer_llm_calls=10,
            max_service_llm_calls=32, max_service_tool_calls=20, max_format_recoveries=0),
        external_schedule=task.external_schedule, task=task,
        certificate=witness.certificate, witness=witness.trace,
        skill_contexts={"service": context},
    )


def _run_service_task(root, number, frozen, task_record, profile_id, resolutions, service_snapshot,
                      *, force_seed_error=False, updated_skill_expected=False):
    world = aftersales.World.model_validate(frozen.world)
    config = _task_config(frozen, task_record, profile_id, service_snapshot)
    customer = _task_customer_client(number, world, resolutions)
    service = ServiceScriptClient(task_number=number, updated_skill_expected=updated_skill_expected,
                                  force_seed_error=force_seed_error)
    execution = run(aftersales, world, config, customer, service)
    if len(execution.calls) == 0 or len(execution.config.skill_contexts) != 1:
        raise AssertionError("actual Service execution lacks recorded model context")
    first_service = next(row for row in execution.calls if row.role == "service")
    service_system = first_service.record.request["messages"][0]["content"]
    context = config.skill_contexts["service"]
    if context.rendered not in service_system or context.snapshot_hash != service_snapshot.snapshot_hash:
        raise AssertionError("Service Skill was recorded but not present in its actual request")
    if updated_skill_expected and not service.skill_context_verified:
        raise AssertionError("Task 3 did not consume the updated Service Skill")
    actual_score = score(aftersales, world, task_record.dialogue_witnesses[0].certificate.task,
                         execution.trace)
    final_world = aftersales.World.model_validate(execution.trace.final_world)
    goals = task_record.dialogue_witnesses[0].certificate.task.goals
    final_goal_reached = all(goal.satisfied(final_world) for goal in goals)
    process_errors = [row for row in execution.oracle.get("service_decisions", [])
                      if row.get("classification") in {"false_rejection", "incorrect_refusal_reason"}]
    # Preserve the complete actual run immediately, including failed smokes.
    trace_path = _write(root, f"tasks/task-{number}/trace.json", execution.trace)
    execution_path = _write(root, f"tasks/task-{number}/execution.json", execution)
    task_path = _write(root, f"tasks/task-{number}/certified_task.json", task_record)
    if number == 1:
        if not final_goal_reached or not process_errors or actual_score["success"]:
            raise AssertionError("Task 1 outcome mismatch: " + json.dumps({
                "status": execution.status, "final_goal_reached": final_goal_reached,
                "process_errors": process_errors, "strict_score": actual_score,
                "oracle": execution.oracle, "errors": execution.errors,
                "tools": execution.tools}, ensure_ascii=False, sort_keys=True))
    elif not actual_score["success"]:
        raise AssertionError(f"Task {number} failed its independent native task score: {actual_score}")
    agent_replay = replay_execution(aftersales, execution, world=world, config=config)
    _write(root, f"tasks/task-{number}/score.json", {
        "protocol": "aftersales-task-outcome-v1", "final_goal_reached": final_goal_reached,
        "process_errors": process_errors, "task_success": bool(actual_score["success"]),
        "strict_score": actual_score, "oracle": execution.oracle,
        "task_certificate_hash": task_record.dialogue_witnesses[0].certificate.certificate_hash,
        "agent_replay": agent_replay,
    })
    return {
        "task_number": number, "execution": execution, "task_record": task_record,
        "score": actual_score, "final_goal_reached": final_goal_reached,
        "process_errors": process_errors, "agent_replay": agent_replay,
        "trace_path": str(trace_path.resolve()), "execution_path": str(execution_path.resolve()),
        "task_path": str(task_path.resolve()), "service_client": service,
        "customer_client": customer,
    }








def _designer_patch_client(parent: LibrarySnapshot, evidence_ids):
    version = parent.skills[0].version + 1
    raw_skill = {
        "type": "design", "id": "aftersales.discovery", "version": version,
        "scope": {"domains": ["aftersales"], "tools": []},
        "trigger": {"keywords": ["order", "refund", "challenge"], "intents": ["multi-order test"]},
        "description": "Use verified process-decision evidence to design a distinct, legal follow-up challenge.",
        "selection": ["Select only existing customer profiles and orders from the frozen registration."],
        "transformations": [DESIGNER_COMPOSITION_SENTENCE,
                            "Change the selected remedy between probes without merging profile facts."],
        "interpretation": ["Treat an Oracle-linked decision error as evidence and keep unrelated outcomes separate."],
        "stop": ["Stop when the native compiler cannot prove the proposal within its frozen construction budget."],
    }
    data = {"action": "UPDATE", "role": "designer", "base_snapshot_hash": parent.snapshot_hash,
            "skill_id": parent.skills[0].id, "skill": raw_skill,
            "rationale": "The source tasks show that a process error can coexist with final completion; preserve that distinction and compose separate order goals.",
            "evidence_ids": list(evidence_ids)}
    return _answer(calls=[_call("designer-reflection", "submit_designer_patch", data)])


def _service_patch_client(parent: LibrarySnapshot, evidence_ids):
    source_skill = parent.skills[0]
    raw_skill = {
        "type": "decision", "id": source_skill.id, "version": source_skill.version + 1,
        "scope": {"domains": list(source_skill.scope.domains), "tools": list(source_skill.scope.tools)},
        "trigger": source_skill.trigger.model_dump(mode="json"),
        "description": "Verify the current order and case before declining a policy-permitted resolution.",
        "preconditions": ["Read the current order and the relevant case using the authenticated customer scope.",
                          "Verify evidence binding and current order-line eligibility before deciding."],
        "procedure": [SERVICE_RECOVERY_SENTENCE,
                      "Use only the exact Customer-declared write operation and continue through the actual quote and consent steps."],
        "postconditions": ["Check the resulting line status and report only the business tool result."],
        "recovery": ["If an earlier response was mistaken, acknowledge it, re-check live state and continue from the current valid step."],
    }
    data = {"action": "UPDATE", "role": "service", "base_snapshot_hash": parent.snapshot_hash,
            "skill_id": source_skill.id, "skill": raw_skill,
            "rationale": "Task 1's independent Oracle identifies a false refusal of a permitted request; Task 2 provides a second real execution trace for the decision procedure.",
            "evidence_ids": list(evidence_ids)}
    return _answer(calls=[_call("service-reflection", "submit_skill_patch", data)])


def _checked_designer_reflection(parent, evidence_ids, request):
    user = json.loads(request["messages"][1]["content"])
    feedback = user["verified_feedback"]
    if user["library"]["snapshot_hash"] != parent.snapshot_hash:
        raise AssertionError("Designer Reflection received the wrong parent Snapshot")
    if {row["id"] for row in feedback} != set(evidence_ids):
        raise AssertionError("Designer Reflection did not receive both real task records")
    if not any(row["process_errors"] and row["process_errors"][0]["classification"] == "false_rejection"
               for row in feedback):
        raise AssertionError("Designer Reflection did not receive the Oracle-confirmed process error")
    return _designer_patch_client(parent, evidence_ids)


def _checked_service_reflection(parent, evidence_ids, request):
    user = json.loads(request["messages"][1]["content"])
    if user["library"]["snapshot_hash"] != parent.snapshot_hash:
        raise AssertionError("Service Reflection received the wrong parent Snapshot")
    rows = user["evidence"]
    if {row["episode_id"] for row in rows} != set(evidence_ids):
        raise AssertionError("Service Reflection did not receive both actual task records")
    first = next(row for row in rows if row["episode_id"] == "task-1")
    if not any(decision["kind"] == "false_rejection" for decision in first.get("task_decisions", [])):
        raise AssertionError("Service Reflection did not receive the linked process-error evidence")
    return _service_patch_client(parent, evidence_ids)


def _patch_snapshot(root, role, parent, patch, *, allowed_tools):
    gate = StaticSkillGate(allowed_tools=allowed_tools, allowed_domains=("aftersales",))
    validation = gate.validate(parent, patch)
    outcome = {"static_gate": validation.model_dump(mode="json"),
               "dynamic_gate": {"status": "disabled_for_this_smoke_only",
                                "reason": "No additional Service task is permitted by the three-task smoke protocol."},
               "parent_snapshot_hash": parent.snapshot_hash, "patch": patch.model_dump(mode="json") if patch else None}
    _write(root, f"reflections/{role}_gate.json", outcome)
    if not validation.passed or patch is None:
        raise ValueError(f"{role} SkillPatch did not pass the native static gate: {validation.reasons}")
    candidate = apply_patch(parent, patch, f"aftersales-three-task-smoke-{role}-reflection")
    store = LibraryStore(root / "libraries" / role)
    store.save(parent)
    store.save(candidate)
    _write(root, f"libraries/{role}/selected.json", {
        "selected_snapshot_hash": candidate.snapshot_hash,
        "parent_snapshot_hash": parent.snapshot_hash,
        "selection_basis": "Static Skill Gate pass; performance/dynamic gate intentionally not run in this smoke.",
        "patch_hash": digest(patch.model_dump(mode="json")),
        "skill_versions": [{"id": s.id, "version": s.version, "content_hash": s.content_hash}
                            for s in candidate.skills],
    })
    return candidate, validation


def _make_evidence_for_reflection(root, task_rows, customer_snapshot, service_snapshots):
    evidences, hashes = [], []
    for row, service_snapshot in zip(task_rows, service_snapshots):
        evidence, evidence_hash = _event_and_decision_evidence(root, row, customer_snapshot, service_snapshot)
        evidences.append(evidence)
        hashes.append(evidence_hash)
    return evidences, hashes


def _reflection_flow(root, task_rows, d0, s0, customer_snapshot):
    evidences, evidence_hashes = _make_evidence_for_reflection(root, task_rows, customer_snapshot, [s0, s0])
    feedback = []
    for row, evidence in zip(task_rows, evidences):
        feedback.append({"id": evidence.episode_id, "world_hash": row["task_record"].frozen.world_hash,
            "task_hash": row["task_record"].task_hash, "trace_hash": row["execution"].trace.trace_hash,
            "final_goal_reached": row["final_goal_reached"], "task_success": row["score"]["success"],
            "process_errors": row["process_errors"], "oracle": row["execution"].oracle,
            "evidence_hash": evidence.evidence_hash})

    designer_client = ScriptedClient(ModelSettings(
        model=REFLECTOR_MODEL.model, base_url=REFLECTOR_MODEL.base_url, options=REFLECTOR_MODEL.options),
        lambda request: _checked_designer_reflection(d0, [e.episode_id for e in evidences], request))
    # Use the real Designer Reflector request/patch parser, with a domain policy
    # set by this smoke rather than its legacy CloudOps default.
    designer_result = reflect_designer(designer_client, REFLECTOR_MODEL, d0, feedback,
        "aftersales-smoke-g1", domain_policy=DomainPolicy(add_domains=("aftersales",)))
    designer_reflection_path = _write_append_only_attempt(
        root, "reflections/designer_reflection.json", designer_result)
    if designer_result.get("patch") is None:
        raise ValueError("Designer Reflector did not produce a valid SkillPatch: " + str(designer_result.get("error")))
    designer_patch = SkillPatch.model_validate(designer_result["patch"])
    d1, designer_gate = _patch_snapshot(root, "designer", d0, designer_patch, allowed_tools=aftersales.TOOLS)

    service_input = ReflectionInput(
        generation=1, role="service", library=s0, evidence=tuple(evidences),
        allowed_tools=tuple(aftersales.TOOLS), domain_policy=DomainPolicy(add_domains=("aftersales",)),
        public_policy=json.dumps(aftersales.POLICY, ensure_ascii=False, sort_keys=True),
        boundaries="Only After-sales declarative Skill text may change; keep Engine, Reference, Oracle and Customer authority fixed.",
    )
    service_client = ScriptedClient(ModelSettings(model=REFLECTOR_MODEL.model, base_url=REFLECTOR_MODEL.base_url,
        options=REFLECTOR_MODEL.options), lambda request: _checked_service_reflection(
            s0, [e.episode_id for e in evidences], request))
    # The smoke stores full request/response provenance for offline replay. Keep
    # that complete evidence, but give the single local scripted Reflection a
    # larger input cap than the production default (no network call is made).
    service_record = ServiceReflector(
        service_client, REFLECTOR_MODEL, max_input_chars=2_000_000
    ).reflect(service_input)
    service_reflection_path = _write_append_only_attempt(
        root, "reflections/service_reflection.json", service_record)
    if service_record.patch is None:
        raise ValueError("Service Reflector did not produce a valid SkillPatch: " + str(service_record.error))
    s1, service_gate = _patch_snapshot(root, "service", s0, service_record.patch, allowed_tools=aftersales.TOOLS)
    return (d1, s1, {"designer": designer_gate, "service": service_gate}, evidence_hashes,
            designer_result, service_record,
            {"designer": str(designer_reflection_path.relative_to(root)),
             "service": str(service_reflection_path.relative_to(root))})


def _task_context(snapshot, skill_renderer, evidence_rows, hypothesis):
    return {
        "skill_snapshot_hash": snapshot.snapshot_hash,
        "skill_rendered": skill_renderer.render(snapshot.skills),
        "evidence_ids": [row["episode_id"] for row in evidence_rows],
        "hypothesis": hypothesis,
        "source_evidence": evidence_rows,
    }


def _task_summary(row):
    return {"episode_id": f"task-{row['task_number']}",
            "trace_hash": row["execution"].trace.trace_hash,
            "final_goal_reached": row["final_goal_reached"],
            "task_success": bool(row["score"]["success"]),
            "process_errors": row["process_errors"],
            "service_skill_snapshot_hash": row["execution"].config.skill_contexts["service"].snapshot_hash}


def _load_task_row(root, number, frozen):
    base = root / "tasks" / f"task-{number}"
    execution = AgentExecution.model_validate_json((base / "execution.json").read_text(encoding="utf-8"))
    task_record = __import__("usami_benchmark.tasks", fromlist=["CertifiedTask"]).CertifiedTask.model_validate_json(
        (base / "certified_task.json").read_text(encoding="utf-8"))
    score_record = json.loads((base / "score.json").read_text(encoding="utf-8"))
    if execution.config.initial_world_hash != frozen.world_hash or not verify_task(task_record):
        raise ValueError(f"saved Task {number} is not bound to the resumed frozen registration")
    replay = replay_execution(aftersales, execution,
        world=aftersales.World.model_validate(frozen.world), config=execution.config)
    if not replay["verified"] or score_record["agent_replay"].get("verified") is not True:
        raise ValueError(f"saved Task {number} failed exact model/Engine Replay")
    return {"task_number": number, "execution": execution, "task_record": task_record,
        "score": score_record["strict_score"], "final_goal_reached": score_record["final_goal_reached"],
        "process_errors": score_record["process_errors"], "agent_replay": replay,
        "trace_path": str((base / "trace.json").resolve()),
        "execution_path": str((base / "execution.json").resolve()),
        "task_path": str((base / "certified_task.json").resolve()),
        "service_client": None, "customer_client": None}


def _check_frozen_unchanged(frozen, rows):
    for row in rows:
        if row["execution"].trace.initial_world != frozen.world:
            raise ValueError(f"Task {row['task_number']} did not start from the exact frozen initial world")
        if row["execution"].config.initial_world_hash != frozen.world_hash:
            raise ValueError(f"Task {row['task_number']} changed its registered world hash")


def _tamper_check(adapter_execution):
    tampered = AgentExecution.model_validate(adapter_execution.model_dump(mode="json"))
    tampered.calls[0].record.response = {"tampered": True}
    try:
        replay_execution(aftersales, tampered)
    except ValueError:
        return {"tampered_replay_rejected": True, "reason": "execution/request-response integrity or recorded completion mismatch"}
    raise AssertionError("Replay accepted a tampered model record")


def run_smoke(output_dir, *, resume=False, resume_from=None):
    root = Path(output_dir).resolve()
    source_root = Path(resume_from).resolve() if resume_from is not None else None
    previous_failures = []
    existing_manifest = None
    if source_root is not None:
        if root.exists():
            raise FileExistsError("resumed run output must be a new, unused directory: " + str(root))
        source_manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
        if source_manifest.get("protocol") != PROTOCOL or source_manifest.get("status") != "BLOCKED":
            raise ValueError("resume source must be a BLOCKED run of this exact protocol")
        root.mkdir(parents=True)
        for relative in ("world/frozen_world.json", "libraries/designer/initial.json",
                         "libraries/service/initial.json", "libraries/customer/initial.json",
                         "tasks/task-1", "designer/task-1-observation.json"):
            source = source_root / relative
            target = root / relative
            if not source.exists():
                raise FileNotFoundError("resume source lacks completed Task 1 artifact: " + str(source))
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
        if source_manifest.get("failure"):
            previous_failures.append(source_manifest["failure"])
        existing_manifest = source_manifest
        resume = True
    if root.exists() and not resume:
        raise FileExistsError("Smoke output is append-only; choose a new output directory: " + str(root))
    if resume:
        if not root.is_dir():
            raise FileNotFoundError("resume directory is absent: " + str(root))
        existing = existing_manifest or json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if existing.get("protocol") != PROTOCOL or existing.get("status") != "BLOCKED":
            raise ValueError("only a blocked run of this exact protocol can be resumed")
        if existing.get("failure"):
            previous_failures.append(existing["failure"])
    else:
        root.mkdir(parents=True)
    manifest = {"protocol": PROTOCOL, "status": "running", "service_execution_tasks_planned": 3,
        "dynamic_gate": "disabled_for_this_smoke_only", "online_llm_calls": 0,
        "customer_skill_evolves": False, "customer_identity": "u1",
        "training_protocol": "frozen_world_three_task_skill_update_smoke-v1"}
    if resume:
        manifest["resumed_from_blocked_run"] = True
        manifest["previous_failures"] = previous_failures
        if source_root is not None:
            manifest["resumed_from_run"] = str(source_root)
    atomic_json(root / "manifest.json", manifest)
    try:
        if resume:
            manifest["resumed_from_blocked_run"] = True
            manifest["previous_failures"] = previous_failures
            frozen = FrozenWorld.model_validate_json((root / "world/frozen_world.json").read_text(encoding="utf-8"))
            d0 = LibrarySnapshot.model_validate_json((root / "libraries/designer/initial.json").read_text(encoding="utf-8"))
            s0 = LibrarySnapshot.model_validate_json((root / "libraries/service/initial.json").read_text(encoding="utf-8"))
            c0 = LibrarySnapshot.model_validate_json((root / "libraries/customer/initial.json").read_text(encoding="utf-8"))
        else:
            frozen = freeze(default_spec("aftersales", 1))
            d0, s0, c0 = _skill_libraries()
            for role, snapshot in (("designer", d0), ("service", s0), ("customer", c0)):
                _write(root, f"libraries/{role}/initial.json", snapshot)
                if role != "customer":
                    LibraryStore(root / "libraries" / role).save(snapshot)
            _write(root, "world/frozen_world.json", frozen)
        if frozen.spec.domain != "aftersales" or frozen.world_hash != digest(frozen.world):
            raise ValueError("native frozen After-sales world failed its source hash")
        world = aftersales.World.model_validate(frozen.world)
        if any(aftersales.invariants(world)):
            raise ValueError("initial frozen After-sales world violates native invariants")
        if any(profile not in world.profiles or world.profiles[profile].identity != "u1"
               for profile in (PRIMARY_PROFILE, *COMPOSED_PROFILES)):
            raise ValueError("registered Customer scope is absent or changes identity")
        manifest.update({"frozen_world_hash": frozen.world_hash,
            "frozen_registration_hash": frozen.registration_hash,
            "world_seed": frozen.spec.seed, "world_partition": frozen.spec.partition,
            "world_generation_source_hash": frozen.generator_source_hash,
            "world_rules_source_hash": frozen.rules_source_hash,
            "initial_designer_snapshot_hash": d0.snapshot_hash,
            "initial_service_snapshot_hash": s0.snapshot_hash,
            "fixed_customer_snapshot_hash": c0.snapshot_hash,
            "fixed_customer_model": CUSTOMER_MODEL.model, "service_model": MODEL.model,
            "reflection_model": REFLECTOR_MODEL.model})
        atomic_json(root / "manifest.json", manifest)

        if resume and (root / "tasks/task-1/execution.json").exists():
            task1 = _load_task_row(root, 1, frozen)
            task1_record = task1["task_record"]
            task1_summary = json.loads((root / "designer/task-1-observation.json").read_text(encoding="utf-8"))
        else:
            task1_record = _single_task(frozen)
            _write(root, "tasks/task-1/proposal.json", task1_record.selection)
            task1 = _run_service_task(root, 1, frozen, task1_record, PRIMARY_PROFILE, "refund", s0,
                                      force_seed_error=True)
            task1_summary = _task_summary(task1)
            _write(root, "designer/task-1-observation.json", task1_summary)
        if task1_summary["task_success"] or not task1_summary["final_goal_reached"] or not task1_summary["process_errors"]:
            raise AssertionError("Task 1 did not preserve success/error distinction")

        task2_selection = _composition_selection(world, ("exchange", "reship"))
        task2_context = _task_context(d0, SkillRenderer(), [task1_summary],
            "A declared, policy-permitted operation can be refused even when the business request later completes. Probe two existing orders separately and preserve each profile's facts.")
        task2_client = TaskDesignerClient(task2_selection, expected_skill_hash=d0.snapshot_hash,
                                          expected_version=1, expected_evidence_ids=("task-1",))
        task2_designer = design_and_compile(frozen, task2_client,
            ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1), prompt_context=task2_context,
            protocol="frozen-world-task-designer-v1")
        verify_designer_execution(task2_designer)
        _write(root, "designer/task-2-execution.json", task2_designer)
        if not task2_client.context_verified or len(task2_designer.task.dialogue_witnesses[0].certificate.task.composition.profile_ids) != 2:
            raise AssertionError("Task 2 Designer did not consume Task 1 evidence or prove a multi-object composition")
        _write(root, "designer/task-2-proposal.json", {
            "source_evidence_ids": task2_context["evidence_ids"], "hypothesis": task2_context["hypothesis"],
            "selection": task2_designer.selection.model_dump(mode="json"), "task_hash": task2_designer.task.task_hash,
            "proof": verify_designer_execution(task2_designer), "multi_object_attempt": {
                "profile_ids": task2_designer.selection.composition.profile_ids,
                "distinct_goal_count": len(task2_designer.selection.composition.goals),
                "proved_by_native_reference_engine_oracle_replay": True,
            }, "designer_context_verified": task2_client.context_verified,
        })
        task2_record = task2_designer.task
        if resume and (root / "tasks/task-2/execution.json").exists():
            task2 = _load_task_row(root, 2, frozen)
            task2_record = task2["task_record"]
            task2_summary = json.loads((root / "designer/task-2-observation.json").read_text(encoding="utf-8"))
        else:
            task2 = _run_service_task(root, 2, frozen, task2_record, COMPOSED_PROFILES[0],
                                      ("exchange", "reship"), s0)
            task2_summary = _task_summary(task2)
            _write(root, "designer/task-2-observation.json", task2_summary)

        _check_frozen_unchanged(frozen, [task1, task2])
        d1, s1, gates, evidence_hashes, designer_reflection, service_reflection, reflection_artifacts = _reflection_flow(
            root, [task1, task2], d0, s0, c0)
        if d1.snapshot_hash == d0.snapshot_hash or s1.snapshot_hash == s0.snapshot_hash:
            raise AssertionError("both statically accepted updates must publish child snapshots")

        task3_selection = _composition_selection(world, ("refund", "exchange"))
        history = [task1_summary, task2_summary]
        hypothesis = "Use the updated strategy to build a separate, evidence-grounded two-order challenge; keep each order's resolution and information dependency distinct."
        task3_context = _task_context(d1, SkillRenderer(), history, hypothesis)
        task3_client = TaskDesignerClient(task3_selection, expected_skill_hash=d1.snapshot_hash,
            expected_version=2, expected_evidence_ids=("task-1", "task-2"))
        task3_designer = design_and_compile(frozen, task3_client,
            ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1), prompt_context=task3_context,
            protocol="frozen-world-task-designer-v1")
        verify_designer_execution(task3_designer)
        if not task3_client.context_verified:
            raise AssertionError("Task 3 Designer Skill/history context was not consumed")
        _write(root, "designer/task-3-execution.json", task3_designer)
        _write(root, "designer/task-3-proposal.json", {
            "source_evidence_ids": task3_context["evidence_ids"], "hypothesis": hypothesis,
            "selection": task3_designer.selection.model_dump(mode="json"), "task_hash": task3_designer.task.task_hash,
            "proof": verify_designer_execution(task3_designer),
            "designer_snapshot_hash": d1.snapshot_hash, "designer_context_verified": task3_client.context_verified,
            "new_skill_text_in_request": SkillRenderer().render(d1.skills) in task3_designer.request["messages"][0]["content"],
        })
        task3 = _run_service_task(root, 3, frozen, task3_designer.task, COMPOSED_PROFILES[0],
                                  ("refund", "exchange"), s1, updated_skill_expected=True)
        task3_summary = _task_summary(task3)
        _write(root, "designer/task-3-observation.json", task3_summary)
        if not task3_summary["task_success"]:
            raise AssertionError("Task 3 did not complete under the selected Skill snapshots")
        _check_frozen_unchanged(frozen, [task1, task2, task3])

        # Register only Task 1/2 evidence as Reflection inputs; Task 3 is a verification
        # of selected Skills and never feeds back into the already completed updates.
        _write(root, "verification/task-3-skill-consumption.json", {
            "designer_snapshot_hash": d1.snapshot_hash,
            "designer_skill_version": d1.skills[0].version,
            "designer_skill_text": d1.skills[0].model_dump(mode="json"),
            "designer_request_contains_rendered_skill": SkillRenderer().render(d1.skills) in task3_designer.request["messages"][0]["content"],
            "service_snapshot_hash": s1.snapshot_hash,
            "service_skill_version": s1.skills[0].version,
            "service_skill_content_hash": s1.skills[0].content_hash,
            "service_rendered_skill": task3["execution"].config.skill_contexts["service"].rendered,
            "service_first_request_contains_rendered_skill": task3["execution"].config.skill_contexts["service"].rendered in next(
                row.record.request["messages"][0]["content"] for row in task3["execution"].calls if row.role == "service"),
            "service_behavior_used_skill": task3["service_client"].query_before_open and any(
                tool["name"] == "get_order" and tool["arguments"] for tool in task3["execution"].tools),
            "source_evidence_ids": task3_context["evidence_ids"],
            "task_hash": task3["task_record"].task_hash,
        })
        tamper = _tamper_check(task3["execution"])
        _write(root, "verification/tamper_replay.json", tamper)

        all_rows = [task1, task2, task3]
        service_calls = sum(row["execution"].cost["service_calls"] for row in all_rows)
        customer_calls = sum(row["execution"].cost["customer_calls"] for row in all_rows)
        business_tool_calls = sum(row["execution"].cost["tool_calls"] for row in all_rows)
        task1_oracle_errors = task1["process_errors"]
        manifest.update({"status": "EXECUTED", "service_execution_tasks_planned": 3,
            "service_execution_tasks_completed": len(all_rows), "task_ids": ["task-1", "task-2", "task-3"],
            "all_initial_world_hashes": [row["execution"].config.initial_world_hash for row in all_rows],
            "service_llm_calls": service_calls, "customer_llm_calls": customer_calls,
            "designer_task_calls": 2,
            "reflection_calls": int(designer_reflection.get("call") is not None) + service_reflection.calls,
            "total_business_tool_calls": business_tool_calls,
            "recorded_model_tokens": "not reported by scripted offline fixtures",
            "online_llm_calls": 0, "dynamic_gate": "disabled_for_this_smoke_only",
            "task_outcomes": [task1_summary, task2_summary, task3_summary],
            "oracle_confirmed_task1_process_errors": task1_oracle_errors,
            "designer_snapshot_hashes": [d0.snapshot_hash, d1.snapshot_hash],
            "service_snapshot_hashes": [s0.snapshot_hash, s1.snapshot_hash],
            "designer_static_gate": gates["designer"].model_dump(mode="json"),
            "service_static_gate": gates["service"].model_dump(mode="json"),
            "reflection_evidence_hashes": evidence_hashes,
            "reflection_artifacts": reflection_artifacts,
            "all_three_agent_replays_verified": all(row["agent_replay"]["verified"] for row in all_rows),
            "all_three_native_task_certificates_verified": all(verify_task(row["task_record"]) for row in all_rows),
            "task3_new_skill_context_verified": True, "tamper_replay_rejected": tamper["tampered_replay_rejected"],
            "claim_boundary": "Engineering closure and evidence plumbing only; no real-model learning or performance claim."})
        atomic_json(root / "manifest.json", manifest)
        return manifest
    except Exception as exc:
        manifest.update({"status": "BLOCKED", "failure": {"type": type(exc).__name__, "message": str(exc)}})
        atomic_json(root / "manifest.json", manifest)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None,
                        help="new output directory; existing directories are never overwritten")
    parser.add_argument("--resume", action="store_true",
                        help="continue an incomplete BLOCKED run, reusing and replaying its completed Service tasks")
    parser.add_argument("--resume-from", type=Path, default=None,
                        help="start a new immutable run directory by carrying forward a blocked run's verified Task 1")
    args = parser.parse_args(argv)
    output = args.output or Path("experiments/vast_coevo/results/aftersales-coevo-smoke-001")
    result = run_smoke(output, resume=args.resume, resume_from=args.resume_from)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
