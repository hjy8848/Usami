"""Supplementary entity/subsystem counts over goals AND operation domains."""
import argparse
from collections import Counter
from pathlib import Path
from usami.audit.signatures import resource_type
from usami.benchmark.manifest import load_manifest
from usami.benchmark.release_v2 import write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=Path('benchmarks/v0.2.0'));a=p.parse_args()
    systems,entities,atoms=Counter(),Counter(),Counter()
    splits={}
    for split in ('train','validation','test-demo'):
        m=load_manifest(a.release/f'service-{split}.json')
        splits[split]={'instances':len(m.instances),'structures':len({i.task.structure_signature for i in m.instances}),'semantics':len({i.task.semantic_signature for i in m.instances})}
        for i in m.instances:
            touched={(p.collection,p.entity) for atom in i.task.goal.atoms for p in atom.predicates}
            touched.update((resource_type(op),op.resource_id) for op in i.task.capabilities)
            systems['+'.join(sorted({kind for kind,rid in touched}))]+=1
            entities[str(len(touched))]+=1
            atoms['+'.join(sorted(a.kind for a in i.task.goal.atoms))]+=1
    write_json(a.release/'coverage-details.json',{'methodology':'Goal predicates plus fixed operation domains; includes refusal targets and creation operations. Original coverage.json subsystem metric counts terminal-predicate entities only.','operation_and_goal_subsystem_combinations':dict(systems),'distinct_touched_resources':dict(entities),'atomic_goal_combinations':dict(atoms),'splits':splits})


if __name__=='__main__':main()
