"""Actual autonomous Customer baseline: first world × all preregistered trials."""
import argparse
from pathlib import Path
from usami.benchmark.manifest import load_manifest
from usami.benchmark.suite import run_suite
from usami.benchmark.release_v2 import write_json
from usami.interaction.__main__ import provider_environment
from usami.service.client import OpenAICompatibleClient,settings_from_env


def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=Path('benchmarks/v0.2.0'));p.add_argument('--out',type=Path,default=Path('outputs/discovery-pilot'));a=p.parse_args()
    m=load_manifest(a.release/'discovery-demo.json');m.suite_id='usami-v0.2-discovery-pilot';m.instances=m.instances[:1]
    m.service_model=settings_from_env(provider_environment('service'));m.customer_model=settings_from_env(provider_environment('customer'))
    m.sampling={'design':'First frozen owner/capacity world, all three preregistered trials; no attack script.'};m.seal()
    profile=a.out/'discovery-profile.json'
    if profile.exists():
        if load_manifest(profile)!=m:raise ValueError('Existing profile differs')
    else:m.save(profile)
    def clients(m,i):
        s=OpenAICompatibleClient.from_env(provider_environment('service'))
        try:return s,OpenAICompatibleClient.from_env(provider_environment('customer'))
        except Exception:s.close();raise
    report=run_suite(m,a.out/'discovery',clients,progress=lambda i,t,r:print(f'Discovery {t}: {r.interaction.status}',flush=True))
    write_json(a.out/'pilot-report.json',{'kind':'ACTUAL AUTONOMOUS CUSTOMER / SERVICE LLM PILOT','customer_model':m.customer_model.model_dump(mode='json'),'service_model':m.service_model.model_dump(mode='json'),'discovery_profile_hash':m.manifest_hash,'discovery_report':report,'official_full_release_score':None})


if __name__=='__main__':main()
