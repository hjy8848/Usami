"""Paired one-call comparison of v4, world-grounded batch, and rule sampling.

Use a one-world registered pool for a strict one-request A/B call-budget match.
This compares task proposal/certification only; no Customer or Service runs here.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from usami.service.client import ModelSettings
from usami.service.models import ServiceError, strict_json
from usami_benchmark.designer_batch import (
    BatchDesignerConfig, run_batch, run_rule_baseline, save_run, _usage as response_usage, _usage_complete,
)
from usami_benchmark.designer_exploration import (
    DesignerBudget, DesignerFailure, design, verify_execution, verify_failed_journal,
)
from usami_benchmark.grounder import GroundingBudget
from usami_benchmark.tasks import ConstructionBudget
from usami_benchmark.world_index import load_world_index
from vast_coevo.schema import atomic_json


class ResponseFileClient:
    def __init__(self, settings, responses):
        self.settings = settings
        self.responses = list(responses)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        if not self.responses:
            raise ServiceError("OFFLINE_RESPONSE_MISSING", "response file contains no response for this request")
        return self.responses.pop(0)


def _usage(responses):
    rows = [response_usage(response) for response in responses]
    return {key: sum(row[key] or 0 for row in rows) for key in ("input_tokens", "output_tokens", "total_tokens")} | {
        "usage_complete": _usage_complete(rows)}


def _response_file(path):
    payload = strict_json(Path(path).read_text())
    if isinstance(payload, dict) and "responses" in payload:
        settings = ModelSettings.model_validate(payload.get("model", {
            "model": "offline-scripted", "base_url": "https://fixture.invalid/v1", "options": {}}))
        responses = payload["responses"]
    else:
        settings = ModelSettings(model="offline-scripted", base_url="https://fixture.invalid/v1", options={})
        responses = [payload]
    return settings, responses


def run_comparison(index, output_dir, *, batch_count=5, online=False,
                   v4_response=None, batch_response=None):
    if len(index.worlds) != 1:
        raise ValueError("strict one-call A/B comparison requires exactly one registered frozen world")
    if online and (v4_response or batch_response):
        raise ValueError("choose online credentials or offline response files, not both")
    if bool(v4_response) != bool(batch_response):
        raise ValueError("offline comparison requires response files for both v4 and Batch")
    if not online and not v4_response:
        raise ValueError("provide --online or both --v4-response and --batch-response")
    if index.worlds[0].partition not in {"train", "validation"} or index.worlds[0].domain != "aftersales":
        raise ValueError("comparison requires an After-sales train/validation world")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    indexed = index.worlds[0]
    frozen = indexed.frozen
    rule_run = run_rule_baseline(index, batch_count, partition=indexed.partition)
    save_run(rule_run, index, root / "C-rule-combination")

    client = None
    preflight_error = None
    if online:
        try:
            from usami.service.client import OpenAICompatibleClient
            client = OpenAICompatibleClient.from_env()
        except Exception as exc:
            preflight_error = str(exc)
    else:
        v4_settings, v4_rows = _response_file(v4_response)
        batch_settings, batch_rows = _response_file(batch_response)
        if v4_settings != batch_settings:
            raise ValueError("offline v4 and Batch response files must declare identical model settings")
        client_settings = v4_settings
    if online and client is not None:
        client_settings = client.settings

    v4_result = {"status": "BLOCKED_EXTERNAL_MODEL", "service_executions": 0}
    batch_result = None
    try:
        if preflight_error is None:
            v4_client = client if online else ResponseFileClient(client_settings, v4_rows)
            v4_started = time.perf_counter()
            try:
                execution = design(frozen, v4_client,
                    ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1),
                    budget=DesignerBudget(max_exploration_calls=0, max_revisions=0, max_queries=1))
                replay = verify_execution(execution)
                responses = [row["response"] for row in execution.exchanges if "response" in row]
                v4_result = {"status": "CERTIFIED", "protocol": execution.protocol,
                    "world_registration_hash": indexed.registration_hash, "world_hash": indexed.world_hash,
                    "request_count": len(execution.exchanges), "metrics": execution.metrics,
                    "cost": {**execution.cost, **_usage(responses),
                        "local_end_to_end_ms": round((time.perf_counter() - v4_started) * 1000, 3)}, "replay": replay,
                    "execution": execution.model_dump(mode="json")}
            except DesignerFailure as exc:
                journal = exc.journal
                replay = verify_failed_journal(frozen, journal)
                responses = [row["response"] for row in journal.get("exchanges", []) if "response" in row]
                v4_result = {"status": "FAILED_OR_UNPROVEN", "failure": journal.get("failure"),
                    "failure_category": journal.get("failure_category"), "request_count": len(journal.get("exchanges", [])),
                    "cost": {**_usage(responses),
                        "local_end_to_end_ms": round((time.perf_counter() - v4_started) * 1000, 3)},
                    "replay": replay, "journal": journal, "service_executions": 0}
            atomic_json(root / "A-v4-result.json", v4_result, immutable=True)

            batch_client = client if online else ResponseFileClient(client_settings, batch_rows)
            config = BatchDesignerConfig(num_challenges=batch_count,
                partition=indexed.partition,
                grounding=GroundingBudget(partition=indexed.partition, max_matches=1),
                construction=ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1))
            run = run_batch(index, batch_client, config)
            save_run(run, index, root / "B-world-grounded-batch")
            batch_result = {"status": run.status, "metrics": run.metrics, "cost": run.cost,
                "replay": "see B-world-grounded-batch/replay-verification.json", "service_executions": 0}
        else:
            atomic_json(root / "A-v4-result.json", {"status": "BLOCKED_EXTERNAL_MODEL",
                "reason": preflight_error, "request_count": 0, "service_executions": 0}, immutable=True)
            from usami.service.models import ModelSettings
            from usami.service.client import ServiceError
            class UnavailableClient:
                settings = ModelSettings(model="unavailable", base_url="https://unavailable.invalid/v1", options={})
                available = False
                unavailable_reason = preflight_error
            config = BatchDesignerConfig(num_challenges=batch_count, partition=indexed.partition,
                grounding=GroundingBudget(partition=indexed.partition, max_matches=1),
                construction=ConstructionBudget(max_nodes=4096, max_depth=16, max_paths=1))
            run = run_batch(index, UnavailableClient(), config)
            save_run(run, index, root / "B-world-grounded-batch")
            batch_result = {"status": run.status, "metrics": run.metrics, "cost": run.cost,
                "reason": preflight_error, "service_executions": 0}
    finally:
        if online and client is not None:
            client.close()

    v4_calls = v4_result.get("cost", {}).get("calls", v4_result.get("request_count", 0))
    batch_calls = (batch_result or {}).get("cost", {}).get("designer_api_calls", 0)
    v4_total = v4_result.get("cost", {}).get("total_tokens", 0)
    batch_total = (batch_result or {}).get("cost", {}).get("total_tokens", 0)
    v4_certified = int(v4_result.get("status") == "CERTIFIED")
    batch_certified = int((batch_result or {}).get("metrics", {}).get("certified_challenges", 0))
    def normalized(tokens, certified):
        return {"tokens_per_certified": round(tokens / certified, 3) if certified else None,
            "certified_per_1000_tokens": round(certified * 1000 / tokens, 6) if tokens else None}
    report = {
        "protocol": "world-grounded-designer-abc-comparison-v1",
        "world_registration_hash": indexed.registration_hash,
        "world_hash": indexed.world_hash,
        "partition": indexed.partition,
        "model_settings": client_settings.model_dump(mode="json") if "client_settings" in locals() else None,
        "budget_control": {
            "api_call_matched": v4_calls == batch_calls == 1,
            "token_budget_matched": False,
            "token_budget_note": "Actual provider token use is measured and normalized; this one-call run does not claim equal total-token budgets.",
            "v4_calls": v4_calls, "batch_calls": batch_calls,
            "v4_total_tokens": v4_total, "batch_total_tokens": batch_total,
            "v4_cost_normalized": normalized(v4_total, v4_certified),
            "batch_cost_normalized": normalized(batch_total, batch_certified),
            "currency_cost": "NOT_MEASURED; no provider price schedule is bundled",
        },
        "A_v4": {k: v for k, v in v4_result.items() if k not in {"execution", "journal"}},
        "B_world_grounded_batch": batch_result,
        "C_rule_combination_sampling": {"status": rule_run.status, "metrics": rule_run.metrics,
            "cost": rule_run.cost, "service_executions": 0},
        "service_execution": "NOT RUN; certified task generation is not Service performance evidence",
    }
    atomic_json(root / "comparison.json", report, immutable=True)
    (root / "report.md").write_text(
        "# World-Grounded Designer A/B/C comparison\n\n"
        f"- Frozen world: `{indexed.registration_hash}` (`{indexed.partition}`)\n"
        f"- A v4 status: `{v4_result.get('status')}`; calls={v4_calls}; tokens={v4_total}\n"
        f"- B batch status: `{(batch_result or {}).get('status')}`; calls={batch_calls}; tokens={batch_total}\n"
        f"- C rule sampler: `{rule_run.metrics.get('certified_challenges')}` certified of `{rule_run.metrics.get('raw_generated_challenges')}` candidates; calls=0\n"
        f"- Equal API-call budget: `{v4_calls == batch_calls == 1}`; equal token budget: `False`\n"
        f"- Certified tasks per 1k observed tokens: A={normalized(v4_total, v4_certified)['certified_per_1000_tokens']}; B={normalized(batch_total, batch_certified)['certified_per_1000_tokens']}\n"
        "- Service executions: 0. This experiment evaluates task generation and certification only.\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--batch-count", type=int, default=5, choices=range(1, 6))
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--v4-response")
    parser.add_argument("--batch-response")
    args = parser.parse_args(argv)
    index = load_world_index(args.index)
    report = run_comparison(index, args.output_dir, batch_count=args.batch_count, online=args.online,
        v4_response=args.v4_response, batch_response=args.batch_response)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["B_world_grounded_batch"].get("metrics", {}).get("certified_challenges", 0) else 2


if __name__ == "__main__":
    raise SystemExit(main())
