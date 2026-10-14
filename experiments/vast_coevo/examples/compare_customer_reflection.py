"""One real Customer Reflection on exactly the cloudops-live-002 evidence.

Old sources verify old evidence in an isolated offline subprocess. Current
Reflector consumes the same hash-bound evidence through a read-only relocation;
no historical JSON, response, Skill, verdict or Oracle is rewritten. The new
proposal is not dynamically selected or claimed to be an evolution success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tarfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def under(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("archive path escapes extraction directory")
    return path


def prepare(bundle, output):
    extraction = output / "historical-bundle"
    extraction.mkdir(parents=True)
    with tarfile.open(bundle) as archive:
        for member in archive.getmembers():
            if Path(member.name).is_absolute() or ".." in Path(member.name).parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe archive member")
            target = under(extraction, member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as destination:
                    destination.write(source.read())
    manifest = json.loads((extraction / "bundle-manifest.json").read_text())
    index = next(index for index, row in enumerate(manifest["runs"]) if row["run_id"] == "cloudops-live-002")
    entry = manifest["runs"][index]
    # Use the archived runtime, not current source pins, to independently verify
    # complete historical Episodes and the historical Controller verdict.
    checked = subprocess.run([sys.executable, "-I", str(REPO / "experiments/vast_coevo/examples/replay_live_bundle.py"),
                              "--extract", str(extraction), "--worker-index", str(index)], capture_output=True, text=True)
    if checked.returncode:
        raise RuntimeError("historical native replay failed: " + checked.stderr)
    receipt = json.loads(checked.stdout)
    if receipt["online_calls"] != 0 or receipt["episodes_replayed"] != 8:
        raise ValueError("unexpected historical verification coverage")
    return extraction, entry, receipt


def historical_input(extraction, entry):
    from integrations.usami import UsamiAdapter, UsamiProfile, ServiceTaskProfile
    from vast_coevo.reflection.reflector import ReflectionInput
    from vast_coevo.reflection.scope import DomainPolicy
    from vast_coevo.models import EpisodeEvidence, ModelSpec
    from vast_coevo.skills.library import LibrarySnapshot
    from vast_coevo.schema import digest

    data = under(extraction, entry["data"])
    stored = json.loads((data / "runs/cloudops-live-002/evolution/g0.customer.json").read_text())
    original = stored["record"]
    if digest(original) != stored["record_hash"]:
        raise ValueError("historical evolution record changed")
    audit = json.loads((REPO / "experiments/vast_coevo/results/CUSTOMER_UPDATE_SCOPE_AUDIT.json").read_text())
    if audit["stored_record_hash"] != stored["record_hash"] or audit["materialized_original_patch"] != original["patch"]:
        raise ValueError("historical audit does not match the actual original proposal")
    old = original["reflection"]["input"]
    rows = tuple(EpisodeEvidence.model_validate(row) for row in old["evidence"])
    plan = json.loads(under(extraction, entry["plan"]).read_text())
    adapter = UsamiAdapter(data / "native", tuple(UsamiProfile.model_validate(p) for p in plan["profiles"]),
                          tuple(ServiceTaskProfile.model_validate(t) for t in plan["service_tasks"]))
    original_root = entry["original_root"].rstrip("/")
    read_text = Path.read_text
    def relocated(path, *args, **kwargs):
        value = str(path)
        if value.startswith(original_root + "/"):
            path = under(data, value[len(original_root)+1:])
        return read_text(path, *args, **kwargs)
    Path.read_text = relocated
    try:
        views = tuple(adapter.reflection_view(row) for row in rows)
        forbidden = tuple(sorted({identifier for row in rows for identifier in adapter.forbidden_identifiers(row.config)}))
    finally:
        Path.read_text = read_text
    value = ReflectionInput(generation=old["generation"], role="customer", library=LibrarySnapshot.model_validate(old["library"]),
                            evidence=rows, interaction_views=views, allowed_tools=old["allowed_tools"],
                            public_policy=old["public_policy"], boundaries=old["boundaries"],
                            domain_policy=DomainPolicy(add_domains=("cloudops",)))
    model = ModelSpec.model_validate(original["reflection"]["call"]["model"])
    return value, model, stored, forbidden


def main():
    from vast_coevo.schema import atomic_json, digest
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=REPO / "experiments/vast_coevo/results/live-pilot-bundle.tar.gz")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--offline-check", action="store_true", help="verify and prepare input; zero model calls")
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists():
        raise ValueError("comparison output already exists; no repeated Reflection")
    output.mkdir(parents=True)
    extraction, entry, receipt = prepare(args.bundle.resolve(), output)
    value, model, old, forbidden = historical_input(extraction, entry)
    from integrations.usami.adapter import source_hashes
    pins = source_hashes()
    for name, expected in pins.items():
        original = REPO / name
        if hashlib.sha256(original.read_bytes()).hexdigest() != expected:
            raise ValueError("current reflection source changed while freezing")
        target = output / "source-snapshot" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    manifest = dict(schema_version=1, run_id=args.run_id, purpose="customer_goal_direction_comparison",
                    source_run_id="cloudops-live-002", old_record_hash=old["record_hash"],
                    historical_bundle_sha256=hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
                    model=model.model_dump(mode="json"), max_reflection_calls=0 if args.offline_check else 1,
                    max_input_chars=400000, source_evidence_hashes=[row.evidence_hash for row in value.evidence],
                    input_hash=digest(value), code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                    source_hashes=pins,
                    code_changes_pending=bool(subprocess.check_output(["git", "diff", "--name-only"], cwd=REPO, text=True).strip()),
                    dynamic_gate_run=False, evolution_success_claim=False, replay_receipt=receipt)
    atomic_json(output / "manifest.json", manifest, immutable=True)
    atomic_json(output / "old-evolution.json", old, immutable=True)
    atomic_json(output / "new-input.json", value.model_dump(mode="json"), immutable=True)
    if args.offline_check:
        print(json.dumps(dict(run_id=args.run_id, online_calls=0, input_hash=digest(value), replay=receipt)))
        return
    from integrations.usami.cli import transport
    from vast_coevo.reflection.reflector import CustomerReflector
    from vast_coevo.skills.validation import StaticSkillGate
    atomic_json(output / "reflection.started.json", dict(run_id=args.run_id, input_hash=digest(value), model=model.model_dump(mode="json")), immutable=True)
    # Model/sampling are taken from the historical record, never a fallback.
    client = transport(model)
    try:
        record = CustomerReflector(client, model).reflect(value)
    finally:
        client.close()
    atomic_json(output / "new-reflection.json", record.model_dump(mode="json"), immutable=True)
    # Structural validation is separate from semantic experiment review and
    # does not apply/publish a candidate or execute any dynamic comparisons.
    static = StaticSkillGate(allowed_tools=value.allowed_tools, forbidden_identifiers=forbidden,
                             allowed_domains=("cloudops",)).validate(value.library, record.patch) if record.patch else None
    summary = dict(run_id=args.run_id, reflection_calls=record.calls, error=record.error,
                   action=record.patch.action if record.patch else None,
                   static_validation=static.model_dump(mode="json") if static else None,
                   semantic_review_status=record.semantic_review_status,
                   dynamic_gate_run=False, evolution_success_claim=False)
    atomic_json(output / "summary.json", summary, immutable=True)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
