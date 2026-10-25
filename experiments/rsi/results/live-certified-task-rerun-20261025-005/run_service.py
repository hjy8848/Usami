"""One live Service rerun of the unchanged, independently certified 003 task."""
from pathlib import Path
import importlib.util
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(__file__).resolve().parent
SOURCE = ROOT / "experiments/rsi/results/live-one-world-task-revision-20261025-003"
spec = importlib.util.spec_from_file_location("minimal_run", ROOT /
    "experiments/rsi/results/live-one-world-one-task-qwen3.7-plus-20261025-002/run_one.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
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
    original = json.loads((SOURCE / "summary.json").read_text())
    population = base.WorldPopulation(SOURCE / "worlds", base.distribution(),
        base.OpenAIDesignerProvider(client), seed=84, max_attempts=1)
    adapter = base.UsamiAdapter({}, OUTPUT / "native-episodes", model=base.LiveModel(client))
    verifier = base.NativePackageVerifier({}, base.Archive(OUTPUT / "task-records"))
    budget = base.EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
        max_service_tool_calls=72, max_model_calls=12)
    summary = {"kind": "certified-task-service-rerun-diagnostic-v1", "source_run": str(SOURCE),
        "training": "NOT_RUN", "world_generation_calls": 0, "challenge_generation_calls": 0,
        "customer": "unchanged deterministic AcceptingCustomer fixture", "service_episodes_started": 0,
        "model": settings.model, "timeout_seconds": settings.timeout_seconds, "status": "RUNNING"}
    stage = "independent_recertification"
    try:
        period_ref = original["world_period_ref"]
        worlds = population.worlds(period_ref)
        assert len(worlds) == 1 and worlds[0][2].world_hash == original["world_hash"]
        summary["world_hash"] = worlds[0][2].world_hash
        from experiments.rsi.fixtures.open_world_validation import customer_binding
        bridge = base.OpenChallengeBridge(population, period_ref, adapter, verifier,
            customer_binding, episode_budget=budget, mode="reference")
        receipt = bridge.certify(original["challenge_attempt"]["proposal"])
        assert receipt == original["challenge_attempt"]["receipt"]
        summary["receipt"] = receipt
        summary["challenge_replay_verification"] = bridge.verify_attempt(bridge.attempt_refs[-1])
        summary["capabilities"] = bridge.public_view()["task_certification_capabilities"]
        stage = "single_service_episode"
        policy = 'def step(view, state):\n    if "model_observation" in view:\n        return {"kind": "ACTION", "state": state, "action": view["model_observation"]}\n    return {"kind": "MODEL", "state": state, "request": view["baseline_request"]}\n'
        service = base.ServiceSnapshot(snapshot.ref, base.ProgramArtifact("P", policy), base.ExperienceArtifact())
        summary["service_snapshot_ref"] = service.ref
        summary["service_episodes_started"] = 1
        result = adapter.run_task(service, receipt["task_ref"], models, ledger,
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
            "model_call_count", "world_hash", "service_episodes_started")}, indent=2))


if __name__ == "__main__":
    main()
