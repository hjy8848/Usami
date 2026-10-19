from __future__ import annotations
import copy, json, os, shutil, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/Users/spring/RSI/Usami')
OUT = ROOT / 'experiments/vast_coevo/results/aftersales-service-skill-ab-lite-schema-20261019-001'
SOURCE = ROOT / 'experiments/vast_coevo/results/aftersales-answer-deepseek-live-20261019-001/journal.json'
SKILL_DIR = ROOT / 'experiments/vast_coevo/results/aftersales-service-repair-live-20261019-001'
SNAPSHOT_PATH = SKILL_DIR / 'libraries/service/snapshots/0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35.json'
CONTEXT_PATH = SKILL_DIR / 'attempts/0006/retest/config.json'
MODEL = 'dashscope/qwen3.7-plus'
BASE_URL = 'http://10.130.138.46:8010/v1'


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def safe_source_summary(record):
    task_record = record['config']['task']
    witness = task_record['dialogue_witnesses'][0]
    task = witness['certificate']['task']
    return {
        'source_execution_hash': record.get('execution_hash'),
        'source_task_hash': task.get('task_hash'),
        'world_hash': task_record['frozen'].get('world_hash'),
        'seed': task_record['frozen'].get('spec', {}).get('seed'),
        'domain': task.get('domain'),
        'profile_id': task.get('profile_id'),
        'customer_request': task.get('composition', {}).get('customer_request'),
        'known_source_service_error_count': record.get('score', {}).get('metrics', {}).get('successful_business_violation'),
        'source_oracle_status': record.get('score', {}).get('oracle_status'),
        'source_replay_verified': record.get('score', {}).get('replay_verified'),
    }


def main():
    if OUT.exists():
        raise SystemExit('Refusing to overwrite existing run directory: ' + str(OUT))
    if not SOURCE.is_file() or not SNAPSHOT_PATH.is_file() or not CONTEXT_PATH.is_file():
        raise SystemExit('Required source task, candidate snapshot, or rendered context is missing')

    sys.path.insert(0, str(ROOT))
    from usami_harness.models import Budget, digest
    from usami.service.client import OpenAICompatibleClient, key_from_env
    from usami.service.models import ModelSettings
    from usami_benchmark.episodes import dialogue_adapter, tool_names
    from usami_benchmark.tasks import CertifiedTask, verify_task
    from usami_dialogue.agents import TaskRunConfig, SkillPromptContext, service_response_schema, run as agent_run, replay as agent_replay
    from usami_dialogue.tasks import score as native_score, verify_certificate
    from vast_coevo.skills.library import LibrarySnapshot
    from vast_coevo.skills.renderer import SkillRenderer

    source_raw = json.loads(SOURCE.read_text(encoding='utf-8'))
    registered_raw = source_raw['config']['task']
    registered = CertifiedTask.model_validate(registered_raw)
    if not verify_task(registered):
        raise SystemExit('Source certified task failed native verification')
    witness = registered.dialogue_witnesses[0]
    task = witness.certificate.task
    adapter = dialogue_adapter(task.domain, task.rules_version)
    frozen_world = adapter.World.model_validate(copy.deepcopy(registered.frozen.world))
    if not verify_certificate(adapter, frozen_world, witness.certificate, witness.trace):
        raise SystemExit('Source dialogue certificate failed native verification')

    snapshot_raw = json.loads(SNAPSHOT_PATH.read_text(encoding='utf-8'))
    snapshot = LibrarySnapshot.model_validate(snapshot_raw)
    if snapshot.snapshot_hash != '0a22df6944e48eecd15ee42e5fc55536e264fbcb0dadd9e5c812841542a63d35':
        raise SystemExit('Candidate Service snapshot hash differs from the registered candidate')
    context_archive = json.loads(CONTEXT_PATH.read_text(encoding='utf-8'))
    rendered = SkillRenderer().render(snapshot.skills)
    if rendered != context_archive['skill_context']['rendered']:
        raise SystemExit('Candidate Skill rendering differs from the archived prompt context')
    skill_context = SkillPromptContext(
        snapshot_hash=snapshot.snapshot_hash,
        skill_ids=[skill.id for skill in snapshot.skills],
        rendered=rendered,
    )
    if skill_context.context_hash != context_archive['skill_context']['context_hash']:
        raise SystemExit('Candidate prompt context hash differs from the archived context')

    # Keep the exact same task/world, Customer model, Service model, tool set and budget.
    # Only the optional Service skill_contexts field differs between the pair.
    budget = Budget.model_validate(source_raw['config']['budget'])
    settings = ModelSettings(
        model=MODEL,
        base_url=BASE_URL,
        timeout_seconds=90.0,
        options={'temperature': 0},  # no max_tokens cap; call/turn budgets bound the run
        trust_env=False,
    )
    key_env = {
        'USAMI_LLM_KEYCHAIN_SERVICE': 'litellm',
        'USAMI_LLM_KEYCHAIN_ACCOUNT': 'litellm-api-key',
    }
    api_key = key_from_env(key_env)
    if not api_key:
        raise SystemExit('LiteLLM Keychain entry was empty')

    OUT.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), OUT / 'runner.py')
    dump(OUT / 'registered-task.json', registered)
    dump(OUT / 'candidate-service-snapshot.json', snapshot)
    dump(OUT / 'source-summary.json', safe_source_summary(source_raw))
    response_schema = service_response_schema(adapter)
    response_schema_hash = digest(response_schema)
    dump(OUT / 'service-response-schema.json', response_schema)
    dump(OUT / 'preflight.json', {
        'response_schema_version': 'aftersales-quote-backed-response-v1',
        'response_schema_hash': response_schema_hash,
        'response_schema_file': 'service-response-schema.json',
        'source_task_verified': True,
        'source_certificate_verified': True,
        'candidate_snapshot_verified': True,
        'candidate_snapshot_hash': snapshot.snapshot_hash,
        'candidate_skill_ids': [skill.id for skill in snapshot.skills],
        'candidate_skill_content_hashes': {skill.id: skill.content_hash for skill in snapshot.skills},
        'candidate_prompt_context_hash': skill_context.context_hash,
        'candidate_prompt_matches_archive': True,
        'source_world_hash': registered.frozen.world_hash,
        'source_task_hash': registered.task_hash,
        'budget': budget.model_dump(mode='json'),
        'model': settings.model_dump(mode='json'),
        'dynamic_gate': 'not run; this is a paired diagnostic regression smoke only',
        'retry_policy': 'no automatic provider retry',
    })
    manifest = {
        'protocol': 'aftersales-service-skill-ab-lite-schema-v2',
        'protocol_change': 'offered_operation now has a closed union of after-sales commit_resolution/release_refund shapes plus null; runtime still verifies a real current quote',
        'status': 'RUNNING',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'model': settings.model_dump(mode='json'),
        'frozen_task_hash': registered.task_hash,
        'frozen_world_hash': registered.frozen.world_hash,
        'service_snapshot_without_skill': 'be7e66f910c2d0ec5143c7abfea8491fd9a1eb9cbc70a766c992436bebefb728',
        'service_snapshot_with_skill': snapshot.snapshot_hash,
        'skill_id': snapshot.skills[0].id if snapshot.skills else None,
        'skill_content_hash': snapshot.skills[0].content_hash if snapshot.skills else None,
        'customer_model_and_customer_policy': 'same in both runs; no Customer Skill injected',
        'only_intended_difference': 'Service SkillPromptContext omitted vs exact candidate snapshot rendered into Service system message',
        'protocol_change': 'Both arms use the corrected exact quote-backed offered_operation schema; no other prompt, task, model, tool, world, or budget changes.',
        'response_schema_hash': response_schema_hash,
        'budget': budget.model_dump(mode='json'),
        'partition': 'train; targeted regression using a previously observed failure case, not held-out evidence',
        'dynamic_gate': 'not run; diagnostics only',
        'retry_policy': 'no automatic provider retry; each condition run once',
        'runs': [],
    }
    dump(OUT / 'manifest.json', manifest)
    results = []
    overall_error = None
    try:
        for label, contexts in [('without-skill', {}), ('with-skill', {'service': skill_context})]:
            run_root = OUT / label
            run_root.mkdir()
            run_world = adapter.World.model_validate(copy.deepcopy(registered.frozen.world))
            run_cfg = TaskRunConfig(
                task=task,
                certificate=witness.certificate,
                witness=witness.trace,
                profile_id=task.profile_id,
                initial_world_hash=run_world.state_hash,
                mode='sandbox',
                tools=tool_names(registered),
                budget=budget,
                external_schedule=list(task.external_schedule),
                skill_contexts=contexts,
            )
            dump(run_root / 'config.json', {
                'protocol': 'service-skill-ab-run-config-v1',
                'condition': label,
                'task_hash': registered.task_hash,
                'world_hash': run_world.state_hash,
                'model': settings.model_dump(mode='json'),
                'budget': budget.model_dump(mode='json'),
                'service_snapshot_hash': snapshot.snapshot_hash if contexts else 'be7e66f910c2d0ec5143c7abfea8491fd9a1eb9cbc70a766c992436bebefb728',
                'skill_context': skill_context.model_dump(mode='json') if contexts else None,
                'tool_names': run_cfg.tools,
                'mode': run_cfg.mode,
            })
            customer_client = OpenAICompatibleClient(settings, api_key)
            service_client = OpenAICompatibleClient(settings, api_key)
            started = time.time()
            try:
                execution = agent_run(adapter, run_world, run_cfg, customer_client, service_client)
            finally:
                customer_client.close()
                service_client.close()
            elapsed = round(time.time() - started, 3)
            score_world = adapter.World.model_validate(copy.deepcopy(registered.frozen.world))
            score = native_score(adapter, score_world, task, execution.trace)
            replay_world = adapter.World.model_validate(copy.deepcopy(registered.frozen.world))
            replay_result = agent_replay(adapter, execution, world=replay_world, config=run_cfg)
            if not replay_result.get('verified'):
                raise RuntimeError('Offline request/trace Replay did not verify for ' + label)

            # Verify the treatment prompt actually included the complete candidate text.
            service_calls = [call for call in execution.calls if call.role == 'service']
            first_service_system = service_calls[0].record.request['messages'][0]['content'] if service_calls else ''
            injection_verified = (rendered in first_service_system and snapshot.snapshot_hash in first_service_system) if contexts else ('<VAST_SKILLS>' not in first_service_system)
            if not injection_verified:
                raise RuntimeError('Service skill injection/control absence failed verification for ' + label)

            ops = execution.oracle.get('operations', [])
            classes = Counter(row.get('classification', 'unknown') for row in ops)
            run_result = {
                'condition': label,
                'status': execution.status,
                'elapsed_seconds': elapsed,
                'final_goal_reached': bool(score.get('completion_subgoals') and all(score['completion_subgoals'])),
                'oracle_status': score.get('oracle_status'),
                'task_success': bool(score.get('success')),
                'successful_business_violations': int(classes.get('successful_business_violation', 0)),
                'authorization_only_errors': int(classes.get('authorization_only', 0)),
                'false_rejections': int(classes.get('false_rejection', 0)),
                'legal_operations': int(classes.get('legal_execution', 0)),
                'operations': [{'event_id': row.get('dialogue_event_id'), 'operation': row.get('operation'),
                                'classification': row.get('classification'), 'reference_codes': row.get('violations', []),
                                'success': row.get('success')} for row in ops],
                'cost': execution.cost,
                'skill_injection_verified': injection_verified,
                'replay': replay_result,
            }
            dump(run_root / 'journal.json', execution)
            dump(run_root / 'score.json', score)
            dump(run_root / 'summary.json', run_result)
            results.append(run_result)
            print(json.dumps({'condition': label, 'status': execution.status,
                              'task_success': run_result['task_success'],
                              'oracle_status': run_result['oracle_status'],
                              'calls': execution.cost.get('customer_calls', 0)+execution.cost.get('service_calls', 0),
                              'tokens': execution.cost.get('total_tokens'),
                              'violations': run_result['successful_business_violations'],
                              'replay_verified': replay_result.get('verified'),
                              'skill_injection_verified': injection_verified}, ensure_ascii=False), flush=True)
            manifest['runs'].append(run_result)
            dump(OUT / 'manifest.json', manifest)
    except Exception as exc:
        overall_error = {'type': type(exc).__name__, 'message': str(exc), 'automatic_retry': False}
        dump(OUT / 'failure.json', overall_error)
    finally:
        manifest['runs'] = results
        manifest['failure'] = overall_error
        manifest['status'] = 'COMPLETED' if len(results) == 2 and overall_error is None else 'PARTIAL_OR_BLOCKED'
        dump(OUT / 'manifest.json', manifest)
    if overall_error:
        print(json.dumps({'status':'PARTIAL_OR_BLOCKED','error':overall_error,'completed_conditions':len(results)},ensure_ascii=False), flush=True)
        return 2
    print(json.dumps({'status':'COMPLETED','result_dir':str(OUT),'conditions':len(results)},ensure_ascii=False), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
