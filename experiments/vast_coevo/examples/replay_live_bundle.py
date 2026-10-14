"""Offline replay of published live evidence against its exact recorded sources.

Filesystem redirects relocate absolute artifact references without rewriting any
signed JSON, model request, Skill hash, native trace, policy or Oracle result.
Each source version is imported in an isolated subprocess. No credentials or
model connection are needed. Only this repository's archived sources execute;
Skill data and model outputs are never executed as code.
"""
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


def worker(root, index):
    manifest = json.loads((root / "bundle-manifest.json").read_text())
    entry = manifest["runs"][index]
    data, source = under(root, entry["data"]), under(root, entry["source"])
    paths = sorted(data.glob("native/episodes/*/native.json"))
    if not paths:
        raise ValueError("bundle has no native episodes")
    pins = json.loads(paths[0].read_text())["source_hashes"]
    for name, expected in pins.items():
        if hashlib.sha256(under(source, name).read_bytes()).hexdigest() != expected:
            raise ValueError("archived source hash mismatch: " + name)
    # The path string in original evidence remains untouched and hash-checked.
    original = entry["original_root"].rstrip("/")
    read_text = Path.read_text

    def relocated(path, *args, **kwargs):
        value = str(path)
        if value.startswith(original + "/"):
            path = under(data, value[len(original) + 1:])
        return read_text(path, *args, **kwargs)

    Path.read_text = relocated
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    from integrations.usami import UsamiAdapter, UsamiProfile, ServiceTaskProfile
    from vast_coevo.models import EpisodeEvidence
    from vast_coevo.skills.library import LibrarySnapshot
    raw = [json.loads(path.read_text()) for path in paths]
    plan = json.loads(under(root, entry["plan"]).read_text())
    profiles = [UsamiProfile.model_validate(item) for item in plan["profiles"]]
    tasks = [ServiceTaskProfile.model_validate(item) for item in plan["service_tasks"]]

    def offline_only(*args, **kwargs):
        raise AssertionError("offline bundle replay cannot start a model client")

    adapter = UsamiAdapter(data / "native", profiles, tasks, client_factory=offline_only)
    requests = 0
    for path, native in zip(paths, raw):
        evidence = EpisodeEvidence.model_validate_json(path.with_name("evidence.json").read_text())
        result = adapter.replay(evidence, LibrarySnapshot.model_validate(native["customer_snapshot"]),
                                LibrarySnapshot.model_validate(native["service_snapshot"]))
        if not result.verified:
            raise ValueError(evidence.episode_id + ": " + result.reason)
        requests += result.request_count
    report = json.loads((data / "runs" / entry["run_id"] / "report.json").read_text())
    if report["status"] != entry["status"]:
        raise ValueError("recorded run status differs from bundle manifest")
    from vast_coevo.evidence.archive import EvidenceArchive
    from vast_coevo.evolution.controller import CoEvolutionController
    from vast_coevo.storage.runs import RunStore
    from vast_coevo.skills.library import LibraryStore

    class OfflineClient:
        complete = staticmethod(offline_only)

    store = RunStore(data / "runs")
    rerun = CoEvolutionController(adapter, OfflineClient(), OfflineClient(), LibraryStore(data / "libraries"),
                                  EvidenceArchive(data / "evidence"), store).run(store.load_config(entry["run_id"]))
    if rerun.model_dump(mode="json") != report:
        raise ValueError("full Controller report changed during offline replay")
    return {"run_id": entry["run_id"], "status": report["status"], "episodes_replayed": len(paths),
            "agent_requests_replayed": requests, "reflection_calls_recorded": report["consumption"]["reflection_calls"],
            "generations": len(report["generations"]), "online_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path(__file__).resolve().parents[1] / "results" / "live-pilot-bundle.tar.gz")
    parser.add_argument("--extract", type=Path)
    parser.add_argument("--worker-index", type=int)
    args = parser.parse_args()
    if args.worker_index is not None:
        print(json.dumps(worker(args.extract.resolve(), args.worker_index), ensure_ascii=False))
        return
    root = args.extract.resolve() if args.extract else Path(tempfile.mkdtemp(prefix="vast-live-replay-"))
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.bundle, "r:gz") as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            if name.is_absolute() or ".." in name.parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe archive member")
            destination = under(root, member.name)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, destination.open("wb") as target:
                    target.write(src.read())
    manifest = json.loads((root / "bundle-manifest.json").read_text())
    for index in range(len(manifest["runs"])):
        result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--extract", str(root),
                                 "--worker-index", str(index)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        print(result.stdout.strip())


if __name__ == "__main__":
    main()
