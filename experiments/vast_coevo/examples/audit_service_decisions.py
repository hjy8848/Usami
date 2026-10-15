"""Read-only audit of the released 116 episodes, after full frozen-source Replay."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from replay_service_repair import under
from integrations.usami.adapter import NativeArtifact
from integrations.usami.domains import native_trace, execution_of
from integrations.usami.service_audit import audit_writes
from vast_coevo.models import EpisodeEvidence
from vast_coevo.schema import atomic_json, digest


def audit_bundle(bundle_path, output):
    bundle_path, output = Path(bundle_path).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('audit output already exists; original evidence cannot be overwritten')
    with tempfile.TemporaryDirectory(prefix='service-decision-audit-') as temporary:
        root = Path(temporary)
        with tarfile.open(bundle_path) as archive:
            for member in archive.getmembers():
                if Path(member.name).is_absolute() or '..' in Path(member.name).parts or not (member.isfile() or member.isdir()):
                    raise ValueError('unsafe archive member')
                path = under(root, member.name)
                if member.isdir(): path.mkdir(parents=True,exist_ok=True)
                else:
                    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(archive.extractfile(member).read())
        manifest = json.loads((root/'bundle-manifest.json').read_text())
        if manifest['kind'] != 'single_service_repair_cross': raise ValueError('not the released Service repair bundle')
        for name, expected in manifest['files'].items():
            if hashlib.sha256(under(root,name).read_bytes()).hexdigest() != expected: raise ValueError('bundle member changed: '+name)
        # The old runtime is imported only inside this isolated subprocess.
        replay = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('replay_service_repair.py')),
            '--worker', str(root)], capture_output=True, text=True)
        if replay.returncode: raise RuntimeError(replay.stderr)
        receipt = json.loads(replay.stdout.splitlines()[-1])
        if receipt['episodes_replayed'] != 116 or receipt['online_calls'] != 0:
            raise ValueError('incomplete frozen-source Replay')
        reports = []
        for path in sorted(root.rglob('evidence.json')):
            raw = json.loads(path.read_text())
            if 'episode_id' not in raw or 'native_trace_hash' not in raw: continue
            evidence = EpisodeEvidence.model_validate(raw)
            original = manifest['original_root'].rstrip('/')+'/'
            if not evidence.trace.path.startswith(original): raise ValueError('unexpected original evidence root')
            native_path = under(root, evidence.trace.path[len(original):])
            artifact_raw = json.loads(native_path.read_text())
            if digest(artifact_raw) != evidence.trace.sha256: raise ValueError('original artifact hash changed')
            artifact = NativeArtifact.model_validate(artifact_raw)
            if (artifact.model_calls != evidence.model_calls or artifact.injections != evidence.injections or
                    artifact.config != evidence.config or artifact.service_snapshot.snapshot_hash != evidence.service_snapshot_hash):
                raise ValueError('audit inputs not bound to frozen-replayed artifact')
            trace = native_trace('cloudops', json.loads(artifact.native_trace_json), artifact.track)
            reports.append(audit_writes(evidence, execution_of('cloudops', trace, artifact.track), artifact.service_snapshot))
        if len(reports) != 116: raise ValueError('expected exactly 116 immutable source episodes')
        writes = [row for report in reports for row in report['writes']]
        failed = [row for row in writes if row['outcome']['classification'] == 'successful_business_violation']
        summary = dict(episodes=len(reports), writes=len(writes), successful_business_violations=len(failed),
            successful_unapproved_writes=sum(row['outcome']['success'] and not row['exact_customer_authorized'] for row in writes),
            business_rules=dict(Counter(row['reference_error_code'] or 'EXPECTED_TRANSITION_MISMATCH' for row in failed)),
            failure_diagnoses=dict(Counter(label for row in failed for label in row['diagnosis'])),
            violations_with_blocking_facts_verified=sum(row['reference_blocking_facts_verified'] for row in failed),
            violations_with_skill_injected=sum(bool(row['actual_skill_injection']) for row in failed),
            by_cross_group={group: dict(episodes=sum(report['episode_id'].endswith('.'+group) for report in reports),
                violations=sum(row['outcome']['classification']=='successful_business_violation'
                    for report in reports if report['episode_id'].endswith('.'+group) for row in report['writes']))
                for group in ('C0xS0', 'C1xS0', 'C0xS1', 'C1xS1')})
        result = dict(schema_version=1, kind='historical-service-decision-audit', historical_only=True,
            selection_changed=False, oracle_engine_rules_changed=False,
            bundle_sha256=hashlib.sha256(bundle_path.read_bytes()).hexdigest(), frozen_source_replay=receipt,
            audit_source_hashes={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (ROOT/'integrations/usami/service_audit.py', Path(__file__))},
            summary=summary, reports=reports)
        atomic_json(output,result,immutable=True)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(audit_bundle(args.bundle,args.output),ensure_ascii=False,indent=2))
