"""Replay the published real Customer goal comparison with zero online calls."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def under(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("bundle path escapes extraction directory")
    return path


def worker(root):
    bundle = json.loads((root / "bundle-manifest.json").read_text())
    source = under(root, bundle["source"])
    data = under(root, bundle["records"])
    manifest = json.loads((data / "manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if hashlib.sha256(under(source, name).read_bytes()).hexdigest() != expected:
            raise ValueError("reflection source hash mismatch: " + name)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    from vast_coevo.reflection.reflector import CustomerReflector, ReflectionInput
    from vast_coevo.models import ModelSpec
    original = json.loads((data / "new-reflection.json").read_text())
    call = original["call"]
    class RecordedClient:
        def __init__(self):
            self.calls = 0
        def complete(self, request):
            if request != call["request"] or self.calls:
                raise ValueError("Reflection wire request changed or was repeated")
            self.calls += 1
            return call["response"]
    client = RecordedClient()
    record = CustomerReflector(client, ModelSpec.model_validate(call["model"]), max_input_chars=manifest["max_input_chars"]).reflect(
        ReflectionInput.model_validate(original["input"]))
    if record.model_dump(mode="json") != original or client.calls != 1:
        raise ValueError("Reflection record changed during exact source replay")
    return dict(run_id=manifest["run_id"], recorded_reflection_calls_replayed=1,
                complete_record_identical=True, source_modules_verified=len(manifest["source_hashes"]), online_calls=0)


def main():
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=repo / "experiments/vast_coevo/results/customer-goal-comparison-bundle.tar.gz")
    parser.add_argument("--history-bundle", type=Path, default=repo / "experiments/vast_coevo/results/live-pilot-bundle.tar.gz")
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker.resolve())))
        return
    root = Path(tempfile.mkdtemp(prefix="customer-goal-replay-"))
    with tarfile.open(args.bundle) as archive:
        for member in archive.getmembers():
            if Path(member.name).is_absolute() or ".." in Path(member.name).parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe archive member")
            path = under(root, member.name)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, path.open("wb") as destination:
                    destination.write(source.read())
    bundle = json.loads((root / "bundle-manifest.json").read_text())
    manifest = json.loads((under(root, bundle["records"]) / "manifest.json").read_text())
    if hashlib.sha256(args.history_bundle.read_bytes()).hexdigest() != manifest["historical_bundle_sha256"]:
        raise ValueError("historical evidence bundle differs")
    from compare_customer_reflection import prepare
    _, _, receipt = prepare(args.history_bundle.resolve(), root / "history-verification")
    if receipt != manifest["replay_receipt"]:
        raise ValueError("independent historical replay receipt changed")
    result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker", str(root)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
