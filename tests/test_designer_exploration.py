import copy
import json

import pytest

from usami_benchmark.designer import design_and_compile, designer_view, verify_designer_execution
from usami_benchmark.designer_exploration import (
    PROTOCOL, DialogueDesignerProposal, DesignerBudget, DesignerFailure,
    compile_proposal, inspect_world,
    verify_failed_journal,
)
from usami_benchmark.registry import default_spec
from usami_benchmark.tasks import ConstructionBudget
from usami_benchmark.worlds import freeze
from test_vast_usami import ScriptedClient, SPEC, answer, call
from test_vnext_open_compositions import multi_order_selection


@pytest.fixture(scope="module")
def frozen():
    return freeze(default_spec("aftersales", 0))


def proposal(frozen):
    raw = multi_order_selection(frozen).composition.model_dump(mode="json")
    raw.pop("protocol")
    raw.pop("frames")
    raw.pop("refusal_operations")
    return raw


def submit(args, identifier="submit"):
    return answer(calls=[call(identifier, "submit_frozen_world_task", args)])


def test_compact_view_and_bounded_read_tools_do_not_mutate_world(frozen):
    before = frozen.model_dump(mode="json")
    view = designer_view(frozen, protocol=PROTOCOL)
    assert "world" not in view and "customer_profiles_and_native_task_contracts" not in view
    assert designer_view(frozen) == view
    assert len(json.dumps(view)) < len(json.dumps(frozen.world)) / 10
    page = inspect_world(frozen, {"action": "list_profiles", "identity": "u0", "limit": 2})
    assert len(page["items"]) == 2 and page["total"] > 2
    detail = inspect_world(frozen, {"action": "read_profile", "profile_id": page["items"][0]["profile_id"]})
    assert detail["identity"] == "u0" and detail["facts"] and detail["related_objects"]
    rules = inspect_world(frozen, {"action": "read_rules"})
    assert "refunded" in rules["native_field_enums"]["lines"]["status"]
    with pytest.raises(ValueError):
        inspect_world(frozen, {"action": "read_objects", "collection": "__dict__"})
    with pytest.raises(ValueError):
        inspect_world(frozen, {"action": "read_objects", "collection": "orders", "ids": ["invented"]})
    assert frozen.model_dump(mode="json") == before


def test_high_level_schema_derives_exact_native_scope_and_certifies_multi_order(frozen):
    raw = proposal(frozen)
    assert "frames" not in DialogueDesignerProposal.model_json_schema()["properties"]
    _, certified = compile_proposal(frozen, raw, ConstructionBudget(max_nodes=512, max_depth=16))
    old = multi_order_selection(frozen)
    assert certified.selection.composition.goals == old.composition.goals
    assert certified.selection.composition.frames == old.composition.frames
    assert len(certified.selection.composition.profile_ids) == 2
    raw["frames"] = []
    with pytest.raises(ValueError):
        compile_proposal(frozen, raw, ConstructionBudget())


def test_cross_identity_and_invented_state_are_not_repaired(frozen):
    raw = proposal(frozen)
    raw["profile_ids"].append("profile_u1_order0_line1")
    with pytest.raises(ValueError, match="same authenticated identity"):
        compile_proposal(frozen, raw, ConstructionBudget())
    raw = proposal(frozen)
    raw["goals"][0]["accepted_values"] = ["resolved"]
    with pytest.raises(ValueError, match="native vocabulary"):
        compile_proposal(frozen, raw, ConstructionBudget())


def test_explore_reject_correct_and_exact_replay(frozen, tmp_path):
    good = proposal(frozen)
    bad = copy.deepcopy(good)
    bad["goals"][0]["accepted_values"] = ["resolved"]
    responses = [answer(calls=[
        call("profiles", "inspect_frozen_world", {"action": "list_profiles", "identity": "u0"}),
        call("rules", "inspect_frozen_world", {"action": "read_rules"}),
    ]), answer(calls=[
        call("profile", "inspect_frozen_world", {"action": "read_profile", "profile_id": good["profile_ids"][0]}),
        call("ready", "ready_to_submit", {}),
    ]), submit(bad, "bad"), submit(good, "good")]
    client = ScriptedClient(SPEC, responses)
    result = design_and_compile(frozen, client, ConstructionBudget(max_nodes=512, max_depth=16),
        prompt_context={"skill_snapshot_hash": "a" * 64, "skill_rendered": "An updated discovery skill."},
        protocol=PROTOCOL, designer_budget=DesignerBudget(max_exploration_calls=2),
        journal_path=tmp_path / "journal.json")
    assert len(client.requests) == 4
    assert client.requests[0]["tool_choice"] == "auto"
    assert all(request["tool_choice"]["function"]["name"] == "submit_frozen_world_task" for request in client.requests[2:])
    assert "An updated discovery skill." in result.request["messages"][0]["content"]
    assert any("native vocabulary" in (msg.get("content") or "") for msg in client.requests[-1]["messages"])
    assert result.metrics["valid_proposal_rate"] == 0.5
    assert result.metrics["reference_path_business_steps"] > 1
    assert verify_designer_execution(result)["verified"]
    assert verify_designer_execution(json.loads(result.model_dump_json()))["actual_online_calls"] == 0
    tampered = result.model_copy(deep=True)
    tampered.exchanges[0]["tool_results"][0]["data"]["items"][0]["identity"] = "fake"
    tampered.execution_hash = tampered.computed_hash()
    with pytest.raises(ValueError):
        verify_designer_execution(tampered)
    journal = json.loads((tmp_path / "journal.json").read_text())
    assert journal["proposal_attempts"] == 2 and journal["status"] == "CERTIFIED"


def test_at_most_three_corrections_and_preserved_failure(frozen, tmp_path):
    raw = proposal(frozen)
    raw["goals"][0]["accepted_values"] = ["invented"]
    client = ScriptedClient(SPEC, [submit(raw, f"bad-{i}") for i in range(4)])
    with pytest.raises(DesignerFailure, match="submission budget exhausted") as caught:
        design_and_compile(frozen, client, protocol=PROTOCOL,
            designer_budget=DesignerBudget(max_exploration_calls=0), journal_path=tmp_path / "journal.json")
    assert len(client.requests) == 4
    assert caught.value.journal["proposal_attempts"] == 4
    assert json.loads((tmp_path / "journal.json").read_text())["status"] == "BLOCKED"
    assert verify_failed_journal(frozen, caught.value.journal)["verified"]


def test_exploration_budget_and_read_errors_are_visible(frozen):
    good = proposal(frozen)
    client = ScriptedClient(SPEC, [answer(calls=[call("read", "inspect_frozen_world",
        {"action": "read_objects", "collection": "orders", "ids": ["missing"]})]), submit(good)])
    result = design_and_compile(frozen, client, ConstructionBudget(max_nodes=512, max_depth=16),
        protocol=PROTOCOL, designer_budget=DesignerBudget(max_exploration_calls=1))
    assert result.exchanges[0]["tool_results"][0]["status"] == "error"
    assert len(client.requests) == 2 and result.metrics["proposal_attempts"] == 1


def test_transport_failure_is_not_retried(frozen, tmp_path):
    client = ScriptedClient(SPEC, [RuntimeError("offline provider")])
    with pytest.raises(DesignerFailure, match="no retry") as caught:
        design_and_compile(frozen, client, protocol=PROTOCOL, journal_path=tmp_path / "journal.json")
    assert len(client.requests) == 1
    assert caught.value.journal["exchanges"][0]["transport_error"]["type"] == "RuntimeError"
    assert verify_failed_journal(frozen, caught.value.journal)["verified"]


def test_search_feedback_is_unproven_not_an_impossibility_claim(frozen):
    raw = proposal(frozen)
    client = ScriptedClient(SPEC, [submit(raw, f"limited-{i}") for i in range(4)])
    with pytest.raises(DesignerFailure) as caught:
        design_and_compile(frozen, client, ConstructionBudget(max_nodes=1, max_depth=1),
            protocol=PROTOCOL, designer_budget=DesignerBudget(max_exploration_calls=0))
    feedback = caught.value.journal["exchanges"][0]["feedback"]
    assert feedback["category"] == "search_unproven"
    assert "does not prove impossibility" in feedback["meaning"]
    assert verify_failed_journal(frozen, caught.value.journal)["verified"]


def test_incomplete_model_output_can_be_corrected_within_submission_budget(frozen):
    truncated = {"choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": "unfinished"}}]}
    client = ScriptedClient(SPEC, [truncated, submit(proposal(frozen))])
    result = design_and_compile(frozen, client, ConstructionBudget(max_nodes=512, max_depth=16),
        protocol=PROTOCOL, designer_budget=DesignerBudget(max_exploration_calls=0))
    assert result.metrics["proposal_attempts"] == 2
    assert verify_designer_execution(result)["verified"]


@pytest.mark.parametrize("domain", ["aftersales", "airline", "property", "education"])
def test_all_native_dialogue_domains_have_read_only_exploration(domain):
    world = freeze(default_spec(domain, 0))
    page = inspect_world(world, {"action": "list_profiles", "limit": 1})
    detail = inspect_world(world, {"action": "read_profile", "profile_id": page["items"][0]["profile_id"]})
    assert detail["facts"] and detail["related_objects"]
    assert inspect_world(world, {"action": "read_rules"})["native_field_enums"]


def test_reserved_exploration_supports_actual_corrections(frozen):
    raw = proposal(frozen)
    raw["goals"][0]["accepted_values"] = ["invented"]
    responses = [answer(calls=[call("first", "inspect_frozen_world", {"action": "read_rules"})]),
                 submit(raw, "bad-1"),
                 answer(calls=[call("inspect-more", "inspect_frozen_world", {"action": "list_profiles"})]),
                 submit(raw, "bad-2"), submit(raw, "bad-3"), submit(raw, "bad-4")]
    client = ScriptedClient(SPEC, responses)
    budget = DesignerBudget(max_exploration_calls=2, initial_exploration_calls=1, actionable_feedback=True)
    with pytest.raises(DesignerFailure) as caught:
        design_and_compile(frozen, client, protocol=PROTOCOL, designer_budget=budget)
    journal = caught.value.journal
    assert [row["stage"] for row in journal["exchanges"]] == ["exploration", "submission", "exploration", "submission", "submission", "submission"]
    assert journal["exchanges"][1]["feedback"]["remaining_exploration_calls"] == 1
    assert journal["exchanges"][3]["feedback"]["unchanged_submission"] is True
    assert journal["proposal_attempts"] == 4 and verify_failed_journal(frozen, journal)["verified"]
    # Old v2 journals omit these fields; their request and replay shape stays intact.
    assert set(DesignerBudget().model_dump(mode="json")) == {"max_exploration_calls", "max_revisions", "max_queries"}


def test_requested_profile_context_includes_immutable_order_and_evidence(frozen):
    raw = {"action": "read_profile", "profile_id": "profile_u0_order0_line0"}
    before = frozen.model_dump(mode="json")
    minimal = inspect_world(frozen, raw)
    linked = inspect_world(frozen, raw, include_related_objects=True)
    assert "orders" not in minimal["related_objects"]
    assert linked["related_objects"]["orders"]["u0_order0"] == frozen.world["orders"]["u0_order0"]
    assert linked["related_objects"]["evidence"]["photo_u0_order0_line0"] == frozen.world["evidence"]["photo_u0_order0_line0"]
    assert "u1_order0" not in linked["related_objects"]["orders"]
    assert sum(len(rows) for rows in linked["related_objects"].values()) <= 32
    assert designer_view(frozen, protocol=PROTOCOL)["clock"] == frozen.world["clock"]
    assert frozen.model_dump(mode="json") == before


def test_qwen_keeps_exploration_thinking_but_can_force_submission(frozen):
    from vast_coevo.models import ModelSpec
    spec = ModelSpec(model="dashscope/qwen3.7-plus", base_url="https://fixture.invalid/v1",
                     options={"enable_thinking": True})
    client = ScriptedClient(spec, [answer(calls=[call("ready", "ready_to_submit", {})]), submit(proposal(frozen))])
    result = design_and_compile(frozen, client, ConstructionBudget(max_nodes=512, max_depth=16), protocol=PROTOCOL)
    assert client.requests[0]["enable_thinking"] is True
    assert client.requests[1]["enable_thinking"] is False
    assert client.requests[1]["tool_choice"]["function"]["name"] == "submit_frozen_world_task"
    assert verify_designer_execution(result)["verified"]
