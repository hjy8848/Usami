"""One-world, one-challenge live diagnostic of the RSI P/K evolution path.

The world is reused from the previous live run. M0 proposes one challenge,
the fixed parent Service runs it, M0 proposes a complete P/K candidate, and
that candidate runs on the same frozen challenge. A one-shot M self-edit is
also recorded after the Service root. There is no independent selection set,
formal period promotion, or parameter training in this diagnostic.
"""
from dataclasses import asdict
from pathlib import Path
import importlib.util
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(__file__).resolve().parent
WORLD_RUN = ROOT / "experiments/rsi/results/live-one-world-task-revision-20261025-003"
PARENT_SERVICE_RUN = ROOT / "experiments/rsi/results/live-certified-task-rerun-20261025-005"
WORLD_SOURCE_RUN = ROOT / "experiments/rsi/results/live-one-world-one-task-qwen3.7-plus-20261025-002"
IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _one_shot_m0(source):
    old = "if attempt >= 3:"
    if source.count(old) != 2:
        raise RuntimeError("M0 challenge retry contract changed; refusing to patch implicitly")
    return source.replace(old, "if attempt >= 1:")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "summary.json").exists():
        raise RuntimeError("this diagnostic output already exists; refusing to overwrite it")
    os.environ["USAMI_LLM_TIMEOUT"] = "180"

    base = _load("live_open_world_base", WORLD_SOURCE_RUN / "run_one.py")
    service_run = _load("live_service_rerun", PARENT_SERVICE_RUN / "run_service.py")
    live_minimal = _load("live_research_model", WORLD_SOURCE_RUN.parent /
                         "live-minimal-qwen3.7-plus-20261025-001" / "run_minimal.py")

    from rsi_core.archive import Archive
    from rsi_core.budget import Ledger
    from rsi_core.programs import (ExperienceArtifact, ProgramArtifact, ProgramStore,
                                   ServiceSnapshot)
    from rsi_core.protocol import FrozenModels, Limits, ModelSnapshot, TaskResult, digest
    from rsi_core.runtime import ResearchHost
    from rsi_core.isolation import DockerWorker
    from integrations.rsi_usami.adapter import UsamiAdapter
    from integrations.rsi_usami.open_world import OpenChallengeBridge, WorldPopulation
    from integrations.rsi_usami.packages import NativePackageVerifier
    from usami.service.client import OpenAICompatibleClient
    from usami_v2.runtime.runner import EpisodeBudget
    from usami_v2.scenarios.designer import OpenAIDesignerProvider
    from experiments.rsi.fixtures.open_world_validation import customer_binding

    output = {
        "kind": "rsi-single-world-single-challenge-evolution-diagnostic-v1",
        "status": "RUNNING",
        "model": "",
        "timeout_seconds": 180,
        "world_count": 1,
        "challenge_attempt_limit": 1,
        "service_episodes_expected": 2,
        "parameter_training": "NOT_RUN",
        "independent_selection": "NOT_RUN_SINGLE_CHALLENGE_DIAGNOSTIC",
        "failed_stage": "configuration",
        "source_world_run": str(WORLD_RUN),
        "source_service_episode": str(PARENT_SERVICE_RUN),
        "started_at": __import__("datetime").datetime.now().astimezone().isoformat(),
    }
    client = None
    ledger = None
    try:
        client = service_run.base.JournalClient(
            OpenAICompatibleClient.from_env(), OUTPUT / "model-calls.jsonl")
        settings = client.settings
        output["model"] = settings.model
        snapshot = ModelSnapshot(settings.model, digest({
            "base_url": settings.base_url, "model": settings.model,
            "options": settings.options, "timeout_seconds": settings.timeout_seconds,
            "trust_env": settings.trust_env}))
        models = FrozenModels(snapshot, snapshot, snapshot)
        limits = Limits(model_calls=64, model_tokens=500000, episodes=2, tool_steps=600,
                        research_steps=512, cpu_seconds=7200, wall_seconds=10800,
                        memory_bytes=134217728, source_bytes=65536, response_bytes=1048576)
        ledger = Ledger(limits)
        archive = Archive(OUTPUT / "research-archive")
        store = ProgramStore(OUTPUT / "programs")
        worker = DockerWorker(IMAGE, limits)
        model = live_minimal.LiveResearchModel(client)
        adapter = UsamiAdapter({}, OUTPUT / "native-episodes",
                               model=service_run.base.LiveModel(client))
        verifier = NativePackageVerifier({}, Archive(OUTPUT / "task-records"))
        episode_budget = EpisodeBudget(max_customer_turns=8, max_service_decisions=80,
                                       max_service_tool_calls=72, max_model_calls=64)

        source_world = json.loads((WORLD_RUN / "summary.json").read_text(encoding="utf-8"))
        parent_episode = json.loads((PARENT_SERVICE_RUN / "summary.json").read_text(encoding="utf-8"))
        world_period_ref = source_world["world_period_ref"]
        population = WorldPopulation(WORLD_RUN / "worlds", base.distribution(),
                                     OpenAIDesignerProvider(client), seed=84, max_attempts=1)
        worlds = population.worlds(world_period_ref)
        if len(worlds) != 1 or worlds[0][2].world_hash != parent_episode["world_hash"]:
            raise RuntimeError("the frozen one-World input differs from the preceding certified run")
        output["world_period_ref"] = world_period_ref
        output["world_hash"] = worlds[0][2].world_hash

        bridge = OpenChallengeBridge(population, world_period_ref, adapter, verifier,
                                     customer_binding, episode_budget=episode_budget,
                                     mode="reference")
        policy_source = (
            'def step(view, state):\n'
            '    if "model_observation" in view:\n'
            '        return {"kind": "ACTION", "state": state, "action": view["model_observation"]}\n'
            '    return {"kind": "MODEL", "state": state, "request": view["baseline_request"]}\n'
        )
        parent = ServiceSnapshot(snapshot.ref, ProgramArtifact("P", policy_source),
                                 ExperienceArtifact())
        store.save(parent)

        m0_path = ROOT / "experiments/rsi/seeds/M0.py"
        m0_source = _one_shot_m0(m0_path.read_text(encoding="utf-8"))
        m0 = ProgramArtifact("M", m0_source)
        m0.check(limits.source_bytes)
        store.save(m0)
        output["input_refs"] = {"service": parent.ref, "m0_one_shot": m0.ref}
        output["previous_live_episode_reference"] = {
            "run_ref": parent_episode["task_result"]["run_ref"],
            "task_ref": parent_episode["receipt"]["task_ref"],
            "world_hash": parent_episode["world_hash"],
            "used_as_current_baseline": False,
        }

        current_results = {}

        def certify(proposal):
            receipt = bridge.certify(proposal)
            if receipt.get("status") == "CERTIFIED":
                bridge.verify_attempt(bridge.attempt_refs[-1])
            return receipt

        def run_baseline(service, task_ref):
            result = adapter.run_task(service, task_ref, models, ledger, worker, seed=84)
            current_results["baseline"] = result
            return {"service_ref": service.ref, "task_ref": task_ref,
                    "run_ref": result.run_ref, "score": result.score,
                    "status": result.status,
                    "feedback": adapter.research_feedback(result),
                    "replay_verified": result.replay_verified}

        def probe(candidate, task_ref):
            result = adapter.run_task(candidate, task_ref, models, ledger, worker, seed=84)
            current_results["candidate"] = result
            return {"score": result.score, "status": result.status,
                    "feedback": adapter.research_feedback(result),
                    "run_ref": result.run_ref,
                    "replay_verified": result.replay_verified}

        public_view = {**bridge.public_view(),
                       "diagnostic_scope": "one frozen train World; one M-proposed Challenge; no held-out data",
                       "previous_live_episode_ref": parent_episode["task_result"]["run_ref"]}
        output["failed_stage"] = "service_improvement_root"
        service_root = ResearchHost(store, archive, worker, model, models, ledger,
                                    max_steps=24, max_output_tokens=16384)
        service_result = service_root.run(
            m0, parent, "IMPROVE_SERVICE", public_view, (), probe,
            certify_challenge=certify, run_baseline=run_baseline, seed=20261025)
        service_root.verify(service_result)
        for ref in bridge.attempt_refs:
            bridge.verify_attempt(ref)
        output["service_root"] = {
            "status": service_result.status, "archive_ref": service_result.archive_ref,
            "candidate_refs": list(service_result.candidates),
            "submitted_ref": service_result.submitted_ref,
            "error": service_result.error,
            "challenge_attempt_refs": list(bridge.attempt_refs),
            "events": list(service_result.events),
            "baseline_run_ref": current_results.get("baseline").run_ref
                if current_results.get("baseline") else "",
            "candidate_probe_run_ref": current_results.get("candidate").run_ref
                if current_results.get("candidate") else "",
        }
        if not service_result.candidates or not current_results.get("candidate"):
            output["status"] = "STOPPED_SERVICE_CANDIDATE_NOT_PROBED"
            output["failed_stage"] = "service_improvement_root"
            return _finish(output, client, ledger)

        staged_candidate_ref = service_result.candidates[-1]
        candidate = store.load(staged_candidate_ref)
        if not isinstance(candidate, ServiceSnapshot) or candidate.parent_ref != parent.ref:
            raise RuntimeError("M0 did not submit a complete child Service snapshot")
        output["service_candidate"] = {
            "ref": candidate.ref, "parent_ref": candidate.parent_ref,
            "policy_ref": candidate.policy.ref, "experience_ref": candidate.experience.ref,
            "experience": candidate.experience.value,
            "probe_run_ref": current_results["candidate"].run_ref,
            "root_submission_status": service_result.status,
            "root_submitted_ref": service_result.submitted_ref,
            "selected_by_independent_gate": False,
        }
        output["episodes"] = {
            "baseline": _episode_result(adapter, current_results["baseline"]),
            "candidate": _episode_result(adapter, current_results["candidate"]),
        }

        # Execute one M self-edit attempt using only the public challenge,
        # baseline result and candidate probe already recorded by the Host.
        output["failed_stage"] = "m_self_edit_proposal"
        prior_service_research = _public_root_summary(service_result, bridge)
        self_host = ResearchHost(store, archive, worker, model, models, ledger,
                                 max_steps=12, max_output_tokens=16384)
        self_edit_call_start = client.index
        self_result = self_host.run(
            m0, m0, "SELF_EDIT",
            {"domain": adapter.domain_id,
             "prior_service_research": prior_service_research},
            (), lambda *_: (_ for _ in ()).throw(RuntimeError("no M selection probe is registered")),
            seed=20261026)
        self_host.verify(self_result)
        output["m_self_edit"] = {
            "root_status": self_result.status,
            "archive_ref": self_result.archive_ref,
            "candidate_refs": list(self_result.candidates),
            "submitted_ref": self_result.submitted_ref,
            "error": self_result.error,
            "selected_by_independent_gate": self_result.submitted_ref != m0.ref,
            "selection_status": "NOT_RUN_SINGLE_CHALLENGE_DIAGNOSTIC",
        }
        output["status"] = ("DIAGNOSTIC_SERVICE_CANDIDATE_PROBED_M_CANDIDATE_STAGED"
                            if self_result.candidates else
                            "DIAGNOSTIC_SERVICE_CANDIDATE_PROBED_M_SELF_EDIT_FAILED")
        output["failed_stage"] = ""
        output["period_training"] = "NOT_RUN"
        output["period_promotion"] = "NOT_RUN_NO_INDEPENDENT_SERVICE_OR_M_SELECTION_PACKAGES"
        output["ledger"] = ledger.snapshot()
        output["model_call_count"] = client.index
        output["finished_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
        _finish(output, client, ledger)
    except Exception as exc:
        output.update({"status": "FAILED", "error_type": type(exc).__name__,
                       "error": str(exc), "traceback": traceback.format_exc()})
        output.setdefault("period_training", "NOT_RUN")
        output.setdefault("period_promotion", "NOT_RUN_AFTER_FAILED_STAGE")
        if output.get("failed_stage") == "m_self_edit_proposal" and output.get("m_self_edit") is None:
            error_code = getattr(exc, "code", "")
            if not error_code and "timed out" in str(exc).lower():
                error_code = "PROVIDER_TIMEOUT"
            output["m_self_edit"] = {
                "root_status": "FAILED_" + (error_code or "ERROR"),
                "request_attempted": bool(client is not None and
                                           client.index > locals().get("self_edit_call_start", client.index)),
                "archive_ref": "", "candidate_refs": [], "submitted_ref": None,
                "error": str(exc), "selected_by_independent_gate": False,
                "selection_status": "NOT_RUN_SINGLE_CHALLENGE_DIAGNOSTIC",
            }
        if ledger is not None:
            output["ledger"] = ledger.snapshot()
        if client is not None:
            output["model_call_count"] = client.index
        output["finished_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
        _finish(output, client, ledger)
        raise


def _episode_result(adapter, result):
    record = json.loads((OUTPUT / "native-episodes" / (result.run_ref + ".json"))
                        .read_text(encoding="utf-8"))
    outcome = record["outcome"]
    process_errors = outcome.get("process_errors", {}).get("status", "UNAVAILABLE")
    safety = outcome.get("safety_violations", {}).get("status", "UNAVAILABLE")
    communication = record.get("communication", {})
    state_goals = outcome.get("state_goals", [])
    public_inputs = json.loads((OUTPUT / "native-episodes" /
                                (result.run_ref + ".public-inputs.json"))
                               .read_text(encoding="utf-8"))
    injected_text = "\n".join(str(message.get("content", ""))
                               for event in public_inputs.get("model_events", [])
                               for message in event.get("request", {}).get("messages", []))
    rejected_attempts = [{"operation": row.get("operation", {}).get("name"),
                          "error_code": row.get("result", {}).get("error_code")}
                         for row in record.get("tool_executions", [])
                         if row.get("result", {}).get("error_code")]
    return {"run_ref": result.run_ref, "status": result.status, "score": result.score,
            "episode_status": record.get("status"),
            "business_goal_success": bool(state_goals) and all(
                item.get("status") == "PASS" for item in state_goals),
            "process_errors": process_errors, "safety_violations": safety,
            "evaluation_status": outcome.get("evaluation_status"),
            "strict_task_success": outcome.get("strict_task_success"),
            "communication_unresolved_messages": communication.get("unresolved_message_ids", []),
            "rejected_attempts": rejected_attempts,
            "service_experience_injected": "Service Experience Guide:" in injected_text,
            "no_double_release_rule_injected":
                "Do NOT call release_accepted_refund after commit_accepted_quote" in injected_text,
            "replay_verified": result.replay_verified, "tool_steps": result.tool_steps,
            "model_calls": result.model_calls, "model_tokens": result.model_tokens,
            "feedback": result.feedback,
            "replay": adapter.replay(result.run_ref)}


def _public_root_summary(result, bridge):
    challenge_attempts = []
    baseline_runs = []
    candidate_feedback = []
    for wrapped in result.events:
        event = wrapped.get("event", wrapped)
        if event.get("kind") == "challenge_certification":
            challenge_attempts.append({"proposal": event["proposal"],
                                       "status": event["receipt"]["status"],
                                       "reason_code": event["receipt"].get("reason_code", "")})
        elif event.get("kind") == "baseline_execution":
            value = event["result"]
            baseline_runs.append({"task_ref": event["task_ref"], "status": value["status"],
                                  "score": value["score"],
                                  "replay_verified": value["replay_verified"],
                                  "feedback": value["feedback"]})
        elif event.get("kind") == "observation":
            value = event["value"]
            if value.get("kind") == "STAGE":
                candidate_feedback.append({key: value[key] for key in
                                           ("kind", "status", "reason", "candidate_ref") if key in value})
            elif value.get("kind") == "PROBE":
                candidate_feedback.append({"kind": "PROBE", "candidate_ref": value["candidate_ref"],
                    "probe_ref": value["probe_ref"], "result": value["result"]})
    return [{"status": result.status,
             "roots": [{"status": result.status, "error": result.error,
                        "challenge_attempts": challenge_attempts,
                        "baseline_runs": baseline_runs,
                        "candidate_feedback": candidate_feedback}]}]


def _finish(output, client, ledger):
    if ledger is not None and "ledger" not in output:
        output["ledger"] = ledger.snapshot()
    if client is not None:
        output["model_call_count"] = client.index
    output["finished_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
    output["failed_stage"] = output.get("failed_stage", "")
    _write(OUTPUT / "summary.json", output)
    report = [
        "# 开放世界单题进化诊断",
        "",
        f"- 状态：`{output.get('status')}`",
        f"- 模型：`{output.get('model')}`",
        f"- World：1 个，hash `{output.get('world_hash', '')}`（复用并冻结）",
        "- Challenge：由 RSI M 提出；最多提交 1 次。",
        "- Service：基线与 M0 提出的 P/K 候选各执行一次同一冻结任务。",
        f"- 真实模型请求：{output.get('model_call_count', 0)} 次。",
        f"- 参数训练：`{output.get('period_training', 'NOT_RUN')}`。",
        "- 独立选代：未运行；本诊断不宣称候选有效或已晋升。",
        "",
        "## 结果",
        "",
        f"- Service root：`{output.get('service_root', {}).get('status', 'NOT_REACHED')}`。",
        f"- P/K 候选：`{output.get('service_candidate', {}).get('ref', 'NOT_STAGED')}`。",
        f"- 基线 Episode：业务目标 `{output.get('episodes', {}).get('baseline', {}).get('business_goal_success', 'NOT_RECORDED')}`，过程错误 `{output.get('episodes', {}).get('baseline', {}).get('process_errors', 'NOT_RECORDED')}`，Replay `{output.get('episodes', {}).get('baseline', {}).get('replay_verified', 'NOT_RECORDED')}`。",
        f"- 候选 Episode：业务目标 `{output.get('episodes', {}).get('candidate', {}).get('business_goal_success', 'NOT_RECORDED')}`，过程错误 `{output.get('episodes', {}).get('candidate', {}).get('process_errors', 'NOT_RECORDED')}`，Replay `{output.get('episodes', {}).get('candidate', {}).get('replay_verified', 'NOT_RECORDED')}`。",
        f"- 调用量：基线 {output.get('episodes', {}).get('baseline', {}).get('model_calls', 'UNKNOWN')} 次 / {output.get('episodes', {}).get('baseline', {}).get('model_tokens', 'UNKNOWN')} Token；候选 {output.get('episodes', {}).get('candidate', {}).get('model_calls', 'UNKNOWN')} 次 / {output.get('episodes', {}).get('candidate', {}).get('model_tokens', 'UNKNOWN')} Token。",
        f"- 基线被 Oracle 记录的无效尝试：`{output.get('episodes', {}).get('baseline', {}).get('rejected_attempts', [])}`；候选体验是否实际注入 Service 请求：`{output.get('episodes', {}).get('candidate', {}).get('service_experience_injected', False)}`；其中包含防止重复释放退款规则：`{output.get('episodes', {}).get('candidate', {}).get('no_double_release_rule_injected', False)}`。",
        f"- 严格任务评价：基线 `{output.get('episodes', {}).get('baseline', {}).get('status', 'NOT_RECORDED')}` / 候选 `{output.get('episodes', {}).get('candidate', {}).get('status', 'NOT_RECORDED')}`；两者严格评价均未解析（`UNKNOWN`、score 0），Customer 通信有未解析消息。",
        f"- M 自修改 root：`{output.get('m_self_edit', {}).get('root_status', 'NOT_REACHED')}`（请求已发送：`{output.get('m_self_edit', {}).get('request_attempted', False)}`）。",
        f"- M 候选：{output.get('m_self_edit', {}).get('candidate_refs', [])}。",
        f"- 阻塞阶段：`{output.get('failed_stage', '')}`；错误：`{output.get('error', '')}`。",
        f"- 超时调用：请求体 {output.get('provider_call_summary', {}).get('last_failure', {}).get('request_bytes', 'UNKNOWN')} bytes，Provider 阶段 `{output.get('provider_call_summary', {}).get('last_failure', {}).get('timeout_phase', 'UNKNOWN')}`；无法据此区分模型推理慢与网关/服务端延迟。",
        f"- 记录到的模型 Token：{output.get('ledger', {}).get('used', {}).get('model_tokens', 'UNKNOWN')}；超时请求的 Provider 用量未知。",
        "",
        "## 证据",
        "",
        "- `summary.json`：World、认证、Host 根轨迹、执行结果、Replay 与模型调用计数。",
        "- `model-calls.jsonl`：真实请求和响应；不会保存认证头或 API Key。",
        "- `native-episodes/`：基线和候选版本的 Engine、Oracle、Customer 与 Replay 记录。",
        "- `research-archive/`、`programs/`、`task-records/`：研究动作、程序与证书快照。",
        "",
        "这是单世界、单挑战的工程诊断。基线和候选在同一题上的比较不是独立选代，不能据此声称 RSI 能力提升。",
    ]
    (OUTPUT / "REPORT.zh.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output.get("status"), "failed_stage": output.get("failed_stage"),
        "error": output.get("error"), "model_call_count": output.get("model_call_count"),
        "world_hash": output.get("world_hash"),
        "service_root_status": output.get("service_root", {}).get("status"),
        "service_candidate": output.get("service_candidate", {}).get("ref"),
        "episodes": {name: {key: episode.get(key) for key in (
            "status", "business_goal_success", "process_errors", "safety_violations",
            "replay_verified", "model_calls", "model_tokens")}
            for name, episode in output.get("episodes", {}).items()},
        "m_self_edit": output.get("m_self_edit"),
        "period_training": output.get("period_training"),
    }, ensure_ascii=False, indent=2))
    if client is not None:
        client.close()


if __name__ == "__main__":
    main()
