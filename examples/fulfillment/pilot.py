"""Six actual Service families and open Discovery x three preregistered trials."""
import argparse
from pathlib import Path
from usami_harness.provider import model_settings,client
from usami_fulfillment.benchmark import load,write_json,validate
from usami_fulfillment.suite import run_suite

RECIPES=('paid_fulfillment','regional_transfer','packed_cancellation','return_restock',
         'draft_amendment','stock_refusal')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,default=Path('benchmarks/fulfillment-v0.1'))
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    service,customer=model_settings('service'),model_settings('customer')
    normal=load(args.release/'service-train.json')
    chosen=[]
    for recipe in RECIPES:
        options=[i for i in normal.instances if i.generation_recipe==recipe]
        if not options:raise ValueError('missing exact base pilot recipe '+recipe)
        chosen.append(sorted(options,key=lambda i:i.generation_recipe)[0])
    normal.instances=chosen;normal.suite_id='fulfillment-v0.1-service-pilot';normal.service_model=service;normal.seal()
    discovery=load(args.release/'discovery-demo.json');discovery.suite_id='fulfillment-v0.1-open-discovery-pilot'
    discovery.service_model=service;discovery.customer_model=customer;discovery.seal()
    # Every instance/trial/settings is fixed on disk before the first live call.
    for name,manifest in [('service-profile.json',normal),('discovery-profile.json',discovery)]:
        validate(manifest)
        path=args.out/name
        if path.exists():
            if load(path)!=manifest:raise ValueError('prior profile differs; register a new attempt directory')
        else:write_json(path,manifest)
    def clients(manifest,instance):
        service=client('service')
        try:return service,client('customer') if manifest.track=='customer_discovery' else None
        except BaseException:service.close();raise
    normal_report=run_suite(normal,args.out/'service',clients)
    discovery_report=run_suite(discovery,args.out/'discovery',clients)
    write_json(args.out/'pilot-report.json',{'kind':'ACTUAL LIVE LLM PILOT','service_model':service.model_dump(mode='json'),
        'customer_model':customer.model_dump(mode='json'),'service_report':normal_report,'discovery_report':discovery_report,
        'official_full_release_score':False,'interpretation':'Six selected Service families; one unconditioned Discovery world x three preregistered trials. No fixed Customer goal, family, script or witness. Every failure and real call budget is retained.'})


if __name__=='__main__':main()
