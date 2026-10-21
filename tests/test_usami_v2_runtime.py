"""P3/P4 focused tests: customer authority, one frozen-world episode and Replay."""
import json
from datetime import timedelta

import pytest

from usami_harness.models import digest
from usami_v2.commerce.models import ExternalEvent, Operation, case_id, quote_id
from usami_v2.runtime.agents import CustomerPrompt, ServiceAction, ServicePrompt
from usami_v2.runtime.agents import OpenAICustomerAgent, OpenAIServiceAgent
from usami_v2.runtime.customer import (
    CustomerDecision, CustomerProfile, CustomerRuntime, OfferPresentation, render_offer,
)
from usami_v2.runtime.runner import (
    EpisodeBudget, _execution, replay_episode, run_episode, save_episode, verify_episode_artifact,
)
from usami_v2.scenarios.builder import build_world
from usami_v2.scenarios.tasks import InformationObjective, RemedyGoal, TaskSpec
from test_usami_v2_builder import scene


def frozen(seed=17):
    result = build_world(scene(), seed)
    assert result.status == "SAT"
    return result.world, dict(result.private_aliases)


def refund_task(world, aliases):
    line_id = aliases["damaged"]
    return TaskSpec(
        task_id="runtime-refund", world_hash=world.state_hash,
        customer_id=aliases["customer"],
        customer_request="Please refund the damaged item line " + line_id + ".",
        remedy_goals=(RemedyGoal(goal_id="refund-damaged", line_id=line_id, quantity=1,
                                 allowed_remedies=("refund",), maximum_extra_charge_cents=0),),
        partition="train", source_distribution_hash=digest("P3/P4 focused runtime"))


class ScriptedRefundService:
    last_call = None
    uses_model = False

    def __init__(self, world, aliases):
        self.world, self.aliases, self.index = world, aliases, 0
        self.case = case_id(aliases["damaged"], (0,))
        self.quote = quote_id(self.case, 1)
        self.evidence = next(row.id for row in world.evidence.values()
                             if row.line_id == aliases["damaged"])

    def decide(self, prompt: ServicePrompt):
        assert not hasattr(prompt, "profile") and not hasattr(prompt, "task_goals")
        merchant = next(iter(self.world.merchants))
        line = self.aliases["damaged"]
        actions = [
            ServiceAction(kind="operation", operation=Operation(
                name="open_remedy_case", scope_id=merchant, resource_id=line,
                params={"quantity": 1, "issue": "damaged"})),
            ServiceAction(kind="operation", operation=Operation(
                name="verify_submitted_evidence", scope_id=merchant, resource_id=self.case,
                params={"evidence_id": self.evidence})),
            ServiceAction(kind="operation", operation=Operation(
                name="prepare_remedy_quote", scope_id=merchant, resource_id=self.case,
                params={"remedy": "refund", "target_sku_id": None,
                        "warehouse_id": None, "pickup_slot": None})),
            ServiceAction(kind="reply", message="Please confirm this exact refund quote.",
                          present_quote_id=self.quote, present_for="commit_accepted_quote"),
            ServiceAction(kind="operation", operation=Operation(
                name="commit_accepted_quote", scope_id=merchant, resource_id=self.quote, params={})),
            ServiceAction(kind="reply", message=self.aliases["damaged"] + ": refund status is released.",
                          subject_ids=(self.aliases["damaged"],)),
        ]
        action = actions[self.index]
        self.index += 1
        return action


class ScriptedCustomer:
    last_call = None
    uses_model = False

    def decide(self, prompt: CustomerPrompt, profile: CustomerProfile):
        if prompt.offer:
            return CustomerDecision(message="I accept this refund quote.",
                                    accept_quote_id=prompt.offer.quote_id,
                                    accept_operation=prompt.offer.operation,
                                    finish=True)
        return CustomerDecision(message="Thank you.", finish=True)


class ReadOnlyService:
    last_call = None
    uses_model = False

    def __init__(self, world, line_id):
        self.world, self.line_id, self.index = world, line_id, 0

    def decide(self, prompt: ServicePrompt):
        merchant = next(iter(self.world.merchants))
        if self.index == 0:
            action = ServiceAction(kind="operation", operation=Operation(
                name="get_refundable_balance", scope_id=merchant,
                resource_id=self.line_id, params={}))
        else:
            action = ServiceAction(kind="reply", message=self.line_id + ": quantity is 1.",
                                   subject_ids=(self.line_id,))
        self.index += 1
        return action


class NoConsentSandboxService:
    last_call = None
    uses_model = False

    def __init__(self, world, aliases):
        self.aliases, self.index = aliases, 0
        self.merchant = next(iter(world.merchants))
        self.case = case_id(aliases["damaged"], (0,))
        self.quote = quote_id(self.case, 1)
        self.evidence = next(row.id for row in world.evidence.values()
                             if row.line_id == aliases["damaged"])

    def decide(self, prompt):
        line = self.aliases["damaged"]
        actions = [
            ServiceAction(kind="operation", operation=Operation(
                name="open_remedy_case", scope_id=self.merchant, resource_id=line,
                params={"quantity": 1, "issue": "damaged"})),
            ServiceAction(kind="operation", operation=Operation(
                name="verify_submitted_evidence", scope_id=self.merchant, resource_id=self.case,
                params={"evidence_id": self.evidence})),
            ServiceAction(kind="operation", operation=Operation(
                name="prepare_remedy_quote", scope_id=self.merchant, resource_id=self.case,
                params={"remedy": "refund", "target_sku_id": None,
                        "warehouse_id": None, "pickup_slot": None})),
            ServiceAction(kind="operation", operation=Operation(
                name="commit_accepted_quote", scope_id=self.merchant, resource_id=self.quote, params={})),
            ServiceAction(kind="reply", message=line + ": refund status is released.", subject_ids=(line,)),
        ]
        action = actions[self.index]
        self.index += 1
        return action


class FinishCustomer:
    last_call = None
    uses_model = False

    def decide(self, prompt, profile):
        return CustomerDecision(message="Thanks.", finish=True)


def test_customer_quote_consent_is_exact_and_finish_waits_for_service_execution():
    world, aliases = frozen()
    task = refund_task(world, aliases)
    profile = CustomerProfile(customer_id=aliases["customer"],
                              delegated_line_ids=(aliases["damaged"],))
    record = run_episode(world, task, profile, ScriptedCustomer(), ScriptedRefundService(world, aliases),
                         budget=EpisodeBudget(max_customer_turns=3, max_service_decisions=10,
                                              max_service_tool_calls=8, max_model_calls=0))
    assert record.replay_verified
    assert record.status == "customer_finished"
    assert record.outcome.final_goal_reached is True
    assert record.outcome.strict_task_success is True
    assert len(record.tool_executions) == 4
    assert all(row.oracle["status"] == "pass" for row in record.tool_executions)
    assert any(event.kind == "customer_transition"
               and event.payload.get("decision", {}).get("finish") is True
               and event.payload.get("customer_event", {}).get("finish_allowed") is False
               for event in record.events)
    consent = next(iter(record.final_world.consents.values()))
    assert consent.operation == "commit_accepted_quote"
    assert consent.quote_id == next(iter(record.final_world.quotes))
    assert replay_episode(record).verified


def test_sandbox_business_violation_cannot_be_scored_as_strict_task_success():
    world, aliases = frozen()
    task = refund_task(world, aliases)
    profile = CustomerProfile(customer_id=aliases["customer"],
                              delegated_line_ids=(aliases["damaged"],))
    record = run_episode(world, task, profile, ScriptedCustomer(),
                         NoConsentSandboxService(world, aliases),
                         budget=EpisodeBudget(max_customer_turns=2, max_service_decisions=8,
                                              max_service_tool_calls=8, max_model_calls=0),
                         mode="sandbox")
    assert record.replay_verified and replay_episode(record).verified
    assert record.outcome.final_goal_reached is True
    assert record.outcome.strict_task_success is False
    assert any(row.goal_id == "service_operation_compliance" and row.status == "FAIL"
               for row in record.outcome.compliance)
    violation = next(row for tool in record.tool_executions for row in tool.oracle["operations"]
                     if row["classification"] == "successful_business_violation")
    assert violation["operation"] == "commit_accepted_quote"


def test_customer_runtime_rejects_cross_identity_scope_and_wrong_offer_binding():
    world, aliases = frozen()
    other = CustomerProfile(customer_id=aliases["customer"],
                            delegated_line_ids=(aliases["damaged"],))
    runtime = CustomerRuntime(other)
    initialized = runtime.initialize(world, "Please help with my damaged item.")
    delegation = next(iter(initialized.world.delegations.values()))
    assert delegation.source_customer_event_hash
    assert not initialized.world.consents

    # The Customer cannot accept an unpresented or different quote; a Service
    # request alone never creates the missing consent.
    with pytest.raises(ValueError, match="actually presented quote"):
        runtime.apply(initialized.world, CustomerDecision(
            accept_quote_id="quote-fabricated", accept_operation="commit_accepted_quote"),
            presentation=None, event_index=3)
    raw = scene().model_dump(mode="json", exclude={"record_hash"})
    raw["customer_aliases"] = ["customer", "other"]
    # The second Customer exists but owns no line in this world.
    built = build_world(type(scene()).model_validate(raw), 19)
    second_aliases = dict(built.private_aliases)
    with pytest.raises(ValueError, match="identity scope"):
        CustomerRuntime(CustomerProfile(customer_id=second_aliases["other"],
                                        delegated_line_ids=(second_aliases["damaged"],))).initialize(
                                            built.world, "Wrong identity")

    # Even a correctly hashed presentation cannot replace the actual quote
    # terms with cheaper terms before the Customer consents.
    world, aliases = frozen()
    profile = CustomerProfile(customer_id=aliases["customer"],
                              delegated_line_ids=(aliases["damaged"],))
    runtime = CustomerRuntime(profile)
    world = runtime.initialize(world, "Please refund my damaged item.").world
    service = ScriptedRefundService(world, aliases)
    for index in range(3):
        action = service.decide(None)
        world, _ = _execution(world, aliases["customer"], action.operation,
                               "tamper_setup_{:02d}".format(index), "reference")
    presentation = render_offer(world, service.quote, "commit_accepted_quote", "offer_10", 10,
                                "Please confirm this quote.", expected_customer_id=aliases["customer"])
    forged_data = presentation.model_dump(mode="json", exclude={"record_hash"})
    forged_data["rendered_terms"] = "Offer terms: refund 1 cent"
    forged = OfferPresentation.model_validate(forged_data)
    with pytest.raises(ValueError, match="terms differ from the actual business quote"):
        runtime.apply(world, CustomerDecision(accept_quote_id=service.quote,
            accept_operation="commit_accepted_quote"), presentation=forged, event_index=11)


def test_read_only_request_is_scored_from_delivered_fact_and_replayed(tmp_path):
    world, aliases = frozen()
    line = aliases["damaged"]
    text = "Please tell me the quantity for damaged line " + line + "."
    task = TaskSpec(
        task_id="read-quantity", world_hash=world.state_hash, customer_id=aliases["customer"],
        customer_request=text, information_goals=(InformationObjective(
            goal_id="quantity", subject_id=line, subject_mention="damaged line",
            fact_kind="quantity", public_request="quantity for damaged line"),),
        partition="train", source_distribution_hash=digest("P4 communication"))
    profile = CustomerProfile(customer_id=aliases["customer"])
    record = run_episode(world, task, profile, FinishCustomer(), ReadOnlyService(world, line),
                         budget=EpisodeBudget(max_customer_turns=2, max_service_decisions=4,
                                              max_service_tool_calls=2, max_model_calls=0))
    assert record.outcome.strict_task_success is True
    assert record.communication.fulfilled == 1
    assert record.replay_verified and replay_episode(record).verified
    artifact = tmp_path / "private" / "episode.json"
    save_episode(record, artifact)
    assert artifact.stat().st_mode & 0o077 == 0
    assert verify_episode_artifact(artifact)["verified"]
    with pytest.raises(FileExistsError):
        save_episode(record, artifact)


def test_replay_rejects_modified_event_and_model_context_is_not_service_visible():
    world, aliases = frozen()
    task = refund_task(world, aliases)
    profile = CustomerProfile(customer_id=aliases["customer"],
                              delegated_line_ids=(aliases["damaged"],))
    record = run_episode(world, task, profile, ScriptedCustomer(), ScriptedRefundService(world, aliases),
                         budget=EpisodeBudget(max_customer_turns=3, max_service_decisions=10,
                                              max_service_tool_calls=8, max_model_calls=0))
    raw = record.model_dump(mode="json")
    event = next(row for row in raw["events"] if row["kind"] == "service_reply")
    event["payload"]["message"]["text"] = "tampered reply"
    with pytest.raises(ValueError, match="content hash differs"):
        type(record).model_validate(raw)


def test_runner_rejects_duplicate_frozen_external_event_ids_before_execution():
    world, aliases = frozen()
    task = refund_task(world, aliases)
    profile = CustomerProfile(customer_id=aliases["customer"])
    event = ExternalEvent(id="duplicate-event", kind="stock_adjustment",
        target_id=next(iter(world.inventory)), at=world.clock + timedelta(days=1), integer_value=1)
    with pytest.raises(ValueError, match="schedule repeats an event ID"):
        run_episode(world, task, profile, FinishCustomer(), ReadOnlyService(world, aliases["damaged"]),
                    external_events=(event, event))


def test_explicit_openai_adapters_capture_request_and_raw_output_without_network():
    from usami.service.models import ModelSettings, ServiceError

    class RecordedClient:
        settings = ModelSettings(model="offline-fixture", base_url="https://example.invalid/v1")

        def __init__(self, response):
            self.response = response
            self.requests = []

        def complete(self, request):
            self.requests.append(request)
            return self.response

    def response(tool_name, arguments, finish_reason="tool_calls"):
        return {"choices": [{"finish_reason": finish_reason, "message": {
            "role": "assistant", "content": None, "tool_calls": [{
                "id": "call-offline", "type": "function", "function": {
                    "name": tool_name, "arguments": json.dumps(arguments)}}]}}],
            "usage": {"prompt_tokens": 13, "completion_tokens": 7}}

    customer_args = {"message": "Please help with my order.", "delegate_line_ids": ["line-own"],
        "allowed_preparations": ["open_remedy_case"], "accept_quote_id": None,
        "accept_operation": None, "reject_quote_id": None, "withdraw_delegation_ids": [],
        "disclose_fact_ids": [], "finish": False}
    customer_client = RecordedClient(response("customer_turn", customer_args))
    profile = CustomerProfile(customer_id="customer-own", delegated_line_ids=("line-own",))
    decision = OpenAICustomerAgent(customer_client).decide(
        CustomerPrompt(public_request="Help with line-own."), profile)
    assert decision.delegate_line_ids == ("line-own",)
    assert customer_client.requests[0]["tool_choice"]["function"]["name"] == "customer_turn"
    assert customer_client.requests[0]["stream"] is False

    service_args = {"message": "I will check the request.", "present_quote_id": None,
        "present_for": "commit_accepted_quote", "subject_ids": ["line-own"]}
    service_client = RecordedClient(response("respond_to_customer", service_args))
    service = OpenAIServiceAgent(service_client)
    action = service.decide(ServicePrompt(customer_id="customer-own",
        customer_request="Help with line-own.", observed_subject_ids=("customer-own", "line-own")))
    assert action.kind == "reply" and action.subject_ids == ("line-own",)
    assert action.call.request == service_client.requests[0]
    assert "PRIVATE CUSTOMER PROFILE" not in json.dumps(service_client.requests[0])

    malformed = response("respond_to_customer", service_args, finish_reason="length")
    broken_service = OpenAIServiceAgent(RecordedClient(malformed))
    with pytest.raises(ServiceError, match="complete structured function call"):
        broken_service.decide(ServicePrompt(customer_id="customer-own", customer_request="Help."))
    assert broken_service.last_call.response == malformed
