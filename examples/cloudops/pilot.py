"""Preregister actual Service/Customer model profiles, then collect immutable runs."""
import argparse
from pathlib import Path
from usami.interaction.__main__ import provider_environment
from usami.service.client import OpenAICompatibleClient,settings_from_env
from usami_cloudops.benchmark import load,validate,write_json
from usami_cloudops.suite import run_suite


def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=Path('benchmarks/cloudops-v0.1'));p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();service=settings_from_env(provider_environment('service'));customer=settings_from_env(provider_environment('customer'))
    normal=load(args.release/'service-validation.json');normal.instances=[i for i in normal.instances if i.task.family in {'billing_recovery','capacity_expand','viewer_refusal'}]
    normal.suite_id='cloudops-v0.1-service-pilot';normal.service_model=service;normal.seal();validate(normal)
    discovery=load(args.release/'discovery-demo.json');discovery.instances=discovery.instances[:1];discovery.suite_id='cloudops-v0.1-discovery-pilot'
    discovery.service_model=service;discovery.customer_model=customer;discovery.seal();validate(discovery)
    # Both profiles materialized BEFORE any provider call. No task-family constraint in Discovery.
    for name,m in (('service-profile.json',normal),('discovery-profile.json',discovery)):
        file=args.out/name
        if file.exists():
            if load(file)!=m:raise ValueError('prior pilot differs; no automatic retries')
        else:write_json(file,m)
    def clients(m,i):
        s=OpenAICompatibleClient.from_env(provider_environment('service'))
        try:return s,OpenAICompatibleClient.from_env(provider_environment('customer')) if m.track=='customer_discovery' else None
        except Exception:s.close();raise
    service_report=run_suite(normal,args.out/'service',clients)
    discovery_report=run_suite(discovery,args.out/'discovery',clients)
    write_json(args.out/'pilot-report.json',{'kind':'ACTUAL LIVE LLM PILOT','service_model':service.model_dump(mode='json'),'customer_model':customer.model_dump(mode='json'),
        'service_report':service_report,'discovery_report':discovery_report,'official_full_release_score':False,
        'interpretation':'Three selected Service cases and one completely open Discovery world x three preregistered trials. Customer receives no fixed task, attack script, family or witness. Sandbox evidence is simulated CloudOps policy evidence, not an external cloud vulnerability.'})
    print('Recorded and replayed complete pilot. No retries or model-result replacements.',flush=True)


if __name__=='__main__':main()
