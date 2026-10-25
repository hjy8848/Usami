"""Retry only the timed-out M self-edit root with a 300-second provider timeout."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parents[5]
PARENT_RUN = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent
IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def main():
    if (OUTPUT / "model-calls.jsonl").exists():
        raise RuntimeError("retry already made a provider call; refusing to repeat it")
    previous_preflight = OUTPUT / "summary.json"
    if previous_preflight.exists():
        previous = json.loads(previous_preflight.read_text(encoding="utf-8"))
        if previous.get("model_call_count") not in (None, 0):
            raise RuntimeError("retry output already contains a model call; refusing to repeat it")
        previous_preflight.replace(OUTPUT / "preflight-failure.json")
        previous_report = OUTPUT / "REPORT.zh.md"
        if previous_report.exists():
            previous_report.replace(OUTPUT / "preflight-failure.md")
    os.environ["USAMI_LLM_TIMEOUT"] = "300"
    os.environ["USAMI_LLM_TRUST_ENV"] = "1"

    source = load("live_open_world_source", PARENT_RUN / "run_evolution.py")
    base = load("live_service_base", ROOT /
                "experiments/rsi/results/live-one-world-one-task-qwen3.7-plus-20261025-002/run_one.py")
    live_minimal = load("live_research_model", ROOT /
                        "experiments/rsi/results/live-minimal-qwen3.7-plus-20261025-001/run_minimal.py")

    from rsi_core.archive import Archive
    from rsi_core.budget import Ledger
    from rsi_core.isolation import DockerWorker
    from rsi_core.programs import ProgramArtifact, ProgramStore
    from rsi_core.protocol import FrozenModels, Limits, ModelSnapshot, digest
    from rsi_core.runtime import ResearchHost
    from usami.service.client import OpenAICompatibleClient

    output = {"kind": "rsi-m-self-edit-timeout-retry-diagnostic-v1",
              "source_run": str(PARENT_RUN), "status": "RUNNING",
              "timeout_seconds": 300, "training": "NOT_RUN",
              "independent_selection": "NOT_RUN_NO_M_PROBE_SET",
              "retry_policy": "one explicit retry of the previously timed-out M request"}
    client = None
    try:
        prior = json.loads((PARENT_RUN / "summary.json").read_text(encoding="utf-8"))
        old_calls = [json.loads(line) for line in
                     (PARENT_RUN / "model-calls.jsonl").read_text(encoding="utf-8").splitlines()
                     if line.strip()]
        failed_call = old_calls[-1]
        original_messages = failed_call["request"].get("messages", [])
        original_model_request = json.loads(original_messages[-1]["content"])
        if failed_call.get("status") != "error" or original_model_request.get("target_role") != "M":
            raise RuntimeError("the previous call is not a failed M proposal; refusing to call another stage")

        parent_ref = original_model_request["target_ref"]
        original_programs = ProgramStore(PARENT_RUN / "programs")
        m0 = original_programs.load(parent_ref)
        if not isinstance(m0, ProgramArtifact) or m0.kind != "M":
            raise RuntimeError("previous target is not the archived M research program")
        if m0.source != original_model_request.get("current_program_source"):
            raise RuntimeError("archived M source differs from the timed-out request")

        public_research = original_model_request["prior_service_research"]
        reconstructed = source._public_root_summary(
            SimpleNamespace(events=prior["service_root"]["events"],
                            status=prior["service_root"]["status"],
                            error=prior["service_root"]["error"]), None)
        context_matches = public_research == reconstructed
        if not context_matches:
            raise RuntimeError("saved root evidence no longer reconstructs the original public M context")
        write(OUTPUT / "public-context.json", public_research)

        client = base.JournalClient(OpenAICompatibleClient.from_env(), OUTPUT / "model-calls.jsonl")
        settings = client.settings
        if settings.timeout_seconds != 300 or not settings.trust_env:
            raise RuntimeError("provider client did not load the requested 300-second proxy-aware settings")

        # The model and sampling identity stay frozen to the original run; only
        # the transport read timeout is extended for this one request.
        parameter_hash = digest({"base_url": settings.base_url, "model": settings.model,
                                "options": settings.options, "timeout_seconds": 180,
                                "trust_env": settings.trust_env})
        snapshot = ModelSnapshot(settings.model, parameter_hash)
        models = FrozenModels(snapshot, snapshot, snapshot)
        previous_limits = prior["ledger"]["limits"]
        limits = Limits(**previous_limits)
        ledger = Ledger(limits)
        for scope, resource in (("prior_run", prior["ledger"]["used"]),):
            ledger.charge(scope, **resource)

        store = ProgramStore(OUTPUT / "programs")
        if store.save(m0) != m0.ref:
            raise RuntimeError("M parent snapshot hash changed")
        archive = Archive(OUTPUT / "research-archive")
        worker = DockerWorker(IMAGE, limits)
        model = live_minimal.LiveResearchModel(client)
        host = ResearchHost(store, archive, worker, model, models, ledger,
                            max_steps=12, max_output_tokens=16384)

        output.update({"model": settings.model, "m_parent_ref": m0.ref,
                       "previous_failed_call_index": failed_call.get("call_index"),
                       "public_context_matches_original": context_matches,
                       "world_hash": prior.get("world_hash"),
                       "previous_run_model_calls": prior.get("model_call_count"),
                       "failed_stage": "m_self_edit_model_request"})
        result = host.run(
            m0, m0, "SELF_EDIT",
            {"domain": "usami-commerce-v2", "prior_service_research": public_research},
            (), lambda *_: (_ for _ in ()).throw(
                RuntimeError("no independent M selection probes are registered")),
            seed=20261026)
        output["host_verification"] = host.verify(result)
        output["m_result"] = {"status": result.status,
                              "submitted_ref": result.submitted_ref,
                              "parent_ref": m0.ref,
                              "candidate_refs": list(result.candidates),
                              "archive_ref": result.archive_ref,
                              "error": result.error,
                              "selected_by_independent_gate": False}
        output["candidates"] = []
        for ref in result.candidates:
            candidate = store.load(ref)
            output["candidates"].append({"ref": ref, "parent_ref": candidate.parent_ref,
                                         "source_bytes": len(candidate.source.encode("utf-8")),
                                         "static_contract": candidate.check(limits.source_bytes).kind})
        output["status"] = "M_CANDIDATE_STAGED_NOT_SELECTED" if result.candidates else result.status
        output["failed_stage"] = ""
        output["selection"] = "NOT_RUN_SINGLE_CHALLENGE_DIAGNOSTIC"
        output["model_call_count"] = client.index
        output["ledger"] = ledger.snapshot()
        output["retry_model_tokens"] = max(
            0, ledger.snapshot()["used"]["model_tokens"] -
            prior["ledger"]["used"]["model_tokens"])
    except Exception as exc:
        output.update({"status": "FAILED", "error_type": type(exc).__name__,
                       "error": str(exc), "traceback": traceback.format_exc()})
        if client is not None:
            output["model_call_count"] = client.index
        if "ledger" in locals():
            output["ledger"] = ledger.snapshot()
        if "host" in locals() and "result" not in locals():
            output["host_archive_ref"] = "embedded in error if Host archived before raising"
    finally:
        if client is not None:
            client.close()
        call_log = OUTPUT / "model-calls.jsonl"
        if call_log.exists():
            rows = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            if rows:
                last = rows[-1]
                usage = last.get("provider_response", {}).get("usage", {})
                output["provider_call"] = {
                    "status": last.get("status"), "call_index": last.get("call_index"),
                    "timeout_phase": last.get("provider_response", {}).get("timeout_phase"),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "request_bytes": len(json.dumps(last.get("request", {}),
                                                     ensure_ascii=False).encode()),
                }
        output["finished_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
        write(OUTPUT / "summary.json", output)
        report = [
            "# M 自修改 300 秒单次续跑",
            "",
            f"- 状态：`{output.get('status')}`。",
            f"- 来源：复用上次单题进化运行 `{PARENT_RUN.name}` 的同一 M、冻结 World 和真实 Service 基线/候选证据。",
            f"- World hash：`{output.get('world_hash', '')}`。",
            f"- 模型：`{output.get('model', '')}`；仅延长本次 Provider 请求超时至 300 秒。",
            f"- M 父版本：`{output.get('m_parent_ref', '')}`。",
            f"- M 结果：`{output.get('m_result', {}).get('status', 'FAILED')}`；候选：{output.get('candidates', [])}。",
            f"- 本次请求：{output.get('model_call_count', 0)} 次，Provider 状态 `{output.get('provider_call', {}).get('status', 'UNKNOWN')}`，Token 用量 {output.get('provider_call', {}).get('prompt_tokens', 'UNKNOWN')} 输入 + {output.get('provider_call', {}).get('completion_tokens', 'UNKNOWN')} 输出；模型在 300 秒截止前返回。",
            f"- M 候选通过静态接口检查并已归档，但 Host 因没有独立 M Probe，保留父版本（`NOOP`）；没有执行或选中候选。",
            f"- 独立选代：`{output.get('selection', 'NOT_RUN')}`；训练未运行。",
            "",
            "模型请求和响应保存在 `model-calls.jsonl`；复用的公开研究上下文保存在 `public-context.json`；",
            "通过静态 Stage 的 M 代码会保存在 `programs/`，Host 研究事件归档在 `research-archive/`。",
        ]
        if output.get("error"):
            report.insert(-3, f"- 错误：`{output['error']}`。")
        (OUTPUT / "REPORT.zh.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print(json.dumps({key: output.get(key) for key in (
            "status", "error", "model_call_count", "m_parent_ref", "m_result", "candidates",
            "selection", "ledger")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
