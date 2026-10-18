"""Versioned, bounded read/explore/submit protocol for frozen dialogue worlds.

Only native frame declarations are compiler-generated. Objectives, customer
choices and event selection remain Designer decisions; native certification is
unchanged. Recorded exchanges replay through this same deterministic program.
"""
from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field

from usami.service.models import ModelSettings, ServiceError, strict_json
from usami.service.runner import completion_message
from usami_dialogue.composition import _contract
from usami_dialogue.scope import load_profiles
from usami_dialogue.tasks import Goal, InformationRequirement, PreferenceRequirement
from usami_harness.models import Model, digest
from vast_coevo.schema import atomic_json

from .contracts import TRACKS
from .public_policy import catalogue
from .splits import verified_world
from .tasks import CertifiedTask, ConstructionBudget, OpenDialogueComposition, TaskSelection, compile_task


PROTOCOL = "frozen-world-designer-exploration-v2"


class DesignerBudget(Model):
    max_exploration_calls: int = Field(default=5, ge=0, le=12)
    max_revisions: int = Field(default=3, ge=0, le=3)
    max_queries: int = Field(default=20, ge=1, le=48)
    initial_exploration_calls: Optional[int] = Field(default=None, ge=1, le=12, exclude_if=lambda value: value is None)
    actionable_feedback: bool = Field(default=False, exclude_if=lambda value: value is False)
    include_related_objects: bool = Field(default=False, exclude_if=lambda value: value is False)


class DialogueDesignerProposal(Model):
    profile_ids: list[str] = Field(min_length=1, max_length=8)
    customer_request: str = Field(min_length=1, max_length=6000)
    goals: list[Goal] = Field(default_factory=list, max_length=32)
    refusal_operations: list[dict] = Field(default_factory=list, max_length=16)
    information_requirements: list[InformationRequirement] = Field(default_factory=list, max_length=64)
    preference_requirements: list[PreferenceRequirement] = Field(default_factory=list, max_length=64)
    confirmation_requirements: list[dict] = Field(default_factory=list, max_length=16)
    external_schedule: list[str] = Field(default_factory=list, max_length=64)


class ReadQuery(Model):
    action: Literal["list_profiles", "read_profile", "read_objects", "read_rules"]
    identity: Optional[str] = None
    profile_id: Optional[str] = None
    collection: Optional[str] = None
    ids: list[str] = Field(default_factory=list, max_length=8)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=4, ge=1, le=8)


def _adapter_world(frozen):
    if TRACKS[frozen.spec.domain] != "B":
        raise ValueError("exploration-v2 requires a native dialogue domain")
    adapter = importlib.import_module("usami_" + frozen.spec.domain + ".adapter")
    return adapter, adapter.World.model_validate(frozen.world)


def field_enums(adapter):
    schema = adapter.World.model_json_schema()
    result = {}
    for collection, raw in schema["properties"].items():
        additional = raw.get("additionalProperties", {})
        reference = additional.get("$ref", "") if isinstance(additional, dict) else ""
        entity = schema.get("$defs", {}).get(reference.rsplit("/", 1)[-1], {})
        values = {name: spec["enum"] for name, spec in entity.get("properties", {}).items() if "enum" in spec}
        if values:
            result[collection] = values
    return result


def exploration_view(frozen, *, include_context=True):
    """Compact catalogue, never the complete world or a selected task."""
    frozen = verified_world(frozen)
    _, world = _adapter_world(frozen)
    identities = {}
    for profile in world.profiles.values():
        identities[profile.identity] = identities.get(profile.identity, 0) + 1
    result = {"protocol": PROTOCOL, "world_hash": frozen.world_hash,
            "frozen_registration_hash": frozen.registration_hash, "domain": frozen.spec.domain,
            "rules_version": frozen.spec.rules_version,
            "identities": [{"identity": key, "profile_count": value} for key, value in sorted(identities.items())],
            "collections": {key: len(value) for key, value in frozen.world.items() if isinstance(value, dict)}}
    if include_context:
        result["clock"] = frozen.world["clock"]
    return result


def inspect_world(frozen, raw, *, include_related_objects=False):
    """Read from registered world data only; no Engine writes or Reference calls."""
    query = ReadQuery.model_validate(raw)
    adapter, world = _adapter_world(frozen)
    if query.action == "read_rules":
        return {"policy": catalogue(frozen.spec.domain, frozen.spec.rules_version),
                "native_field_enums": field_enums(adapter),
                "operation_schema": adapter.Operation.model_json_schema()}
    if query.action == "list_profiles":
        rows = [{"profile_id": key, "identity": private.identity}
                for key, private in sorted(world.profiles.items())
                if query.identity is None or private.identity == query.identity]
        return {"items": rows[query.offset:query.offset + query.limit], "total": len(rows),
                "offset": query.offset, "limit": query.limit}
    if query.action == "read_profile":
        if query.profile_id not in world.profiles:
            raise ValueError("profile_id does not exist in the frozen world")
        private = adapter.private_state(world, query.profile_id)
        related = {}
        for rule in _contract(adapter, world, private):
            collection = frozen.world.get(rule.collection, {})
            rows = {key: row for key, row in collection.items() if isinstance(row, dict) and
                    (key == rule.selector_value if rule.selector_field == "$key"
                     else row.get(rule.selector_field) == rule.selector_value)}
            if rows:
                related.setdefault(rule.collection, {}).update(rows)
        if include_related_objects:
            # Mutation frames omit immutable order dates, evidence and owners.
            # Follow existing entity references from this profile, bounded to
            # 24 records / two edges; do not decide policy or choose a target.
            def references(value):
                if isinstance(value, str):
                    yield value
                elif isinstance(value, dict):
                    for item in value.values():
                        yield from references(item)
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        yield from references(item)
            index = {}
            for collection, entities in frozen.world.items():
                if not isinstance(entities, dict):
                    continue
                for key, entity in entities.items():
                    if isinstance(entity, dict) and entity.get("id") == key:
                        index.setdefault(key, []).append((collection, entity))
            pending = set(private.protected_objects) | set(references(private.facts))
            seen = set()
            count = 0
            for _ in range(3):
                following = set()
                for key in sorted(pending - seen):
                    seen.add(key)
                    for collection, entity in index.get(key, []):
                        if count >= 24:
                            break
                        related.setdefault(collection, {})[key] = copy.deepcopy(entity)
                        following.update(references(entity))
                        count += 1
                pending = following
        return {"profile_id": query.profile_id, "identity": private.identity,
                "facts": private.facts, "preference_space": private.preference_space,
                "initial_preferences": private.initial_preferences,
                "confirmable_actions": list(private.confirmable_actions),
                "customer_operations": adapter.candidate_intents(world, private),
                "related_objects": related,
                "registered_external_events": [row.model_dump(mode="json") for row in world.external_events.values()
                    if any(value in private.protected_objects for value in row.model_dump(mode="json").values())]}
    collection = frozen.world.get(query.collection)
    if not isinstance(collection, dict):
        raise ValueError("collection must name a registered frozen collection")
    if query.ids:
        if any(key not in collection for key in query.ids):
            raise ValueError("requested object does not exist in the frozen collection")
        return {"items": {key: copy.deepcopy(collection[key]) for key in query.ids}}
    keys = sorted(collection)
    return {"items": {key: copy.deepcopy(collection[key]) for key in keys[query.offset:query.offset + query.limit]},
            "total": len(keys), "offset": query.offset, "limit": query.limit}


def compile_proposal(frozen, proposal, construction_budget):
    """Derive native scope without choosing, repairing or replacing objectives."""
    proposal = DialogueDesignerProposal.model_validate(proposal)
    adapter, world = _adapter_world(frozen)
    profiles = load_profiles(adapter, world, proposal.profile_ids[0], proposal.profile_ids)
    frames = {}
    for _, private in profiles:
        for frame in _contract(adapter, world, private):
            frames.setdefault(digest(frame), frame)
    enums = field_enums(adapter)
    for goal in proposal.goals:
        values = enums.get(goal.collection, {}).get(goal.field)
        if values is not None and any(value not in values for value in goal.accepted_values):
            raise ValueError(f"invalid values for {goal.collection}.{goal.field}; native vocabulary is {values}")
    composition = OpenDialogueComposition(**proposal.model_dump(mode="json"), frames=list(frames.values()))
    selection = TaskSelection(kind="dialogue", family="open_composition_v1",
                              profile_id=proposal.profile_ids[0], composition=composition)
    return selection, compile_task(frozen, selection, construction_budget)


POLICY = (
    "You are the autonomous Benchmark Task Designer in a read-only frozen business world. "
    "Use inspect_frozen_world to choose whom and what to investigate; you have a bounded exploration phase. "
    "Read the business rules and field vocabulary, inspect profiles and actual related objects. "
    "Select useful business challenges yourself, not a task supplied by the harness. You may combine several "
    "profiles only for the same authenticated identity. Do not invent facts, permissions, entities, events, "
    "proofs or expected refusal codes. Current v2 completion goals address existing objects; created-object "
    "predicates are not supported yet. The compiler derives native frames; never write frames or selector fields. "
    "An external event occurs only if you select its registered ID in external_schedule. "
    "Call ready_to_submit when prepared. The next phase forces submit_frozen_world_task. "
    "On rejection, correct your own proposal using the feedback; do not claim search failure proves impossibility. "
    "Keep replies concise and use the tools, rather than writing an essay."
)


def _tool(name, description, schema):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}


def _tools(stage):
    if stage == "submission":
        return [_tool("submit_frozen_world_task", "Submit business targets and objectives; native scope is compiler-owned.",
                      DialogueDesignerProposal.model_json_schema())]
    return [_tool("inspect_frozen_world", "Bounded read-only inspection; never writes or evaluates a future answer.", ReadQuery.model_json_schema()),
            _tool("ready_to_submit", "Finish exploration and proceed to the forced submission phase.",
                  {"type": "object", "properties": {}, "additionalProperties": False})]


def _messages(frozen, context, budget):
    policy = POLICY
    if context.get("skill_rendered"):
        policy += "\nApplied Designer Skill from snapshot " + str(context.get("skill_snapshot_hash")) + ":\n" + context["skill_rendered"]
    return [{"role": "system", "content": policy},
            {"role": "user", "content": json.dumps({"catalogue": exploration_view(frozen, include_context=budget.include_related_objects),
                "budget": budget.model_dump(mode="json"),
                "prior_evidence": {key: value for key, value in context.items() if key != "skill_rendered"}},
                ensure_ascii=False, sort_keys=True)}]


class ExplorationExecution(Model):
    protocol: Literal["frozen-world-designer-exploration-v2"] = PROTOCOL
    frozen_hash: str
    model: ModelSettings
    budget: DesignerBudget
    construction_budget: ConstructionBudget
    prompt_context: dict
    exchanges: list[dict]
    request: dict
    response: dict
    selection: TaskSelection
    task: CertifiedTask
    cost: dict
    metrics: dict
    execution_hash: str = ""

    def computed_hash(self):
        return digest(self.model_dump(mode="json", exclude={"execution_hash"}))


class DesignerFailure(ValueError):
    def __init__(self, message, journal):
        super().__init__(message)
        self.journal = journal


def design(frozen, client, construction_budget=None, prompt_context=None, *, budget=None, journal_path=None):
    frozen = verified_world(frozen)
    _adapter_world(frozen)
    # New sessions use the complete query context. Explicit old serialized
    # budgets retain their omitted/default flags for exact historical replay.
    budget = budget or DesignerBudget(initial_exploration_calls=3, actionable_feedback=True, include_related_objects=True)
    construction_budget = construction_budget or ConstructionBudget()
    context = copy.deepcopy(prompt_context or {})
    settings = client.settings.model_copy(deep=True)
    messages = _messages(frozen, context, budget)
    journal = {"protocol": PROTOCOL, "frozen_hash": frozen.registration_hash,
               "model": settings.model_dump(mode="json"), "budget": budget.model_dump(mode="json"),
               "construction_budget": construction_budget.model_dump(mode="json"), "prompt_context": context,
               "status": "RUNNING", "exchanges": [], "queries": 0, "proposal_attempts": 0}

    def save():
        journal["journal_hash"] = digest({key: value for key, value in journal.items() if key != "journal_hash"})
        if journal_path is not None:
            atomic_json(Path(journal_path), journal, immutable=False)

    def fail(message):
        journal.update(status="BLOCKED", failure=message)
        save()
        raise DesignerFailure(message, copy.deepcopy(journal))

    save()
    seen = set()
    stage = "exploration" if budget.max_exploration_calls else "submission"
    exploration_calls = 0
    while True:
        request = settings.request(copy.deepcopy(messages), _tools(stage))
        if stage == "submission":
            request["tool_choice"] = {"type": "function", "function": {"name": "submit_frozen_world_task"}}
            # DashScope Qwen supports thinking for exploration, but rejects a
            # forced function in thinking mode. Only an explicitly enabled
            # option is switched at this phase; old omitted-option journals
            # retain their original requests and failure replay.
            if settings.model.lower().startswith("dashscope/qwen") and settings.options.get("enable_thinking") is True:
                request["enable_thinking"] = False
            journal["proposal_attempts"] += 1
        else:
            exploration_calls += 1
        row = {"stage": stage, "request": copy.deepcopy(request), "tool_results": []}
        journal["exchanges"].append(row)
        save()
        try:
            response = client.complete(request)
        except Exception as exc:
            row["transport_error"] = {"type": type(exc).__name__, "message": str(exc)}
            fail("Designer transport failed; no retry performed: " + str(exc))
        row["response"] = copy.deepcopy(response)
        save()
        parsed = None
        calls = []
        try:
            message, calls = completion_message(response, seen)
            messages.append(message)
            if stage == "submission":
                if len(calls) != 1 or calls[0]["function"]["name"] != "submit_frozen_world_task":
                    raise ValueError("submission requires exactly one submit_frozen_world_task call")
                raw = strict_json(calls[0]["function"]["arguments"])
                parsed = DialogueDesignerProposal.model_validate(raw)
                selection, task = compile_proposal(frozen, parsed.model_dump(mode="json"), construction_budget)
            else:
                ready = not calls
                for call in calls:
                    try:
                        name = call["function"]["name"]
                        args = strict_json(call["function"]["arguments"])
                        if name == "ready_to_submit":
                            if args != {}:
                                raise ValueError("ready_to_submit takes no arguments")
                            ready = True
                            result = {"status": "ready"}
                        elif name == "inspect_frozen_world":
                            journal["queries"] += 1
                            if journal["queries"] > budget.max_queries:
                                raise ValueError("read-only query budget exhausted")
                            result = {"status": "ok", "data": inspect_world(frozen, args, include_related_objects=budget.include_related_objects)}
                        else:
                            raise ValueError("only registered read-only exploration tools are allowed")
                    except (ValueError, TypeError, KeyError) as exc:
                        result = {"status": "error", "detail": str(exc)}
                    row["tool_results"].append(result)
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(result, ensure_ascii=False, sort_keys=True)})
                initial_limit = (journal["proposal_attempts"] == 0 and budget.initial_exploration_calls is not None
                                 and exploration_calls >= budget.initial_exploration_calls)
                if ready or exploration_calls >= budget.max_exploration_calls or initial_limit:
                    stage = "submission"
                    messages.append({"role": "user", "content": "Exploration phase is finished. Submit your own business challenge now."})
                save()
                continue
        except (ValueError, TypeError, KeyError, ServiceError) as exc:
            feedback = {"status": "rejected", "detail": str(exc),
                        "category": "search_unproven" if "did not prove" in str(exc) else "invalid_proposal",
                        "meaning": "A bounded search failure does not prove impossibility. No task or world has been repaired for you."}
            if budget.actionable_feedback:
                submitted = [exchange for exchange in journal["exchanges"] if exchange["stage"] == "submission"]
                def arguments(exchange):
                    choices = exchange.get("response", {}).get("choices", [{}])
                    tool_calls = choices[0].get("message", {}).get("tool_calls") or []
                    return [item.get("function", {}).get("arguments") for item in tool_calls]
                feedback.update(
                    remaining_exploration_calls=max(0, budget.max_exploration_calls - exploration_calls),
                    remaining_submissions=max(0, 1 + budget.max_revisions - journal["proposal_attempts"]),
                    construction_budget=construction_budget.model_dump(mode="json"),
                    unchanged_submission=len(submitted) > 1 and arguments(submitted[-1]) == arguments(submitted[-2]),
                    correction_guidance="Revise your own proposal; repeating an unchanged rejected proposal does not change deterministic certification. You may inspect another profile, choose other legitimate objectives, or revise optional requirements. Registered external events occur only when explicitly scheduled. Use only actual facts; no answer has been selected for you.")
            row["feedback"] = feedback
            # Preserve malformed raw responses in the journal, but never insert
            # incomplete assistant/tool messages into the provider conversation.
            if messages and messages[-1].get("role") == "assistant":
                for call in calls:
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(feedback, ensure_ascii=False, sort_keys=True)})
            messages.append({"role": "user", "content": json.dumps(feedback, ensure_ascii=False, sort_keys=True)})
            save()
            if stage == "submission" and journal["proposal_attempts"] >= 1 + budget.max_revisions:
                fail("Designer submission budget exhausted: " + str(exc))
            stage = ("exploration" if exploration_calls < budget.max_exploration_calls
                     and journal["queries"] < budget.max_queries else "submission")
            continue

        row["tool_results"] = [{"status": "certified", "task_hash": task.task_hash}]
        journal["status"] = "CERTIFIED"
        save()
        usages = [exchange["response"].get("usage", {}) for exchange in journal["exchanges"]]
        cost = {"calls": len(usages), "usage_complete": all(all(type(usage.get(key)) is int
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")) for usage in usages)}
        for dest, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"), ("total_tokens", "total_tokens")):
            cost[dest] = sum(usage.get(source, 0) or 0 for usage in usages)
        signature = {"goals": [{"collection": g.collection, "field": g.field, "values": g.accepted_values} for g in parsed.goals],
                     "refusal_operations": [op.get("name") for op in parsed.refusal_operations]}
        metrics = {"proposal_attempts": journal["proposal_attempts"], "certified_proposals": 1,
                   "valid_proposal_rate": 1 / journal["proposal_attempts"], "queries": journal["queries"],
                   "objective_signature": digest(signature), "selected_profiles": len(parsed.profile_ids),
                   "reference_path_business_steps": sum(event.kind == "business" for event in task.dialogue_witnesses[0].trace.events),
                   "service_execution_count": 0}
        execution = ExplorationExecution(frozen_hash=frozen.registration_hash, model=settings, budget=budget,
            construction_budget=construction_budget, prompt_context=context, exchanges=journal["exchanges"],
            request=request, response=response, selection=selection, task=task, cost=cost, metrics=metrics)
        return execution.model_copy(update={"execution_hash": execution.computed_hash()})


class _ReplayClient:
    def __init__(self, settings, exchanges):
        self.settings, self.exchanges, self.index = settings, exchanges, 0

    def complete(self, request):
        if self.index >= len(self.exchanges):
            raise ValueError("missing recorded Designer response")
        row = self.exchanges[self.index]
        self.index += 1
        if request != row["request"]:
            raise ValueError("Designer request, query results or phase differs from recorded input")
        if "transport_error" in row:
            error = row["transport_error"]
            # Reproduce an exception name/message without importing or executing
            # any exception type named by an untrusted journal.
            raise type(error["type"], (Exception,), {})(error["message"])
        return copy.deepcopy(row["response"])


def verify_execution(record):
    row = ExplorationExecution.model_validate(record.model_dump(mode="json") if isinstance(record, ExplorationExecution) else record)
    if row.execution_hash != row.computed_hash() or row.frozen_hash != row.task.frozen.registration_hash:
        raise ValueError("Designer exploration integrity differs")
    client = _ReplayClient(row.model, row.exchanges)
    rebuilt = design(row.task.frozen, client, row.construction_budget, row.prompt_context, budget=row.budget)
    if rebuilt != row or client.index != len(row.exchanges):
        raise ValueError("Designer exploration, feedback, objective or certification Replay differs")
    return {"verified": True, "protocol": PROTOCOL, "model_calls": client.index,
            "actual_online_calls": 0, "task_hash": row.task.task_hash, "task_replay": True}


def verify_failed_journal(frozen, journal):
    """Reproduce a bounded failure, including query results and all feedback."""
    journal = copy.deepcopy(journal)
    expected_hash = digest({key: value for key, value in journal.items() if key != "journal_hash"})
    if journal.get("journal_hash") != expected_hash or journal.get("status") != "BLOCKED":
        raise ValueError("invalid failed Designer journal integrity/status")
    if journal["frozen_hash"] != frozen.registration_hash:
        raise ValueError("failed Designer journal belongs to another frozen world")
    client = _ReplayClient(ModelSettings.model_validate(journal["model"]), journal["exchanges"])
    try:
        design(frozen, client, ConstructionBudget(**journal["construction_budget"]), journal["prompt_context"],
               budget=DesignerBudget(**journal["budget"]))
    except DesignerFailure as exc:
        if exc.journal != journal or client.index != len(journal["exchanges"]):
            raise ValueError("failed Designer query/feedback Replay differs") from exc
        return {"verified": True, "failure_reproduced": True, "model_calls": client.index, "actual_online_calls": 0}
    raise ValueError("recorded failed Designer run unexpectedly certified")
