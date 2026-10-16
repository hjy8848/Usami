"""One real seed task -> one global examiner submission -> real Service -> replay.

No Reflection in this smoke/demo. Multi-generation execution uses the existing
integrations.usami run command and an examiner-enabled exploration profile.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO))
from integrations.usami import UsamiAdapter,UsamiProfile,ServiceTaskProfile
from integrations.usami.adapter import source_hashes
from integrations.usami.cli import model_from_env
from integrations.usami.domains import execution_of,native_trace
from integrations.usami.costs import _sum, _tools
from vast_coevo.models import Budget,EpisodeEvidence
from vast_coevo.schema import atomic_json
from vast_coevo.skills.library import LibrarySnapshot,empty_snapshot

DEFAULT_SEED_TASK={'saas':'seat_activate','cloudops':'dependency_boot','fulfillment':'receiving_recovery','stayops':'room_cleaning'}


def prepare(domain,seed,mode):
    generator={}
    if domain=='saas':
        generator={'version':'saas-generator-0.2.0','rules':{'version':'saas-rules-0.2.0'}}
    base=UsamiProfile(config_id='seed',domain=domain,seed=seed,identity='user_000' if domain=='saas' else 'u0',mode=mode,generator=generator)
    author=UsamiProfile.model_validate({**base.model_dump(mode='json'),'config_id':'exam','examiner_protocol':'usami-examiner-v1'})
    return base,author


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','replay'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--domain',choices=tuple(DEFAULT_SEED_TASK),default='cloudops')
    parser.add_argument('--seed',type=int,default=731)
    parser.add_argument('--seed-task',help='initial native Service Task; the examiner chooses its subsequent task independently')
    parser.add_argument('--mode',choices=['reference','sandbox'],default='sandbox')
    parser.add_argument('--customer-library');parser.add_argument('--service-library')
    args=parser.parse_args(argv);root=Path(args.output).resolve()
    if args.command=='replay':
        manifest=json.loads((root/'manifest.json').read_text())
        profiles=[UsamiProfile.model_validate(p) for p in manifest['profiles']]
        tasks=[ServiceTaskProfile.model_validate(t) for t in manifest['service_tasks']]
        a=UsamiAdapter(root/'native',profiles,tasks)
        c=LibrarySnapshot.model_validate(manifest['customer']);s=LibrarySnapshot.model_validate(manifest['service'])
        results=[]
        for path in sorted((root/'native').glob('episodes/*/evidence.json')):
            e=EpisodeEvidence.model_validate_json(path.read_text());r=a.replay(e,c,s)
            results.append({'episode':e.episode_id,**r.model_dump(mode='json')})
        atomic_json(root/'replay.json',results)
        print(json.dumps(results,ensure_ascii=False,indent=2));return 0 if len(results)==2 and all(r['verified'] for r in results) else 1
    # Resolve model settings before creating the output; credentials are loaded by
    # the existing client, never serialized. Existing output is never overwritten.
    cm,sm=model_from_env('customer'),model_from_env('service')
    c=LibrarySnapshot.model_validate_json(Path(args.customer_library).read_text()) if args.customer_library else empty_snapshot('customer')
    s=LibrarySnapshot.model_validate_json(Path(args.service_library).read_text()) if args.service_library else empty_snapshot('service')
    if (c.role,s.role)!=('customer','service'):raise ValueError('reversed library roles')
    base,author=prepare(args.domain,args.seed,args.mode)
    task=ServiceTaskProfile(task_ref='initial-task',config_id=base.config_id,scenario=args.seed_task or DEFAULT_SEED_TASK[args.domain])
    budget=Budget(max_customer_turns=1,max_customer_llm_calls=1,max_service_llm_calls=8,max_service_tool_calls=16)
    a=UsamiAdapter(root/'native',[base,author],[task])
    seed_config=a.config_for('seed',cm,sm,budget,task_ref=task.task_ref)
    exam_config=a.config_for('exam',cm,sm,budget)
    root.mkdir(parents=True,exist_ok=False)
    manifest={'protocol':'usami-examiner-v1','profiles':[p.model_dump(mode='json') for p in (base,author)],
        'service_tasks':[task.model_dump(mode='json')],'customer':c.model_dump(mode='json'),'service':s.model_dump(mode='json'),
        'seed_config':seed_config.model_dump(mode='json'),'exam_config':exam_config.model_dump(mode='json'),
        'max_llm_calls':17,'max_tool_calls':32,'reflection_calls':0,'source_hashes':source_hashes()}
    atomic_json(root/'manifest.json',manifest,immutable=True)
    rows=[]
    try:
        first=a.run_service_task(seed_config,task.task_ref,c,s,'seed-task');rows.append(first)
        if not first.replay.verified or any(x in first.termination for x in ('error','interrupted')):
            raise ValueError('initial Service task did not finish with verifiable evidence')
        a._examiner_history[args.domain]=[a._history_item(first)]
        second=a.run_episode(exam_config,c,s,'authored-exam');rows.append(second)
        status='completed' if second.replay.verified and second.termination=='completed' else 'failed'
        error=None
    except (Exception,KeyboardInterrupt) as exc:
        status='failed';error=type(exc).__name__+': '+str(exc)
    calls=[call for row in rows for call in row.model_calls]
    unfinished=[str(path.parent) for path in (root/'native').glob('episodes/*/online-start.json') if not (path.parent/'evidence.json').exists()]
    summary={'cost_scope':'completed_evidence_only','unfinalized_attempts':unfinished,'cost_complete':not unfinished,'status':status,'error':error,'episodes':len(rows),'reflection_calls':0,
        'customer_cost':_sum([call for call in calls if call.role=='customer'],sum(len(_tools(call)) for call in calls if call.role=='customer')),
        'service_cost':_sum([call for call in calls if call.role=='service'],sum(r.consumption.tool_calls for r in rows)),
        'evidence':[r.evidence_hash for r in rows],'replay_verified':all(r.replay.verified for r in rows),
        'construction_errors':[r.termination for r in rows if 'construction' in r.termination]}
    atomic_json(root/'summary.json',summary,immutable=True)
    print(json.dumps(summary,ensure_ascii=False,indent=2));return 0 if status=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
