"""Post-run descriptive attribution audit; does not change registered scores.

Exact parsed Customer intentions are compared with unchanged Reference decisions
at the actual turn prestate and the committed Service operations. No LLM judge,
keyword notion of test quality, inferred authorization or new Reflection.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from compare_customer_performance import load, evidence_for, artifact_trace
from vast_coevo.models import EpisodeEvidence
from vast_coevo.schema import atomic_json
from usami_cloudops.models import Operation, World
from usami_cloudops.rules import decide, owner, role


def project_context(world,pid,actor):
    if pid not in world.projects:return None
    project=world.projects[pid]
    data=dict(project=project.model_dump(mode='json',exclude={'name'}),
              invoice=world.invoices[project.invoice_id].model_dump(mode='json'),
              instances={key:value.model_dump(mode='json',exclude={'name'}) for key,value in world.instances.items() if value.project_id==pid},
              actor_owner=owner(world,actor,pid),actor_role=role(world,actor,pid))
    return data


def review(root):
    manifest,libraries,adapter=load(root)
    training=World.model_validate_json((root/'source-training-world.json').read_text())
    if training.state_hash!=manifest['training_world_hash']:raise ValueError('source training world changed')
    rows=[]
    for job in manifest['jobs']:
        _,path=evidence_for(root,job)
        if not path.exists():continue
        evidence=EpisodeEvidence.model_validate_json(path.read_text())
        artifact,trace=artifact_trace(evidence)
        execution=trace.service_execution
        engine_events=[e for e in execution.world_trace.events if e.kind=='operation']
        states={execution.world_trace.initial_state.state_hash:execution.world_trace.initial_state}
        for event in engine_events:
            states[event.before.state_hash]=event.before
            states[event.after.state_hash]=event.after
        audits={r['event_id']:r for r in execution.oracle['operations']}
        tools_by_turn={}
        for record in execution.llm_records:
            turn=sum(m.get('role')=='user' for m in record.request['messages'])
            for choice in (record.response or {}).get('choices',[])[:1]:
                for call in choice.get('message',{}).get('tool_calls',[]) or []:
                    tools_by_turn[call['id']]=turn
        event_turn={tool.event_id:tools_by_turn.get(tool.call_id) for tool in execution.tool_records if tool.event_id}
        turns=[]
        for n,turn in enumerate(trace.turns,1):
            state=states.get(turn['before_hash'])
            choices=[e for e in engine_events if event_turn.get(e.id)==n]
            intentions=[]
            for item in turn['intents']:
                op=Operation.model_validate(item['operation'])
                decision=decide(state,evidence.config.identity,op) if state else None
                exact=[e for e in choices if e.payload['operation']==op.model_dump(mode='json')]
                classifications=[audits[e.id]['classification'] for e in exact]
                reply=turn['response']['final_reply'] or ''
                if item['disposition']!='accepted':category='customer_intent_unverified_or_duplicate'
                elif decision is None or decision.error_code=='INVALID_WORLD':category='reference_unknown_after_invalid_state'
                elif 'successful_business_violation' in classifications:category='service_successful_business_violation_on_exact_intent'
                elif 'authorization_only' in classifications:category='authorization_anomaly_separate_from_business_violation'
                elif 'legal_execution' in classifications:category='lawful_exact_intent_executed' if decision.allowed else 'lawful_execution_after_prerequisite_changes'
                elif not decision.allowed and 'rejected_invalid_attempt' in classifications:category='reference_disallowed_exact_intent_service_attempt_blocked'
                elif not decision.allowed and not exact and decision.error_code in reply:category='supported_service_policy_refusal'
                elif not decision.allowed and not exact:category='reference_disallowed_intent_not_executed_refusal_explanation_unverified'
                elif decision.allowed and 'false_rejection' in classifications:category='oracle_false_rejection'
                else:category='lawful_intent_not_executed_or_result_unknown'
                intentions.append(dict(operation=op.model_dump(mode='json'),disposition=item['disposition'],
                                       same_initial_target_context_as_source=op.project_id in training.projects and op.project_id in execution.world_trace.initial_state.projects and project_context(execution.world_trace.initial_state,op.project_id,evidence.config.identity)==project_context(training,op.project_id,'u0'),
                                       turn_start_reference_allowed=decision.allowed if decision else None,
                                       turn_start_reference_error=decision.error_code if decision else None,
                                       service_exact_event_ids=[e.id for e in exact],oracle_classifications=classifications,category=category))
            turns.append(dict(turn=n,customer_message=turn['action']['message'],intentions=intentions,
                              service_reply=turn['response']['final_reply'],service_events=[dict(event_id=e.id,operation=e.payload['operation'],oracle=audits[e.id]) for e in choices]))
        rows.append(dict(episode_id=job['episode_id'],scene_id=job['scene_id'],arm=job['arm'],turns=turns))
    groups={}
    root_types={}
    novelty={}
    for arm in ('C0','C1'):
        selected=[r for r in rows if r['arm']==arm]
        groups[arm]=dict(Counter(i['category'] for row in selected for t in row['turns'] for i in t['intentions']))
        root_types[arm]=sorted({(e['oracle']['operation'],e['oracle']['reference_error_code'] or 'EXPECTED_TRANSITION_MISMATCH')
                               for row in selected for t in row['turns'] for e in t['service_events']
                               if e['oracle']['classification']=='successful_business_violation'})
        intents=[i for row in selected for t in row['turns'] for i in t['intentions']]
        novelty[arm]=dict(explicit_write_intents=len(intents),same_source_initial_target_context=sum(i['same_initial_target_context_as_source'] for i in intents),
                         project_distribution=dict(Counter(i['operation']['project_id'] for i in intents)),
                         operation_distribution=dict(Counter(i['operation']['name'] for i in intents)))
    report=dict(schema_version=1,purpose='post_run_descriptive_attribution_audit',preregistered_scores_changed=False,
                note='Reference-disallowed Customer intentions can be intentional negative probes; they are not automatically Customer mistakes. No hidden facts or review results are fed back to either agent.',
                groups=groups,distinct_primary_reference_rule_types=root_types,target_context_novelty=novelty,episodes=rows)
    atomic_json(root/'attribution-review.json',report)
    print(json.dumps(groups,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    review(parser.parse_args().root.resolve())
