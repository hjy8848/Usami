"""Append-only recovery: reuse completed calls, retain failed Episodes, never retry.

Only fully recorded Customer output failures become local Episode failures.
No native package, evidence, Reflection, Service gate or business rule is changed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import multigen_heldout as experiment
from episode_resilience import POLICY, ResilientController
from vast_coevo.schema import atomic_json, digest
from multigen_budget import CallLedger


def prepare(parent, root):
    if root.exists(): raise ValueError('never overwrite recovery registration')
    m = experiment.read(parent/'MANIFEST.json')
    registered = experiment.read(parent/'PROTOCOL_REGISTRATION.json')
    if digest({k:v for k,v in m.items() if k!='manifest_hash'}) != m['manifest_hash']:
        raise ValueError('parent manifest changed')
    if hashlib.sha256((parent/'EXPERIMENT_PROTOCOL.md').read_bytes()).hexdigest()!=registered['protocol_sha256']:
        raise ValueError('parent protocol changed')
    if experiment.source_hashes()!=m['source_hashes']:
        raise ValueError('native/core source changed; old evidence cannot be silently reinterpreted')
    audit=experiment.read(parent/'REPLAY_AUDIT.json')
    consistency=experiment.read(parent/'WIRE_EVIDENCE_CONSISTENCY.json')
    usage=experiment.read(parent/'wire-ledger/usage.json')
    if (audit['status']!='PASS' or not consistency['wire_native_reflection_match'] or usage['pending']
            or (parent/'HELDOUT_RESULTS.json').exists() or (parent/'HELDOUT_PROGRESS.json').exists()):
        raise ValueError('parent must have verified known outcomes and unopened heldout')
    for summary in (parent/'work').glob('*/summary.json'):
        runs=experiment.RunStore(summary.parent/'runs')
        if runs.pending(summary.parent.name): raise ValueError('unknown pending controller operation')
    root.mkdir(parents=True)
    for name in ('work','wire-ledger','libraries','worlds'):
        shutil.copytree(parent/name,root/name)
    # Only copied derived summaries are replaced. Original parent remains immutable.
    for ident in ('r0-A','r0-B'):
        (root/'work'/ident/'summary.json').unlink()
    for name in ('MANIFEST.json','STATUS.json','EXPERIMENT_PROTOCOL.md','REPLAY_AUDIT.json'):
        shutil.copyfile(parent/name,root/('PARENT_'+name))
    shutil.copyfile(parent/'SMOKE_SUMMARY.json',root/'SMOKE_SUMMARY.json')
    shutil.copyfile(parent/'raw-evidence.tar.gz',root/'PARENT_EVIDENCE.tar.gz')
    m.update(run_id=root.name,protocol='vast-multigen-heldout-recovery-v3',episode_error_policy=POLICY,
             code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=experiment.REPO,text=True).strip())
    m['recovery']=dict(parent_root=str(parent),parent_manifest_hash=experiment.read(parent/'MANIFEST.json')['manifest_hash'],
        parent_bundle_sha256=hashlib.sha256((root/'PARENT_EVIDENCE.tar.gz').read_bytes()).hexdigest(),
        inherited_calls=sum(v['calls'] for v in usage['buckets'].values()),
        inherited_tokens=sum(v['tokens'] for v in usage['buckets'].values()),
        changes=['known replayable Customer output failure ends only its Episode',
                 'no duplicate calls; inherited failed Episode remains failed',
                 'resume both original journals; completed A is cache only',
                 'heldout bucket ceiling 4M within unchanged global 10M; heldout remains unseen'],
        excluded=['business changes','Service gate changes','output repair','automatic retry','new Smoke'],
        native_paths='inherited content-addressed artifacts retain original parent paths; parent bundle is preserved')
    m['failure_policy']='recorded replayable CUSTOMER_OUTPUT_INVALID is local; unknown outcomes, Service errors, replay/integrity failures and caps still halt; no retries'
    m['budget']['buckets']['heldout']['tokens']=4_000_000
    drivers=set(m['driver_hashes'])|{str(Path(__file__).resolve().relative_to(experiment.REPO)),
                                  str(Path(__file__).resolve().with_name('episode_resilience.py').relative_to(experiment.REPO))}
    m['driver_hashes']={name:hashlib.sha256((experiment.REPO/name).read_bytes()).hexdigest() for name in sorted(drivers)}
    m.pop('manifest_hash');m['manifest_hash']=digest(m)
    atomic_json(root/'MANIFEST.json',m,immutable=True)
    protocol=f'''# 故障隔离修复后的续跑协议\n\nManifest: {m['manifest_hash']}\n\n父实验 {parent} 全部记录保留，原 Manifest 不变。此次由用户“修复吧”授权，续用相同模型、Prompt、2 代、1 次重复、12 个陌生世界 / 72 场 Held-out，并发上限 4。\n\n只将已收到完整回复、真实 Replay 通过的 CUSTOMER_OUTPUT_INVALID 视为 Episode 局部失败。保留原回复、消耗、失败标签及统计分母；不修补输出、不重试该 Episode。其余安全、证据、预算、未知调用与 Service 错误仍按原逻辑阻断。Service Reflection、Static/Dynamic Gate 不变。\n\nA 两代全部复用；B 已完成操作复用，从未执行步骤继续。跳过已完成 Smoke。继承 388 次 / 2448150 Token；本轮累计硬上限仍为 1000 万，历史更早 961580 Token 另计。Held-out 桶从 300 万增至 400 万以预留上下文波动，仍受同一个 1000 万总上限约束；训练两臂上限不变。不能称为原 v2 协议无故障完成。\n\n测试题、证书、业务世界、身份、工具、评分与 Bootstrap 定义不变；单次独立训练重复只支持探索性结论。先完成训练、冻结最终服务，再解封 Held-out。\n'''
    (root/'EXPERIMENT_PROTOCOL.md').write_text(protocol)
    atomic_json(root/'PROTOCOL_REGISTRATION.json',dict(manifest_hash=m['manifest_hash'],protocol_sha256=hashlib.sha256(protocol.encode()).hexdigest()),immutable=True)
    for name in set(m['source_hashes'])|set(m['driver_hashes']):
        target=root/'source-snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(experiment.REPO/name,target)
    (root/'.gitignore').write_text('work/\nevaluation/\nwire-ledger/\nsource-snapshot/\n.execute.lock\n')
    print(json.dumps({'registered':str(root),'manifest_hash':m['manifest_hash'],'inherited_calls':388}),flush=True)


def execute(root):
    import os
    os.environ.setdefault('USAMI_LLM_KEYCHAIN_SERVICE','litellm')
    os.environ.setdefault('USAMI_LLM_KEYCHAIN_ACCOUNT','litellm-api-key')
    m=experiment.pinned(root)
    if m.get('episode_error_policy')!=POLICY: raise ValueError('explicit recovery policy required')
    ledger=CallLedger(root/'wire-ledger',m['budget'])
    if ledger.state['pending']: raise ValueError('unknown external calls, refusing retry')
    with (root/'.execute.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        atomic_json(root/'EXECUTION_STARTED.json',{'manifest_hash':m['manifest_hash'],'mode':'recovery'},immutable=True)
        try:
            with ThreadPoolExecutor(max_workers=m['max_workers']) as pool:
                runs=list(pool.map(lambda arm:experiment.one_run(root,m,ledger,'r0-'+arm,arm,m['training_profiles'][0],m['generations'],'r0-'+arm),('A','B')))
            atomic_json(root/'EVOLUTION_SUMMARY.json',dict(runs=runs,ledger=ledger.state),immutable=True)
            if any(r['report']['status']!='completed' for r in runs): raise ValueError('training incomplete; heldout remains sealed')
            experiment.finish_evaluation(root,m,ledger,runs)
        except BaseException as exc:
            atomic_json(root/'STATUS.json',{'status':'BLOCKED','error':type(exc).__name__+': '+str(exc),'ledger':ledger.state},immutable=True)
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute'))
    parser.add_argument('--parent',type=Path)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare': prepare(args.parent.resolve(),args.root.resolve())
    else: execute(args.root.resolve())
