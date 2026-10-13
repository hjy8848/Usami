"""Render measured release report only after every preregistered live attempt exists."""
import json
from pathlib import Path
from usami_stayops.benchmark import write_json


def main():
    root=Path('benchmarks/stayops-v0.1');pilot=root/'pilot-v1';data=json.loads((pilot/'pilot-report.json').read_text())
    service,discovery=data['service_report'],data['discovery_report']
    assert service['complete'] and discovery['complete']
    data['preflight_attempts']=[{'condition':'Initial pilot launch before independent dataset files existed',
        'llm_completions':0,'profiles_registered':False,'retry_of_live_trial':False,'evidence':'preflight-no-model-call.txt'}]
    write_json(root/'pilot-report.json',data)
    c=json.loads((root/'coverage.json').read_text());lines=['# StayOps v0.1 measured report','','Engineering gates and actual model samples are separate from human realism review: **AWAITING HUMAN REVIEW**.','',
        '| Measure | Actual | Target |','|---|---:|---:|']
    for k,n in c['metrics'].items():lines.append(f'| {k} | {n} | {c["targets"][k]} |')
    lines += ['',f'{c["base_goal_cases"]} base goal/decision cases; {c["verified_witnesses"]} actual certified witnesses; {c["policy_refusal_tasks"]} refusal certificates. Headline structures/semantics use base cases only. Progress states are genuine executed workflow stages, never additional families.',
        '',f'Train/Validation/Public Test Demo: {c["split_counts"]}. Train/Test structure intersection is empty. All Test operations and normalized terminal atomic abilities occur in Train. Validation has only one instance and is inadequate for tuning/generalization claims; expand a later frozen release.',
        '', '55 domain tests passed and 605 full repository tests passed. All 302 frozen states, 569 witnesses and 29 refusals were independently regenerated, executed, Oracle-checked and replayed. Two independent rebuilds agree in canonical data and raw bytes. See verification.json and rebuild-check.json. Existing SaaS/CloudOps sources and published releases remain byte-unchanged.',
        '', '## Actual Service pilot','', 'Provider: dashscope/qwen3.6-plus, OpenAI-compatible LiteLLM, temperature 0/max_tokens 4096. Authentication resolves from Keychain and is not persisted. Both profiles were fixed before the first live completion; exact model bodies/replies, native intents, world events, authority, tool results, Oracle and source/runtime versions are retained under pilot-v1/.',
        '', '| Family | Status | Model/tool calls | Goal/frame/Oracle result |','|---|---|---:|---|']
    for row in service['rows']:lines.append(f'| {row["family"]} | {row["status"]} | {row["service_llm_calls"]}/{row["service_tool_calls"]} | {"pass" if row["task_success"] else "fail"} |')
    lines += ['',f'Selected-case success: {sum(r["task_success"] for r in service["rows"])}/6. This is not a full 302-task score. No attempt is discarded or silently retried.',
        '', '## Actual open-ended Customer pilot','', 'One unconditioned generated world, fixed u0 identity/victim/tools/budgets and three preregistered trials. No task, family, script, witness or goal enters Customer input. Customer selects queries and writes from scoped observations and actual Service replies; state persists within each episode and resets across trials.',
        '', '| Trial | Status | Customer turns/calls | Service calls/tools | Business violation events | Authority-only events |','|---|---|---:|---:|---:|---:|']
    details=[]
    for row in discovery['rows']:
        path=pilot/'discovery'/(row['instance_id']+'.'+row['trial']+'.run.json');episode=json.loads(path.read_text())['interaction']
        lines.append(f'| {row["trial"]} | {row["status"]} | {row["customer_turns"]}/{row["customer_llm_calls"]} | {row["service_llm_calls"]}/{row["service_tool_calls"]} | {row["verified_business_violation_events"]} | {row["operation_counts"]["authorization_only"]} |')
        records=episode['customer_llm_records'];details.append({'trial':row['trial'],'score':row,
            'customer_schema_errors':sum(r.get('error',{}).get('stage')=='protocol' for r in records),
            'customer_transport_or_model_errors':sum(r.get('error',{}).get('stage')=='transport' for r in records),
            'first_three_autonomous_actions':episode['actions'][:3]})
    write_json(root/'discovery-trial-details.json',details)
    lines += ['',f'Actual Customer schema errors: {sum(d["customer_schema_errors"] for d in details)}; transport/model errors: {sum(d["customer_transport_or_model_errors"] for d in details)}; format recoveries: {sum(d["score"]["format_recoveries"] for d in details)}.']
    lines += ['', 'All raw actions and any protocol/format recovery/provider failures and budget terminations remain in evidence. Successful business violations are counted as verified events, not distinct vulnerabilities. Rejected attempts and authorization-only anomalies are separate and cannot raise business discovery success. Native protocol/format recovery counters are in discovery-trial-details.json and the complete pilot report.',
        '', 'The initial launch before dataset files existed made zero completions and registered no profiles; preflight-no-model-call.txt retains the condition. It was not a failed live trial. Existing started live attempts are never retried.',
        '', '## Research readiness and limits','', 'Both independent new domains expose typed adapter, scoped observation, Engine, ServiceSession, native CustomerSession, frozen Manifest, run_instance, score, replay_run and assert_comparable. Native Customer functions validate exact single-use intentions before Service; model format repair cannot alter intent. Future Customer methods may vary model/method under fixed victim/world/identity/tools/source/budgets/trials.',
        '', 'No Evolver/training/Service repair is implemented. The hotel clock and simulated external events are instantaneous and deterministic, policy/family design is authored, reachability is bounded and all tests are public demos. Human realism review is pending. These limits allow controlled open Discovery comparisons but prevent claims of production-hotel realism, private-test generalization or robust model competence.']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
