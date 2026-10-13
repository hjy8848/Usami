"""Full independent generation/certificate audit, never LLM performance evidence."""
import argparse
import hashlib
import json
from usami_harness.models import digest
from pathlib import Path
from usami_stayops import adapter
from usami_stayops.benchmark import load,write_json
from usami_stayops.goals import make_task,progress_task
from usami_harness.goals import execute
from usami_harness.models import Request
from usami_stayops.engine import Engine,replay_trace
from usami_stayops.oracle import evaluate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,default=Path('benchmarks/stayops-v0.1'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--compare',type=Path);args=parser.parse_args()
    records=[];bases={};worlds=0;witnesses=0;refusals=0;legal=None
    for split in ['train','validation','test-demo']:
        manifest=load(args.release/f'service-{split}.json',verify_generation=False)
        for instance in manifest.instances:
            recipe=instance.generation_recipe
            base=recipe.rsplit('@',2)[0] if '@' in recipe else recipe
            key=(instance.world['seed'],base)
            if key not in bases:bases[key]=make_task(*key)
            initial,task=bases[key]
            if '@' in recipe:
                _,route,phase=recipe.rsplit('@',2)
                initial,task=progress_task(initial,task,int(route),int(phase))
            if initial.model_dump(mode='json')!=instance.world or task!=instance.task:
                raise ValueError('frozen recipe/certificate mismatch '+instance.id)
            worlds+=1
            for witness in task.witnesses:
                trace=execute(adapter,initial,task.identity,witness.operations)
                if trace.trace_hash!=witness.trace_hash:raise ValueError('exact proof trace differs')
                witnesses+=1
                if recipe=='complete_stay' and legal is None:legal=trace
            refusals+=task.kind=='policy_refusal'
            records.append({'instance':instance.id,'recipe':recipe,'witnesses':len(task.witnesses),
                            'oracle_replay_verified':True,'refusal_verified':task.kind=='policy_refusal'})
        print(f'{split}: exact recipes, Reference/Engine/Oracle/replay verified',flush=True)
    discovery=load(args.release/'discovery-demo.json')
    world,_=make_task(42,'deposit_refusal');engine=Engine(world)
    operation=adapter.Operation(name='confirm_reservation',scope_id='p0',resource_id='b0')
    request=Request(id='sandbox',identity='u0',operation=operation.model_dump(mode='json'))
    engine.register(request);engine.execute('u0',operation,request.id,'sandbox')
    trace=engine.finish();oracle=evaluate(trace,engine.requests);replay_trace(trace,engine.requests)
    if oracle['operations'][0]['classification']!='successful_business_violation':raise ValueError('sandbox evidence missing')
    write_json(args.out/'legal-complete-stay.trace.json',legal)
    write_json(args.out/'sandbox-unpaid-reservation-confirm.trace.json',trace);write_json(args.out/'sandbox-oracle.json',oracle)
    comparison=None
    if args.compare:
        filenames=['service-train.json','service-validation.json','service-test-demo.json','discovery-demo.json',
                   'coverage.json','review-examples.json','TASK_EXAMPLES.md']
        comparison={name:json.loads((args.release/name).read_text())==json.loads((args.compare/name).read_text()) for name in filenames if name.endswith('.json')}
        if not all(comparison.values()):raise ValueError('independent canonical frozen data differs')
        comparison['markdown_byte_equal_informational']=((args.release/'TASK_EXAMPLES.md').read_bytes()==(args.compare/'TASK_EXAMPLES.md').read_bytes())
    report={'kind':'OFFLINE SOFTWARE VERIFICATION, NOT REAL LLM PERFORMANCE',
        'instances_verified':worlds,'witnesses_verified':witnesses,'certified_refusals_verified':refusals,
        'discovery_unconditioned_worlds':len(discovery.instances),'independent_rebuild_exact':comparison,
        'records':records,'sandbox_oracle':oracle}
    write_json(args.out/'verification.json',report)
    print({'instances':worlds,'witnesses':witnesses,'refusals':refusals,'independent_rebuild':comparison},flush=True)


if __name__=='__main__':main()
