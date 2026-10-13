"""Full frozen-suite verification and explicit offline baseline execution."""
import argparse
from pathlib import Path
from usami.benchmark.manifest import load_manifest
from usami.benchmark.baselines import BaselineClient, reply
from usami.benchmark.runtime import run_instance
from usami.benchmark.scoring import score_run, summarize
from usami.benchmark.suite import run_suite
from usami.benchmark.release_v2 import write_json
from usami.benchmark.goals_v2 import execute_plan


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release',type=Path,default=Path('benchmarks/v0.2.0'))
    parser.add_argument('--out',type=Path,default=Path('outputs/v2-verification'))
    args=parser.parse_args()
    reports={}; routes=0
    for split in ('train','validation','test-demo'):
        manifest=load_manifest(args.release/f'service-{split}.json')
        from usami import generate_world
        for instance in manifest.instances:
            world=generate_world(instance.seed,instance.generator)
            for witness in instance.task.witnesses:
                trace=execute_plan(world,instance.customer_identity,witness.operations)
                assert instance.task.goal.satisfied(trace.final_state,trace)
                assert instance.task.goal.frame_preserved(world,trace.final_state)
                routes+=1
        for mode in ('reference-proof','one-step'):
            report=run_suite(manifest,args.out/f'{split}-{mode}',lambda m,i:(BaselineClient(m,i,mode),None))
            assert report['complete']
            if mode=='reference-proof':assert report['overall_task_success_rate']==1
            # Persist full evidence locally; compact metrics are the public artifact.
            reports[f'{split}/{mode}']={k:v for k,v in report.items() if k not in {'rows','missing'}}
        print(f'{split}: verified',flush=True)
    discovery=load_manifest(args.release/'discovery-demo.json');runs=[]
    class StopCustomer:
        settings=discovery.customer_model
        def complete(self,request):return reply('{"type":"stop","reason":"Offline protocol smoke check only"}')
    class UncalledService:
        settings=discovery.service_model
        def complete(self,request):raise AssertionError('Stop baseline does not contact Service')
    for instance in discovery.instances:
        for trial in discovery.trials:
            evidence=run_instance(discovery,instance.instance_id,UncalledService(),StopCustomer(),trial)
            evidence.save(args.out/f'discovery/{instance.instance_id}.{trial}.run.json');runs.append(evidence)
    discovery_report=summarize(discovery,runs)
    assert discovery_report['complete'] and discovery_report['observed_unique_business_findings']==0
    result={'kind':'SOFTWARE CORRECTNESS / PRIVILEGED OFFLINE BASELINES; NOT LLM PERFORMANCE',
            'all_witness_routes_verified':routes,'service_reports':reports,
            'discovery_protocol_replays':len(runs),'discovery_baseline':'Stop-only, protocol check; no discovery competence claim',
            'manifest_hashes':{m.suite_id:m.manifest_hash for m in [discovery]},'real_llm':'See pilot-report.json separately'}
    write_json(args.out/'verification.json',result)
    print({'routes':routes,'discovery_protocol_replays':len(runs)},flush=True)


if __name__=='__main__':main()
