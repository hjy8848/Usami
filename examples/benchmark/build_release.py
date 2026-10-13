"""Rebuild the public protocol fixtures. No model calls; Demo Test is not blind."""
import json
from pathlib import Path

from usami.benchmark.manifest import create_service_manifest, create_discovery_manifest, split_overlap
from usami.service.models import ModelSettings

ROOT = Path(__file__).resolve().parents[2]


def main():
    output = ROOT / "benchmarks/v0.1.0"
    output.mkdir(parents=True, exist_ok=True)
    # This is a protocol fixture profile, never a claimed live model evaluation.
    model = ModelSettings(model="fixture_model", base_url="https://example.invalid/v1")
    counts, manifests = {}, {}
    for name, start, worlds, family, quota in (
        ("train", 0, 64, "seat_before_plan", 8),
        ("validation", 1000000, 64, "seat_before_plan", 4),
        ("test-demo", 2000000, 64, "plan_before_seats", 8),
    ):
        manifest = create_service_manifest(range(start, start + worlds),
            {f"{family}/owner": quota, f"{family}/billing_admin": quota}, model,
            split="test" if name == "test-demo" else name, visibility="demo" if name == "test-demo" else "public")
        manifest.save(output / f"service-{name}.json")
        manifests[name] = manifest
        counts[name] = {"instances": len(manifest.instances), "quotas": manifest.sampling["quotas"],
                        "candidate_counts": manifest.sampling["candidate_counts"],
                        "structures": len({i.task.structure_signature for i in manifest.instances}),
                        "semantics": len({i.task.semantic_signature for i in manifest.instances}),
                        "manifest_hash": manifest.manifest_hash, "dataset_hash": manifest.dataset_hash}
        print(f"{name}: {len(manifest.instances)} causal multi-route tasks", flush=True)
    discovery = create_discovery_manifest([3000000, 3000001], "user_002", model, model,
        split="test", visibility="demo", trials=["r0", "r1", "r2"])
    discovery.save(output / "discovery-demo.json")
    counts["discovery-demo"] = {"instances": len(discovery.instances), "trials": discovery.trials,
                                "manifest_hash": discovery.manifest_hash, "dataset_hash": discovery.dataset_hash}
    counts["train_vs_test"] = split_overlap(manifests["train"], manifests["test-demo"], require_holdout=True)
    counts["train_vs_validation"] = split_overlap(manifests["train"], manifests["validation"])
    (output / "coverage.json").write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
