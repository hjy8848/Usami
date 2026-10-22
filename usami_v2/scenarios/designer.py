"""Two-stage, world-grounded Designer with independent business certification.

Stage one proposes only a constrained ScenarioSpec draft. Stage two sees the
constructed business world and proposes a TaskDraft using aliases. The compiler
resolves aliases and attaches immutable provenance; the Designer never supplies
an answer key, Reference implementation or proof witness.
"""
from datetime import timedelta
import json
from typing import Any, Callable, Dict, Literal, Optional, Protocol, Tuple

from pydantic import Field, model_validator

from usami.service.client import CompletionClient
from usami.service.models import ModelSettings, ServiceError
from usami_harness.models import digest
from usami_v2.contracts import Sealed
from usami_v2.runtime.agents import AgentCall, _json_arguments, _one_tool_call, _usage
from usami_v2.runtime.runner import EpisodeRecord, replay_episode
from usami_v2.commerce.models import World, unit_credit
from usami_v2.scenarios.builder import BuildResult, build_world, verify_build
from usami_v2.scenarios.distribution import DistributionSpec, SamplingSlot
from usami_v2.scenarios.schema import (
    Attribute, IntegerRange, LineVariable, OrderVariable, RelationConstraint,
    SKUVariable, StockConstraint, WarehouseVariable, ScenarioSpec, BuildBudget,
)
from usami_v2.scenarios.task_certification import (
    CustomerScenario as ProofCustomerScenario, ProofBudget, TaskCertification, certify_task,
    verify_task_certificate,
)
from usami_v2.scenarios.tasks import (
    GroundedRemedyGoal, InformationObjective, TaskSpec, TaskSpecV2,
    check_task_scope, request_names_remedy,
)


class ScenarioDraft(Sealed):
    scenario_id: str
    merchant_alias: str = "merchant"
    customer_aliases: Tuple[str, ...]
    skus: Tuple[SKUVariable, ...]
    warehouses: Tuple[WarehouseVariable, ...]
    orders: Tuple[OrderVariable, ...]
    stock: Tuple[StockConstraint, ...] = ()
    default_stock: IntegerRange = IntegerRange(low=0, high=5)
    refund_approval_limit_cents: int = Field(default=50000, ge=0, strict=True)
    constraints: Tuple[RelationConstraint, ...] = ()

    def compile(self, distribution: DistributionSpec):
        return ScenarioSpec(
            scenario_id=self.scenario_id, merchant_alias=self.merchant_alias,
            customer_aliases=self.customer_aliases, skus=self.skus, warehouses=self.warehouses,
            orders=self.orders, stock=self.stock, default_stock=self.default_stock,
            refund_approval_limit_cents=self.refund_approval_limit_cents,
            constraints=self.constraints, provenance_kind="designer_exploration",
            distribution_hash=distribution.record_hash)


class RemedyDraft(Sealed):
    goal_id: str
    line_alias: str
    public_request_span: str = Field(min_length=1)
    subject_mention: str = Field(min_length=1)
    quantity: int = Field(ge=1, strict=True)
    allowed_remedies: Tuple[Literal["refund", "exchange", "reship"], ...] = Field(min_length=1)
    required_attributes: Tuple[Attribute, ...] = ()
    maximum_extra_charge_cents: Optional[int] = Field(default=None, ge=0, strict=True)
    latest_arrival_within_days: Optional[int] = Field(default=None, ge=0, strict=True)
    target_stage: Literal["settled", "delivered"] = "settled"


class InformationDraft(Sealed):
    goal_id: str
    subject_alias: str
    subject_mention: str
    fact_kind: Literal["refund_amount", "extra_charge", "arrival_date", "refund_status",
                       "shipment_status", "quantity", "currency"]
    public_request: str


class TaskDraft(Sealed):
    task_id: str
    customer_alias: str
    customer_request: str = Field(min_length=1)
    remedy_goals: Tuple[RemedyDraft, ...] = ()
    information_goals: Tuple[InformationDraft, ...] = ()
    parent_training_evidence_hashes: Tuple[str, ...] = ()

    @model_validator(mode="after")
    def unique_goal_ids(self):
        rows = self.remedy_goals + self.information_goals
        if not rows or len({row.goal_id for row in rows}) != len(rows):
            raise ValueError("TaskDraft needs unique business or information goals")
        if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
               for value in self.parent_training_evidence_hashes):
            raise ValueError("training evidence references must be SHA-256 hashes")
        normalized_request = " ".join(self.customer_request.casefold().split())
        for goal in self.remedy_goals:
            span = " ".join(goal.public_request_span.casefold().split())
            if not span or span not in normalized_request:
                raise ValueError("each remedy goal must quote its supporting public request span")
            mention = " ".join(goal.subject_mention.casefold().split())
            if not mention or mention not in span:
                raise ValueError("each remedy goal must name its object in the public request span")
            if not request_names_remedy(span, goal.allowed_remedies):
                raise ValueError("public request span must state every accepted remedy")
        return self


class DesignerTrainingEvidence(Sealed):
    """Curated training-only observations; no held-out or validator-only labels."""

    source_record_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    partition: Literal["train"]
    summary: str = Field(min_length=1)
    observed_events: Tuple[Dict[str, Any], ...] = ()


class DesignerCall(Sealed):
    phase: Literal["world", "task"]
    attempt: int = Field(ge=0, strict=True)
    call: AgentCall
    parsed_output_hash: str
    validation_feedback: str = ""


class TaskDesignAttempt(Sealed):
    attempt: int = Field(ge=0, strict=True)
    draft: TaskDraft
    task_hash: str = ""
    certification_hash: str = ""
    status: Literal["COMPILED", "CERTIFIED", "REJECTED", "UNKNOWN", "ERROR"]
    reason: str = ""


class WorldDesignAttempt(Sealed):
    attempt: int = Field(ge=0, strict=True)
    proposal_hash: str = ""
    build_result_hash: str = ""
    status: Literal["SAT", "UNSAT", "UNKNOWN", "ERROR"]
    reason: str = ""


class ChallengeQualityVector(Sealed):
    protocol: Literal["commerce-challenge-quality-vector-v1"] = "commerce-challenge-quality-vector-v1"
    world_hash: str
    task_hash: str
    business_certificate_hash: str
    business_valid: bool
    business_witnesses: int = Field(ge=0, strict=True)
    distinct_consequence_classes: int = Field(ge=0, strict=True)
    diagnosability: bool
    diagnostic_evidence_refs: Tuple[str, ...] = ()
    objective_kinds: Tuple[str, ...] = ()
    scenario_structure: str
    task_structure: str
    structural_signature: str
    novel_against_history: bool
    authorized_training_evidence_hash: str
    interaction_certified: bool = False
    interaction_certificate_hash: str = ""
    decision_power: Literal["diagnostic_only"] = "diagnostic_only"
    quality_status: Literal["business_certified_interaction_pending", "fully_interaction_certified",
                            "task_certification_incomplete"]


class PostRunQualityVector(Sealed):
    protocol: Literal["commerce-post-run-quality-v1"] = "commerce-post-run-quality-v1"
    pre_run_quality_hash: str
    execution_hash: str
    replay_verified: bool
    strict_task_success: Optional[bool]
    final_goal_reached: Optional[bool]
    oracle_business_errors: int = Field(ge=0, strict=True)
    false_rejections: int = Field(ge=0, strict=True)
    protocol_failures: int = Field(ge=0, strict=True)
    customer_failures: int = Field(ge=0, strict=True)
    transport_failures: int = Field(ge=0, strict=True)
    correct_rejections: int = Field(ge=0, strict=True)
    blocked_illegal_attempts: int = Field(ge=0, strict=True)
    legal_operations: int = Field(ge=0, strict=True)
    distinct_error_classes: Tuple[str, ...] = ()
    model_calls: int = Field(ge=0, strict=True)
    known_tokens: Optional[int] = Field(default=None, ge=0, strict=True)
    decision_power: Literal["diagnostic_only"] = "diagnostic_only"


class DesignerRun(Sealed):
    protocol: Literal["commerce-two-stage-designer-v1"] = "commerce-two-stage-designer-v1"
    run_id: str
    status: Literal["CERTIFIED", "UNKNOWN", "BLOCKED"]
    sampling_slot: SamplingSlot
    distribution: DistributionSpec
    scenario_spec: Optional[ScenarioSpec] = None
    build_result: Optional[BuildResult] = None
    build_attempts: Tuple[BuildResult, ...] = ()
    world_attempts: Tuple[WorldDesignAttempt, ...] = ()
    task_draft: Optional[TaskDraft] = None
    task: Optional[TaskSpec] = None
    certification: Optional[TaskCertification] = None
    task_attempts: Tuple[TaskDesignAttempt, ...] = ()
    pre_run_quality: Optional[ChallengeQualityVector] = None
    interaction_episode: Optional[EpisodeRecord] = None
    calls: Tuple[DesignerCall, ...] = ()
    validation_errors: Tuple[str, ...] = ()


class DesignerProvider(Protocol):
    def submit(self, phase: str, messages, model_schema): ...


def _tool_schema(name, model):
    schema = model.model_json_schema()
    schema.pop("title", None)
    tool = {"type": "function", "function": {"name": name,
        "description": "Submit exactly one structured proposal for this design stage.",
        "parameters": schema}}
    return tool


def _feedback(exc):
    if isinstance(exc, ServiceError):
        return "{}: {}".format(exc.code, str(exc))
    return "{}: {}".format(type(exc).__name__, str(exc))


def _is_provider_failure(exc):
    """Provider failures are not proposal feedback and must not be retried as corrections."""
    return isinstance(exc, ServiceError) and exc.code.startswith("PROVIDER_")


def _attempt_error(phase, exc):
    kind = "provider failed" if _is_provider_failure(exc) else "proposal rejected"
    return "{} {}: {}".format(phase, kind, _feedback(exc))


def _submit(provider, phase, messages, model, attempt, calls):
    if hasattr(provider, "last_call"):
        provider.last_call = None
    try:
        return provider.submit(phase, messages, model)
    except Exception as exc:
        call = getattr(exc, "agent_call", None) or getattr(provider, "last_call", None)
        if call is not None:
            calls.append(DesignerCall(phase=phase, attempt=attempt, call=call,
                                      parsed_output_hash="",
                                      validation_feedback="" if _is_provider_failure(exc) else _feedback(exc)))
        raise


class OpenAIDesignerProvider:
    """OpenAI-compatible Function Calling adapter; call only when explicitly used."""

    def __init__(self, client: CompletionClient):
        self.client = client
        self.settings: ModelSettings = client.settings.model_copy(deep=True)
        self.last_call: Optional[AgentCall] = None

    def submit(self, phase, messages, model):
        self.last_call = None
        name = "submit_world_constraints" if phase == "world" else "submit_customer_task"
        tool = _tool_schema(name, model)
        request = self.settings.request(messages, [tool])
        # Qwen3 thinking-mode endpoints reject both `required` and forced
        # function objects with HTTP 400. `auto` remains usable there; the
        # local parser below still requires exactly one complete call to this
        # phase's expected function, so provider compatibility does not relax
        # the Designer protocol.
        if "qwen3" in self.settings.model.casefold():
            request["tool_choice"] = "auto"
        else:
            request["tool_choice"] = {"type": "function", "function": {"name": name}}
        request["parallel_tool_calls"] = False
        try:
            raw = self.client.complete(request)
        except Exception as exc:
            code = getattr(exc, "code", None)
            error = {"type": type(exc).__name__,
                     "code": code if isinstance(code, str) else "DESIGNER_REQUEST_FAILED"}
            # Keep bounded provider diagnostics for offline audit. The native
            # OpenAI-compatible client redacts its credential in ServiceError
            # responses; only persist a response after applying that redactor.
            provider_response = getattr(exc, "response", None)
            redactor = getattr(self.client, "_redact", None)
            if isinstance(provider_response, dict) and callable(redactor):
                error["provider_response"] = redactor(provider_response)
            self.last_call = AgentCall(role="designer", request=request,
                                       response={"error": error})
            raise
        self.last_call = AgentCall(role="designer", request=request, response=raw,
                                   prompt_tokens=_usage(raw, "prompt_tokens"),
                                   completion_tokens=_usage(raw, "completion_tokens"))
        message = _one_tool_call(raw)
        call = message["tool_calls"][0]
        if call["function"]["name"] != name:
            raise ServiceError("MODEL_OUTPUT_INVALID", "Designer called the wrong phase submission tool")
        output = model.model_validate(_json_arguments(call["function"]["arguments"]))
        return output, self.last_call


def compile_task(draft: TaskDraft, spec: ScenarioSpec, build: BuildResult,
                 distribution: DistributionSpec, allowed_training_hashes=()):
    draft, spec, build, distribution = draft.checked(), spec.checked(), build.checked(), distribution.checked()
    if build.status != "SAT" or not build.world:
        raise ValueError("a SAT frozen world is required before task design")
    aliases = dict(build.private_aliases)
    if draft.customer_alias not in aliases:
        raise ValueError("TaskDraft references a Customer alias outside the frozen world")
    if not set(draft.parent_training_evidence_hashes).issubset(set(allowed_training_hashes)):
        raise ValueError("TaskDraft references training evidence outside the authorized input set")
    remedies, information = [], []
    for row in draft.remedy_goals:
        if row.line_alias not in aliases:
            raise ValueError("TaskDraft references an unknown order-line alias")
        line_variable = next(line for order in spec.orders for line in order.lines
                             if line.alias == row.line_alias)
        sku_variable = next(sku for sku in spec.skus if sku.alias == line_variable.original_sku)
        normalized_mention = " ".join(row.subject_mention.casefold().split())
        if (" ".join(line_variable.issue.casefold().split()) not in normalized_mention
                or " ".join(sku_variable.family.casefold().split()) not in normalized_mention):
            raise ValueError("public object mention must identify the frozen line issue and SKU family")
        original_id = aliases[row.line_alias]
        arrival = (build.world.clock + timedelta(days=row.latest_arrival_within_days)
                   if row.latest_arrival_within_days is not None else None)
        remedies.append(GroundedRemedyGoal(
            goal_id=row.goal_id, line_id=original_id, quantity=row.quantity,
            allowed_remedies=row.allowed_remedies, required_attributes=row.required_attributes,
            maximum_extra_charge_cents=row.maximum_extra_charge_cents,
            latest_arrival=arrival, target_stage=row.target_stage,
            public_request_span=row.public_request_span, subject_mention=row.subject_mention))
    for row in draft.information_goals:
        if row.subject_alias not in aliases:
            raise ValueError("TaskDraft references an unknown public order or line alias")
        information.append(InformationObjective(
            goal_id=row.goal_id, subject_id=aliases[row.subject_alias], subject_mention=row.subject_mention,
            fact_kind=row.fact_kind, public_request=row.public_request))
    if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
           for value in draft.parent_training_evidence_hashes):
        raise ValueError("invalid training evidence hash")
    task = TaskSpecV2(
        task_id=draft.task_id, world_hash=build.world_hash, customer_id=aliases[draft.customer_alias],
        customer_request=draft.customer_request, remedy_goals=tuple(remedies),
        information_goals=tuple(information), partition=distribution.split,
        source_distribution_hash=distribution.record_hash,
        parent_training_evidence_hashes=draft.parent_training_evidence_hashes)
    return check_task_scope(build.world, task)


def _structure_signatures(spec, world, task, certificate):
    aliases = {}
    aliases.update({row: "customer" for row in spec.customer_aliases})
    aliases.update({row.alias: "sku" for row in spec.skus})
    aliases.update({row.alias: "warehouse" for row in spec.warehouses})
    aliases.update({row.alias: "order" for row in spec.orders})
    aliases.update({line.alias: "line" for order in spec.orders for line in order.lines})

    def expression_shape(expression):
        return sorted((aliases.get(row.variable, "unknown"), row.field,
                       1 if row.coefficient > 0 else -1, abs(row.coefficient),
                       bool(row.warehouse)) for row in expression.terms)

    world_structure = {
        "customers": len(spec.customer_aliases), "skus": len(spec.skus),
        "families": sorted({row.family for row in spec.skus}),
        "warehouses": len(spec.warehouses), "orders": len(spec.orders),
        "lines": sum(len(row.lines) for row in spec.orders),
        "stock_constraints": len(spec.stock),
        "constraint_shapes": sorted((row.operator, expression_shape(row.left), expression_shape(row.right))
                                    for row in spec.constraints),
    }
    task_structure = {
        "remedy_goals": sorted((tuple(sorted(row.allowed_remedies)), row.quantity,
                                 tuple(sorted((a.name, a.value) for a in row.required_attributes)),
                                 row.maximum_extra_charge_cents is not None,
                                 row.latest_arrival is not None, row.target_stage)
                                for row in task.remedy_goals),
        "information_goals": sorted(row.fact_kind for row in task.information_goals),
        "distinct_target_lines": len({row.line_id for row in task.remedy_goals}),
        "mixed_objectives": bool(task.remedy_goals and task.information_goals),
    }
    def candidate_outcome(candidate):
        goal = next((row for row in task.remedy_goals if row.goal_id == candidate.goal_id), None)
        if goal is None:
            return {"remedy": candidate.remedy, "goal_kind": "unknown"}, 0, 0
        line = world.lines[goal.line_id]
        original = world.skus[line.sku_id]
        credit = unit_credit(line, tuple(range(goal.quantity)))
        if candidate.remedy == "refund":
            return {"remedy": "refund", "return_required": original.return_required}, -credit, 0
        target = world.skus[candidate.target_sku_id]
        warehouse = world.warehouses[candidate.warehouse_id]
        inventory = next(row for row in world.inventory.values()
                         if row.sku_id == target.id and row.warehouse_id == warehouse.id)
        route = next(row for row in world.routes.values() if row.warehouse_id == warehouse.id)
        delta = target.price_cents * goal.quantity + route.fee_cents - credit
        if candidate.remedy == "reship":
            delta = 0
        attrs_match = all(target.attributes.get(row.name) == row.value for row in goal.required_attributes)
        within_budget = (goal.maximum_extra_charge_cents is None
                         or max(delta, 0) <= goal.maximum_extra_charge_cents)
        within_deadline = (goal.latest_arrival is None
                           or world.clock + timedelta(days=route.days) <= goal.latest_arrival)
        return ({"remedy": candidate.remedy, "compatible": attrs_match,
                 "charge_relation": "within" if within_budget else "over",
                 "deadline_relation": "within" if within_deadline else "late",
                 "stock_relation": "sufficient" if inventory.available >= goal.quantity else "short",
                 "return_required": original.return_required}, delta, route.days * 86400)

    all_rows = []
    valid_rows = []
    for attempt in certificate.attempts:
        row_features = [candidate_outcome(candidate) for candidate in attempt.candidates]
        all_rows.append((attempt.status, tuple(sorted(item[0]["remedy"] for item in row_features)),
                         tuple(sorted(digest(item[0]) for item in row_features))))
        if attempt.status == "WITNESS":
            valid_rows.extend(row_features)
    costs = sorted({row[1] for row in all_rows_raw(certificate, candidate_outcome)})
    delays = sorted({row[2] for row in all_rows_raw(certificate, candidate_outcome)})
    consequence_classes = set()
    for consequence, money, delay in valid_rows:
        normalized = {**consequence, "relative_cost_rank": costs.index(money),
                      "relative_delay_rank": delays.index(delay)}
        consequence_classes.add(digest(normalized))
    world_structure["candidate_outcome_structure"] = sorted(all_rows)
    # IDs and absolute prices/times are deliberately absent from signatures.
    scenario_sig, task_sig = digest(world_structure), digest(task_structure)
    return (world_structure, task_structure, scenario_sig, task_sig,
            digest({"world": scenario_sig, "task": task_sig}), len(consequence_classes))


def all_rows_raw(certificate, candidate_outcome):
    for attempt in certificate.attempts:
        for candidate in attempt.candidates:
            yield candidate_outcome(candidate)


def _quality(spec, world, task, certificate, history_signatures, training_hashes,
             interaction_episode=None):
    ws, ts, world_sig, task_sig, combined, consequence_count = _structure_signatures(
        spec, world, task, certificate)
    witnesses = [row for row in certificate.attempts if row.status == "WITNESS"]
    interaction_ok = bool(interaction_episode and interaction_episode.replay_verified
                          and interaction_episode.outcome.strict_task_success is True)
    proof_refs = [certificate.record_hash] + [row.record_hash for row in witnesses]
    if interaction_episode:
        proof_refs.append(interaction_episode.record_hash)
    business_valid = certificate.business_reachability_certified or interaction_ok
    objectives = tuple(sorted(("remedy" for _ in task.remedy_goals),)) + tuple(
        sorted("information:" + row.fact_kind for row in task.information_goals))
    return ChallengeQualityVector(
        world_hash=certificate.world_hash, task_hash=certificate.task_hash,
        business_certificate_hash=certificate.record_hash,
        business_valid=business_valid,
        business_witnesses=len(witnesses), distinct_consequence_classes=consequence_count,
        diagnosability=bool(witnesses or interaction_ok), diagnostic_evidence_refs=tuple(proof_refs),
        objective_kinds=objectives,
        scenario_structure=json.dumps(ws, sort_keys=True), task_structure=json.dumps(ts, sort_keys=True),
        structural_signature=combined, novel_against_history=combined not in set(history_signatures),
        authorized_training_evidence_hash=digest(tuple(sorted(training_hashes))),
        interaction_certified=interaction_ok,
        interaction_certificate_hash=interaction_episode.record_hash if interaction_ok else "",
        quality_status=("fully_interaction_certified" if interaction_ok
                        else "business_certified_interaction_pending" if certificate.business_reachability_certified
                        else "task_certification_incomplete"))


def _chat(phase, content, distribution, slot, errors=()):
    return [
        {"role": "system", "content": (
            "You are the autonomous Usami Designer. Propose only the requested structured artifact. "
            "Do not invent or modify business rules, customer identity, Oracle results, task certificates, "
            "or a solution witness. Use the frozen distribution and supplied aliases."
        )},
        {"role": "user", "content": json.dumps({"phase": phase, "frozen_distribution": distribution.model_dump(mode="json"),
            "pre_registered_slot": slot.model_dump(mode="json"), "available_context": content,
            "validator_feedback": list(errors)}, ensure_ascii=False)},
    ]


def design_and_certify(provider: DesignerProvider, distribution: DistributionSpec, slot: SamplingSlot, *,
                       build_budget: Optional[BuildBudget] = None,
                       proof_budget: Optional[ProofBudget] = None,
                       allowed_training_hashes=(), history_signatures=(),
                       customer_scenario_factory: Optional[Callable[[Any, TaskSpec], ProofCustomerScenario]] = None,
                       training_evidence: Tuple[DesignerTrainingEvidence, ...] = (),
                       interaction_certifier: Optional[Callable[[World, TaskSpec, ProofCustomerScenario], EpisodeRecord]] = None,
                       max_attempts: int = 3) -> DesignerRun:
    """Run the two LLM phases with bounded compiler feedback and native proof.

    Reference witnesses, Oracle data and private customer proof policy are never
    added to a Designer prompt. Correction attempts receive rejection reasons only.
    """
    distribution, slot = distribution.checked(), slot.checked()
    if slot.distribution_hash != distribution.record_hash:
        raise ValueError("pre-registered sampling slot belongs to another distribution")
    if customer_scenario_factory is None:
        raise ValueError("a trusted, private CustomerScenario factory is required before any Designer model call")
    if max_attempts < 1 or max_attempts > 3:
        raise ValueError("Designer correction budget must be between one and three attempts")
    evidence = tuple(row.checked() for row in training_evidence)
    allowed_training_hashes = tuple(sorted(set(allowed_training_hashes)))
    if any(row.source_record_hash not in set(allowed_training_hashes) for row in evidence):
        raise ValueError("Designer context contains training evidence outside the authorized hash set")
    build_budget, proof_budget = (build_budget or BuildBudget()).checked(), (proof_budget or ProofBudget()).checked()
    calls, errors, scenario, build_attempts, world_attempts = [], [], None, [], []
    build = None
    for attempt in range(max_attempts):
        draft = None
        candidate_build = None
        content = {"required_provenance": "compiler-attached", "supported_fields": list(ScenarioDraft.model_fields.keys()),
                   "attempt_seed": slot.seed}
        try:
            draft, call = _submit(provider, "world", _chat("world", content, distribution, slot, errors),
                                  ScenarioDraft, attempt, calls)
            calls.append(DesignerCall(phase="world", attempt=attempt, call=call,
                                      parsed_output_hash=draft.record_hash))
            scenario = draft.compile(distribution)
            candidate_build = build_world(scenario, slot.seed, build_budget)
            build_attempts.append(candidate_build)
            if candidate_build.status != "SAT":
                feedback = "world builder returned {}: {}".format(candidate_build.status, candidate_build.reason)
                errors.append(feedback)
                world_attempts.append(WorldDesignAttempt(attempt=attempt, proposal_hash=draft.record_hash,
                    build_result_hash=candidate_build.record_hash, status=candidate_build.status, reason=feedback))
                continue
            verify_build(scenario, candidate_build)
            world_attempts.append(WorldDesignAttempt(attempt=attempt, proposal_hash=draft.record_hash,
                build_result_hash=candidate_build.record_hash, status="SAT", reason="native build certificate passed"))
            build = candidate_build
            break
        except Exception as exc:
            feedback = _attempt_error("world", exc)
            errors.append(feedback)
            world_attempts.append(WorldDesignAttempt(attempt=attempt,
                proposal_hash=draft.record_hash if draft else "",
                build_result_hash=candidate_build.record_hash if candidate_build else "",
                status="ERROR", reason=feedback))
            if calls and not _is_provider_failure(exc):
                last = calls[-1]
                if last.phase == "world" and last.attempt == attempt:
                    calls[-1] = DesignerCall(phase=last.phase, attempt=last.attempt, call=last.call,
                                             parsed_output_hash=last.parsed_output_hash,
                                             validation_feedback=feedback)
            if _is_provider_failure(exc):
                break
    if not scenario or not build or build.status != "SAT":
        # Preserve the last available attempt instead of manufacturing a world.
        return DesignerRun(
            run_id="designer-" + digest([slot.record_hash, tuple(x.record_hash for x in calls)])[:20],
            status="BLOCKED", sampling_slot=slot, distribution=distribution,
            scenario_spec=scenario, build_result=candidate_build, build_attempts=tuple(build_attempts),
            world_attempts=tuple(world_attempts),
            calls=tuple(calls), validation_errors=tuple(errors or ["no parseable world proposal"]))

    aliases = dict(build.private_aliases)
    world_context = {
        "world_hash": build.world_hash,
        "customers": [{"alias": alias, "id": aliases[alias]} for alias in scenario.customer_aliases],
        "orders": [{"alias": order.alias, "id": aliases[order.alias], "customer_alias": order.customer_alias,
                    "lines": [{"alias": line.alias, "id": aliases[line.alias],
                               "original_sku_alias": line.original_sku,
                               "quantity": build.world.lines[aliases[line.alias]].quantity,
                               "issue": line.issue, "evidence_valid": line.evidence_valid}
                              for line in order.lines]} for order in scenario.orders],
        "skus": [{"alias": sku.alias, "id": aliases[sku.alias], "family": sku.family,
                  "attributes": {row.name: row.value for row in sku.attributes}}
                 for sku in scenario.skus],
        "warehouses": [{"alias": row.alias, "id": aliases[row.alias],
                         "delivery_days": next(r.days for r in build.world.routes.values()
                                               if r.warehouse_id == aliases[row.alias]),
                         "delivery_fee_cents": next(r.fee_cents for r in build.world.routes.values()
                                                    if r.warehouse_id == aliases[row.alias])}
                        for row in scenario.warehouses],
        "inventory": [{"sku_alias": sku.alias, "warehouse_alias": wh.alias,
                       "available": next(inv.available for inv in build.world.inventory.values()
                                         if inv.sku_id == aliases[sku.alias]
                                         and inv.warehouse_id == aliases[wh.alias])}
                      for sku in scenario.skus for wh in scenario.warehouses],
        "clock": build.world.clock.isoformat(),
        "reference_policy": "independent; not included in this context",
    }
    errors, task_attempts = [], []
    evidence_context = [row.model_dump(mode="json") for row in evidence]
    task_context = {**world_context, "authorized_training_evidence": evidence_context}
    draft_task, task, certificate, interaction_episode = None, None, None, None
    for attempt in range(max_attempts):
        draft_task, task, certificate, interaction_episode = None, None, None, None
        try:
            draft_task, call = _submit(provider, "task", _chat("task", task_context, distribution, slot, errors),
                                       TaskDraft, attempt, calls)
            calls.append(DesignerCall(phase="task", attempt=attempt, call=call,
                                      parsed_output_hash=draft_task.record_hash))
            if not set(draft_task.parent_training_evidence_hashes).issubset(set(allowed_training_hashes)):
                raise ValueError("TaskDraft cites training evidence outside the authorized context")
            task = compile_task(draft_task, scenario, build, distribution, allowed_training_hashes)
            proof_customer = customer_scenario_factory(build.world, task)
            certificate = certify_task(build.world, task, proof_customer, proof_budget, minimum_witnesses=1)
            if certificate.status == "CERTIFIED":
                verify_task_certificate(build.world, task, proof_customer, certificate)
            if interaction_certifier is not None:
                interaction_episode = interaction_certifier(build.world.clone(), task, proof_customer)
                if not isinstance(interaction_episode, EpisodeRecord):
                    raise ValueError("interaction certifier must return a sealed EpisodeRecord")
                interaction_replay = replay_episode(interaction_episode)
                if (interaction_episode.initial_world.state_hash != build.world_hash
                        or interaction_episode.task.record_hash != task.record_hash
                        or not interaction_replay.verified):
                    raise ValueError("interaction Episode is not bound to the frozen task/world or fails Replay")
            interaction_ok = bool(interaction_episode and interaction_episode.outcome.strict_task_success is True
                                   and interaction_episode.replay_verified)
            if certificate.status == "CERTIFIED" or interaction_ok:
                task_attempts.append(TaskDesignAttempt(attempt=attempt, draft=draft_task,
                    task_hash=task.record_hash, certification_hash=certificate.record_hash,
                    status="CERTIFIED", reason=("native Reference certificate passed" if certificate.status == "CERTIFIED"
                                                  else "independent interaction Episode passed strict evaluation and Replay")))
                break
            task_attempts.append(TaskDesignAttempt(attempt=attempt, draft=draft_task,
                task_hash=task.record_hash, certification_hash=certificate.record_hash,
                status="UNKNOWN" if certificate.status == "UNKNOWN" else "REJECTED",
                reason=", ".join(certificate.blockers)))
            raise ValueError("independent Reference returned {}: {}".format(
                certificate.status, ", ".join(certificate.blockers)))
        except Exception as exc:
            provider_failure = _is_provider_failure(exc)
            feedback = (_attempt_error("task", exc) if provider_failure else
                        "task proposal rejected or uncertified: " + _feedback(exc))
            errors.append(feedback)
            if draft_task is not None and (not task_attempts or task_attempts[-1].draft.record_hash != draft_task.record_hash):
                task_attempts.append(TaskDesignAttempt(attempt=attempt, draft=draft_task,
                    task_hash=task.record_hash if task else "", certification_hash=certificate.record_hash if certificate else "",
                    status="ERROR" if provider_failure else "REJECTED", reason=feedback))
            if calls and calls[-1].phase == "task" and not provider_failure:
                last = calls[-1]
                if last.attempt == attempt:
                    calls[-1] = DesignerCall(phase=last.phase, attempt=last.attempt, call=last.call,
                                             parsed_output_hash=last.parsed_output_hash,
                                             validation_feedback=feedback)
            if provider_failure:
                break
    if task is None or certificate is None or certificate.status != "CERTIFIED":
        # A pure communication task can be fully proved by the independent
        # interaction Runner even though the bounded transaction certifier marks
        # it UNKNOWN. Preserve both records and the distinction.
        interaction_ok = bool(interaction_episode and interaction_episode.outcome.strict_task_success is True
                              and interaction_episode.replay_verified)
        if task is None or certificate is None or not interaction_ok:
            status = "UNKNOWN" if certificate is not None and certificate.status == "UNKNOWN" else "BLOCKED"
            return DesignerRun(run_id="designer-" + digest([slot.record_hash, tuple(x.record_hash for x in calls)])[:20],
                status=status, sampling_slot=slot, distribution=distribution, scenario_spec=scenario,
                build_result=build, build_attempts=tuple(build_attempts), world_attempts=tuple(world_attempts),
                task_draft=draft_task, task=task, certification=certificate, interaction_episode=interaction_episode,
                task_attempts=tuple(task_attempts), calls=tuple(calls), validation_errors=tuple(errors))
    quality = _quality(scenario, build.world, task, certificate, history_signatures,
                       draft_task.parent_training_evidence_hashes, interaction_episode)
    return DesignerRun(
        run_id="designer-" + digest([slot.record_hash, scenario.record_hash, task.record_hash])[:20],
        status="CERTIFIED", sampling_slot=slot, distribution=distribution, scenario_spec=scenario,
        build_result=build, build_attempts=tuple(build_attempts), world_attempts=tuple(world_attempts),
        task_draft=draft_task, task=task, certification=certificate, interaction_episode=interaction_episode,
        task_attempts=tuple(task_attempts), pre_run_quality=quality, calls=tuple(calls), validation_errors=tuple(errors))


def post_run_quality(pre_run: ChallengeQualityVector, episode):
    """Return a diagnostic vector only; it never accepts or rejects a Designer Skill."""
    violations = []
    false_rejections = 0
    correct_rejections = 0
    blocked_illegal = 0
    legal_operations = 0
    transport_failures = 0
    for tool in episode.tool_executions:
        for row in tool.oracle.get("operations", []):
            violations.extend(row.get("violations", []))
            false_rejections += row.get("classification") == "false_rejection"
            correct_rejections += (row.get("classification") == "rejected_invalid_attempt"
                                   and row.get("operation_correct") is True)
            blocked_illegal += row.get("classification") == "rejected_invalid_attempt"
            legal_operations += row.get("classification") == "legal_execution"
    for call in episode.model_calls:
        error = call.response.get("error", {}) if isinstance(call.response, dict) else {}
        transport_failures += int(isinstance(error, dict) and str(error.get("code", "")).startswith((
            "PROVIDER_", "API_", "HTTP_")))
    return PostRunQualityVector(
        pre_run_quality_hash=pre_run.record_hash, execution_hash=episode.record_hash,
        replay_verified=episode.replay_verified, strict_task_success=episode.outcome.strict_task_success,
        final_goal_reached=episode.outcome.final_goal_reached,
        oracle_business_errors=sum(bool(row.get("success") and row.get("classification") == "successful_business_violation")
                                   for tool in episode.tool_executions for row in tool.oracle.get("operations", [])),
        false_rejections=false_rejections,
        protocol_failures=int(episode.status in ("service_protocol_error", "customer_protocol_error")),
        customer_failures=int(episode.status == "customer_protocol_error"),
        transport_failures=transport_failures, correct_rejections=correct_rejections,
        blocked_illegal_attempts=blocked_illegal, legal_operations=legal_operations,
        distinct_error_classes=tuple(sorted(set(violations))),
        model_calls=len(episode.model_calls), known_tokens=episode.total_tokens)
