"""Portable, source-pinned offline Replay of the complete 40-Episode bundle."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def under(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('archive path escapes root')
    return path


def worker(root):
    manifest=json.loads((root/'manifest.json').read_text())
    bundle=json.loads((root/'bundle-manifest.json').read_text())
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(root/'source-snapshot'))
    script=root/'experiment-script.py'
    if hashlib.sha256(script.read_bytes()).hexdigest()!=manifest['experiment_script_sha256']:
        raise ValueError('experiment script hash changed')
    spec=importlib.util.spec_from_file_location('frozen_customer_experiment',script)
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    sys.modules['compare_customer_performance']=experiment
    read_text=Path.read_text
    original=bundle['original_root'].rstrip('/')
    def relocated(path,*args,**kwargs):
        name=str(path)
        if name.startswith(original+'/'):path=under(root,name[len(original)+1:])
        return read_text(path,*args,**kwargs)
    # Read-only relocation; signed payloads, paths and hashes are never rewritten.
    Path.read_text=relocated
    try:
        before=json.loads((root/'replay.json').read_text())
        rebuilt=experiment.replay_all(root)
        if rebuilt!=before:raise ValueError('Replay receipt differs from published original')
        expected=json.loads((root/'results.json').read_text())
        actual=experiment.report(root)
        if json.loads(json.dumps(actual))!=expected:raise ValueError('complete metrics/report differs from published original')
        review_script=root/'review-script.py'
        if review_script.exists():
            expected_review=json.loads((root/'attribution-review.json').read_text())
            spec=importlib.util.spec_from_file_location('frozen_customer_review',review_script)
            review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
            review.review(root)
            if json.loads((root/'attribution-review.json').read_text())!=expected_review:
                raise ValueError('post-run attribution audit changed during replay')
    finally:Path.read_text=read_text
    print(json.dumps(dict(episodes_replayed=rebuilt['episodes_replayed'],source_modules_verified=len(manifest['source_hashes']),
                          complete_statistics_identical=True,online_calls=0)),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--worker',type=Path)
    args=parser.parse_args()
    if args.worker:return worker(args.worker.resolve())
    if not args.bundle:parser.error('--bundle is required')
    with tempfile.TemporaryDirectory(prefix='customer-paired-replay-') as temp:
        root=Path(temp)
        with tarfile.open(args.bundle) as archive:
            for member in archive.getmembers():
                if Path(member.name).is_absolute() or '..' in Path(member.name).parts or not(member.isfile() or member.isdir()):
                    raise ValueError('unsafe archive member')
                path=under(root,member.name)
                if member.isdir():path.mkdir(parents=True,exist_ok=True)
                else:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(archive.extractfile(member).read())
        bundle=json.loads((root/'bundle-manifest.json').read_text())
        if bundle['kind']!='paired_customer_performance':raise ValueError('wrong bundle kind')
        for name,expected in bundle['files'].items():
            if hashlib.sha256(under(root,name).read_bytes()).hexdigest()!=expected:
                raise ValueError('artifact SHA256 mismatch: '+name)
        result=subprocess.run([sys.executable,'-I',str(Path(__file__).resolve()),'--worker',str(root)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        # Worker prints intermediate report rows; show the final portable receipt.
        print(result.stdout.splitlines()[-1],flush=True)


if __name__=='__main__':main()
