"""Post-run descriptive audit; never input to Reflection, gates or either Agent."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from continue_coevolution import context,all_evidence,artifact_trace,paired_interval,verify_injection
from vast_coevo.schema import atomic_json
from vast_coevo.skills.validation import StaticSkillGate
from vast_coevo.skills.library import apply_patch
from vast_coevo.skills import SkillPatch
from vast_coevo.evolution.models import ValidationCase


def review(root):
    m,adapter,store,archive,libs=context(root)
    rows=list(all_evidence(root));byid={r.episode_id:r for r in rows}
    cross=json.loads((root/'cross-manifest.json').read_text());result=json.loads((root/'results.json').read_text())
    evo=json.loads((root/'service-evolution.json').read_text());cg=json.loads((root/'customer-gate.json').read_text())
    static_identical=None;candidate_identical=None
    if evo['patch'] is not None:
        cases=[ValidationCase.model_validate(c) for c in m['development_cases']+m['task_cases']]
        tools=tuple(sorted({n for c in cases for n in adapter.public_capabilities(c.config)}))
        forbidden=tuple(sorted({n for c in cases for n in adapter.forbidden_identifiers(c.config)}))
        patch=SkillPatch.model_validate(evo['patch'])
        checked=StaticSkillGate(allowed_tools=tools,forbidden_identifiers=forbidden,allowed_domains={c.config.domain for c in cases}).validate(libs['S0'],patch)
        if checked.model_dump(mode='json')!=evo['static_validation']:raise ValueError('Static Gate result changed')
        static_identical=True
        if evo['candidate_snapshot_hash'] is not None:
            candidate=apply_patch(libs['S0'],patch,source=m['run_id']+'.service.reflection')
            if candidate!=libs['S1']:raise ValueError('actual Patch candidate content/hash changed')
            candidate_identical=True
    reg=[]
    for row in rows:
        if row.track!='service_task':continue
        art=json.loads(Path(row.trace.path).read_text());task=art['task_profile']
        reg.append(dict(episode_id=row.episode_id,scenario=task['scenario'],snapshot_hash=row.service_snapshot_hash,
                        legal_task_success=row.legal_task_success,correct_refusal=row.correct_refusal,
                        violations=len(row.failures),termination=row.termination))
    first_request_checks=[]
    for scene in m['test_scenes']:
        arms={j['group']:byid[j['id']] for j in cross['jobs'] if j['scene_id']==scene['id'] and j['id'] in byid}
        first={g:next((c for c in row.model_calls if c.role=='customer'),None) for g,row in arms.items()}
        for label in ('C0','C1'):
            left=first.get(label+'xS0');right=first.get(label+'xS1')
            if left is not None and right is not None:
                if left.request!=right.request:raise ValueError('initial Customer wire request changed with Service Skill')
                first_request_checks.append(dict(scene_id=scene['id'],customer=label,request_hash=left.request_hash,identical=True))
    comparisons=[]
    for scene in m['test_scenes']:
        pair={d['arm']:d for d in result['cross_details'] if d['scene_id']==scene['id']}
        if len(pair)!=len(cross['groups']):continue
        comparisons.append(dict(scene_id=scene['id'],violations={g:d['business_violations'] for g,d in pair.items()},
             effective_tests={g:d['effective_tests'] for g,d in pair.items()},query_failures={g:d['query_failures'] for g,d in pair.items()}))
    intervals={}
    for a,b,label in [('C0xS0','C1xS0','customer_at_S0'),('C0xS1','C1xS1','customer_at_S1'),('C0xS0','C0xS1','service_at_C0'),('C1xS0','C1xS1','service_at_C1')]:
        pairs=[p for p in comparisons if a in p['violations'] and b in p['violations']]
        if pairs:
            deltas=[p['violations'][b]-p['violations'][a] for p in pairs]
            intervals[label]=dict(difference='second minus first',first=a,second=b,estimate=paired_interval(deltas),
                                  lower=sum(x<0 for x in deltas),higher=sum(x>0 for x in deltas),tie=sum(x==0 for x in deltas))
    grouped={}
    for g in cross['groups']:
        selected=[byid[j['id']] for j in cross['jobs'] if j['group']==g and j['id'] in byid]
        destinations=Counter();rules=Counter();injections=[];samples=[];categories=Counter();query_codes=Counter();terminations=Counter();query_failures_after_violation=0;unauthorized_successes=[];unauthorized_failures=[]
        for row in selected:
            art,trace=artifact_trace(row);injections+=verify_injection(row,art.customer_snapshot,art.service_snapshot)
            terminations[row.termination]+=1
            events_by_id={event.event_id:event for event in row.events};already_violated=False
            for tool in trace.service_execution.tool_records:
                event=events_by_id.get(tool.event_id)
                if event and event.classification=='successful_business_violation':already_violated=True
                if tool.name.startswith(('get_','list_')) and tool.response.get('success') is False:
                    query_codes[tool.response.get('error_code','unknown')]+=1
                    query_failures_after_violation+=int(already_violated)
            oracle={o['event_id']:o for o in trace.service_execution.oracle['operations']}
            for event in row.events:
                categories[event.classification]+=1
                if event.authorized is False or event.classification=='authorization_only':
                    entry=dict(episode_id=row.episode_id,event_id=event.event_id,operation=oracle[event.event_id]['operation'],classification=event.classification)
                    (unauthorized_successes if oracle[event.event_id]['success'] else unauthorized_failures).append(entry)
                if event.classification=='successful_business_violation':rules[oracle[event.event_id]['reference_error_code'] or 'EXPECTED_TRANSITION_MISMATCH']+=1
            for action in trace.actions:
                for operation in action.requested_operations:
                    destinations[operation.project_id]+=1
            if len(samples)<4:
                samples.append(dict(episode_id=row.episode_id,requests=[a.model_dump(mode='json') for a in trace.actions],
                                    service_replies=[turn['response']['final_reply'] for turn in trace.turns]))
        grouped[g]=dict(unauthorized_successes=unauthorized_successes,unauthorized_failed_attempts=unauthorized_failures,terminations=dict(terminations),query_error_codes=dict(query_codes),query_failures_after_first_violation=query_failures_after_violation,primary_rules=dict(rules),oracle_categories=dict(categories),write_target_projects=dict(destinations),
                        requests_issued=sum(len(artifact_trace(row)[1].actions) for row in selected),
                        injection_calls=sum(c['calls'] for c in injections),injection_calls_with_hits=sum(c['calls_with_hits'] for c in injections),
                        skill_hits=sorted({tuple(hit) for c in injections for hit in c['hits']}),representative_tests=samples)
    audit=dict(schema_version=1,kind='post_run_descriptive_audit',no_feedback_to_agents=True,first_customer_requests=first_request_checks,
               static_gate_identical=static_identical,candidate_snapshot_identical=candidate_identical,customer_accepted=cg['gate']['passed'],customer_rejection_reasons=cg['gate']['reasons'],
               service_stages=dict(generated=evo['patch'] is not None,static_passed=bool(evo['static_validation'] and evo['static_validation']['passed']),
                                   dynamic_passed=bool(evo['dynamic_validation'] and evo['dynamic_validation']['passed']),selected=evo['outcome']=='accepted'),
               service_rejection_reasons=evo['reasons'],regressions=reg,groups=grouped,pairs=comparisons,paired_uncertainty=intervals,
               scope_limit='20 purposefully constructed worlds, one draw per combination; no broad generalization claim.')
    atomic_json(root/'AUDIT.json',audit)
    print(json.dumps(dict(groups={g:v['primary_rules'] for g,v in grouped.items()},regression_episodes=len(reg),paired_uncertainty=intervals),ensure_ascii=False),flush=True)
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);a=p.parse_args();review(a.root.resolve())
