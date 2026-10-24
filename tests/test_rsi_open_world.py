"""Open Benchmark -> RSI integration, separate from autonomous model evidence."""
from pathlib import Path
import json

import pytest

from rsi_core.archive import Archive
from integrations.rsi_usami.adapter import UsamiAdapter
from integrations.rsi_usami.packages import NativePackageVerifier
from integrations.rsi_usami.open_world import WorldPopulation, OpenChallengeBridge, run_open_period
from usami_v2.scenarios.designer import TaskDraft
from usami_v2.scenarios.grounding import AbstractChallenge, GroundingBudget, ground_challenge
from experiments.rsi.fixtures.open_world_validation import (
    ProceduralWorldProvider, context, customer_binding, distribution, proposal,
)


def pool(tmp_path, split="train", seed=84):
    population = WorldPopulation(tmp_path, distribution(split=split), ProceduralWorldProvider(), seed=seed)
    ref = population.next_period(3)
    return population, ref


def bridge(tmp_path, population, ref):
    archive = Archive(tmp_path / "archive")
    adapter = UsamiAdapter({}, tmp_path / "native")
    verifier = NativePackageVerifier({}, archive)
    return OpenChallengeBridge(population, ref, adapter, verifier, customer_binding)


def test_world_distribution_continues_after_resume_with_structural_variation(tmp_path):
    population, first = pool(tmp_path)
    assert len(set(population.load_period(first)["structural_signatures"])) >= 2
    first_hashes = {build.world_hash for _, _, build in population.worlds(first)}
    from integrations.rsi_usami.open_world import world_structure
    from usami_v2.scenarios.builder import build_world
    from usami_v2.scenarios.schema import ScenarioSpec
    _, spec, built = population.worlds(first)[0]
    reseeded = build_world(spec, built.seed + 1)
    assert built.world_hash != reseeded.world_hash
    assert world_structure(spec, built) == world_structure(spec, reseeded)
    data = spec.model_dump(mode="json", exclude={"record_hash"})
    for sku in data["skus"]:
        sku.pop("record_hash", None)
        sku["family"] = "renamed-" + sku["family"]
    renamed = ScenarioSpec.model_validate(data)
    assert world_structure(spec, built) == world_structure(renamed, build_world(renamed, built.seed))
    resumed = WorldPopulation(tmp_path, distribution(), ProceduralWorldProvider(), seed=84)
    second = resumed.next_period(3)
    assert resumed.load_period(second)["previous_ref"] == first
    assert first_hashes.isdisjoint({build.world_hash for _, _, build in resumed.worlds(second)})
    assert resumed.load_period(second)["schedule"] != resumed.load_period(first)["schedule"]
    # Only the existing World phase is used, never a pre-authored TaskDraft.
    assert all(call["phase"] == "world" for value in resumed.load_period(second)["world_runs"] for call in value["calls"])
    with pytest.raises(ValueError, match="changed"):
        WorldPopulation(tmp_path, distribution(split="heldout"), ProceduralWorldProvider(), seed=84)


def test_abstract_challenge_reuses_native_goal_contract_and_multiple_binding_selection(tmp_path):
    population, ref = pool(tmp_path)
    challenge = AbstractChallenge.model_validate(proposal(True))
    assert isinstance(challenge, TaskDraft)
    result = ground_challenge(challenge, population.worlds(ref), GroundingBudget(selection_seed=17))
    assert result.status == "GROUNDED" and len(result.candidates) > 1
    assert result == ground_challenge(challenge, population.worlds(ref), GroundingBudget(selection_seed=17))
    for candidate in result.candidates:
        _, spec, build = next(row for row in population.worlds(ref) if row[0] == candidate.world_ref)
        selected = dict(candidate.line_binding)
        assert len(set(selected.values())) == 2
        owners = {o.customer_alias for o in spec.orders if any(l.alias in selected.values() for l in o.lines)}
        assert owners == {candidate.customer_alias}
        assert all(goal.line_alias in selected.values() for goal in candidate.draft.remedy_goals)
    bad = proposal()
    bad["remedy_goals"][0]["public_request_span"] = "An invented refund request."
    with pytest.raises(ValueError, match="verbatim"):
        AbstractChallenge.model_validate(bad)
    bad = proposal()
    bad["customer_request"] += " line_123456789abc"
    with pytest.raises(ValueError, match="concrete"):
        AbstractChallenge.model_validate(bad)


def test_no_match_budget_and_relations_are_explicit(tmp_path):
    population, ref = pool(tmp_path)
    bad = proposal()
    bad["line_selectors"][0]["family"] = "nonexistent-family"
    assert ground_challenge(bad, population.worlds(ref)).status == "NO_MATCH"
    budget = ground_challenge(proposal(True), population.worlds(ref), GroundingBudget(max_bindings=1))
    assert budget.search_truncated
    relational = proposal(True)
    relational["line_relations"] = [{"left": "item", "right": "other", "kind": "different_order"}]
    result = ground_challenge(relational, population.worlds(ref))
    assert result.status == "GROUNDED"
    for candidate in result.candidates:
        _, spec, _ = next(row for row in population.worlds(ref) if row[0] == candidate.world_ref)
        orders = {line.alias: order.alias for order in spec.orders for line in order.lines}
        assert len({orders[alias] for _, alias in candidate.line_binding}) == 2


def test_reference_registration_replay_and_scope_failures(tmp_path):
    population, ref = pool(tmp_path / "worlds")
    integration = bridge(tmp_path, population, ref)
    manifest = integration.public_view()["task_certification_capabilities"]
    assert manifest["return_receipt_event_configured"] is False
    assert manifest["policy_review_event_configured"] is False
    assert "world_hash" not in manifest and "customer_scopes" not in manifest
    receipt = integration.certify(proposal(True))
    assert receipt["status"] == "CERTIFIED"
    assert integration.verify_attempt(integration.attempt_refs[-1])["verified"]
    record = integration.archive.load(integration.attempt_refs[-1])
    assert len(record["grounding"]["candidates"]) > 1
    selected = next(a for a in record["proof_attempts"] if a["candidate_hash"] == record["selected"])
    assert selected["certificate"]["business_reachability_certified"]
    assert selected["certificate"]["interaction_certified"] is False
    assert integration.certify(proposal(True)) == receipt
    assert len(integration.adapter.tasks) == len(integration.verifier.tasks) == 1
    impossible = proposal(True, "impossible")
    impossible["customer_request"] = impossible["customer_request"].replace("3 days", "0 days")
    impossible["remedy_goals"][1]["public_request_span"] = impossible["remedy_goals"][1]["public_request_span"].replace("3 days", "0 days")
    impossible["remedy_goals"][1]["latest_arrival_within_days"] = 0
    rejected = integration.certify(impossible)
    assert rejected == {"status": "UNVERIFIED", "reason_code": "REFERENCE_UNPROVEN"}
    assert integration.verify_attempt(integration.attempt_refs[-1])["verified"]
    unknown = proposal(True, "unsupported")
    unknown["remedy_goals"][1]["target_stage"] = "delivered"
    assert integration.certify(unknown)["status"] == "UNVERIFIED"
    assert integration.verify_attempt(integration.attempt_refs[-1])["verified"]
    heldout, test_ref = pool(tmp_path / "heldout", split="heldout")
    with pytest.raises(ValueError, match="validation/heldout"):
        bridge(tmp_path / "leak", heldout, test_ref)
    forged = proposal()
    forged["parent_training_evidence_hashes"] = ["a" * 64]
    assert integration.certify(forged)["reason_code"] == "UNAUTHORIZED_TRAINING_EVIDENCE"
    path = integration.archive.root / (integration.attempt_refs[0] + ".json")
    data = json.loads(path.read_text())
    data["selected"] = "tampered"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity"):
        integration.verify_attempt(integration.attempt_refs[0])


def test_catalogue_has_no_native_ids_private_bindings_or_answers(tmp_path):
    population, ref = pool(tmp_path)
    value = json.dumps(population.catalogue(ref))
    for _, spec, build in population.worlds(ref):
        assert all(entity_id not in value for _, entity_id in build.private_aliases)
        assert all(row.alias not in value for row in spec.orders)
    for key in ("private_aliases", "witness_hashes", "evidence_valid", "oracle", "certificate_ref"):
        assert key not in value


def test_two_formal_rsi_periods_use_multiple_worlds_native_runtime_and_probe(tmp_path):
    config = context(tmp_path)
    first = run_open_period(world_count=3, **config)
    host = config["host"]
    config["service"] = host.store.load(first["rsi_period"]["output_service_ref"])
    config["designer"] = host.store.load(first["rsi_period"]["output_designer_ref"])
    second = run_open_period(world_count=3, **config)
    episode_worlds, goal_shapes = set(), set()
    for execution in (first, second):
        assert execution["rsi_period"]["status"] == "READY_FOR_TRAINING"
        group = host.archive.load(execution["rsi_period"]["service_rounds"][0]["group_ref"])
        assert group["status"] == "USABLE"
        for root_ref in group["root_refs"]:
            root = host.archive.load(root_ref)
            kinds = [row["event"]["kind"] for row in root["events"]]
            assert "challenge_certification" in kinds and "baseline_execution" in kinds
            observations = [row["event"]["value"] for row in root["events"] if row["event"]["kind"] == "observation"]
            assert any(row["kind"] == "PROBE" for row in observations)
            initial = next(row["event"]["input"]["view"] for row in root["events"] if row["event"]["kind"] == "decision")
            rendered = json.dumps(initial)
            for _, _, build in config["population"].worlds(execution["world_period_ref"]):
                assert all(native_id not in rendered for _, native_id in build.private_aliases)
            assert "open_world_catalogue" in initial
        for attempt_ref in execution["challenge_attempt_refs"]:
            record = host.archive.load(attempt_ref)
            assert record["receipt"]["status"] == "CERTIFIED"
            goal_shapes.add(tuple(tuple(g["allowed_remedies"]) for g in record["proposal"]["remedy_goals"]))
    from usami_v2.runtime.runner import EpisodeRecord
    adapter = config["service_evaluator"].adapter
    for ref, path in adapter.runs.items():
        episode = EpisodeRecord.model_validate_json(path.read_text())
        assert adapter.replay(ref)["verified"]
        assert episode.outcome.final_goal_reached is True, episode.terminal_reason
        assert episode.outcome.safety_violations.status == "PASS"
        episode_worlds.add(episode.initial_world.state_hash)
    assert len(episode_worlds) >= 3 and len(goal_shapes) >= 2
    assert first["world_period_ref"] != second["world_period_ref"]
    assert first["rsi_period"]["training_status"] == second["rsi_period"]["training_status"] == "NOT_RUN"


def test_native_return_receipt_capability_remains_available(tmp_path):
    from usami_v2.scenarios.designer import ScenarioDraft
    from usami_v2.scenarios.task_certification import CustomerScenario
    from usami_v2.runtime.customer import CustomerProfileV2

    class ReturnWorlds(ProceduralWorldProvider):
        def submit(self, phase, messages, model):
            draft, call = super().submit(phase, messages, model)
            data = draft.model_dump(mode="json", exclude={"record_hash"})
            for sku in data["skus"]:
                sku.pop("record_hash", None)
                sku["return_required"] = True
            return ScenarioDraft.model_validate(data), call

    def binding(world, task):
        profile, original, factory = customer_binding(world, task)
        data = profile.model_dump(mode="json", exclude={"record_hash"})
        data["return_pickup_slot"] = "weekday-evening"
        return CustomerProfileV2.model_validate(data), CustomerScenario(
            customer_id=original.customer_id, delegated_line_ids=original.delegated_line_ids,
            return_pickup_slot="weekday-evening", return_received_after_days=2), factory

    population = WorldPopulation(tmp_path / "return-worlds", distribution(), ReturnWorlds(), seed=84)
    ref = population.next_period(2)
    integration = bridge(tmp_path, population, ref)
    assert integration.certify(proposal())["status"] == "UNVERIFIED"
    assert integration.verify_attempt(integration.attempt_refs[-1])["verified"]
    from integrations.rsi_usami.open_world import propose_open_challenge
    from usami_v2.runtime.agents import AgentCall
    class CaptureRevision:
        def submit(self, phase, messages, model):
            self.feedback = json.loads(messages[-1]["content"])["rejection"]
            return model.model_validate(proposal()), AgentCall(role="designer", request={"messages": messages},
                                                              response={"fixture": True})
    capture = CaptureRevision()
    propose_open_challenge(capture, integration, previous_attempt_ref=integration.attempt_refs[-1])
    assert capture.feedback["compiler_feedback"] == [
        "this task requires a return-receipt event that is not configured for certification"]
    configured = OpenChallengeBridge(population, ref, integration.adapter, integration.verifier, binding,
        capability_options={"return_receipt_event_configured": True})
    assert configured.certify(proposal())["status"] == "CERTIFIED"
    assert configured.verify_attempt(configured.attempt_refs[-1])["verified"]


def test_live_submission_api_records_provider_output_and_controlled_revision(tmp_path):
    from integrations.rsi_usami.open_world import propose_open_challenge
    from usami_v2.runtime.agents import AgentCall
    population, ref = pool(tmp_path / "worlds")
    integration = bridge(tmp_path, population, ref)
    invalid = proposal()
    invalid["line_selectors"][0]["family"] = "nonexistent"
    rejected = integration.certify(invalid)
    attempt_ref = integration.attempt_refs[-1]
    assert rejected["reason_code"] == "NO_MATCH"

    class RecordedProvider:
        def submit(self, phase, messages, model):
            self.messages = messages
            output = model.model_validate(proposal(True))
            return output, AgentCall(role="designer", request={"messages": messages}, response={"fixture": True})

    provider = RecordedProvider()
    result = propose_open_challenge(provider, integration, previous_attempt_ref=attempt_ref)
    assert result["status"] == "CERTIFIED"
    last_message = json.loads(provider.messages[-1]["content"])
    assert last_message["rejection"] == rejected
    assert set(last_message) == {"instruction", "prior_proposal", "rejection"}
    with pytest.raises(ValueError, match="certified challenge"):
        propose_open_challenge(provider, integration, previous_attempt_ref=result["attempt_ref"])
