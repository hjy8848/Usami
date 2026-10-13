"""Replay new-domain live pilots using their exact archived runtime sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('pilot',type=Path);args=parser.parse_args()
    pilot=args.pilot.resolve();profile=json.loads((pilot/'service-profile.json').read_text())
    package={'fulfillment':'usami_fulfillment','stayops':'usami_stayops'}[profile['domain']]
    with tempfile.TemporaryDirectory(prefix='usami-archived-pilot-') as tmp:
        root=Path(tmp)
        with tarfile.open(pilot/'runtime-source.tar.gz') as archive:
            for path,expected in profile['source_hashes'].items():
                relative=Path(path)
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('unsafe archived source path')
                member=archive.getmember(path)
                if not member.isfile():raise ValueError('expected an archived source file')
                data=archive.extractfile(member).read()
                if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('original archived source hash mismatch')
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        code='''
import json,importlib,sys
from pathlib import Path
module=importlib.import_module(sys.argv[1]+'.benchmark');pilot=Path(sys.argv[2])
report=json.loads((pilot/'pilot-report.json').read_text())
for track in ['service','discovery']:
 manifest=module.load(pilot/(track+'-profile.json'))
 paths=[pilot/track/(i.id+'.'+trial+'.run.json') for i in manifest.instances for trial in manifest.trials]
 assert set(paths)==set((pilot/track).glob('*.run.json'))
 runs=[module.Run.model_validate_json(p.read_text()) for p in paths]
 rebuilt=module.summarize(manifest,runs)
 assert rebuilt==report[track+'_report']
 print(track+': '+str(len(runs))+' exact archived-source real attempts replayed, including failures; no provider calls')
'''
        subprocess.run([sys.executable,'-c',code,package,str(pilot)],cwd=root,
                       env={**os.environ,'PYTHONPATH':str(root)},check=True)


if __name__=='__main__':main()
