"""Offline provenance audit: formal development discoveries vs Reflection inputs.

Reads only work/r0-* development records; never reads evaluation/Held-out data,
constructs transports, modifies historical evidence, or changes training policy.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from integrations.usami import UsamiAdapter
from integrations.usami.adapter import NativeArtifact
from vast_coevo.models import EpisodeEvidence


def audit(root):
    episodes={};reflections=[];checks=[]
    for arm in ('A','B'):
        work=root/'work'/('r0-'+arm)
        for path in sorted((work/'native/episodes').glob('*/evidence.json')):
            e=EpisodeEvidence.model_validate_json(path.read_text())
            if e.config.partition!='development':raise ValueError('heldout cannot enter training audit')
            artifact=NativeArtifact.model_validate_json(Path(e.trace.path).read_text())
            t=artifact.native_trace
            episodes[e.episode_id]=dict(arm=arm,id=e.episode_id,generation=int(e.episode_id.split('.')[0][1:]),
                evidence_hash=e.evidence_hash,world_hash=e.config.initial_world_hash,
                track=e.track,termination=e.termination,customer_snapshot=e.customer_snapshot_hash,
                events=[v.model_dump(mode='json') for v in e.events],
                failures=[v.model_dump(mode='json') for v in e.failures],
                customer_actions=t.get('actions',[]),trace=e.trace.model_dump(mode='json'),
                source=str(path.relative_to(root)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                service_reflection_membership=[])
        for path in sorted((work/'runs'/('r0-'+arm)/'evolution').glob('g*.service.json')):
            r=json.loads(path.read_text())['record'];ref=r['reflection']
            ids=[]
            for e in ref['input']['evidence']:
                row=episodes[e['episode_id']]
                if row['evidence_hash']!=e['evidence_hash']:raise ValueError('Reflection evidence differs from original')
                row['service_reflection_membership'].append(r['generation']);ids.append(e['episode_id'])
            reflections.append(dict(arm=arm,generation=r['generation'],action=r['patch']['action'],
                evidence_ids=ids,verified_failures=sum(len(e['failures']) for e in ref['input']['evidence']),
                actual_violations=sum(ev['classification']=='successful_business_violation' for e in ref['input']['evidence'] for ev in e['events']),
                source=str(path.relative_to(root))))
    discoveries=[e for e in episodes.values() if e['failures']]
    for row in discoveries:
        e=EpisodeEvidence.model_validate_json((root/row['source']).read_text())
        a=NativeArtifact.model_validate_json(Path(e.trace.path).read_text())
        adapter=UsamiAdapter(root/'audit-offline-unused',(a.profile,))
        checked=adapter.replay(e,a.customer_snapshot,a.service_snapshot)
        if not checked.verified:raise ValueError('discovery replay failed: '+checked.reason)
        checks.append(dict(episode_id=e.episode_id,replay=checked.model_dump(mode='json')))
    return dict(schema_version=1,online_calls=0,historical_data_changed=False,
        scope='formal A/B development only; no Smoke, evaluation or heldout data read',
        source_root=str(root.resolve()),episodes=list(episodes.values()),reflections=reflections,
        discovery_replays=checks,
        summary=dict(formal_episodes=len(episodes),reflections=len(reflections),
            distinct_autonomous_worlds=len({e['world_hash'] for e in episodes.values() if e['track']=='discovery'}),
            distinct_task_worlds=len({e['world_hash'] for e in episodes.values() if e['track']=='service_task'}),
            reflection_input_episodes=len({eid for r in reflections for eid in r['evidence_ids']}),
            successful_business_violations=sum(ev['classification']=='successful_business_violation' for e in episodes.values() for ev in e['events']),
            failure_episodes=len(discoveries),independent_failure_fingerprints=len({f['fingerprint'] for e in discoveries for f in e['failures']}),
            discovered_but_never_reflected=[e['id'] for e in discoveries if not e['service_reflection_membership']],
            terminations=dict(Counter(e['termination'] for e in episodes.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise FileExistsError('do not overwrite audit results')
    value=audit(args.root.resolve());args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value['summary'],ensure_ascii=False))
