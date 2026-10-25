"""ALFWorld TextWorld adapter smoke or one untrained RSI Core period."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from integrations.alfworld.adapter import AlfWorldAdapter, AlfWorldEnvironmentFactory
from integrations.alfworld.packages import (AlfWorldChallengeBridge,
                                             build_adaptation_provider,
                                             build_task_banks)
from integrations.alfworld.tasks import AlfWorldTaskRegistry, discover_tasks
from rsi_core.archive import Archive
from rsi_core.budget import Ledger
from rsi_core.evaluation import Evaluator, ServiceEvaluator
from rsi_core.isolation import DockerWorker
from rsi_core.programs import (DesignerSnapshot, ExperienceArtifact, ProgramArtifact,
                               ProgramStore, ServiceSnapshot)
from rsi_core.protocol import Completion, FrozenModels, Limits, ModelSnapshot, digest
from rsi_core.runtime import ResearchHost


DEFAULT_WORKER_IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"


class LiveResearchModel:
    """Bridge the existing OpenAI-compatible client to RSI and Service calls."""

    def __init__(self, client, transcript_path):
        self.client = client
        self.transcript_path = Path(transcript_path)
        self.calls = 0

    def _record(self, request, response, status):
        row = {"call": self.calls, "status": status, "request": request,
               "response": response}
        with self.transcript_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def complete(self, snapshot, request, *, max_tokens, seed):
        if snapshot.model_id != self.client.settings.model:
            raise ValueError("frozen model snapshot differs from configured provider model")
        if "response_schema" not in request:
            payload = {**self.client.settings.options, **request,
                       "max_tokens": max_tokens}
            self.calls += 1
            try:
                raw = self.client.complete(payload)
            except Exception as exc:
                self._record(payload, {"error_type": type(exc).__name__, "error": str(exc)}, "error")
                raise
            self._record(payload, raw, "ok")
            usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
            return Completion(raw, int(usage.get("prompt_tokens") or 0),
                              int(usage.get("completion_tokens") or 0))

        schema = request["response_schema"]
        messages = [
            {"role": "system", "content": "Return one structured result using the registered function tool."},
            {"role": "user", "content": json.dumps(request["request"], ensure_ascii=False,
                                                       sort_keys=True)},
        ]
        tool = {"type": "function", "function": {
            "name": "submit_research_result",
            "description": "Submit the result requested by RSI Core.",
            "parameters": schema}}
        payload = self.client.settings.request(messages, [tool])
        payload["max_tokens"] = max_tokens
        payload["parallel_tool_calls"] = False
        if "qwen" in snapshot.model_id.casefold():
            payload["tool_choice"] = "auto"
        else:
            payload["tool_choice"] = {"type": "function", "function": {
                "name": "submit_research_result"}}
        self.calls += 1
        try:
            raw = self.client.complete(payload)
        except Exception as exc:
            self._record(payload, {"error_type": type(exc).__name__, "error": str(exc)}, "error")
            raise
        self._record(payload, raw, "ok")
        choices = raw.get("choices", []) if isinstance(raw, dict) else []
        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        message = choices[0].get("message", {}) if len(choices) == 1 else {}
        calls = message.get("tool_calls", [])
        if len(calls) == 1:
            function = calls[0].get("function", {})
            if function.get("name") == "submit_research_result":
                try:
                    output = json.loads(function.get("arguments", ""))
                except (TypeError, ValueError):
                    output = function.get("arguments", "")
            else:
                output = {"unexpected_function": function.get("name", ""),
                          "arguments": function.get("arguments", "")}
        elif not calls and isinstance(message.get("content"), str):
            try:
                output = json.loads(message["content"])
            except ValueError:
                output = message["content"]
        else:
            output = {"invalid_tool_call_count": len(calls)}
        return Completion(output, int(usage.get("prompt_tokens") or 0),
                          int(usage.get("completion_tokens") or 0))


class SmokeWorker:
    """Fixed environment smoke policy; no model call or candidate code execution."""

    def invoke(self, program, view, state, ledger, scope):
        actions = view["admissible_actions"]
        if not actions:
            return {"kind": "ACTION", "state": state, "action": "look"}
        index = int(state.get("step", 0)) % len(actions)
        return {"kind": "ACTION", "state":{"step": int(state.get("step", 0)) + 1},
                "action": actions[index]}


def _limits():
    return Limits(model_calls=2500, model_tokens=5000000, episodes=512,
                  tool_steps=40000, research_steps=30000, cpu_seconds=25000,
                  wall_seconds=14400)


def _phase_budgets():
    return {
        "root": {"model_calls": 300, "model_tokens": 600000, "episodes": 8,
                 "tool_steps": 1200, "research_steps": 256, "cpu_seconds": 2400},
        "selection": {"model_calls": 140, "model_tokens": 280000, "episodes": 8,
                      "tool_steps": 1200, "research_steps": 256, "cpu_seconds": 2400},
        "reward": {"model_calls": 140, "model_tokens": 280000, "episodes": 8,
                   "tool_steps": 1200, "research_steps": 256, "cpu_seconds": 2400},
    }


def _self_edit_context(package_provider, task_catalogue):
    sampled = package_provider.sample_training_context(
        20261025, counts={"C_probe": 1, "C_select": 1, "C_reward": 1})
    return {"probe_packages": sampled.probe,
            "select_packages": sampled.selection,
            "reward_packages": sampled.reward,
            "seeds": (31, 47), "phase_budgets": _phase_budgets(),
            "sampling_ref": sampled.archive_ref,
            "public_view": {"domain": "alfworld-textworld",
                            "challenge_catalogue": task_catalogue}}


def _model_snapshots(client):
    settings = client.settings
    snapshot = ModelSnapshot(
        settings.model,
        digest({"base_url": settings.base_url, "model": settings.model,
                "options": settings.options, "timeout_seconds": settings.timeout_seconds,
                "trust_env": settings.trust_env}))
    return FrozenModels(snapshot, snapshot, snapshot)


def run_smoke(data_root, output, *, config_path=None, task_count=5, max_steps=50):
    if type(task_count) is not int or task_count < 1:
        raise ValueError("smoke task_count must be a positive integer")
    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = Archive(output / "archive")
    source_tasks = discover_tasks(data_root, splits=("train",))
    if len(source_tasks) < task_count:
        raise ValueError("ALFWorld train split has " + str(len(source_tasks))
                         + " supported tasks; smoke requested " + str(task_count))
    # Prefer one task per native task type, then fill remaining slots stably.
    representatives = {}
    for task in source_tasks:
        representatives.setdefault(task.task_type, task)
    selected = list(representatives.values())[:task_count]
    if len(selected) < task_count:
        selected_refs = {task.task_ref for task in selected}
        selected.extend(task for task in source_tasks if task.task_ref not in selected_refs
                        and len(selected) < task_count)
    registry = AlfWorldTaskRegistry(data_root, archive, selected)
    tasks = registry.tasks
    limits = _limits()
    models = FrozenModels(
        ModelSnapshot("alfworld-smoke-no-model", "fixed"),
        ModelSnapshot("alfworld-smoke-no-model", "fixed"),
        ModelSnapshot("alfworld-smoke-no-model", "fixed"))
    adapter = AlfWorldAdapter(tasks, output / "episodes",
                              AlfWorldEnvironmentFactory(data_root, config_path,
                                                         max_steps=max_steps),
                              max_steps=max_steps)
    policy = ProgramArtifact("P", "def step(view, state):\n    return {'kind':'ACTION','state':state,'action':view['admissible_actions'][0]}\n")
    ledger = Ledger(limits)
    results = []
    for index, task in enumerate(registry.tasks.values()):
        ledger.charge("environment", episodes=1)
        result = adapter.run_task(policy, task.task_ref, models, ledger, SmokeWorker(), seed=index)
        replay = adapter.replay(result.run_ref)
        results.append({"task_ref": task.task_ref, "task_type": task.task_type,
                        "status": result.status, "score": result.score,
                        "steps": result.tool_steps, "replay": replay})
    all_replays_verified = all(row["replay"].get("verified") is True for row in results)
    all_episodes_executed = (len(results) == task_count
                             and all(row["status"] == "VERIFIED" for row in results))
    summary = {"kind": "alfworld_environment_smoke_v1", "mode": "ENVIRONMENT_SMOKE",
               "status": "COMPLETED" if all_episodes_executed and all_replays_verified else "FAILED",
               "fixture_policy": True, "model_calls": 0,
               "episodes": results, "episode_count": len(results),
               "all_replays_verified": all_replays_verified,
               "usage": ledger.snapshot(),
               "claim_boundary": "Native ALFWorld TextWorld startup, actions, scoring and replay; no RSI period or model-quality claim."}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False,
                                                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def run_period_once(data_root, output, *, config_path=None, image=DEFAULT_WORKER_IMAGE,
                    tasks_per_set=1, max_steps=50):
    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive, store = Archive(output / "archive"), ProgramStore(output / "programs")
    source_tasks = discover_tasks(data_root, splits=("train", "valid_unseen"))
    registry = AlfWorldTaskRegistry(data_root, archive, source_tasks)
    p_source = (ROOT / "experiments/rsi/seeds/P0_alfworld.py").read_text(encoding="utf-8")

    from usami.service.client import OpenAICompatibleClient
    client = OpenAICompatibleClient.from_env()
    try:
        models = _model_snapshots(client)
        service0 = ServiceSnapshot(models.business.ref, ProgramArtifact("P", p_source),
                                   ExperienceArtifact())
        banks = build_task_banks(registry, archive, service0,
                                 tasks_per_set=tasks_per_set, audit_task_count=1,
                                 package_seed=20261025)
        task_catalogue = banks.challenge_catalogue()
        live_model = LiveResearchModel(client, output / "model-calls.jsonl")
        limits = _limits()
        host = ResearchHost(
            store, archive, DockerWorker(image, limits), live_model, models, Ledger(limits),
            max_steps=20, max_output_tokens=4096)
        adapter = AlfWorldAdapter(registry.tasks, output / "episodes",
                                  AlfWorldEnvironmentFactory(data_root, config_path,
                                                             max_steps=max_steps),
                                  max_steps=max_steps, model=live_model)
        service_evaluator = ServiceEvaluator(host, adapter, banks.task_provider)
        adaptation_evaluator = Evaluator(host, adapter)
        designer_source = (ROOT / "experiments/rsi/seeds/M0_alfworld.py").read_text(encoding="utf-8")
        designer0 = DesignerSnapshot(models.behavior, ProgramArtifact("M", designer_source))
        store.publish_service(service0)
        store.publish_designer(designer0)
        bridge = AlfWorldChallengeBridge(registry, banks.challenge_tasks)
        round_config = {
            "probe_tasks": banks.task_sets["service_probe"],
            "select_tasks": banks.task_sets["service_select"],
            "reward_tasks": banks.task_sets["service_reward"],
            "seeds": (11, 22), "phase_budgets": _phase_budgets(),
            "certify_challenge": bridge.certify,
            "public_view": {"domain": adapter.domain_id,
                            "challenge_catalogue": bridge.public_catalogue(),
                            "data_version": "alfworld-json-2.1.1",
                            "training_split": "train"}}
        result = None
        try:
            from rsi_core.period import run_period
            result = run_period(
                host, service_evaluator, adaptation_evaluator, designer0, service0,
                (round_config,),
                lambda final_service: _self_edit_context(
                    build_adaptation_provider(
                        registry, archive, final_service,
                        archive.load(banks.manifest_ref)["train_refs_by_role"],
                        package_seed=20261025),
                    task_catalogue))
            status = result["status"]
            error = ""
        except Exception as exc:
            status = "FAILED"
            error = type(exc).__name__ + ": " + str(exc)
            result = {"status": status, "error": error,
                      "cost": host.ledger.snapshot()}
        summary = {
            "kind": "alfworld_rsi_period_v1", "mode": "LIVE_RSI_NO_TRAINING",
            "status": status, "period": result,
            "data_version": "alfworld-json-2.1.1",
            "task_source_counts": {split: len(registry.by_split(split))
                                   for split in ("train", "valid_unseen")},
            "task_partition_manifest_ref": banks.manifest_ref,
            "service_task_sets": {key: asdict(value) for key, value in banks.task_sets.items()},
            "audit_task_set": asdict(banks.audit_task_set),
            "challenge_catalogue": bridge.public_catalogue(),
            "model_calls": live_model.calls,
            "model_transcript": str(output / "model-calls.jsonl"),
            "verl_training_runs": 0, "parameter_updates": 0,
            "training_status": "NOT_RUN",
            "error": error,
            "usage": host.ledger.snapshot(),
            "claim_boundary": "ALFWorld's registered train tasks ground M's abstract task-type proposals; no new ALFWorld worlds are generated, no held-out task is used for training, and no model weights are trained."}
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False,
                                                           indent=2, sort_keys=True) + "\n",
                                               encoding="utf-8")
        return summary
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke", "period"))
    parser.add_argument("--data-root", default=os.environ.get("ALFWORLD_DATA"),
                        help="ALFWORLD_DATA directory containing json_2.1.1")
    parser.add_argument("--config", default=os.environ.get("ALFWORLD_CONFIG"),
                        help="ALFWorld configs/base_config.yaml (or set ALFWORLD_CONFIG)")
    parser.add_argument("--output", required=True, help="New output directory")
    parser.add_argument("--image", default=DEFAULT_WORKER_IMAGE,
                        help="Existing pinned Docker worker image for a real RSI period")
    parser.add_argument("--tasks-per-set", type=int, default=1,
                        help="Distinct training tasks per probe/select/reward role")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--smoke-count", type=int, default=5)
    args = parser.parse_args()
    if not args.data_root:
        parser.error("set ALFWORLD_DATA or pass --data-root")
    if not args.config:
        parser.error("pass --config or set ALFWORLD_CONFIG to the ALFWorld base_config.yaml")
    if args.command == "smoke":
        summary = run_smoke(args.data_root, args.output, config_path=args.config,
                            task_count=args.smoke_count, max_steps=args.max_steps)
    else:
        summary = run_period_once(args.data_root, args.output, config_path=args.config,
                                  image=args.image, tasks_per_set=args.tasks_per_set,
                                  max_steps=args.max_steps)
    print(json.dumps({"summary": str(Path(args.output).resolve() / "summary.json"),
                      "status": summary["status"] if "status" in summary else "RECORDED",
                      "episodes": summary.get("episode_count", "period"),
                      "model_calls": summary.get("model_calls", 0)}, ensure_ascii=False))
    if (args.command == "smoke" and summary["status"] != "COMPLETED"
            or args.command == "period" and summary["status"] not in {"READY_FOR_TRAINING", "COMPLETED"}):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
