"""Render evaluator-only review JSON as readable curated examples; no human ratings."""
import argparse
import json
from pathlib import Path


def render(package, out):
    rows=['# Curated task review examples', '', '**AWAITING EXTERNAL HUMAN REVIEW. Evaluator-only; never send witnesses to Service.**', '']
    for n,e in enumerate(package['examples'],1):
        rows += [f"## {n}. {e['family']} — {e['split']}", '', e['request'], '',
                 f"Authenticated identity: `{e['identity']}`. Roles: " + ', '.join(f"{m['org_id']}={m['role']} ({m['status']})" for m in e['roles']) + '.', '',
                 'Relevant initial facts:', '']
        for s in e['relevant_initial_world']['subscriptions']:
            members=sum(m['org_id']==s['org_id'] and m['status']=='active' for m in e['relevant_initial_world']['memberships'])
            rows.append(f"- {s['id']}: {s['status']}, plan {s['plan_id']}, {s['seats']} seats / {members} active members; period ends {s['period_end']}.")
        rows += ['', 'Terminal business predicates:', '']
        for a in e['goal']['atoms']:
            for p in a['predicates']:
                rows.append(f"- {a['motivation']}: {p['collection']}/{p['entity']}.{p['field']} {p['comparison']} {p['value']}.")
        rows += ['', f"Forbidden side effects: {e['forbidden_side_effects']}", '', 'Validity / causal certificates:', '']
        for w in e['certificates']:
            plan=' → '.join(o['name'] for o in w['operations'])
            rows.append(f"- Legal evaluator witness: {plan}; dependency depth {w['dependency_depth']}; Oracle {w['oracle_status']}; replay {w['replay_verified']}.")
            rows.append(f"  Necessary operation types inside the frozen search domain: {', '.join(w['necessary_operation_types']) or 'none certified'}.")
        if e['policy_certificate']:
            p=e['policy_certificate'];rows.append(f"- Policy certificate {p['error_code']}: {p['reason']}")
        rows += ['', 'Distinct business objectives: ' + ', '.join(e['distinctness']) + '.', '',
                 'Scoring: ' + e['scoring'], '', f"Canonical structure: `{e['structure_signature']}`.", '', 'Human ratings: **not supplied**.', '']
    Path(out).write_text('\n'.join(rows).rstrip()+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=Path('benchmarks/v0.2.0'));a=p.parse_args()
    render(json.loads((a.release/'review-examples.json').read_text()),a.release/'TASK_EXAMPLES.md')
