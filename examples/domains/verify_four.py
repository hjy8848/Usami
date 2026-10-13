"""Four domains' manifests and published current pilots: exact offline replay."""
import json
from pathlib import Path
from usami.benchmark.manifest import load_manifest
from usami.benchmark.runtime import replay_run as replay_saas,BenchmarkRun
from usami_cloudops import benchmark as cloud
from usami_fulfillment import benchmark as fulfillment
from usami_stayops import benchmark as stay


def main():
    result={}
    for name,folder,module in [('saas','v0.2.0',None),('cloudops','cloudops-v0.1',cloud),
                               ('fulfillment','fulfillment-v0.1',fulfillment),('stayops','stayops-v0.1',stay)]:
        root=Path('benchmarks')/folder;counts={}
        for file in ['service-train.json','service-validation.json','service-test-demo.json','discovery-demo.json']:
            # New-domain recipe/certificate regeneration is separately exhaustive
            # in each release's verification.json. This gate checks the frozen
            # pins again and reconstructs every published actual model execution.
            manifest=(load_manifest(root/file) if module is None else
                      module.load(root/file) if name=='cloudops' else
                      module.load(root/file,verify_generation=False))
            counts[file]=len(manifest.instances)
            print(name,file,'verified',len(manifest.instances),flush=True)
        pilot=root/('pilot' if name in {'saas','cloudops'} else 'pilot-v1');replayed=0
        for track in ['service','discovery']:
            manifest=load_manifest(pilot/(track+'-profile.json')) if module is None else module.load(pilot/(track+'-profile.json'))
            paths=sorted((pilot/track).glob('*.run.json'))
            expected=len(manifest.instances)*len(manifest.trials)
            if len(paths)!=expected:raise ValueError('published pilot incomplete: '+name+'/'+track)
            for path in paths:
                if module is None:replay_saas(manifest,BenchmarkRun.load(path))
                else:module.replay_run(manifest,module.Run.model_validate_json(path.read_text()))
                replayed+=1
        result[name]={'manifests':counts,'published_real_pilot_exact_replays':replayed}
        print(name,'exact real pilot replays',replayed,flush=True)
    Path('outputs/four-domain-final-verification.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
