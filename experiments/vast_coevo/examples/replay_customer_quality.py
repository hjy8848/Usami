"""Offline reproduction of a preregistered QGD decision and every probe report."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.usami.adapter import NativeArtifact, UsamiAdapter, source_hashes
from vast_coevo.evaluation.customer import CustomerGateManifest, CustomerQualityResult, ProbeEpisode
from vast_coevo.evaluation.discovery_gate import compare_customer_probes
from vast_coevo.evidence.archive import EvidenceArchive


def replay(directory):
    directory = Path(directory).resolve()
    manifest = CustomerGateManifest.model_validate_json((directory / 'manifest.json').read_text())
    expected = CustomerQualityResult.model_validate_json((directory / 'result.json').read_text())
    if manifest.source_hashes != source_hashes():
        raise ValueError('source pins changed: use the archived source checkout to replay this run')
    if manifest.manifest_hash != expected.manifest_hash:
        raise ValueError('result belongs to a different preregistered manifest')
    archive = EvidenceArchive(directory.parent.parent)
    sides = []
    for hashes in (expected.baseline_reports, expected.candidate_reports):
        reports = []
        for content_hash in hashes:
            report = ProbeEpisode.model_validate_json((directory / (content_hash + '.json')).read_text())
            if report.report_hash != content_hash: raise ValueError('probe report filename differs from content')
            evidence = archive.load(report.evidence_hash)
            artifact = NativeArtifact.model_validate_json(Path(evidence.trace.path).read_text())
            adapter = UsamiAdapter(directory, (artifact.profile,), client_factory=lambda *args: forbidden_online())
            actual = adapter.customer_probes(evidence)
            if actual != report: raise ValueError('offline probe reconstruction differs: ' + report.episode_id)
            reports.append(actual)
        sides.append(reports)
    actual = compare_customer_probes(manifest, *sides)
    if actual != expected: raise ValueError('offline Customer gate decision differs')
    return {'replay_verified': True, 'episodes': sum(map(len, sides)), 'online_calls': 0,
            'decision': actual.decision, 'manifest_hash': manifest.manifest_hash}


def forbidden_online():
    raise AssertionError('offline gate replay cannot create an online client')


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='evidence/customer-quality/<prefix digest>')
    args = parser.parse_args()
    print(json.dumps(replay(args.directory), ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
