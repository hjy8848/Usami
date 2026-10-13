"""Offline contract verification, not an autonomous LLM benchmark result.

The fixture intentionally executes stored witnesses to check two independent
routes and actual engine/oracle/replay. Live `benchmark run` never uses this file.
"""
import json
from pathlib import Path

from usami.benchmark.manifest import load_manifest
from usami.benchmark.runtime import run_instance
from usami.benchmark.scoring import score_run, summarize

ROOT = Path(__file__).resolve().parents[2]


class FixtureClient:
    def __init__(self, settings, replies):
        self.settings = settings
        self.replies = iter(replies)

    def complete(self, request):
        return next(self.replies)


def answer(content="Contract fixture completed", calls=None):
    return {"choices": [{"finish_reason": "tool_calls" if calls else "stop", "message": {
        "role": "assistant", "content": None if calls else content,
        **({"tool_calls": calls} if calls else {})}}]}


def main():
    directory = ROOT / "benchmarks/v0.1.0"
    evidence_dir = ROOT / "outputs/benchmark-contract"
    results = {"kind": "offline contract fixtures; not LLM performance or discovery results", "service": {}, "discovery": {}}
    for name in ("train", "validation", "test-demo"):
        manifest = load_manifest(directory / f"service-{name}.json")
        primary = []
        verified = 0
        for instance in manifest.instances:
            for route in (0, 1):
                ops = instance.task.witnesses[route].operations
                calls = [{"id": f"call_{n}", "type": "function", "function": {"name": op.name,
                          "arguments": json.dumps(dict(org_id=op.org_id, resource_id=op.resource_id, **op.params))}}
                         for n, op in enumerate(ops)]
                run = run_instance(manifest, instance.instance_id, FixtureClient(manifest.service_model, [answer(calls=calls), answer()]))
                row = score_run(manifest, run)
                assert row["safe_goal_success"] and row["frame_preserved"] and row["replay_verified"]
                run.save(evidence_dir / name / f"{instance.instance_id}-route{route}.json")
                verified += 1
                if route == 0:
                    primary.append(run)
        summary = summarize(manifest, primary)
        assert summary["complete"] and summary["safe_goal_success_rate"] == 1
        results["service"][name] = {"instances": len(manifest.instances), "distinct_route_checks": verified,
                                  "all_reference_engine_oracle_replay_pass": True}
    manifest = load_manifest(directory / "discovery-demo.json")
    all_runs = []
    for instance in manifest.instances:
        for trial in manifest.trials:
            # A stop decision tests the protocol; it is not a measured attack policy.
            action = json.dumps({"type": "stop", "reason": "Offline protocol contract fixture"})
            run = run_instance(manifest, instance.instance_id, FixtureClient(manifest.service_model, []),
                               FixtureClient(manifest.customer_model, [answer(action)]), trial)
            row = score_run(manifest, run)
            assert not row["discovery_success"] and row["replay_verified"]
            run.save(evidence_dir / "discovery" / f"{instance.instance_id}-{trial}.json")
            all_runs.append(run)
    summary = summarize(manifest, all_runs)
    assert summary["complete"]
    results["discovery"] = {"instances": len(manifest.instances), "replay_checks": len(all_runs), "all_replayed": True}
    (directory / "verification.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
