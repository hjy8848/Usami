"""All witnesses and complete privileged offline baselines; no LLM capability claim."""
import argparse
import hashlib
from pathlib import Path
from usami_cloudops.benchmark import load,write_json,score,run_instance,summarize
from usami_cloudops.baselines import ProofClient,OneStepClient,StopCustomer
from usami_cloudops.goals import execute
from usami_cloudops.engine import Engine,replay_trace
from usami_cloudops.models import Operation,Request
from usami_cloudops.oracle import evaluate
from usami_cloudops.suite import run_suite


def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=Path('benchmarks/cloudops-v0.1'));p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    reports={};witnesses=0;legal=None
    for split in ('train','validation','test-demo'):
        m=load(args.release/f'service-{split}.json')
        for i in m.instances:
            for witness in i.task.witnesses:
                trace=execute(i.world,i.identity,witness.operations);witnesses+=1
                if i.task.family=='billing_recovery' and legal is None:legal=trace
        for name,cls in (('reference-proof',ProofClient),('one-step',OneStepClient)):
            def clients(manifest,instance):return (cls(manifest.service_model,instance.task) if cls is ProofClient else cls(manifest.service_model,instance.world,instance.task)),None
            reports[split+'/'+name]=run_suite(m,args.out/(split+'-'+name),clients)
    d=load(args.release/'discovery-demo.json');runs=[run_instance(d,i,ProofClient(d.service_model,None),StopCustomer(d.customer_model),trial) for i in d.instances for trial in d.trials]
    protocol=summarize(d,runs)
    world=d.instances[0].world;e=Engine(world);operation=Operation(name='start_instance',project_id='p0',resource_id='p0_web')
    req=Request(id='sandbox_example',identity='u0',operation=operation);e.register(req);e.execute('u0',operation,req.id,'sandbox');trace=e.finish();oracle=evaluate(trace,e.requests);replay_trace(trace,e.requests)
    write_json(args.out/'legal-billing-recovery.trace.json',legal);write_json(args.out/'sandbox-dependency.trace.json',trace);write_json(args.out/'sandbox-oracle.json',oracle)
    write_json(args.out/'verification.json',{'kind':'OFFLINE SOFTWARE VERIFICATION, NOT REAL LLM PERFORMANCE','all_witnesses_verified':witnesses,'service_baselines':reports,
        'discovery_stop_protocol_replays':protocol,'sandbox_example_oracle':oracle,'saas_v0_2':'Core SaaS sources and frozen files byte-unchanged; full test results documented separately.'})


if __name__=='__main__':main()
