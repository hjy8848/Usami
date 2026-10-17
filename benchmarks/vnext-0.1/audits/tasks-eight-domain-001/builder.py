"""Reproduce eight native task proofs and their coverage audit; no model calls.

These hand-selected engineering cases are not a random sample, a balanced Pilot
or a model-performance experiment. The initial independent generators are never
conditioned on these tasks. Inputs are saved before proof construction begins.
"""
import argparse
import json
from pathlib import Path

from usami_harness.models import digest
from vast_coevo.schema import atomic_json
from usami_benchmark.registry import default_spec
from usami_benchmark.worlds import freeze
from usami_benchmark.tasks import TaskSelection, ConstructionBudget, compile_task
from usami_benchmark.artifacts import save_archive
from usami_benchmark.audit import snapshot_sources
from usami_benchmark.task_audit import audit_archive


def requests():
    tools = [
        ('saas', 'user_001', 'cancel_renewal', {'org_id': 'org_001', 'resource_id': 'sub_001', 'params': {}},
         'Cancel automatic renewal for subscription sub_001 in org_001. Leave other settings unchanged.'),
        ('cloudops', 'u2', 'stop_instance', {'project_id': 'p1', 'resource_id': 'p1_r0', 'params': {}},
         'Stop instance p1_r0 in project p1. Do not change other instances or project settings.'),
        ('fulfillment', 'u1', 'set_warehouse_receiving', {'scope_id': 'w1', 'resource_id': 'w1', 'params': {'enabled': False}},
         'Disable receiving at warehouse w1. Preserve its stock, orders and other settings.'),
        ('stayops', 'u0', 'mark_room_clean', {'scope_id': 'p0', 'resource_id': 'p0_type1_room0', 'params': {}},
         'Mark room p0_type1_room0 clean at property p0. Leave reservations and other rooms unchanged.'),
    ]
    rows = []
    for domain, identity, name, parameters, message in tools:
        rows.append({'world_spec': default_spec(domain, 42).model_dump(mode='json'),
                     'selection': TaskSelection(kind='tool', identity=identity, family=name, message=message,
                                                capabilities=[{'name': name, **parameters}]).model_dump(mode='json'),
                     'construction_budget': ConstructionBudget(max_nodes=32, max_depth=3).model_dump(mode='json')})
    for domain, seed, profile, family, parameters in [
        ('aftersales', 1, 'profile_u1_order0_line1', 'settlement_with_duplicate_refusal', {'mixed': True}),
        ('airline', 0, 'profile_u0_booking1', 'refund', {'mixed': True}),
        ('property', 1, 'profile_p0_building0_unit1_asset1', 'repair', {'slot_ids': ['p0_tech0_slot2'], 'mixed': True}),
        ('education', 0, 'profile_u1_enrollment1', 'refund', {'mixed': True}),
    ]:
        rows.append({'world_spec': default_spec(domain, seed).model_dump(mode='json'),
                     'selection': TaskSelection(kind='dialogue', profile_id=profile, family=family,
                                                parameters=parameters).model_dump(mode='json'),
                     'construction_budget': ConstructionBudget(max_nodes=256).model_dump(mode='json')})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    snapshot_sources(root)
    plan = {'protocol': 'eight-domain-task-coverage-checkpoint-v1', 'requests': requests(),
            'model_calls': 0, 'sampling': 'Hand-selected engineering examples; not independent Benchmark test data.',
            'model_experiments': 'NOT RUN'}
    plan['registration_hash'] = digest(plan)
    atomic_json(root / 'registration.json', plan, immutable=True)
    tasks = []
    try:
        for index, raw in enumerate(plan['requests']):
            from usami_benchmark.contracts import WorldSpec
            record = compile_task(freeze(WorldSpec.model_validate(raw['world_spec'])),
                                  TaskSelection.model_validate(raw['selection']),
                                  ConstructionBudget.model_validate(raw['construction_budget']))
            tasks.append(record)
            atomic_json(root / ('completed-' + str(index) + '.json'), {
                'task_hash': record.task_hash, 'record_hash': record.record_hash, 'domain': record.frozen.spec.domain,
            }, immutable=True)
            print('Certified ' + record.frozen.spec.domain, flush=True)
        archive = save_archive(root / 'tasks', tasks)
        result = audit_archive(root / 'tasks', root / 'audit', per_domain_target=40)
        atomic_json(root / 'summary.json', {
            'tasks': len(tasks), 'archive_manifest_hash': archive['manifest_hash'], 'audit': result,
            'model_calls': 0, 'model_experiments': 'NOT RUN', 'pilot_or_core_release': False,
        }, immutable=True)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        atomic_json(root / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
                                           'completed_tasks': len(tasks), 'retry': 'not attempted'}, immutable=True)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
