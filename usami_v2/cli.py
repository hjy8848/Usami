"""Implemented Usami 2.0 commands only; importing never looks up credentials."""
import argparse
import json
from pathlib import Path

from vast_coevo.schema import atomic_json, digest
from usami_v2 import PROTOCOL
from usami_v2.contracts import CommunicationObligation, FactEvidence, PublicRequest, ServiceMessage
from usami_v2.commerce.models import Operation, PARAMETERS, Quote, World
from usami_v2.evaluation.checkpoints import DecisionCheckpoint
from usami_v2.evaluation.challenge_quality import ChallengeDescriptor
from usami_v2.evaluation.readiness import ReadinessPolicy, ReadinessReport
from usami_v2.runtime.observations import WorkingState
from usami_v2.scenarios.distribution import DistributionSpec


def contract_schemas():
    models = (CommunicationObligation, FactEvidence, PublicRequest, ServiceMessage,
              Quote, World, Operation, DecisionCheckpoint, ChallengeDescriptor,
              ReadinessPolicy, ReadinessReport, WorkingState, DistributionSpec)
    schemas = {model.__name__: model.model_json_schema() for model in models}
    schemas["BusinessToolParameters"] = {
        "protocol": "commerce-tool-parameters-v1",
        "tools": {name: model.model_json_schema() for name, model in sorted(PARAMETERS.items())},
    }
    return schemas


def export_schemas(root):
    root = Path(root)
    # Failure leaves any partial output visible. Never replace another attempt.
    root.mkdir(parents=True, exist_ok=False)
    schemas = contract_schemas()
    for name, schema in schemas.items():
        atomic_json(root / (name + ".json"), schema, immutable=True)
    manifest = {
        "protocol": "commerce-schema-bundle-v1", "research_protocol": PROTOCOL,
        "schema_hashes": {name: digest(schema) for name, schema in schemas.items()},
        "model_calls": 0,
        "claim_boundary": "Contract schemas only; no business task, real-model run or readiness PASS.",
    }
    manifest["manifest_hash"] = digest(manifest)
    atomic_json(root / "manifest.json", manifest, immutable=True)
    return manifest


def verify_schemas(root):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected_hash = manifest.get("manifest_hash")
    if expected_hash != digest({k: v for k, v in manifest.items() if k != "manifest_hash"}):
        raise ValueError("schema manifest integrity differs")
    if manifest.get("protocol") != "commerce-schema-bundle-v1" or manifest.get("model_calls") != 0:
        raise ValueError("unrecognized or falsely attributed contract artifact")
    expected = contract_schemas()
    if manifest.get("schema_hashes") != {name: digest(schema) for name, schema in expected.items()}:
        raise ValueError("schema bundle differs from this version of the runtime")
    if {p.name for p in root.iterdir()} != {name + ".json" for name in expected} | {"manifest.json"}:
        raise ValueError("schema bundle file set differs")
    for name, schema in expected.items():
        if json.loads((root / (name + ".json")).read_text(encoding="utf-8")) != schema:
            raise ValueError("schema content was changed: " + name)
    return {"verified": True, "schema_count": len(expected), "model_calls": 0,
            "manifest_hash": expected_hash}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=PROTOCOL)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("schema", help="export implemented contracts; zero model requests")
    export.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-schemas", help="offline integrity and current-schema verification")
    verify.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    result = export_schemas(args.output) if args.command == "schema" else verify_schemas(args.directory)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
