"""Preregister one Service case per workflow and an autonomous Discovery pilot.

Actual clients only. Model settings and credentials come from existing role env /
macOS Keychain configuration. Full recordings are written locally and replayed.
"""
import argparse
from pathlib import Path
from usami.benchmark.manifest import load_manifest
from usami.benchmark.suite import run_suite
from usami.benchmark.release_v2 import write_json
from usami.interaction.__main__ import provider_environment
from usami.service.client import OpenAICompatibleClient, settings_from_env
from usami.benchmark.runtime import run_instance
from usami.benchmark.scoring import score_run, summarize


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',type=Path,default=Path('benchmarks/v0.2.0'))
    parser.add_argument('--out',type=Path,default=Path('outputs/v2-pilot'))
    parser.add_argument('--service-only',action='store_true')
    parser.add_argument('--families',help='Comma-separated preregistered workflow subset; default one per all workflows')
    args=parser.parse_args()
    service_settings=settings_from_env(provider_environment('service'))
    manifests=[load_manifest(args.release/f'service-{split}.json') for split in ('validation','test-demo')]
    pilot=manifests[0].model_copy(deep=True)
    pilot.suite_id='usami-v0.2-stratified-service-pilot'; selected=[];pilot.sampling={'design':'One first frozen instance per workflow, selected before model calls; not a full-suite score.'}
    for manifest in manifests:
        seen=set()
        for instance in manifest.instances:
            if instance.task.family not in seen: selected.append(instance);seen.add(instance.task.family)
    if args.families:
        families=args.families.split(',')
        if len(families)!=len(set(families)) or set(families)-{i.task.family for i in selected}:raise ValueError('unknown or duplicate pilot family')
        selected=[i for i in selected if i.task.family in families]
        pilot.sampling['preregistered_families']=families
    pilot.instances=selected
    pilot.service_model=service_settings;pilot.seal()
    profile=args.out/'service-profile.json'
    if profile.exists():
        if load_manifest(profile)!=pilot:raise ValueError('Existing pilot profile differs; choose a fresh directory')
    else:pilot.save(profile)
    def clients(m,i):return OpenAICompatibleClient.from_env(provider_environment('service')),None
    report=run_suite(pilot,args.out/'service',clients,progress=lambda i,t,r:print(f"Service {i.task.family}: {r.service_execution.status}",flush=True))
    examples=[]
    for row in report['rows']:
        from usami.benchmark.runtime import BenchmarkRun
        run=BenchmarkRun.load(args.out/'service'/f"{row['instance_id']}.{row['trial_id']}.run.json")
        instance=next(i for i in pilot.instances if i.instance_id==row['instance_id'])
        examples.append({'family':instance.task.family,'task_id':instance.instance_id,'request':instance.task.message,'success':row['task_success'],'score':row,'final_reply':run.service_execution.final_reply,
            'tool_results':[{'name':r.name,'response':r.response} for r in run.service_execution.tool_records],
            'oracle_codes':sorted({v.code for req in run.service_execution.oracle.requests for v in req.violations})})
    result={'kind':'ACTUAL SERVICE LLM / AUTONOMOUS CUSTOMER LLM PILOT',
        'service_model':service_settings.model_dump(mode='json'),'service_profile_hash':pilot.manifest_hash,
        'service_report':report,'representative_cases':examples,'official_full_release_score':None,
        'interpretation':'Complete coverage of this preregistered stratified pilot only; no full-suite or benchmark-equivalence claim.'}
    if not args.service_only:
        discovery=load_manifest(args.release/'discovery-demo.json')
        discovery.suite_id='usami-v0.2-discovery-pilot';discovery.instances=discovery.instances[:1]
        discovery.service_model=service_settings;discovery.customer_model=settings_from_env(provider_environment('customer'))
        discovery.sampling={'design':'First frozen owner/capacity world, all three preregistered trials; no attack script.'};discovery.seal()
        profile=args.out/'discovery-profile.json'
        if profile.exists():
            if load_manifest(profile)!=discovery:raise ValueError('Existing Discovery profile differs; choose a fresh directory')
        else:discovery.save(profile)
        def discovery_clients(m,i):
            service=OpenAICompatibleClient.from_env(provider_environment('service'))
            try:return service,OpenAICompatibleClient.from_env(provider_environment('customer'))
            except Exception:service.close();raise
        result['discovery_report']=run_suite(discovery,args.out/'discovery',discovery_clients,progress=lambda i,t,r:print(f"Discovery {t}: {r.interaction.status}",flush=True))
        result['customer_model']=discovery.customer_model.model_dump(mode='json')
        result['discovery_profile_hash']=discovery.manifest_hash
    else:result['discovery_status']='NOT RUN (--service-only)'
    write_json(args.out/'pilot-report.json',result)


if __name__=='__main__':main()
