"""Formal open-World RSI entry and a separately labelled live Designer check.

A trusted Python factory assembles the existing Host/models/task registries and
Customer policy. It returns run_open_period keyword arguments. The CLI never
substitutes scripted proposals, models or task templates for that factory.
"""
import argparse
import importlib
import json
from pathlib import Path

from integrations.rsi_usami.open_world import OpenChallengeBridge, propose_open_challenge, run_open_period


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("period", "validate-designer"))
    parser.add_argument("--factory", required=True, help="trusted module:function(output_directory) -> native RSI context")
    parser.add_argument("--output", required=True)
    parser.add_argument("--world-count", type=int, default=3)
    parser.add_argument("--periods", type=int, default=1)
    parser.add_argument("--period-ref", help="validate-designer: reuse an existing frozen population period")
    parser.add_argument("--revise-attempt", help="validate-designer: explicitly revise one rejected attempt from this period")
    args = parser.parse_args()
    if args.periods < 1 or args.world_count < 1:
        parser.error("periods and world-count must be positive")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    module, name = args.factory.split(":", 1)
    context = getattr(importlib.import_module(module), name)(output)
    if args.command == "period":
        reports = []
        for _ in range(args.periods):
            record = run_open_period(world_count=args.world_count, **context)
            reports.append(record)
            period = record["rsi_period"]
            if period["status"] not in {"READY_FOR_TRAINING", "COMPLETED"}:
                break
            context["service"] = context["host"].store.load(period["output_service_ref"])
            context["designer"] = context["host"].store.load(period["output_designer_ref"])
        summary = {"kind": "open-world-rsi-execution", "factory": args.factory, "periods": reports,
                   "status": reports[-1]["rsi_period"]["status"],
                   "world_population_state": str(context["population"].state_path),
                   "interpretation": "Model/fixture identity is recorded by the configured Host and World provider."}
    else:
        # Credentials are read inside the native client and never enter artifacts.
        from usami.service.client import OpenAICompatibleClient
        from usami_v2.scenarios.designer import OpenAIDesignerProvider
        pool = context["population"]
        ref = args.period_ref or (pool.period_refs[-1] if pool.period_refs else pool.next_period(args.world_count))
        bridge = OpenChallengeBridge(pool, ref, context["service_evaluator"].adapter, context["verifier"],
            context["customer_binding"], episode_budget=context.get("episode_budget"),
            capability_options=context.get("capability_options"), external_event_factory=context.get("external_event_factory"))
        client = OpenAICompatibleClient.from_env()
        try:
            summary = propose_open_challenge(OpenAIDesignerProvider(client), bridge, previous_attempt_ref=args.revise_attempt)
        finally:
            client.close()
    path = output / (args.command + "-summary.json")
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": str(path), "status": summary.get("status", "RECORDED"),
                      "period_count": len(summary.get("periods", []))}, ensure_ascii=False))
    expected = {"CERTIFIED"} if args.command == "validate-designer" else {"READY_FOR_TRAINING", "COMPLETED"}
    if summary["status"] not in expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
