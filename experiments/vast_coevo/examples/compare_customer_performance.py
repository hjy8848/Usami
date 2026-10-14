"""Preregistered 20-world, 40-Episode real C0/C1 CloudOps comparison.

Only Customer Skill differs. No tasks, Reflection, training, selection or retry.
Native Adapter owns sessions, authority, Engine, Oracle, wire logs and Replay.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tarfile
import threading
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from integrations.usami import UsamiAdapter, UsamiProfile
from integrations.usami.adapter import NativeArtifact, source_hashes
from integrations.usami.domains import initial_world
from vast_coevo.evolution.gates import metrics
from vast_coevo.models import Budget, EpisodeConfig, EpisodeEvidence, ModelSpec
from vast_coevo.schema import atomic_json, digest
from vast_coevo.skills import LibrarySnapshot, SkillPatch, StaticSkillGate, apply_patch
from usami_cloudops import generate_world
from usami_cloudops.models import Access, Instance, Payment, Quota, World
from usami_cloudops.rules import invariants, owner, role, usage

# Environments, not agent requests. Every row describes a legal initial state.
# title, project status, billing, quota(cpu/memory/count), running prefix,
# dependency topology, actor, explicit role, sizing profile.
SCENARIOS = (
    ('宽松配额、停机依赖链', 'active','paid',(6,12,3),0,'chain','u0','admin','uniform'),
    ('一台运行、依赖链待启动', 'active','paid',(4,8,2),1,'chain','u0','admin','uniform'),
    ('两台运行、完整链尚有容量', 'active','paid',(6,12,3),2,'chain','u0','admin','uniform'),
    ('CPU 已满、内存与数量宽松', 'active','paid',(4,16,4),2,'chain','u0','admin','uniform'),
    ('内存已满、CPU 与数量宽松', 'active','paid',(8,8,4),2,'chain','u0','admin','uniform'),
    ('实例数已满、CPU 与内存宽松', 'active','paid',(8,16,2),2,'chain','u0','admin','uniform'),
    ('暂停、未付账单、Admin', 'suspended','unpaid',(4,8,2),0,'chain','u0','admin','uniform'),
    ('暂停、付款失败、星形依赖', 'suspended','failed',(6,12,3),0,'star','u0','admin','uniform'),
    ('已付账单但仍暂停', 'suspended','paid',(6,12,3),0,'chain','u0','admin','uniform'),
    ('非负责人 Admin、暂停未付、无依赖', 'suspended','unpaid',(6,12,3),0,'independent','u1','admin','uniform'),
    ('负责人无项目计算权限', 'active','paid',(6,12,3),0,'chain','u0',None,'uniform'),
    ('负责人 Operator、星形依赖已启动根', 'active','paid',(6,12,3),1,'star','u0','operator','uniform'),
    ('负责人 Viewer、无依赖已有运行实例', 'active','paid',(6,12,3),1,'independent','u0','viewer','uniform'),
    ('非负责人 Viewer、四节点汇合依赖', 'active','paid',(8,16,4),0,'diamond','u1','viewer','uniform'),
    ('非负责人 Operator、单实例配额已满', 'active','paid',(2,4,1),1,'chain','u2','operator','uniform'),
    ('非负责人 Operator、已付但暂停的汇合依赖', 'suspended','paid',(8,16,4),0,'diamond','u2','operator','uniform'),
    ('非负责人 Viewer、暂停且付款失败', 'suspended','failed',(4,8,2),0,'chain','u1','viewer','uniform'),
    ('非负责人 Admin、异构资源与无依赖', 'active','paid',(8,12,3),1,'independent','u1','admin','asymmetric'),
    ('非负责人 Admin、汇合依赖部分运行', 'active','paid',(8,16,4),2,'diamond','u1','admin','uniform'),
    ('负责人无计算权限、暂停未付、零配额', 'suspended','unpaid',(0,0,0),0,'star','u0',None,'uniform'),
)


def semantic_state(world):
    """Ignore seeds and display names, retain business state/relationships."""
    data = world.model_dump(mode='json')
    data.pop('seed')
    for collection in ('users','organizations','projects','instances'):
        for entity in data[collection].values():
            entity.pop('name', None)
    return digest(data)


def make_world(index):
    title,status,billing,quota,running,topology,actor,membership,sizing = SCENARIOS[index]
    seed = 2026101401 + index
    world = generate_world(seed)
    project = world.projects['p0']
    project.status = status
    project.quota = Quota(cpu=quota[0],memory=quota[1],instances=quota[2])
    invoice = world.invoices[project.invoice_id]
    invoice.payments = []
    if billing != 'unpaid':
        success = billing == 'paid'
        invoice.payments = [Payment(id='initial_p0_payment',key='initial',method='card_approved' if success else 'card_declined',
                                   amount_cents=invoice.amount_cents,outcome='succeeded' if success else 'failed',at=world.clock)]
    invoice.status = billing
    ids = ['p0_db','p0_app','p0_web']
    if topology == 'diamond':
        world.instances['p0_join'] = Instance(id='p0_join',name='Join',project_id='p0',cpu=2,memory=4)
        ids.append('p0_join')
    edges = {'chain': [[],['p0_db'],['p0_app']], 'star': [[],['p0_db'],['p0_db']],
             'independent': [[],[],[]], 'diamond': [[],['p0_db'],['p0_db'],['p0_app','p0_web']]}[topology]
    for n,rid in enumerate(ids):
        instance = world.instances[rid]
        instance.dependencies = edges[n]
        instance.status = 'running' if n < running else 'stopped'
        if sizing == 'asymmetric':
            instance.cpu,instance.memory = [(1,6),(3,2),(4,4)][n]
    key = 'p0_' + actor
    world.access.pop(key,None)
    if membership:
        world.access[key] = Access(id=key,project_id='p0',user_id=actor,role=membership)
    world = World.model_validate(world.model_dump(mode='json'))
    if invariants(world):
        raise ValueError('invalid scenario: '+str(invariants(world)))
    return title,world,actor


def historical_world():
    value = json.loads((REPO/'experiments/vast_coevo/results/customer-schema-history-001/new-input.json').read_text())
    evidence = value['evidence'][0]
    ref = evidence['trace']
    path = Path(ref['path'])
    if path.exists():
        raw = json.loads(path.read_text())
        if digest(raw) == ref['sha256']:
            return World.model_validate(json.loads(raw['native_trace_json'])['service_execution']['world_trace']['initial_state'])
    with tarfile.open(REPO/'experiments/vast_coevo/results/live-pilot-bundle.tar.gz') as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith('/native.json'):
                raw = json.load(archive.extractfile(member))
                if digest(raw) == ref['sha256']:
                    return World.model_validate(json.loads(raw['native_trace_json'])['service_execution']['world_trace']['initial_state'])
    raise ValueError('cannot verify the actual C1 training world')


def snapshots():
    results = REPO/'experiments/vast_coevo/results'
    report = json.loads((results/'CUSTOMER_SCHEMA_COMPARISON.json').read_text())
    record = json.loads((results/'customer-schema-history-001/new-reflection.json').read_text())
    if report['new_patch'] != record['patch'] or not report['static_validation']['passed']:
        raise ValueError('C1 does not match the statically accepted real proposal')
    c0 = LibrarySnapshot.model_validate_json((REPO/'experiments/vast_coevo/examples/customer-library.json').read_text())
    s0 = LibrarySnapshot.model_validate_json((REPO/'experiments/vast_coevo/examples/service-library.json').read_text())
    patch = SkillPatch.model_validate(record['patch'])
    c1 = apply_patch(c0,patch,'temporary-paired-evaluation:customer-schema-history-001')
    if [s.version for s in c0.skills] != [1] or [s.version for s in c1.skills] != [2]:
        raise ValueError('unexpected C0/C1 versions')
    old = record['input']['evidence'][0]['config']
    return {'C0':c0,'C1':c1,'S0':s0},patch,ModelSpec.model_validate(old['customer_model']),ModelSpec.model_validate(old['service_model'])


def prepare(root, run_id):
    if root.exists():
        raise ValueError('registration output already exists; never overwrite')
    libraries,patch,customer_model,service_model = snapshots()
    # Previous 6-call Service cap exhausted the source Episode. Two Customer
    # turns are retained; 12 Service calls / 16 tools allow two query-write-reply
    # cycles. Pin equally before either arm runs; no result-driven adjustment.
    budget = Budget(max_customer_turns=2,max_customer_llm_calls=3,max_service_llm_calls=12,max_service_tool_calls=16)
    old_world = historical_world()
    profiles,scenes = [],[]
    for index in range(20):
        title,world,actor = make_world(index)
        if semantic_state(world) == semantic_state(old_world):
            raise ValueError('a test world repeats the C1 source business state')
        profile = UsamiProfile(config_id='scene-%02d'%(index+1),domain='cloudops',seed=world.seed,identity=actor,
                               mode='sandbox',split='heldout',frozen_world=world.model_dump(mode='json'))
        profiles.append(profile)
        scenes.append(dict(id=profile.config_id,title=title,seed=world.seed,identity=actor,
                           initial_state_hash=world.state_hash,business_state_hash=semantic_state(world),
                           profile=profile.model_dump(mode='json'),design=dict(zip(
                               ('title','status','billing','quota','running','topology','actor','explicit_role','sizing'),SCENARIOS[index]))))
    if len({s['business_state_hash'] for s in scenes}) != 20:
        raise ValueError('cosmetic variants are not distinct scenarios')
    adapter = UsamiAdapter(root/'native',profiles)
    jobs=[]
    for profile in profiles:
        config = adapter.config_for(profile.config_id,customer_model,service_model,budget)
        for arm in ('C0','C1'):
            jobs.append(dict(episode_id=run_id+'.'+profile.config_id+'.'+arm,scene_id=profile.config_id,arm=arm,
                             config=config.model_dump(mode='json')))
            context = adapter.initial_observation(config)
            from vast_coevo.skills.retriever import SkillContext,SkillRetriever
            from vast_coevo.skills.renderer import render_skills
            hits = SkillRetriever('customer').retrieve(libraries[arm],SkillContext(domain='cloudops',public_text=context.public_text,
                                                                                  available_tools=config.tools))
            if not hits.skills or len(render_skills(hits.skills))>6000:
                raise ValueError('registered Customer skill cannot be injected')
    pins = source_hashes()
    root.mkdir(parents=True)
    for name,hash_value in pins.items():
        path=REPO/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=hash_value:
            raise ValueError('source changed during registration')
        target=root/'source-snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    shutil.copyfile(Path(__file__),root/'experiment-script.py')
    for label,library in libraries.items():
        atomic_json(root/'libraries'/(label+'.json'),library.model_dump(mode='json'),immutable=True)
    atomic_json(root/'candidate-patch.json',patch.model_dump(mode='json'),immutable=True)
    for scene in scenes:
        atomic_json(root/'worlds'/(scene['id']+'.json'),scene['profile']['frozen_world'],immutable=True)
    manifest=dict(schema_version=1,run_id=run_id,track='open_customer_discovery',scenes=scenes,jobs=jobs,max_workers=2,
                  source_hashes=pins,experiment_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
                  source_changes_pending=bool(subprocess.check_output(['git','diff','--name-only'],cwd=REPO,text=True).strip()),
                  training_world_hash=old_world.state_hash,training_business_state_hash=semantic_state(old_world),
                  snapshots={label:value.snapshot_hash for label,value in libraries.items()},
                  customer_model=customer_model.model_dump(mode='json'),service_model=service_model.model_dump(mode='json'),
                  model_random_seed=None,model_seed_note='No provider seed requested; temperature=0 is not a guarantee of bitwise deterministic generation.',
                  budget=budget.model_dump(mode='json'),budget_reason='Retain two Customer turns; source run exhausted six Service calls. Uniform 12-call/16-tool cap frozen before all trials.',
                  mode_reason='Preserve existing CloudOps sandbox semantics; actual transitions independently checked against unchanged reference rules by Oracle.',
                  candidate_selected=False,reflection_calls=0,automatic_retries=0,
                  metrics_protocol=dict(primary='successful_business_violation only; type=(operation, reference_codes); fingerprints reported separately',
                    effective_test='One send_message turn with no duplicate/unverified intentions and at least one authorized, reference-allowed non-context operation. Conservative evaluable lawful-request lower bound; not semantic test quality.',
                    coverage='Observed project status/billing/role and actual operation families; write-tested prerequisites separately. No keyword claims or inferred bugs.',
                    paired='C1-C0; ties on primary violations/types remain ties even when auxiliary metrics differ.',
                    uncertainty='Paired bootstrap mean difference, 10000 resamples seed 20261014; all-zero detection proportion exact one-sided 95% upper bound.',
                    smoke='First registered pair counts in 40. Require exact Replay, correct skill injection, invariant-valid trace, at least one Customer turn with a Service reply and no provider/protocol error. Budget termination is reported, never retried.'))
    atomic_json(root/'manifest.json',manifest,immutable=True)
    print(json.dumps(dict(preregistered_scenes=20,episodes=40,max_workers=2,root=str(root)),ensure_ascii=False),flush=True)


def load(root):
    manifest=json.loads((root/'manifest.json').read_text())
    if source_hashes()!=manifest['source_hashes']:
        raise ValueError('runtime source differs from preregistered pins')
    libraries={label:LibrarySnapshot.model_validate_json((root/'libraries'/(label+'.json')).read_text()) for label in ('C0','C1','S0')}
    if {k:v.snapshot_hash for k,v in libraries.items()}!=manifest['snapshots']:
        raise ValueError('frozen library changed')
    profiles=[UsamiProfile.model_validate(scene['profile']) for scene in manifest['scenes']]
    for scene,profile in zip(manifest['scenes'],profiles):
        world=World.model_validate_json((root/'worlds'/(scene['id']+'.json')).read_text())
        if world!=initial_world(profile) or world.state_hash!=scene['initial_state_hash'] or semantic_state(world)!=scene['business_state_hash']:
            raise ValueError('preregistered world changed')
    return manifest,libraries,UsamiAdapter(root/'native',profiles)


def evidence_for(root,job):
    folder=root/'native/episodes'/digest({'episode_id':job['episode_id']})[:32]
    return folder,folder/'evidence.json'


def artifact_trace(evidence):
    artifact=NativeArtifact.model_validate_json(Path(evidence.trace.path).read_text())
    from usami_cloudops.customer import Interaction
    return artifact,Interaction.model_validate_json(artifact.native_trace_json)


def check_episode(adapter,libraries,job,evidence):
    if evidence.config!=EpisodeConfig.model_validate(job['config']):
        raise ValueError('paired config changed')
    if not evidence.replay.verified:
        raise ValueError('native Replay failed: '+evidence.replay.reason)
    replay=adapter.replay(evidence,libraries[job['arm']],libraries['S0'])
    if not replay.verified:
        raise ValueError(replay.reason)
    artifact,trace=artifact_trace(evidence)
    if not trace.service_execution.oracle['trace_valid']:
        raise ValueError('Oracle trace integrity failed')
    for agent,label in (('customer',job['arm']),('service','S0')):
        expected=libraries[label].skills[0]
        injected=[i for i in evidence.injections if i.role==agent and i.hits]
        if agent=='customer' and not injected:
            raise ValueError('Customer skill not injected')
        if any(any(hit.id!=expected.id or hit.version!=expected.version or hit.content_hash!=expected.content_hash for hit in i.hits) for i in injected):
            raise ValueError('wrong Skill injected')
    return replay,trace


def run(root):
    manifest,libraries,adapter=load(root)
    if manifest['max_workers']!=2 or len(manifest['jobs'])!=40:
        raise ValueError('wrong preregistration scale')
    lock=threading.Lock();active=0;maximum=0;timeline=[]
    def worker(job):
        nonlocal active,maximum
        folder,path=evidence_for(root,job)
        if path.exists():
            row=EpisodeEvidence.model_validate_json(path.read_text())
            check_episode(adapter,libraries,job,row)
            return row
        if (folder/'online-start.json').exists() or (root/'outcomes'/(job['episode_id']+'.json')).exists():
            raise ValueError('an attempted Episode cannot be rerun or replaced: '+job['episode_id'])
        with lock:
            active+=1;maximum=max(maximum,active)
            if active>2:raise ValueError('concurrency exceeds two')
            timeline.append(dict(episode_id=job['episode_id'],event='start',active=active,at=datetime.now(timezone.utc).isoformat()))
            atomic_json(root/'concurrency.json',dict(max_workers=2,max_active=maximum,events=timeline))
        started=time.monotonic()
        try:
            row=adapter.run_episode(EpisodeConfig.model_validate(job['config']),libraries[job['arm']],libraries['S0'],job['episode_id'])
            replay,trace=check_episode(adapter,libraries,job,row)
            result=dict(episode_id=job['episode_id'],arm=job['arm'],scene_id=job['scene_id'],evidence_hash=row.evidence_hash,
                        status=trace.status,termination=row.termination,replay=replay.model_dump(mode='json'),elapsed_seconds=time.monotonic()-started)
            atomic_json(root/'outcomes'/(job['episode_id']+'.json'),result,immutable=True)
            print(json.dumps(result,ensure_ascii=False),flush=True)
            return row
        except Exception as exc:
            atomic_json(root/'outcomes'/(job['episode_id']+'.json'),dict(episode_id=job['episode_id'],error_type=type(exc).__name__,error=str(exc),elapsed_seconds=time.monotonic()-started),immutable=True)
            raise
        finally:
            with lock:
                active-=1;timeline.append(dict(episode_id=job['episode_id'],event='finish',active=active,at=datetime.now(timezone.utc).isoformat()))
                atomic_json(root/'concurrency.json',dict(max_workers=2,max_active=maximum,events=timeline))
    with (root/'run.lock').open('a') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # No extra model smoke request. The first frozen pair is the smoke.
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=list(pool.map(worker,manifest['jobs'][:2]))
            for job,row in zip(manifest['jobs'][:2],first):
                _,trace=check_episode(adapter,libraries,job,row)
                native_errors=any(c.error for c in trace.customer_records+trace.service_execution.llm_records)
                if not trace.turns or not any(t['response']['final_reply'] for t in trace.turns) or native_errors or any(c.error for c in row.model_calls):
                    atomic_json(root/'smoke.json',dict(passed=False,episode_id=job['episode_id'],reason='no completed exchange or transport/protocol error'),immutable=True)
                    raise ValueError('registered smoke pair did not pass; retain both attempts without retry')
            atomic_json(root/'smoke.json',dict(passed=True,episodes=[j['episode_id'] for j in manifest['jobs'][:2]],counts_toward_total=True),immutable=True)
            print('SMOKE PASSED: two registered Episodes; continuing the other 38.',flush=True)
            futures={pool.submit(worker,job):job for job in manifest['jobs'][2:]}
            errors=[]
            for future in as_completed(futures):
                try:future.result()
                except Exception as exc:errors.append(dict(episode_id=futures[future]['episode_id'],error=str(exc)))
            if errors:
                atomic_json(root/'run-errors.json',errors,immutable=True)
                raise ValueError('some Episodes failed; no retries: '+str(errors))


def replay_all(root):
    manifest,libraries,adapter=load(root)
    receipts=[]
    for job in manifest['jobs']:
        _,path=evidence_for(root,job)
        if not path.exists():continue
        row=EpisodeEvidence.model_validate_json(path.read_text())
        replay,_=check_episode(adapter,libraries,job,row)
        receipts.append(dict(episode_id=job['episode_id'],evidence_hash=row.evidence_hash,**replay.model_dump(mode='json')))
    result=dict(episodes_replayed=len(receipts),all_expected_present=len(receipts)==40,online_calls=0,receipts=receipts)
    atomic_json(root/'replay.json',result)
    print(json.dumps({key:value for key,value in result.items() if key!='receipts'}),flush=True)
    return result


def paired_interval(values):
    rng=random.Random(20261014)
    if not values:return None
    samples=sorted(sum(rng.choice(values) for _ in values)/len(values) for _ in range(10000))
    return dict(mean=sum(values)/len(values),bootstrap_95_percent_interval=[samples[249],samples[9749]],resamples=10000,seed=20261014)


def episode_metrics(job,evidence):
    artifact,trace=artifact_trace(evidence)
    execution=trace.service_execution
    engine_events={event.id:event for event in execution.world_trace.events if event.kind=='operation'}
    audit={r['event_id']:r for r in execution.oracle['operations']}
    # Relate each tool to its actual Service turn using original LLM messages.
    tool_turn={}
    for record in execution.llm_records:
        turn=sum(m.get('role')=='user' for m in record.request['messages'])
        if record.response:
            for choice in record.response.get('choices',[])[:1]:
                for call in choice.get('message',{}).get('tool_calls',[]) or []:
                    tool_turn[call['id']]=turn
    legal_turns=set();coverage=set();tested=set();query_failures=0;wrong_id=[];write_attempts=0
    operation_names=set();positive_writes=0
    for tool in execution.tool_records:
        event=engine_events.get(tool.event_id)
        if tool.name=='get_customer_context':continue
        operation_names.add(tool.name)
        if event is None:continue
        op=event.payload['operation'];project=event.before.projects.get(op['project_id']);check=audit.get(event.id)
        turn=tool_turn.get(tool.call_id,0)
        if check and check['authorized'] and check['reference_allowed'] is True:
            legal_turns.add(turn)
        if project:
            tags={'project.'+project.status,'billing.'+event.before.invoices[project.invoice_id].status,
                  'role.'+('owner_' if owner(event.before,evidence.config.identity,project.id) else 'member_')+(role(event.before,evidence.config.identity,project.id) or 'none')}
            coverage.update(tags)
            if not tool.name.startswith(('get_','list_')):tested.update(tags)
        if tool.name in ('get_invoice','pay_invoice','resume_project'):coverage.add('family.billing')
        if tool.name in ('get_project_members','grant_project_access','revoke_project_access'):coverage.add('family.permissions')
        if tool.name in ('get_project','change_project_quota','start_instance','create_instance'):coverage.add('family.quota')
        if tool.name in ('get_instance','list_instances','attach_dependency','detach_dependency','start_instance','stop_instance','delete_instance'):coverage.add('family.dependencies_resources')
        if tool.name.startswith(('get_','list_')) and not tool.response.get('success'):
            query_failures+=1
            if tool.response.get('error_code')=='RESOURCE_NOT_FOUND':
                wrong_id.append(dict(turn=turn,event_id=event.id,operation=op,attribution='unknown; not a confirmed business violation'))
        if not tool.name.startswith(('get_','list_')):
            write_attempts+=1
            positive_writes+=int(bool(check and check['authorized'] and check['reference_allowed'] is True))
    invalid_intents=sum(d['disposition']!='accepted' for t in trace.turns for d in t['intents'])
    effective=[]
    for n,turn in enumerate(trace.turns,1):
        if n in legal_turns and all(i['disposition']=='accepted' for i in turn['intents']):effective.append(n)
    cost={'customer_calls':evidence.consumption.customer_llm_calls,'service_calls':evidence.consumption.service_llm_calls,
          'tool_calls':evidence.consumption.tool_calls,'customer_prompt_tokens':0,'customer_completion_tokens':0,'service_prompt_tokens':0,'service_completion_tokens':0,'total_tokens':0,'missing_usage_calls':0}
    for call in evidence.model_calls:
        info=(call.response or {}).get('usage')
        if not info:cost['missing_usage_calls']+=1;continue
        for key in ('prompt_tokens','completion_tokens'):cost[call.role+'_'+key]+=info.get(key,0)
        cost['total_tokens']+=info.get('total_tokens',info.get('prompt_tokens',0)+info.get('completion_tokens',0))
    m=metrics((evidence,)).model_dump(mode='json')
    types=sorted({(f.operation,tuple(f.reference_codes)) for f in evidence.failures})
    return dict(episode_id=job['episode_id'],scene_id=job['scene_id'],arm=job['arm'],status=trace.status,termination=trace.termination_reason,
                replay_verified=evidence.replay.verified,completed_exchanges=len(trace.turns),
                business_violations=m['business_violations'],failure_types=[list(t) for t in types],fingerprints=m['fingerprints'],
                effective_tests=len(effective),effective_turn_ids=effective,coverage=sorted(coverage),write_tested_context=sorted(tested),
                operation_names=sorted(operation_names),legal_write_decisions=positive_writes,write_attempts=write_attempts,
                rejected_invalid_attempts=m['invalid_attempts'],authorization_anomalies=m['authorization_anomalies'],false_rejections=m['false_rejections'],
                customer_invalid_intents=invalid_intents,customer_output_errors=sum(bool(r.error) for r in trace.customer_records),
                model_errors=sum(bool(c.error) for c in trace.customer_records+execution.llm_records),tool_argument_errors=sum(t.response.get('error_code')=='TOOL_ARGUMENT_INVALID' for t in execution.tool_records),
                query_failures=query_failures,resource_not_found=wrong_id,cost=cost,
                actions=[a.model_dump(mode='json') for a in trace.actions],service_replies=[t['response']['final_reply'] for t in trace.turns],
                injections=[i.model_dump(mode='json') for i in evidence.injections if i.role=='customer'])


def report(root):
    manifest,libraries,adapter=load(root)
    rows=[]
    for job in manifest['jobs']:
        _,path=evidence_for(root,job)
        if path.exists():
            row=EpisodeEvidence.model_validate_json(path.read_text());check_episode(adapter,libraries,job,row)
            rows.append(episode_metrics(job,row))
    groups={}
    sums=('business_violations','effective_tests','rejected_invalid_attempts','authorization_anomalies','false_rejections',
          'customer_invalid_intents','customer_output_errors','model_errors','tool_argument_errors','query_failures','write_attempts','legal_write_decisions')
    for arm in ('C0','C1'):
        selected=[r for r in rows if r['arm']==arm]
        groups[arm]=dict(episodes_recorded=len(selected),episodes_with_no_model_error=sum(r['model_errors']==0 for r in selected),
            normal_budget_or_stop_termination=sum(r['status'] in ('completed','budget_exhausted') for r in selected),
            **{key:sum(r[key] for r in selected) for key in sums},
            distinct_failure_types=sorted({json.dumps(t) for r in selected for t in r['failure_types']}),
            distinct_failure_fingerprints=sorted({f for r in selected for f in r['fingerprints']}),
            coverage=sorted({c for r in selected for c in r['coverage']}),
            write_tested_context=sorted({c for r in selected for c in r['write_tested_context']}),
            operation_names=sorted({c for r in selected for c in r['operation_names']}),
            cost={k:sum(r['cost'][k] for r in selected) for k in (selected[0]['cost'] if selected else {})})
    pairs=[]
    for scene in manifest['scenes']:
        pair={r['arm']:r for r in rows if r['scene_id']==scene['id']}
        if len(pair)!=2:continue
        a,b=pair['C0'],pair['C1']
        delta={key:b[key]-a[key] for key in ('business_violations','effective_tests','rejected_invalid_attempts','query_failures')}
        priority=(delta['business_violations'],len(b['failure_types'])-len(a['failure_types']))
        pairs.append(dict(scene_id=scene['id'],title=scene['title'],primary_winner='C1' if priority>(0,0) else 'C0' if priority<(0,0) else 'tie',
                          differences=delta,C0_episode=a['episode_id'],C1_episode=b['episode_id']))
    result=dict(schema_version=1,c2c_status='EXECUTED' if len(rows)==40 and all(r['replay_verified'] for r in rows) else 'BLOCKED',
                expected_episodes=40,recorded_episodes=len(rows),reflection_calls=0,service_updates=0,candidate_selected=False,
                groups=groups,pairs=pairs,episode_results=rows,
                paired_uncertainty={key:paired_interval([p['differences'][key] for p in pairs]) for key in ('business_violations','effective_tests','rejected_invalid_attempts')},
                zero_detection_upper_95_per_arm=(1-math.pow(.05,1/20)) if all(g['business_violations']==0 and g['episodes_recorded']==20 for g in groups.values()) else None,
                inference_note='Small purposive sample, one stochastic draw per arm; auxiliary request/coverage proxies are not proof of generalization or Service decision correctness.')
    atomic_json(root/'results.json',result)
    lines=['# C0 → C1 Customer 配对实验', '', '**C2C：'+result['c2c_status']+'**。实际记录 '+str(len(rows))+'/40 Episodes；最大并发 2；Reflection 0；Service 更新 0；C1 未正式选中。','',
           '每组恢复同一初始世界、身份、模型、Service、规则和预算；只有 Customer Skill 版本不同。保留原 Sandbox 执行语义，违规只计独立 Oracle 确认的 successful_business_violation。','',
           '| 指标 | 旧 Customer C0 | 新 Customer C1 |','| --- | ---: | ---: |']
    labels=[('完成记录且回放的 Episodes','episodes_recorded'),('无模型错误 Episodes','episodes_with_no_model_error'),('正常停止或 Customer 预算终止','normal_budget_or_stop_termination'),('真实业务违规','business_violations'),('有效测试（合规可评估请求下界）','effective_tests'),('被 Engine 拒绝的非法尝试','rejected_invalid_attempts'),('授权异常（单列）','authorization_anomalies'),('Customer 无效意图','customer_invalid_intents'),('Customer 输出错误','customer_output_errors'),('工具参数错误','tool_argument_errors'),('工具查询失败','query_failures')]
    for label,key in labels:lines.append('| '+label+' | '+str(groups['C0'][key])+' | '+str(groups['C1'][key])+' |')
    lines.append('| 独立错误类型 | '+str(len(groups['C0']['distinct_failure_types']))+' | '+str(len(groups['C1']['distinct_failure_types']))+' |')
    for label,key in [('Customer 模型调用','customer_calls'),('Service 模型调用','service_calls'),('工具调用','tool_calls'),('总 Token','total_tokens')]:
        lines.append('| '+label+' | '+str(groups['C0']['cost'].get(key,0))+' | '+str(groups['C1']['cost'].get(key,0))+' |')
    lines+=['','有效测试是预先固定的保守自动指标：请求没有未验证/重复写意图，且 Service 实际执行了至少一条经 Oracle 判为有授权、Reference 允许的非 context 操作，每轮最多计一次。它不能证明探针质量，正确拒绝与负向探针另列，不计为漏洞。普通 RESOURCE_NOT_FOUND 的责任保持未知。','',
            '独立错误类型按 operation + reference_codes 去重；细粒度 failure fingerprint 另外保存。状态/权限覆盖是实际触达的上下文，写操作考察的上下文单独保存在 results.json，不把初始可见资源自动计为已测试。','',
            '| 场景 | 初始业务情况 | 主指标胜方 | C1−C0 违规 / 有效测试 / 非法尝试 |','| --- | --- | --- | --- |']
    for p in pairs:
        d=p['differences'];lines.append('| '+p['scene_id']+' | '+p['title']+' | '+p['primary_winner']+' | '+str(d['business_violations'])+' / '+str(d['effective_tests'])+' / '+str(d['rejected_invalid_attempts'])+' |')
    lines+=['','各场景 seed、身份、配额、账单、状态、依赖、初始 hash 和完整 World 见 manifest.json 与 worlds/；全部在运行前冻结，业务状态签名排除种子和名称后仍有 20 个不同值，均不等于 C1 的训练世界。','',
            '模型 temperature=0，未请求 provider 随机 seed；这不保证跨在线运行确定性。源码和真实响应支持精确离线回放。Token 来自实际 provider usage，不估算美元费用；缺失 usage 次数另外记录。','']
    if all(g['business_violations']==0 for g in groups.values()):
        lines+=['**双方均未发现经 Oracle 确认的成功业务违规，没有证明发现能力提升。** 请求下界、覆盖与成本仅作辅助比较。','']
    lines+=['配对不确定性（C1−C0）：','', '```json',json.dumps(result['paired_uncertainty'],ensure_ascii=False,indent=2),'```','',
            '20 个场景为有目的的小样本，每场景每组只有一次随机结果，bootstrap 区间不证明广义泛化。若每组 20 次均零发现，一侧 95% 检出率上限约 13.9%，不是证明不存在漏洞。','',
            '## 逐 Episode 原始 Customer 请求','']
    for row in rows:
        lines+=['### '+row['scene_id']+' '+row['arm']+'：'+row['termination'],'']
        for action in row['actions']:
            lines+=['```json',json.dumps(action,ensure_ascii=False,indent=2),'```','']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(c2c_status=result['c2c_status'],episodes=len(rows),groups=groups),ensure_ascii=False),flush=True)
    return result


def bundle(root, output):
    if output.exists():raise ValueError('bundle already exists')
    files=[path for path in root.rglob('*') if path.is_file() and path.name!='run.lock']
    manifest=dict(schema_version=1,kind='paired_customer_performance',original_root=str(root),
                  files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    atomic_json(root/'bundle-manifest.json',manifest,immutable=True)
    with tarfile.open(output,'w:gz') as archive:
        for path in sorted(files+[root/'bundle-manifest.json']):archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
    print(json.dumps(dict(bundle=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare');p.add_argument('--run-id',required=True)
    commands.add_parser('run');commands.add_parser('replay');commands.add_parser('report')
    p=commands.add_parser('bundle');p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve()
    if args.command=='prepare':prepare(root,args.run_id)
    elif args.command=='run':run(root)
    elif args.command=='replay':replay_all(root)
    elif args.command=='report':report(root)
    else:bundle(root,args.output.resolve())


if __name__=='__main__':main()
