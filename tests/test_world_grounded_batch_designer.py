import copy
import json

import pytest

from usami.service.client import ModelSettings
from usami_benchmark.abstract_challenges import (
    BATCH_REVISION_PROTOCOL, PROTOCOL, AbstractChallenge, challenge_fingerprints, validate_challenge,
)
from usami_benchmark.designer_batch import (
    BatchDesignerConfig, TOOL_NAME, replay_run, run_batch,
)
from usami_benchmark.grounder import GroundingBudget, ground_challenge
from usami_benchmark.registry import default_spec
from usami_benchmark.world_index import build_world_index, public_domain_catalogue
from usami_benchmark.worlds import WorldPool, freeze
from usami_harness.models import digest


def _mixed_challenge(challenge_id="mixed-1"):
    return {
        "challenge_id": challenge_id,
        "hypothesis": "Can the service complete an eligible case while refusing an ineligible one?",
        "domain": "aftersales",
        "customer_request": "Please handle both issues using each purchase's actual details.",
        "entity_variables": [
            {"alias": "buyer_a", "type": "profile"}, {"alias": "buyer_b", "type": "profile"},
            {"alias": "line_a", "type": "line"}, {"alias": "line_b", "type": "line"},
        ],
        "entity_constraints": [
            {"alias": "line_a", "predicate": "eligible_for_case", "value": True},
            {"alias": "line_a", "predicate": "has_valid_evidence", "value": True},
            {"alias": "line_b", "predicate": "eligible_for_case", "value": False},
        ],
        "relationship_constraints": [
            {"type": "profile_for_line", "left": "buyer_a", "right": "line_a"},
            {"type": "profile_for_line", "left": "buyer_b", "right": "line_b"},
            {"type": "same_identity", "left": "buyer_a", "right": "buyer_b"},
            {"type": "distinct", "left": "line_a", "right": "line_b"},
        ],
        "objectives": [
            {"kind": "created_object_completion", "target": "line_a", "collection": "cases",
             "field": "status", "accepted_values": ["evidence_verified"]},
            {"kind": "correct_refusal", "target": "line_b", "operation": "open_case"},
        ],
        "required_customer_information": [
            {"profile_alias": "buyer_a", "fact_keys": ["line_id", "issue", "evidence_id"]},
            {"profile_alias": "buyer_b", "fact_keys": ["line_id", "issue"]},
        ],
    }


def _response(challenges, *, usage=True):
    row = {"protocol": PROTOCOL, "challenges": challenges}
    result = {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
        "tool_calls": [{"id": "batch-call-1", "type": "function", "function": {
            "name": TOOL_NAME, "arguments": json.dumps(row, sort_keys=True)}}]}}]}
    if usage:
        result["usage"] = {"prompt_tokens": 321, "completion_tokens": 97, "total_tokens": 418}
    return result


class ScriptedClient:
    def __init__(self, responses):
        self.settings = ModelSettings(model="offline-scripted", base_url="https://fixture.invalid/v1", options={})
        self.responses = list(responses)
        self.requests = []

    def complete(self, request):
        self.requests.append(copy.deepcopy(request))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return copy.deepcopy(response)


@pytest.fixture(scope="module")
def world_and_index():
    frozen = freeze(default_spec("aftersales", 1, "train"))
    return frozen, build_world_index(WorldPool([frozen]))


def test_registered_grammar_rejects_unknown_fields_code_and_ids(world_and_index):
    frozen, index = world_and_index
    valid = AbstractChallenge.model_validate(_mixed_challenge())
    assert validate_challenge(valid).challenge_hash == valid.challenge_hash
    assert challenge_fingerprints(valid)["structural"]

    bad = _mixed_challenge()
    bad["entity_constraints"][0] = {"alias": "line_a", "field": "__import__", "op": "eq", "value": "x"}
    with pytest.raises(ValueError, match="unknown field"):
        validate_challenge(bad)
    bad = _mixed_challenge()
    bad["entity_constraints"][0] = {"alias": "line_a", "predicate": "eval", "value": True}
    with pytest.raises(Exception):
        AbstractChallenge.model_validate(bad)
    bad = _mixed_challenge()
    bad["hypothesis"] += " profile_u1_order0_line0"
    with pytest.raises(ValueError, match="concrete generated-world identifiers"):
        validate_challenge(bad)

    catalogue = public_domain_catalogue(index, "aftersales", partitions=("train",))
    assert frozen.world["profiles"]
    assert not any(profile_id in json.dumps(catalogue) for profile_id in frozen.world["profiles"])


def test_grounder_binds_same_identity_mixed_goals_and_native_certificate_replays(world_and_index):
    frozen, index = world_and_index
    before = frozen.model_dump(mode="json")
    result = ground_challenge(_mixed_challenge(), index, GroundingBudget(max_matches=1, partition="train"))
    assert result.status == "GROUNDED"
    match = result.matches[0]
    assert len(match.profile_ids) == 2
    assert match.identity == frozen.world["profiles"][match.profile_ids[0]]["identity"]
    assert match.binding_hash == digest(match.binding)
    assert frozen.model_dump(mode="json") == before

    from usami_benchmark.tasks import ConstructionBudget, compile_task, verify_task
    task = compile_task(frozen, match.selection, ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1))
    assert verify_task(task)
    witness = task.dialogue_witnesses[0]
    assert witness.certificate.evaluation["created_completion_subgoals"] == [True]
    assert witness.certificate.evaluation["refusal_subgoals"] == [True]

    again = ground_challenge(_mixed_challenge(), index, GroundingBudget(max_matches=1, partition="train"))
    assert [m.binding_hash for m in again.matches] == [m.binding_hash for m in result.matches]


def test_no_match_and_tampered_world_index_are_explicit(world_and_index):
    frozen, index = world_and_index
    out_of_scope = ground_challenge(_mixed_challenge(), index,
        GroundingBudget(max_matches=1, partition="validation"))
    assert out_of_scope.status == "OUT_OF_SCOPE"
    with pytest.raises(ValueError, match="train/validation"):
        public_domain_catalogue(index, "aftersales", partitions=("heldout",))

    no_match = _mixed_challenge("absent"); no_match["objectives"] = [no_match["objectives"][0]]
    no_match["entity_variables"].append({"alias": "order_a", "type": "order"})
    no_match["relationship_constraints"] = [
        {"type": "profile_for_line", "left": "buyer_a", "right": "line_a"},
        {"type": "references", "left": "line_a", "right": "order_a"},
    ]
    no_match["required_customer_information"] = []
    no_match["entity_constraints"] = [
        {"alias": "line_a", "predicate": "within_case_window", "value": True},
        {"alias": "order_a", "field": "status", "op": "eq", "value": "processing"},
    ]
    row = ground_challenge(no_match, index, GroundingBudget(max_matches=1, partition="train"))
    assert row.status == "NO_MATCH"
    assert row.matches == []

    raw = index.model_dump(mode="json")
    raw["worlds"][0]["frozen"]["world"]["clock"] = "tampered"
    with pytest.raises(ValueError):
        type(index).model_validate(raw).checked()


def test_single_shot_calls_once_replays_grounding_and_detects_request_tampering(world_and_index):
    _, index = world_and_index
    client = ScriptedClient([_response([_mixed_challenge()])])
    client.settings = client.settings.model_copy(update={"options": {"max_tokens": 4096}})
    run = run_batch(index, client, BatchDesignerConfig(num_challenges=1,
        grounding=GroundingBudget(max_matches=1, partition="train")))
    assert len(client.requests) == 1
    assert "max_tokens" not in client.requests[0]
    assert run.request_revisions == [0] and run.response_revisions == [0]
    assert run.metrics["total_llm_calls"] == 1
    assert run.cost["total_tokens"] == 418 and run.cost["usage_complete"] is True
    assert run.candidates[0].final_status == "CERTIFIED"
    assert run.candidates[0].model_request_hash == digest(client.requests[0])
    replay = replay_run(run, index)
    assert replay["verified"] and replay["native_certificates_replayed"] == 1
    assert replay["service_executions"] == 0

    tampered = run.model_copy(deep=True)
    tampered.requests[0]["messages"][0]["content"] += " changed"
    tampered.run_hash = tampered.computed_hash()
    with pytest.raises(ValueError, match="recorded model request differs"):
        replay_run(tampered, index)


def test_single_shot_does_not_retry_schema_failure_and_records_missing_usage(world_and_index):
    _, index = world_and_index
    invalid = _mixed_challenge(); invalid["entity_constraints"][0]["predicate"] = "unknown_predicate"
    client = ScriptedClient([_response([invalid], usage=False)])
    run = run_batch(index, client, BatchDesignerConfig(num_challenges=1))
    assert len(client.requests) == 1
    assert run.metrics["schema_errors"] == 1
    assert run.candidates[0].abstract_status == "SCHEMA_INVALID"
    assert run.cost["usage_complete"] is False
    assert replay_run(run, index)["verified"]


def test_one_revision_is_bounded_and_replayed(world_and_index):
    _, index = world_and_index
    invalid = _mixed_challenge()
    invalid["entity_constraints"][0]["predicate"] = "unknown_predicate"
    client = ScriptedClient([_response([invalid]), _response([_mixed_challenge()])])
    run = run_batch(index, client, BatchDesignerConfig(protocol=BATCH_REVISION_PROTOCOL, num_challenges=1,
        grounding=GroundingBudget(max_matches=1, partition="train")))
    assert len(client.requests) == 2
    assert run.candidate_history[0].revision == 0 and run.candidate_history[1].revision == 1
    assert run.candidates[0].final_status == "CERTIFIED"
    assert replay_run(run, index)["verified"]


def test_unconfigured_client_is_not_counted_as_a_real_llm_call(world_and_index):
    _, index = world_and_index

    class Unavailable:
        settings = ModelSettings(model="unavailable", base_url="https://fixture.invalid/v1", options={})
        available = False
        unavailable_reason = "test credential unavailable"

    run = run_batch(index, Unavailable(), BatchDesignerConfig(num_challenges=1))
    assert run.status == "BLOCKED_EXTERNAL_MODEL"
    assert run.metrics["request_attempts"] == 1
    assert run.metrics["total_llm_calls"] == 0
    assert run.metrics["preflight_errors"] == 1 and run.metrics["transport_errors"] == 0
    assert run.cost["designer_api_calls"] == 0
    replay = replay_run(run, index)
    assert replay["verified"] and replay["model_calls_replayed_offline"] == 0
    assert replay["request_records_replayed_offline"] == 1


def test_offline_abc_comparison_uses_same_frozen_world_and_one_call_each(world_and_index, tmp_path):
    from experiments.vast_coevo.examples.compare_world_grounded_designer import run_comparison

    frozen, index = world_and_index
    grounded = ground_challenge(_mixed_challenge(), index, GroundingBudget(max_matches=1, partition="train"))
    assert grounded.status == "GROUNDED"
    proposal = grounded.matches[0].selection.composition.model_dump(mode="json")
    proposal.pop("protocol", None); proposal.pop("frames", None)
    v4_response = {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
        "tool_calls": [{"id": "v4-submit", "type": "function", "function": {
            "name": "submit_frozen_world_task", "arguments": json.dumps(proposal)}}]}}],
        "usage": {"prompt_tokens": 250, "completion_tokens": 70, "total_tokens": 320}}
    batch_response = _response([_mixed_challenge()])
    settings = {"model": "offline-paired", "base_url": "https://fixture.invalid/v1", "options": {}}
    v4_file = tmp_path / "v4.json"; v4_file.write_text(json.dumps({"model": settings, "responses": [v4_response]}))
    batch_file = tmp_path / "batch.json"; batch_file.write_text(json.dumps({"model": settings, "responses": [batch_response]}))
    report = run_comparison(index, tmp_path / "comparison", batch_count=1,
        v4_response=str(v4_file), batch_response=str(batch_file))
    assert report["A_v4"]["status"] == "CERTIFIED"
    assert report["B_world_grounded_batch"]["status"] == "COMPLETED"
    assert report["budget_control"]["api_call_matched"] is True
    assert report["budget_control"]["token_budget_matched"] is False
    assert report["C_rule_combination_sampling"]["cost"]["designer_api_calls"] == 0
