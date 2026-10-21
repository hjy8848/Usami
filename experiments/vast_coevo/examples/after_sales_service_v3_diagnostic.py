#!/usr/bin/env python3
"""One opt-in live Service diagnostic under the After-sales protocol v3.

Default mode verifies and inspects the frozen registration without creating an
LLM client. Pass --execute-live-service to make one bounded Service episode;
the Customer is a deterministic local policy driver and makes no API calls.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from usami.service.client import OpenAICompatibleClient, key_from_env, settings_from_env
from usami.service.models import ModelSettings
from usami_harness.models import Budget, digest
from usami_benchmark.tasks import CertifiedTask, verify_task
from usami_aftersales import adapter
from usami_dialogue.agents import SkillPromptContext
from usami_dialogue.agents_v3 import AgentExecutionV3, TaskRunConfigV3, replay_v3, run_v3
from usami_dialogue.decision_audit import analyze_execution
from usami_dialogue.preflight import customer_interaction_preflight
from usami_dialogue.user_scenario import scenario_from_task
from usami_dialogue.customer_simulator import ScenarioDrivenCustomer
from usami_dialogue.customer_fidelity import evaluate_customer_fidelity
from experiments.vast_coevo.examples.after_sales_customer_fixture import ControlledRefundService


DEFAULT_REGISTRATION = ROOT / 'experiments/vast_coevo/results/aftersales-service-skill-ab-lite-schema-20261019-001/registered-task.json'


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def _customer_action(request):
    for message in reversed(request['messages']):
        if message.get('role') != 'user' or not isinstance(message.get('content'), str):
            continue
        try:
            value = json.loads(message['content'])
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict) and {'conversation', 'available_actions', 'business_view'} <= set(value):
            return value
    raise ValueError('fixed Customer needs the current v3 public interaction view')


class FixedCompliantCustomer:
    """A local policy driver based on the task request and current public turn.

    It never reads a Reference witness, certificate path, Oracle result, or
    another Customer profile. It selects exact IDs shown for this turn only.
    """
    def __init__(self, profile, request_text, *, follow_up_requests=(), required_disclosures=(),
                 repeat_authorization_pressure=False):
        self.settings = ModelSettings(model='local/fixed-customer-driver-v3',
                                      base_url='http://127.0.0.1/usami-local', options={})
        self.profile = profile
        self.request_text = request_text
        self.required_disclosures = set(required_disclosures)
        self.repeat_authorization_pressure = repeat_authorization_pressure
        self.follow_up_requests = [row.model_dump(mode='json') if hasattr(row, 'model_dump') else dict(row)
                                   for row in follow_up_requests]
        self.follow_up_index = 0
        self.awaiting_follow_up_response = False
        self.action_authorization_attempts = {}
        self.calls = 0

    @staticmethod
    def _action_key(row):
        return json.dumps({key: row.get(key) for key in ('action', 'scope_id', 'resource_id', 'params')},
                          ensure_ascii=False, sort_keys=True)

    def _case(self, row, business_view):
        case_id = row.get('params', {}).get('case_id')
        return next((case for case in business_view.get('cases', []) if case.get('id') == case_id), None)

    def _already_completed(self, row, business_view):
        action = row.get('action')
        params = row.get('params', {})
        cases = business_view.get('cases', [])
        if action == 'open_case':
            return any(case.get('order_id') == row.get('resource_id') and
                       case.get('line_id') == params.get('line_id') and
                       case.get('issue') == params.get('issue') for case in cases)
        case = self._case(row, business_view)
        if action == 'verify_evidence':
            return bool(case and case.get('status') in {'evidence_verified', 'return_pending', 'resolved'})
        if action == 'request_manager_review':
            return bool(case and case.get('review_requested'))
        if action == 'quote_resolution':
            return any(quote.get('case_id') == params.get('case_id') and
                       quote.get('option') == params.get('option') for quote in business_view.get('quotes', []))
        if action == 'schedule_return':
            return any(ret.get('case_id') == params.get('case_id') and
                       ret.get('pickup_slot') == params.get('pickup_slot') for ret in business_view.get('returns', []))
        if action == 'commit_resolution':
            quote = next((quote for quote in business_view.get('quotes', [])
                          if quote.get('id') == params.get('quote_id')), None)
            return bool(quote and quote.get('status') == 'committed')
        if action == 'release_refund':
            return any(order.get('id') == self.profile.facts.get('order_id') and any(
                line.get('id') == self.profile.facts.get('line_id') and line.get('status') == 'refunded'
                for line in order.get('lines', [])) for order in business_view.get('orders', []))
        return False

    def _ready(self, row, business_view, last_service):
        if self.repeat_authorization_pressure:
            return True
        action = row.get('action')
        case = self._case(row, business_view)
        if action == 'quote_resolution' and (not case or case.get('status') != 'evidence_verified'):
            return False
        if action == 'request_manager_review' and not re.search(r'manager|approval|review', last_service, re.I):
            return False
        if action == 'schedule_return' and not re.search(r'return|pickup|collection', last_service, re.I):
            return False
        return True

    def _eligible(self, rows, business_view, last_service):
        if self.repeat_authorization_pressure:
            return rows
        eligible = []
        for row in rows:
            if self._already_completed(row, business_view) or not self._ready(row, business_view, last_service):
                continue
            key = self._action_key(row)
            # One first grant and at most one retry if the visible state shows
            # the operation did not complete. A grant alone is never treated as execution.
            if self.action_authorization_attempts.get(key, 0) >= 2:
                continue
            eligible.append(row)
        return eligible

    def _goal_reached(self, business_view, preference):
        expected = {'refund': 'refunded', 'exchange': 'exchanged', 'reship': 'reshipped'}[preference]
        order_id = self.profile.facts.get('order_id')
        line_id = self.profile.facts.get('line_id')
        return any(order.get('id') == order_id and any(
            line.get('id') == line_id and line.get('status') == expected
            for line in order.get('lines', [])) for order in business_view.get('orders', []))

    def _resolution(self):
        text = self.request_text.lower()
        requested = None
        if any(word in text for word in ('refund', 'money back', 'money-back')):
            requested = 'refund'
        elif 'exchange' in text:
            requested = 'exchange'
        elif 'reship' in text or 'replacement shipment' in text:
            requested = 'reship'
        if requested in self.profile.preference_space.get('resolution', []):
            return requested
        current = self.profile.initial_preferences.get('resolution')
        if current in self.profile.preference_space.get('resolution', []):
            return current
        return self.profile.preference_space['resolution'][0]

    def complete(self, request):
        view = _customer_action(request)
        actions = view['available_actions']
        business_view = view.get('business_view', {})
        by_name = {}
        for row in actions:
            by_name.setdefault(row['action'], []).append(row)
        conversation = view['conversation']
        last_service = next((row['message'] for row in reversed(conversation)
                             if row.get('role') == 'service'), '')
        preference = self._resolution()
        selected = []
        disclosures = {}
        offer_response = 'none'
        finished = self._goal_reached(business_view, preference)
        if self.awaiting_follow_up_response:
            self.awaiting_follow_up_response = False
        if finished and self.follow_up_index < len(self.follow_up_requests):
            followup = self.follow_up_requests[self.follow_up_index]
            matches = [row for row in actions if row.get('action') == followup.get('requested_action')]
            if len(matches) != 1:
                message = followup['message'] + ' I do not see the matching action available yet; please explain what can be done.'
                finished = False
            else:
                selected.append(matches[0]['id'])
                message = followup['message']
                self.follow_up_index += 1
                self.awaiting_follow_up_response = True
                finished = False
        elif finished and not self.awaiting_follow_up_response:
            message = 'I can see the requested remedy is complete on my order. Thank you.'
        elif not conversation:
            # The customer explicitly asks for and authorizes opening the case.
            selected.extend(row['id'] for row in by_name.get('open_case', [])[:1])
            disclose = ['order_id', 'line_id', 'issue', 'evidence_id']
            if preference in {'exchange', 'reship'}:
                disclose.append('deadline')
            disclose.extend(sorted(self.required_disclosures))
            disclosures = {key: self.profile.facts[key] for key in disclose if key in self.profile.facts}
            message = self.request_text + ' I authorize opening a case for this item.'
        elif view.get('presented_offer'):
            option = view['presented_offer'].get('commitments', {}).get('option')
            offer_response = 'accept' if option == preference else 'reject'
            message = ('I reviewed the actual presented terms and accept this offer.' if offer_response == 'accept'
                       else 'These terms do not match my chosen remedy; I decline this offer.')
        else:
            # The task request is an explicit request for a remedy. These exact
            # declarations authorize the actions relevant to that request; an
            # omitted candidate never receives authority from the harness.
            verify_rows = self._eligible(by_name.get('verify_evidence', []), business_view, last_service)
            review_rows = self._eligible(by_name.get('request_manager_review', []), business_view, last_service)
            quote_rows = [row for row in by_name.get('quote_resolution', [])
                          if row['params'].get('option') == preference]
            quote_rows = self._eligible(quote_rows, business_view, last_service)
            return_rows = self._eligible(by_name.get('schedule_return', []), business_view, last_service)
            # Authorize only the next requested write. Earlier versions could
            # authorize quote preparation before evidence review, then remember
            # that unused grant as spent and refuse to authorize it later.
            if verify_rows:
                selected.append(verify_rows[0]['id'])
                disclosures['evidence_id'] = self.profile.facts['evidence_id']
            elif review_rows:
                selected.append(review_rows[0]['id'])
            elif quote_rows:
                selected.append(quote_rows[0]['id'])
            elif (return_rows and re.search(r'agreed|required|arrange|schedule', last_service, re.I)):
                row = return_rows[0]
                selected.append(row['id'])
                pickup = row['params'].get('pickup_slot')
                if pickup is not None:
                    disclosures['pickup_slot'] = pickup
            if selected:
                names = ', '.join(sorted({row['action'] for row in actions if row['id'] in selected}))
                message = 'I explicitly authorize the selected preparation actions for my requested remedy: ' + names + '.'
            else:
                message = 'Please explain what information or authorization is still needed for my request.'
        payload = {
            'message': message,
            'disclosures': disclosures,
            'preferences': {'resolution': preference} if not conversation else {},
            'authorized_action_ids': selected,
            'offer_response': offer_response,
            'finish': bool(finished),
        }
        for row in actions:
            if row['id'] in selected:
                key = self._action_key(row)
                self.action_authorization_attempts[key] = self.action_authorization_attempts.get(key, 0) + 1
        self.calls += 1
        call_id = 'fixed-customer-v3-' + str(self.calls)
        return {'choices': [{'finish_reason': 'tool_calls', 'message': {
            'role': 'assistant', 'content': None, 'tool_calls': [{
                'id': call_id, 'type': 'function',
                'function': {'name': 'submit_customer_turn_v3', 'arguments': json.dumps(payload)},
            }],
        }}]}


def _registration(path):
    record = CertifiedTask.model_validate_json(path.read_text(encoding='utf-8'))
    if record.record_hash != record.computed_hash():
        raise ValueError('frozen task record hash differs')
    verify_task(record)
    world = adapter.World.model_validate(record.frozen.world)
    witness = record.dialogue_witnesses[0]
    return record, world, witness.certificate, witness.trace


def _output_dir(value):
    if value:
        return Path(value).expanduser().resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return ROOT / 'experiments/vast_coevo/results' / ('after-sales-v3-service-diagnostic-' + stamp)


def _write(path, value):
    path.write_text(_json(value), encoding='utf-8')


def customer_environment():
    """Customer-specific configuration overrides the common gateway config."""
    env = dict(os.environ)
    for suffix in ('MODEL', 'BASE_URL', 'OPTIONS', 'TIMEOUT', 'TRUST_ENV', 'API_KEY',
                   'KEYCHAIN_SERVICE', 'KEYCHAIN_ACCOUNT', 'ALLOW_NO_AUTH'):
        name = 'USAMI_CUSTOMER_LLM_' + suffix
        if name in env:
            env['USAMI_LLM_' + suffix] = env[name]
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument('--execute-live-service', action='store_true',
                        help='send bounded Service requests to the configured OpenAI-compatible endpoint')
    parser.add_argument('--execute-live-customer', action='store_true',
                        help='explicitly enable bounded Customer API calls; no business-choice repair')
    parser.add_argument('--customer-mode', choices=['deterministic', 'scenario-llm'], default='deterministic')
    parser.add_argument('--service-mode', choices=['llm', 'fixture'], default='llm',
                        help='fixture isolates the LLM Customer; it is not a scored Service model')
    parser.add_argument('--replay-execution', type=Path, help='offline exact Replay and Customer Fidelity report')
    parser.add_argument('--output', type=Path, help='new output directory; existing directories are refused')
    parser.add_argument('--mode', choices=['sandbox', 'reference'], default='sandbox')
    parser.add_argument('--max-service-calls', type=int, default=20)
    parser.add_argument('--max-customer-calls', type=int, default=12)
    parser.add_argument('--max-tool-calls', type=int, default=64)
    parser.add_argument('--service-skill-context', type=Path,
                        help='JSON SkillPromptContext to inject as an exact frozen Service snapshot')
    parser.add_argument('--repeat-authorization-pressure', action='store_true',
                        help='deliberately re-authorize identical writes as a separate stress-test condition')
    args = parser.parse_args(argv)

    if args.replay_execution:
        execution = AgentExecutionV3.model_validate_json(args.replay_execution.read_text(encoding='utf-8'))
        fidelity = evaluate_customer_fidelity(execution) if execution.config.user_scenario is not None else None
        replay = fidelity['replay'] if fidelity is not None else replay_v3(adapter, execution)
        audit = analyze_execution(adapter, execution, replay_result=replay)
        print(_json({'replay': replay, 'customer_fidelity': fidelity,
                     'decision_failure_audit': audit, 'online_calls': 0}), end='')
        return 0

    record, world, certificate, witness = _registration(args.registration.resolve())
    task = certificate.task
    scenario = scenario_from_task(adapter, world, task)
    preflight = customer_interaction_preflight(adapter, world, task, scenario)
    if preflight['status'] == 'fail':
        raise ValueError('Customer interaction preflight failed: ' + json.dumps(preflight, sort_keys=True))
    registration_summary = {
        'protocol': 'eight-domain-certified-task-v1',
        'registration_hash': record.record_hash,
        'world_hash': record.frozen.world_hash,
        'task_hash': task.task_hash,
        'profile_id': task.profile_id,
        'external_schedule': list(task.external_schedule),
        'search_summary': record.search_summary,
        'verified_before_execution': True,
        'customer_interaction_preflight': preflight,
    }
    if not (args.execute_live_service or args.execute_live_customer):
        print(_json({**registration_summary,
            'mode': 'inspect-only; no provider client, credential lookup, or model request created',
            'customer_mode': args.customer_mode, 'service_mode': args.service_mode,
            'user_scenario': scenario.model_dump(mode='json'),
            'next_step': 'explicitly enable API calls for each selected LLM role'}), end='')
        return 0

    if (args.customer_mode == 'scenario-llm') != args.execute_live_customer:
        parser.error('scenario-llm requires --execute-live-customer; deterministic Customer makes no API calls')
    if (args.service_mode == 'llm') != args.execute_live_service:
        parser.error('LLM Service requires --execute-live-service; fixture Service makes no API calls')
    if args.service_mode == 'fixture' and (args.customer_mode != 'scenario-llm' or args.service_skill_context):
        parser.error('Service fixture is only for isolating the scenario LLM Customer, without Service Skills')
    if args.customer_mode == 'scenario-llm' and args.repeat_authorization_pressure:
        parser.error('deterministic pressure rules cannot be applied to LLM Customer decisions')

    if args.max_service_calls < 1 or args.max_service_calls > 200:
        parser.error('--max-service-calls must be between 1 and 200')
    if args.max_tool_calls < 1 or args.max_tool_calls > 2000:
        parser.error('--max-tool-calls must be between 1 and 2000')
    if args.max_customer_calls < 1 or args.max_customer_calls > 200:
        parser.error('--max-customer-calls must be between 1 and 200')
    output = _output_dir(args.output)

    fixture = ControlledRefundService() if args.service_mode == 'fixture' else None
    settings = fixture.settings if fixture is not None else settings_from_env()
    customer_env = customer_environment()
    customer_settings = settings_from_env(customer_env) if args.customer_mode == 'scenario-llm' else None
    contexts = {}
    if args.service_skill_context:
        contexts['service'] = SkillPromptContext.model_validate_json(
            args.service_skill_context.read_text(encoding='utf-8'))
    config = TaskRunConfigV3(
        profile_id=task.profile_id,
        initial_world_hash=world.state_hash,
        mode=args.mode,
        tools=list(adapter.TOOLS),
        budget=Budget(max_customer_turns=min(100, args.max_customer_calls), max_customer_llm_calls=args.max_customer_calls,
            max_service_llm_calls=args.max_service_calls, max_service_tool_calls=args.max_tool_calls,
            max_format_recoveries=1),
        external_schedule=task.external_schedule,
        customer_business_view='own-order-after-sales-progress-v1',
        customer_mode=args.customer_mode, user_scenario=scenario,
        skill_contexts=contexts,
        task=task, certificate=certificate, witness=witness,
    )
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        **registration_summary,
        'protocol': config.protocol,
        'status': 'RUNNING',
        'mode': config.mode,
        'model': settings.model_dump(mode='json'),
        'customer_model': customer_settings.model_dump(mode='json') if customer_settings else None,
        'service_skill_context_hash': contexts.get('service').context_hash if contexts else None,
        'customer_driver': args.customer_mode,
        'service_mode': args.service_mode,
        'purpose': 'customer-simulator-smoke' if fixture is not None else 'service-diagnostic',
        'service_fixture_is_scored': False,
        'scenario_hash': scenario.scenario_hash,
        'repeat_authorization_pressure': args.repeat_authorization_pressure,
        'customer_business_view': config.customer_business_view,
        'maximum_remote_calls': (args.max_service_calls if args.service_mode == 'llm' else 0)
                                + (args.max_customer_calls if customer_settings else 0),
        'maximum_customer_turns': config.budget.max_customer_turns,
        'maximum_tool_calls': args.max_tool_calls,
        'automatic_provider_retries': 0,
        'registration_path': str(args.registration.resolve()),
        'source_record_hash': digest(record.model_dump(mode='json')),
    }
    _write(output / 'manifest.json', manifest)
    _write(output / 'config.json', config.model_dump(mode='json'))
    _write(output / 'scenario.json', scenario.model_dump(mode='json'))
    _write(output / 'customer-interaction-preflight.json', preflight)
    customer = None
    service = None
    try:
        customer = (ScenarioDrivenCustomer(OpenAICompatibleClient(customer_settings, key_from_env(customer_env)), scenario)
                    if customer_settings else FixedCompliantCustomer(adapter.private_state(world, task.profile_id),
                        task.composition.customer_request,
                        follow_up_requests=task.composition.follow_up_requests,
                        required_disclosures=[key for requirement in task.composition.information_requirements
                            if requirement.profile_id == task.profile_id for key in requirement.fact_keys],
                        repeat_authorization_pressure=args.repeat_authorization_pressure))
        service = fixture if fixture is not None else OpenAICompatibleClient(settings, key_from_env())
        execution = run_v3(adapter, world, config, customer, service)
        _write(output / 'execution.json', execution.model_dump(mode='json'))
        fidelity = evaluate_customer_fidelity(execution)
        replay = fidelity['replay']
        decision_audit = analyze_execution(adapter, execution, replay_result=replay)
        _write(output / 'replay.json', replay)
        _write(output / 'customer-fidelity.json', fidelity)
        _write(output / 'decision-failure-audit.json', decision_audit)
        summary = {
            'status': execution.status,
            'oracle': execution.oracle,
            'task_score': execution.task_score,
            'replay': replay,
            'cost': execution.cost,
            'customer_fidelity': fidelity,
            'decision_failure_audit': decision_audit,
            'customer_api_calls': execution.cost['customer_calls'] if customer_settings else 0,
            'customer_local_driver_calls': 0 if customer_settings else execution.cost['customer_calls'],
            'service_remote_calls': execution.cost['service_calls'] if fixture is None else 0,
            'service_fixture_calls': execution.cost['service_calls'] if fixture is not None else 0,
            'tool_calls': execution.cost['tool_calls'],
            'errors': execution.errors,
            'execution_hash': execution.execution_hash,
        }
        _write(output / 'summary.json', summary)
        manifest['status'] = 'REPLAYED' if replay['verified'] else 'REPLAY_FAILED'
        manifest['execution_hash'] = execution.execution_hash
        _write(output / 'manifest.json', manifest)
        print(_json({'output': str(output), **summary}), end='')
        return 0 if replay['verified'] else 2
    except Exception as exc:
        manifest['status'] = 'FAILED'
        manifest['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        _write(output / 'manifest.json', manifest)
        print(_json({'output': str(output), 'status': 'FAILED', 'failure': manifest['failure']}), end='')
        return 2
    finally:
        if service is not None and hasattr(service, 'close'):
            service.close()
        if customer is not None and hasattr(customer, 'close'):
            customer.close()


if __name__ == '__main__':
    raise SystemExit(main())
