"""Re-evaluate actual LLM journals after a scoring-only release correction.

Never bypass source-pin validation: verify the original source snapshot, allow
only scoring_v2.py to differ, and regenerate every recorded LLM request, tool,
World/Oracle event and final execution. No new provider calls are claimed.
"""
import argparse
import hashlib
from pathlib import Path
from usami.benchmark.manifest import BenchmarkManifest, runtime_hashes
from usami.benchmark.runtime import BenchmarkRun, run_instance
from usami.benchmark.scoring import summarize
from usami.benchmark.release_v2 import write_json
from usami.service.client import RecordedCompletionClient


def main():
    p=argparse.ArgumentParser();p.add_argument('--service',type=Path,required=True);p.add_argument('--discovery',type=Path,required=True);p.add_argument('--original-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result={'kind':'ACTUAL LLM OBSERVATIONS, EXACT JOURNAL REPLAY AFTER SCORING-ONLY CORRECTION',
            'new_provider_calls_during_re_evaluation':0,'official_full_release_score':None,
            'correction':'JSON format separated from business policy handling; protected state and external certificate/public code remain required.',
            'interpretation':'Six stratified Service cases and one Discovery world × three preregistered trials; not a full release model score.', 'source_migration':{}}
    for track,root,profile_name,evidence_dir in (('service',a.service,'service-profile.json','service'),('discovery',a.discovery,'discovery-profile.json','discovery')):
        original=BenchmarkManifest.model_validate_json((root/profile_name).read_text())
        snapshot={name:hashlib.sha256((a.original_source/name).read_bytes()).hexdigest() for name in original.source_hashes}
        if snapshot!=original.source_hashes or original.manifest_hash!=original.computed_hash() or original.dataset_hash!=original.computed_dataset_hash():raise ValueError('original source/profile integrity mismatch')
        current=runtime_hashes()
        changed=sorted(name for name in set(snapshot)|set(current) if snapshot.get(name)!=current.get(name))
        if changed!=['usami/benchmark/scoring_v2.py']:raise ValueError('only the scoring module may change for compatible journal re-evaluation')
        updated=original.model_copy(deep=True);updated.source_hashes=current;updated.seal();updated.save(a.out/profile_name)
        original_runs=[BenchmarkRun.load(path) for path in sorted((root/evidence_dir).glob('*.run.json'))]
        regenerated=[]
        for old in original_runs:
            if old.run_hash!=old.computed_hash() or old.manifest_hash!=original.manifest_hash or old.dataset_hash!=original.dataset_hash:raise ValueError('original run integrity/profile mismatch')
            execution=old.service_execution or old.interaction.service_execution
            service=RecordedCompletionClient(updated.service_model,execution.llm_records)
            customer=RecordedCompletionClient(updated.customer_model,old.interaction.customer_records) if old.interaction else None
            new=run_instance(updated,old.instance_id,service,customer,old.trial_id)
            if new.service_execution!=old.service_execution or new.interaction!=old.interaction or service.index!=len(execution.llm_records) or (customer and customer.index!=len(old.interaction.customer_records)):raise ValueError('recorded model inputs or actual execution differ')
            new.save(a.out/evidence_dir/f'{new.instance_id}.{new.trial_id}.run.json');regenerated.append(new)
        report=summarize(updated,regenerated)
        if not report['complete']:raise ValueError('preregistered pilot coverage incomplete')
        result[track+'_report']=report
        result[track+'_model']=updated.service_model.model_dump(mode='json')
        result['source_migration'][track]={'original_manifest_hash':original.manifest_hash,'release_manifest_hash':updated.manifest_hash,'changed_source_files':changed,'byte_identical_model_requests_and_execution':True,'actual_runs':len(regenerated)}
        if updated.customer_model:result['customer_model']=updated.customer_model.model_dump(mode='json')
        print(track,report.get('overall_task_success_rate',report.get('discovery_success_rate')),flush=True)
    write_json(a.out/'pilot-report.json',result)


if __name__=='__main__':main()
