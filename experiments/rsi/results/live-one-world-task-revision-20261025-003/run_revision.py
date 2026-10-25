"""One directed live challenge revision on the unchanged 002 World; no training."""
from pathlib import Path
import importlib.util
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "experiments/rsi/results/live-one-world-one-task-qwen3.7-plus-20261025-002"
OUTPUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("original_minimal_run", SOURCE / "run_one.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class DirectedRevisionProvider(base.OpenAIDesignerProvider):
    def submit(self, phase, messages, model, **kwargs):
        instruction = (
            "This is a directed minimal diagnostic revision, not unrestricted exploration. "
            "Keep the existing frozen World and capability configuration. Submit exactly one remedy goal "
            "and one selector: the missing-parts hub with return_required explicitly false. "
            "Request refund only, quantity 1, target_stage settled. Do not include laptop or mouse goals. "
            "Do not invent a return/approval event, modify the World, supply IDs or proof witnesses. "
            "The Host will independently check the refund against the native approval policy."
        )
        return super().submit(phase, messages + [{"role": "user", "content": instruction}], model, **kwargs)


def main():
    # worlds/ and task-records/ are archived copies of the unchanged 002 inputs.
    original = json.loads((SOURCE / "summary.json").read_text())
    os.environ["USAMI_LLM_TIMEOUT"] = "180"
    client = base.JournalClient(base.OpenAICompatibleClient.from_env(), OUTPUT / "model-calls.jsonl")
    settings = client.settings
    snapshot = base.ModelSnapshot(settings.model, base.digest({"base_url": settings.base_url,
        "model": settings.model, "options": settings.options,
        "timeout_seconds": settings.timeout_seconds, "trust_env": settings.trust_env}))
    models = base.FrozenModels(snapshot, snapshot, snapshot)
    limits = base.Limits(model_calls=64, model_tokens=500000, episodes=4, tool_steps=500,
        research_steps=1000, cpu_seconds=7200, wall_seconds=10800,
        memory_bytes=134217728, source_bytes=65536, response_bytes=1048576)
    ledger = base.Ledger(limits)
    adapter = base.UsamiAdapter({}, OUTPUT / "native-episodes", model=base.LiveModel(client))
    verifier = base.NativePackageVerifier({}, base.Archive(OUTPUT / "task-records"))
    population = base.WorldPopulation(OUTPUT / "worlds", base.distribution(),
        base.OpenAIDesignerProvider(client), seed=84, max_attempts=1)
    period_ref = original["world_period_ref"]
    previous_ref = original["challenge_attempt"]["attempt_ref"]
    budget = base.EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
        max_service_tool_calls=72, max_model_calls=12)
    summary = {"kind": "directed-frozen-world-revision-diagnostic-v1", "training": "NOT_RUN",
        "world_generation_calls": 0, "challenge_submissions": 0, "service_episodes_started": 0,
        "customer": "deterministic AcceptingCustomer fixture", "model": settings.model,
        "timeout_seconds": settings.timeout_seconds, "world_period_ref": period_ref,
        "previous_attempt_ref": previous_ref, "status": "RUNNING"}
    stage = "verify_frozen_inputs"
    try:
        worlds = population.worlds(period_ref)
        assert len(worlds) == 1
        world = worlds[0][2].world
        summary["world_hash"] = world.state_hash
        assert world.state_hash == original["world_runs"][0]["build_result"]["world_hash"]
        hubs = [line for line in world.lines.values() if world.skus[line.sku_id].product_family == "hub"]
        assert len(hubs) == 1
        hub = hubs[0]
        merchant = world.merchants[world.orders[hub.order_id].merchant_id]
        summary["refund_policy_preflight"] = {"paid_cents": hub.allocated_paid_cents,
            "approval_limit_cents": merchant.refund_approval_limit_cents,
            "return_required": world.skus[hub.sku_id].return_required}
        assert not world.skus[hub.sku_id].return_required
        assert hub.allocated_paid_cents <= merchant.refund_approval_limit_cents
        from experiments.rsi.fixtures.open_world_validation import customer_binding
        bridge = base.OpenChallengeBridge(population, period_ref, adapter, verifier,
            customer_binding, episode_budget=budget, mode="reference")
        summary["capabilities"] = bridge.public_view()["task_certification_capabilities"]
        assert not summary["capabilities"]["return_receipt_event_configured"]
        stage = "challenge_revision_and_certification"
        summary["challenge_submissions"] = 1
        challenge = base.propose_open_challenge(DirectedRevisionProvider(client), bridge,
                                               previous_attempt_ref=previous_ref)
        summary["challenge_attempt"] = challenge
        if challenge["status"] != "CERTIFIED":
            summary.update(status="STOPPED_CHALLENGE_NOT_CERTIFIED", failed_stage=stage)
            return
        summary["challenge_replay_verification"] = bridge.verify_attempt(challenge["attempt_ref"])
        stage = "single_service_episode"
        source = 'def step(view, state):\n    if "model_observation" in view:\n        return {"kind": "ACTION", "state": state, "action": view["model_observation"]}\n    return {"kind": "MODEL", "state": state, "request": view["baseline_request"]}\n'
        service = base.ServiceSnapshot(snapshot.ref, base.ProgramArtifact("P", source), base.ExperienceArtifact())
        summary["service_episodes_started"] = 1
        result = adapter.run_task(service, challenge["receipt"]["task_ref"], models, ledger,
                                  base.DockerWorker(base.IMAGE, limits), seed=84)
        summary.update(task_result=result.__dict__, oracle_replay=adapter.replay(result.run_ref),
                       status="COMPLETED_ONE_EPISODE")
    except Exception as exc:
        summary.update(status="FAILED", failed_stage=stage, error_type=type(exc).__name__,
                       error=str(exc), traceback=traceback.format_exc())
    finally:
        summary["model_call_count"] = client.index
        summary["ledger"] = ledger.snapshot()
        (OUTPUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        client.close()
        print(json.dumps({k: summary.get(k) for k in ("status", "failed_stage", "error",
            "model_call_count", "world_hash", "challenge_submissions", "service_episodes_started")}, indent=2))


if __name__ == "__main__":
    main()
