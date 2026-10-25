"""One live World + one live Challenge + one native Service episode; no RSI training."""
from pathlib import Path
import copy
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(__file__).resolve().parent

from rsi_core.archive import Archive
from rsi_core.budget import Ledger
from rsi_core.isolation import DockerWorker
from rsi_core.programs import ExperienceArtifact, ProgramArtifact, ServiceSnapshot
from rsi_core.protocol import Completion, FrozenModels, Limits, ModelSnapshot, digest
from integrations.rsi_usami.adapter import UsamiAdapter
from integrations.rsi_usami.open_world import OpenChallengeBridge, WorldPopulation, propose_open_challenge
from integrations.rsi_usami.packages import NativePackageVerifier
from usami.service.client import OpenAICompatibleClient
from usami_v2.runtime.runner import EpisodeBudget
from usami_v2.scenarios.designer import OpenAIDesignerProvider
from usami_v2.scenarios.distribution import BusinessSource, BusinessStratum, DistributionSpec

IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"


class JournalClient:
    def __init__(self, inner, transcript):
        self.inner, self.settings, self.transcript = inner, inner.settings, Path(transcript)
        self.index = 0

    def _redact(self, value):
        return self.inner._redact(value)

    def close(self):
        self.inner.close()

    def _write(self, value):
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()

    @staticmethod
    def _safe(raw):
        value = copy.deepcopy(raw)
        for choice in value.get("choices", []) if isinstance(value, dict) else []:
            message = choice.get("message") if isinstance(choice, dict) else None
            if isinstance(message, dict):
                message.pop("reasoning_content", None)
        return value

    def complete(self, request):
        self.index += 1
        row = {"call_index": self.index, "request": request,
               "request_hash": digest(request), "status": "pending"}
        try:
            response = self.inner.complete(request)
        except Exception as exc:
            row.update({"status": "error", "error_type": type(exc).__name__,
                        "error_code": getattr(exc, "code", ""), "error": str(exc),
                        "provider_response": getattr(exc, "response", None)})
            self._write(row)
            raise
        response = self._safe(response)
        row.update({"status": "ok", "provider_response": response})
        self._write(row)
        return response


class LiveModel:
    def __init__(self, client):
        self.client = client

    def complete(self, snapshot, request, *, max_tokens, seed):
        if snapshot.model_id != self.client.settings.model:
            raise ValueError("frozen model differs from the configured provider")
        payload = dict(request)
        payload["max_tokens"] = max_tokens
        raw = self.client.complete(payload)
        usage = raw.get("usage", {})
        return Completion(raw, int(usage.get("prompt_tokens") or 0),
                          int(usage.get("completion_tokens") or 0))


def distribution():
    source = BusinessSource(source_id="synthetic-one-world-live", kind="synthetic_assumption",
        reference="One-off live diagnostic; synthetic world design stratum, not an empirical population",
        version="2026-10-25", supported_claims=("single-world interface diagnostic only",))
    return DistributionSpec(distribution_id="usami-one-world-one-task-live", version=1,
        population_scope="one synthetic multi-line commerce world", sources=(source,),
        strata=(BusinessStratum(stratum_id="multi-line-mixed-issues", weight=1,
            weight_basis_source_id=source.source_id,
            contexts=("One customer owns an order with multiple product families and distinct issues.",)),),
        max_generation_attempts=1, split="train")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    os.environ["USAMI_LLM_TIMEOUT"] = "180"
    raw_client = OpenAICompatibleClient.from_env()
    client = JournalClient(raw_client, OUTPUT / "model-calls.jsonl")
    settings = client.settings
    snapshot = ModelSnapshot(settings.model, digest({"base_url": settings.base_url,
        "model": settings.model, "options": settings.options,
        "timeout_seconds": settings.timeout_seconds, "trust_env": settings.trust_env}))
    models = FrozenModels(snapshot, snapshot, snapshot)
    model = LiveModel(client)
    limits = Limits(model_calls=64, model_tokens=500000, episodes=4, tool_steps=500,
        research_steps=1000, cpu_seconds=7200, wall_seconds=10800,
        memory_bytes=134217728, source_bytes=65536, response_bytes=1048576)
    ledger = Ledger(limits)
    adapter = UsamiAdapter({}, OUTPUT / "native-episodes", model=model)
    verifier = NativePackageVerifier({}, Archive(OUTPUT / "task-records"))
    episode_budget = EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
        max_service_tool_calls=72, max_model_calls=12)
    population = WorldPopulation(OUTPUT / "worlds", distribution(),
        OpenAIDesignerProvider(client), seed=84, max_attempts=1)
    summary = {"kind": "one-world-one-task-live-diagnostic-v1", "model": settings.model,
        "timeout_seconds": settings.timeout_seconds, "world_slots": 1, "world_attempts_per_slot": 1,
        "challenge_submissions": 1, "service_episodes": 0, "training": "NOT_RUN",
        "status": "RUNNING", "output": str(OUTPUT)}
    stage = "world_generation"
    try:
        period_ref = population.next_period(1)
        worlds = population.worlds(period_ref)
        summary["world_period_ref"] = period_ref
        summary["world_count_sat"] = len(worlds)
        summary["world_slots"] = population.load_period(period_ref)["schedule"]
        summary["world_runs"] = population.load_period(period_ref)["world_runs"]
        if len(worlds) != 1:
            summary.update({"status": "STOPPED_WORLD_NOT_SAT", "failed_stage": stage})
            return

        from experiments.rsi.fixtures.open_world_validation import customer_binding
        bridge = OpenChallengeBridge(population, period_ref, adapter, verifier, customer_binding,
                                     episode_budget=episode_budget, mode="reference")
        stage = "challenge_generation_and_certification"
        challenge = propose_open_challenge(OpenAIDesignerProvider(client), bridge)
        summary["challenge_attempt"] = challenge
        if challenge.get("status") != "CERTIFIED":
            summary.update({"status": "STOPPED_CHALLENGE_NOT_CERTIFIED", "failed_stage": stage})
            return
        verification = bridge.verify_attempt(challenge["attempt_ref"])
        summary["challenge_replay_verification"] = verification

        stage = "single_service_episode"
        delegate = '''def step(view, state):\n    if "model_observation" in view:\n        return {"kind": "ACTION", "state": state, "action": view["model_observation"]}\n    return {"kind": "MODEL", "state": state, "request": view["baseline_request"]}\n'''
        service = ServiceSnapshot(snapshot.ref, ProgramArtifact("P", delegate), ExperienceArtifact())
        worker = DockerWorker(IMAGE, limits)
        task_ref = challenge["receipt"]["task_ref"]
        task_result = adapter.run_task(service, task_ref, models, ledger, worker, seed=84)
        replay = adapter.replay(task_result.run_ref)
        summary.update({"service_episodes": 1, "task_result": task_result.__dict__,
                        "oracle_replay": replay, "service_run_ref": task_result.run_ref,
                        "strict_task_success": task_result.feedback.get("outcome", {}).get("strict_task_success"),
                        "final_goal_reached": task_result.feedback.get("outcome", {}).get("final_goal_reached"),
                        "forbidden_behavior": task_result.forbidden_behavior,
                        "status": "COMPLETED_ONE_EPISODE"})
    except Exception as exc:
        summary.update({"status": "FAILED", "failed_stage": stage,
                        "error_type": type(exc).__name__, "error": str(exc),
                        "traceback": traceback.format_exc()})
    finally:
        summary["model_call_count"] = client.index
        summary["ledger"] = ledger.snapshot()
        summary["world_population_refs"] = list(population.period_refs)
        (OUTPUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
        client.close()
        print(json.dumps({key: summary.get(key) for key in (
            "status", "failed_stage", "error_code", "error", "model_call_count", "world_count_sat",
            "challenge_submissions", "service_episodes", "strict_task_success", "final_goal_reached",
            "forbidden_behavior")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
