"""Offline native dependency diagnostic verification, no model or network calls."""
import gzip,hashlib,json
from pathlib import Path
import usami_dialogue
from usami_harness.models import digest
from usami_benchmark.worlds import FrozenWorld,freeze
from usami_dialogue.artifacts import adapter_for
from usami_dialogue.engine import ExecutionTrace
from usami_dialogue.dependencies import certify_dependencies,verify_dependency
from usami_dialogue.oracle import evaluate
from usami_dialogue.replay import replay


def verify(root):
    root=Path(root);m=json.loads((root/'manifest.json').read_text());pins=json.loads((root/'source-pins.json').read_text())
    assert m['protocol']=='native-dialogue-dependency-diagnostics-v1' and m['source_pins_hash']==digest(pins)
    assert m['evidence_kind']=='native_dependency_diagnostic' and m['real_api_calls']==0 and m['model_experiments']=='NOT RUN'
    repo=Path(usami_dialogue.__file__).resolve().parents[1]
    folders=[p for p in repo.glob('usami*') if p.is_dir()]+[repo/'integrations',repo/'vast_coevo']
    assert set(pins)=={str(p.relative_to(repo)) for folder in folders for p in folder.rglob('*.py')}
    for relative,expected in pins.items():
        path=Path(relative)
        assert not path.is_absolute() and '..' not in path.parts and path.suffix=='.py'
        assert hashlib.sha256((repo/path).read_bytes()).hexdigest()==expected
    kinds=set();count=0
    for row in m['cases']:
        assert Path(row['path']).name==row['path']
        data=(root/row['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['compressed_sha256']
        raw=json.loads(gzip.decompress(data));assert digest(raw)==row['content_hash']
        frozen=FrozenWorld.model_validate(raw['frozen']).checked();assert freeze(frozen.spec)==frozen
        trace=ExecutionTrace.model_validate(raw['trace']);adapter=adapter_for(trace.domain)
        assert trace.initial_world==frozen.world and evaluate(adapter,trace)['status']=='pass' and replay(adapter,trace)['verified']
        proofs=certify_dependencies(adapter,trace)
        assert [p.model_dump(mode='json') for p in proofs]==raw['dependencies']
        assert all(verify_dependency(adapter,trace,p) for p in proofs)
        observed=sorted({p.proof.kind for p in proofs});assert observed==row['kinds'];kinds.update(observed);count+=len(proofs)
    assert sorted(kinds)==m['kinds']
    return {'verified':True,'kinds':sorted(kinds),'dependency_proofs':count,'model_experiments':'NOT RUN','real_api_calls':0}


if __name__=='__main__':print(verify(Path(__file__).resolve().parent))
