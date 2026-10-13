"""Freeze a protocol before starting agents; score and replay need no network."""
import argparse
import json
from pathlib import Path
import sys

from usami.benchmark.manifest import (Budget, create_discovery_manifest, create_service_manifest,
                                       load_manifest, split_overlap)
from usami.benchmark.runtime import BenchmarkRun, run_instance
from usami.benchmark.scoring import score_run, summarize
from usami.interaction.__main__ import provider_environment
from usami.service.client import OpenAICompatibleClient, settings_from_env
from usami.service.models import ModelSettings
from usami.world.generator import GeneratorConfig


def main(argv=None):
    parser = argparse.ArgumentParser(description="Usami versioned Service Task / Customer Discovery tracks")
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="freeze spec and finite capabilities before any model calls")
    freeze.add_argument("--spec", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--instance", required=True)
    run.add_argument("--trial", default="r0")
    run.add_argument("--out", type=Path, required=True)
    profile = sub.add_parser("profile", help="bind environment model settings without changing the task dataset")
    profile.add_argument("--manifest", type=Path, required=True)
    profile.add_argument("--out", type=Path, required=True)
    score = sub.add_parser("score", help="exact replay and evidence score, offline")
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    summary = sub.add_parser("summarize")
    summary.add_argument("--manifest", type=Path, required=True)
    summary.add_argument("--runs", nargs="+", type=Path, required=True)
    overlap = sub.add_parser("overlap")
    overlap.add_argument("--left", type=Path, required=True)
    overlap.add_argument("--right", type=Path, required=True)
    overlap.add_argument("--require-holdout", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            spec = json.loads(args.spec.read_text(encoding="utf-8"))
            track = spec.pop("track")
            cfg = GeneratorConfig.model_validate(spec.pop("generator", {}))
            service = ModelSettings.model_validate(spec.pop("service_model"))
            seeds = spec.pop("seeds")
            if "budget" in spec:
                spec["budget"] = Budget.model_validate(spec["budget"])
            if track == "service_task":
                manifest = create_service_manifest(seeds, spec.pop("quotas"), service, generator=cfg, **spec)
            elif track == "customer_discovery":
                manifest = create_discovery_manifest(seeds, spec.pop("identity"), service,
                    ModelSettings.model_validate(spec.pop("customer_model")), generator=cfg, **spec)
            else:
                raise ValueError("unknown benchmark track")
            manifest.save(args.out)
            print(json.dumps({"manifest_hash": manifest.manifest_hash, "dataset_hash": manifest.dataset_hash,
                              "track": manifest.track, "instances": len(manifest.instances), "out": str(args.out)}, indent=2))
            return 0
        if args.command == "profile":
            manifest = load_manifest(args.manifest)
            previous_dataset_hash = manifest.dataset_hash
            manifest.service_model = settings_from_env(provider_environment("service"))
            if manifest.track == "customer_discovery":
                manifest.customer_model = settings_from_env(provider_environment("customer"))
            manifest.seal()
            if manifest.dataset_hash != previous_dataset_hash:
                raise ValueError("binding model settings changed fixed dataset conditions")
            manifest.save(args.out)
            result = {"manifest_hash": manifest.manifest_hash, "dataset_hash": manifest.dataset_hash, "out": str(args.out)}
        elif args.command == "overlap":
            result = split_overlap(load_manifest(args.left), load_manifest(args.right), require_holdout=args.require_holdout)
        else:
            manifest = load_manifest(args.manifest)
            if args.command == "score":
                result = score_run(manifest, BenchmarkRun.load(args.run))
            elif args.command == "summarize":
                result = summarize(manifest, [BenchmarkRun.load(path) for path in args.runs])
            else:
                service = OpenAICompatibleClient.from_env(provider_environment("service"))
                customer = None
                try:
                    if manifest.track == "customer_discovery":
                        customer = OpenAICompatibleClient.from_env(provider_environment("customer"))
                    evidence = run_instance(manifest, args.instance, service, customer, args.trial)
                    evidence.save(args.out)
                    result = score_run(manifest, evidence)
                finally:
                    service.close()
                    if customer is not None:
                        customer.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"usami-benchmark: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
