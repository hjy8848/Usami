"""P5 focused tests: two-stage proposal, provenance, proof and diagnostics."""
import json
from datetime import timedelta

import pytest

from usami_v2.runtime.agents import AgentCall
from usami.service.models import ModelSettings, ServiceError
from usami_v2.scenarios.distribution import (
    BusinessSource, BusinessStratum, DistributionSpec, sample_schedule,
)
from usami_v2.scenarios.designer import (
    DesignerTrainingEvidence, InformationDraft, OpenAIDesignerProvider, RemedyDraft, ScenarioDraft, TaskDraft,
    _chat, compile_task, design_and_certify,
)
from usami_v2.scenarios.task_certification import CustomerScenario, ProofBudget
from usami_v2.scenarios.builder import build_world
from test_usami_v2_builder import scene


def distribution_and_slot(seed):
    source = BusinessSource(source_id="unit-test-source", kind="synthetic_assumption",
                            reference="synthetic test fixture", version="1",
                            supported_claims=("offline designer protocol test",))
    stratum = BusinessStratum(stratum_id="single-order", weight=1,
                              weight_basis_source_id=source.source_id,
                              contexts=("damaged-item-remedy",))
    distribution = DistributionSpec(distribution_id="offline-designer-test", version=1,
        population_scope="one synthetic business fixture", sources=(source,), strata=(stratum,),
        split="train")
    return distribution, sample_schedule(distribution, seed, 1)[0]


def scenario_draft(name="scenario", natural_product_names=False):
    base = scene()
    skus = base.skus
    if natural_product_names:
        natural_skus = []
        for row in base.skus:
            if row.alias == "cable":
                natural_skus.append(row)
                continue
            data = row.model_dump(mode="json", exclude={"record_hash"})
            data["family"] = "electronics"
            data["attributes"] += [{"name": "brand", "value": "TechPro"},
                                   {"name": "product", "value": "laptop"}]
            natural_skus.append(type(row).model_validate(data))
        skus = tuple(natural_skus)
    return ScenarioDraft(
        scenario_id=name, merchant_alias=base.merchant_alias,
        customer_aliases=base.customer_aliases, skus=skus,
        warehouses=base.warehouses, orders=base.orders, stock=base.stock,
        default_stock=base.default_stock,
        refund_approval_limit_cents=base.refund_approval_limit_cents,
        constraints=base.constraints)


def task_draft(evidence_hashes=()):
    request = "Please replace the damaged device with a USB-C option within three days and with no more than $20 extra."
    return TaskDraft(
        task_id="designer-exchange", customer_alias="customer",
        customer_request=request,
        remedy_goals=({
            "goal_id": "replace-device", "line_alias": "damaged", "quantity": 1,
            "public_request_span": request,
            "subject_mention": "damaged device",
            "allowed_remedies": ["exchange"],
            "required_attributes": [{"name": "interface", "value": "USB_C"}],
            "maximum_extra_charge_cents": 2000,
            "latest_arrival_within_days": 3,
        },), parent_training_evidence_hashes=evidence_hashes)


def replace_sealed(row, **updates):
    data = row.model_dump(mode="json", exclude={"record_hash"})
    data.update(updates)
    return type(row).model_validate(data)


class RecordedDesigner:
    def __init__(self, world, task):
        self.world, self.task = world, task
        self.contexts = []

    def submit(self, phase, messages, model):
        self.contexts.append((phase, messages))
        output = self.world if phase == "world" else self.task
        request = {"phase": phase, "messages": messages}
        response = {"choices": [{"message": {"role": "assistant", "content": "offline fixture"}}]}
        return output, AgentCall(role="designer", request=request, response=response)


class CorrectingDesigner:
    def __init__(self, world, invalid_task, valid_task):
        self.world, self.tasks, self.contexts = world, [invalid_task, valid_task], []

    def submit(self, phase, messages, model):
        self.contexts.append((phase, messages))
        output = self.world if phase == "world" else self.tasks.pop(0)
        raw = {"phase": phase, "attempt": len(self.contexts)}
        return output, AgentCall(role="designer", request=raw,
            response={"choices": [{"message": {"role": "assistant", "content": "offline correction fixture"}}]})


class TimeoutDesigner:
    def __init__(self):
        self.calls = 0
        self.last_call = None

    def submit(self, phase, messages, model):
        self.calls += 1
        request = {"phase": phase, "messages": messages}
        self.last_call = AgentCall(role="designer", request=request,
            response={"error": {"code": "PROVIDER_TIMEOUT",
                                "provider_response": {"timeout_phase": "ReadTimeout"}}})
        raise ServiceError("PROVIDER_TIMEOUT", "LLM request timed out; no retry performed",
                           {"timeout_phase": "ReadTimeout"})


class FixedCompletionClient:
    def __init__(self, arguments):
        self.settings = ModelSettings(model="offline-test", base_url="http://localhost/v1")
        self.response = {"choices": [{"message": {"role": "assistant", "tool_calls": [{
            "id": "call-1", "type": "function", "function": {
                "name": "submit_customer_task", "arguments": arguments,
            },
        }]}, "finish_reason": "tool_calls"}]}

    def complete(self, request):
        return self.response


def proof_customer(world, task):
    return CustomerScenario(customer_id=task.customer_id,
                           delegated_line_ids=tuple(row.line_id for row in task.remedy_goals),
                           maximum_extra_charge_cents=2000,
                           latest_arrival=world.clock + timedelta(days=3))


def run_designer(seed, evidence):
    distribution, slot = distribution_and_slot(seed)
    training_hash = evidence.source_record_hash
    provider = RecordedDesigner(scenario_draft(), task_draft((training_hash,)))
    run = design_and_certify(provider, distribution, slot,
        proof_budget=ProofBudget(max_plan_candidates=128, max_operation_steps=24, max_witnesses=2),
        allowed_training_hashes=(training_hash,), training_evidence=(evidence,),
        customer_scenario_factory=proof_customer, max_attempts=2)
    return run, provider


def test_two_stage_designer_builds_frozen_world_and_certified_task_with_provenance():
    evidence = DesignerTrainingEvidence(
        source_record_hash="a" * 64, partition="train",
        summary="Service asked for confirmation before committing the quoted remedy.",
        observed_events=({"kind": "service_reply", "text": "Please confirm the quote."},))
    run, provider = run_designer(21, evidence)
    assert run.status == "CERTIFIED"
    assert len(run.calls) == 2 and [call.phase for call in run.calls] == ["world", "task"]
    assert len(run.world_attempts) == len(run.build_attempts) == 1
    assert run.world_attempts[0].status == "SAT"
    assert run.task.partition == "train"
    assert run.task.protocol == "commerce-task-v2"
    assert run.task.remedy_goals[0].public_request_span in run.task.customer_request
    assert run.task.source_distribution_hash == run.distribution.record_hash
    assert run.task.parent_training_evidence_hashes == (evidence.source_record_hash,)
    assert run.certification.business_reachability_certified
    assert run.pre_run_quality.business_valid and run.pre_run_quality.diagnosability
    assert run.pre_run_quality.decision_power == "diagnostic_only"
    task_context = json.loads(provider.contexts[1][1][1]["content"])
    rendered = json.dumps(task_context, sort_keys=True)
    assert evidence.source_record_hash in rendered
    assert task_context["available_context"]["task_certification_capabilities"]["actual_delivery_certifiable"] is False
    assert task_context["available_context"]["task_certification_capabilities"]["information_goals_certifiable"] is False
    assert "candidate_hash" not in rendered and "witness_hashes" not in rendered
    assert run.pre_run_quality.quality_status == "business_certified_interaction_pending"


def test_id_and_seed_renaming_do_not_create_new_decision_structure():
    evidence = DesignerTrainingEvidence(source_record_hash="b" * 64, partition="train",
                                        summary="A training-only interaction observation.")
    left, _ = run_designer(31, evidence)
    right, _ = run_designer(32, evidence)
    assert left.build_result.world_hash != right.build_result.world_hash
    assert set(dict(left.build_result.private_aliases).values()) != set(dict(right.build_result.private_aliases).values())
    assert left.pre_run_quality.structural_signature == right.pre_run_quality.structural_signature
    assert left.pre_run_quality.world_hash != right.pre_run_quality.world_hash


def test_task_compiler_feedback_is_bounded_and_does_not_rebuild_frozen_world():
    evidence = DesignerTrainingEvidence(source_record_hash="e" * 64, partition="train",
                                        summary="A Service decision from a training episode.")
    valid_template = task_draft((evidence.source_record_hash,))
    goal_data = valid_template.remedy_goals[0].model_dump(mode="json", exclude={"record_hash"})
    goal_data["line_alias"] = "unknown-line"
    invalid = TaskDraft(task_id=valid_template.task_id, customer_alias=valid_template.customer_alias,
        customer_request=valid_template.customer_request, remedy_goals=(RemedyDraft.model_validate(goal_data),),
        parent_training_evidence_hashes=valid_template.parent_training_evidence_hashes)
    provider = CorrectingDesigner(scenario_draft(), invalid,
                                  task_draft((evidence.source_record_hash,)))
    distribution, slot = distribution_and_slot(63)
    run = design_and_certify(provider, distribution, slot,
        proof_budget=ProofBudget(max_plan_candidates=128, max_operation_steps=24, max_witnesses=2),
        allowed_training_hashes=(evidence.source_record_hash,), training_evidence=(evidence,),
        customer_scenario_factory=proof_customer, max_attempts=2)
    assert run.status == "CERTIFIED"
    assert len(run.calls) == 3 and [row.phase for row in run.calls] == ["world", "task", "task"]
    assert len(run.build_attempts) == len(run.world_attempts) == 1
    assert [row.status for row in run.task_attempts] == ["REJECTED", "CERTIFIED"]
    correction = json.loads(provider.contexts[2][1][1]["content"])
    assert any("unknown order-line alias" in row for row in correction["validator_feedback"])


def test_provider_timeout_blocks_without_spending_proposal_correction_attempts():
    provider = TimeoutDesigner()
    distribution, slot = distribution_and_slot(64)
    run = design_and_certify(provider, distribution, slot,
        customer_scenario_factory=proof_customer, max_attempts=3)

    assert run.status == "BLOCKED"
    assert provider.calls == 1
    assert len(run.calls) == len(run.world_attempts) == 1
    assert run.world_attempts[0].status == "ERROR"
    assert "world provider failed: PROVIDER_TIMEOUT" in run.validation_errors[0]
    assert "proposal rejected" not in run.validation_errors[0]
    assert run.calls[0].validation_feedback == ""


@pytest.mark.parametrize("arguments,code,feedback", [
    ("{}", "EMPTY_TOOL_ARGUMENTS", "empty object"),
    ('{"task_id":"only"}', "DESIGNER_SCHEMA_INVALID", "customer_alias"),
])
def test_empty_and_incomplete_task_tool_calls_are_classified_and_preserved(arguments, code, feedback):
    client = FixedCompletionClient(arguments)
    provider = OpenAIDesignerProvider(client)
    with pytest.raises(ServiceError) as error:
        provider.submit("task", [{"role": "user", "content": "test"}], TaskDraft)
    assert error.value.code == code
    assert feedback in str(error.value)
    assert provider.last_call is not None
    assert provider.last_call.response == client.response


def test_post_run_quality_is_separate_diagnostic_not_a_selection_rule():
    from usami_v2.scenarios.designer import post_run_quality
    evidence = DesignerTrainingEvidence(source_record_hash="c" * 64, partition="train",
                                        summary="Training sample")
    run, _ = run_designer(41, evidence)
    fake_episode = type("Episode", (), {
        "record_hash": "d" * 64,
        "replay_verified": True,
        "outcome": type("Result", (), {"strict_task_success": False, "final_goal_reached": False})(),
        "tool_executions": (), "status": "agent_error", "model_calls": (), "total_tokens": 0,
    })()
    vector = post_run_quality(run.pre_run_quality, fake_episode)
    assert vector.decision_power == "diagnostic_only"
    assert vector.strict_task_success is False and vector.model_calls == 0


def test_designer_cannot_attach_unmentioned_transaction_goal():
    import pytest
    with pytest.raises(ValueError, match="copied verbatim"):
        TaskDraft(task_id="hidden-goal", customer_alias="customer",
            customer_request="Please refund the damaged item.",
            remedy_goals=({"goal_id": "exchange", "line_alias": "damaged", "quantity": 1,
                           "public_request_span": "Please exchange my laptop instead.",
                           "subject_mention": "laptop",
                           "allowed_remedies": ["exchange"]},))


def test_task_proposal_schema_and_feedback_explain_verbatim_public_quote():
    schema = TaskDraft.model_json_schema()["$defs"]["RemedyDraft"]["properties"]
    assert "exact, contiguous substring" in schema["public_request_span"]["description"]
    assert "appears inside public_request_span" in schema["subject_mention"]["description"]
    assert "exchange or reship" in schema["allowed_remedies"]["description"]
    assert "actual receipt" in schema["target_stage"]["description"]

    distribution, slot = distribution_and_slot(65)
    messages = _chat("task", {"world_hash": "a" * 64}, distribution, slot,
                     errors=("public_request_span must be copied verbatim",))
    instruction = messages[0]["content"]
    assert "never paraphrase" in instruction
    assert "replace the span with text copied exactly" in instruction


def test_natural_product_names_and_replacement_intent_compile_against_frozen_world():
    request = ("I need my damaged TechPro laptop replaced with a USB-C option within three days "
               "and with no more than $20 extra.")
    draft = TaskDraft(task_id="natural-laptop-replacement", customer_alias="customer",
        customer_request=request, remedy_goals=({
            "goal_id": "replace-laptop", "line_alias": "damaged", "quantity": 1,
            "public_request_span": request, "subject_mention": "TechPro laptop",
            "allowed_remedies": ["exchange", "reship"],
            "required_attributes": [{"name": "interface", "value": "USB_C"}],
            "maximum_extra_charge_cents": 2000, "latest_arrival_within_days": 3,
            "target_stage": "settled",
        },))
    distribution, slot = distribution_and_slot(67)
    scenario = scenario_draft("natural-product", natural_product_names=True).compile(distribution)
    built = build_world(scenario, slot.seed)
    assert built.status == "SAT"
    task = compile_task(draft, scenario, built, distribution)
    assert task.remedy_goals[0].line_id == dict(built.private_aliases)["damaged"]
    assert task.remedy_goals[0].target_stage == "settled"
    assert task.remedy_goals[0].allowed_remedies == ("exchange", "reship")

    provider = RecordedDesigner(scenario_draft("natural-product", natural_product_names=True), draft)
    run = design_and_certify(provider, distribution, slot,
        proof_budget=ProofBudget(max_plan_candidates=128, max_operation_steps=24, max_witnesses=2),
        customer_scenario_factory=proof_customer, max_attempts=1)
    assert run.status == "CERTIFIED"
    context = json.loads(provider.contexts[1][1][1]["content"])["available_context"]
    assert context["task_certification_capabilities"]["actual_delivery_certifiable"] is False
    assert context["task_certification_capabilities"]["information_goals_certifiable"] is False


def test_task_compiler_gives_actionable_feedback_for_uncertifiable_targets_and_bad_info_aliases():
    distribution, slot = distribution_and_slot(68)
    scenario_draft_value = scenario_draft()
    scenario = scenario_draft_value.compile(distribution)
    built = build_world(scenario, slot.seed)

    delivered = task_draft()
    goal = replace_sealed(delivered.remedy_goals[0], target_stage="delivered")
    delivered = replace_sealed(delivered, remedy_goals=(goal,))
    with pytest.raises(ValueError, match="actual delivery is not certified.*settled"):
        compile_task(delivered, scenario, built, distribution)

    information = TaskDraft(task_id="customer-alias-info", customer_alias="customer",
        customer_request="Please tell me the refund status for my order.", information_goals=({
            "goal_id": "status", "subject_alias": "customer", "subject_mention": "my order",
            "fact_kind": "refund_status", "public_request": "Please tell me the refund status for my order.",
        },))
    with pytest.raises(ValueError, match="selected Customer's owned order or order-line alias"):
        compile_task(information, scenario, built, distribution, interaction_certifier_available=True)

    line_request = "Please tell me the refund status for my damaged device."
    line_information = TaskDraft(task_id="owned-line-info", customer_alias="customer",
        customer_request=line_request, information_goals=({
            "goal_id": "status", "subject_alias": "damaged", "subject_mention": "damaged device",
            "fact_kind": "refund_status", "public_request": line_request,
        },))
    compiled_information = compile_task(
        line_information, scenario, built, distribution, interaction_certifier_available=True)
    assert compiled_information.information_goals[0].subject_id == dict(built.private_aliases)["damaged"]

    supported_alias_goal = replace_sealed(information.information_goals[0], subject_alias="purchase")
    unsupported_information = replace_sealed(information, information_goals=(supported_alias_goal,))
    with pytest.raises(ValueError, match="require a natural-runtime interaction certifier"):
        compile_task(unsupported_information, scenario, built, distribution)


def test_grounded_bounds_cannot_exceed_the_customer_request():
    distribution, slot = distribution_and_slot(69)
    scenario = scenario_draft().compile(distribution)
    built = build_world(scenario, slot.seed)
    draft = task_draft()
    goal = replace_sealed(draft.remedy_goals[0], maximum_extra_charge_cents=None)
    draft = replace_sealed(draft, remedy_goals=(goal,))
    with pytest.raises(ValueError, match="public extra-charge limit must be included"):
        compile_task(draft, scenario, built, distribution)


@pytest.mark.parametrize("request_text,remedies", [
    ("I need the laptop replaced within five days.", ("exchange", "reship")),
    ("Please send me the correct black ones for the mouse I ordered black but got something else.", ("reship",)),
])
def test_natural_replacement_and_wrong_item_requests_name_supported_remedies(request_text, remedies):
    from usami_v2.scenarios.tasks import request_names_remedy

    assert request_names_remedy(request_text, remedies)
    assert not request_names_remedy("I don't want a replacement for the damaged laptop.", ("exchange",))
