"""Replay all original pre-schema-fix attempts in an isolated source snapshot."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=Path('benchmarks/cloudops-v0.1/pilot-initial'))
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='usami-cloudops-original-') as temporary:
        snapshot = Path(temporary)
        for package in ('usami', 'usami_cloudops'):
            shutil.copytree(root / package, snapshot / package, ignore=shutil.ignore_patterns('__pycache__'))
        source=evidence / 'original-source/customer.py.txt'
        if not source.exists():source=evidence / 'original-source/customer.before_schema_fix.py.txt'
        shutil.copyfile(source, snapshot / 'usami_cloudops/customer.py')
        code = '''
import json,sys
from pathlib import Path
from usami_cloudops.benchmark import load,Run,summarize
root=Path(sys.argv[1]);report=json.loads((root/'pilot-report.json').read_text())
for track in ('service','discovery'):
    if track+'_report' not in report:continue
    manifest=load(root/(track+'-profile.json'))
    paths=[root/track/(i.id+'.'+trial+'.run.json') for i in manifest.instances for trial in manifest.trials]
    assert set(paths)==set((root/track).glob('*.run.json'))
    runs=[Run.model_validate_json(p.read_text()) for p in paths]
    rebuilt=summarize(manifest,runs)
    assert rebuilt==report[track+'_report']
    print(track+': '+str(len(runs))+' original live runs replayed, including errors; no provider calls')
'''
        subprocess.run([sys.executable, '-c', code, str(evidence)], cwd=snapshot,
                       env={**os.environ, 'PYTHONPATH': str(snapshot)}, check=True)


if __name__ == '__main__':
    main()
