"""Run one deterministic, zero-API v0.2 period through the native Core path.

This is an integration fixture, not a model-quality experiment: a scripted
ResearchModel supplies fixed candidate artifacts, a tiny arithmetic Adapter
provides independently replayable tasks, and the period-end hook is identity
only. No verl process or parameter update is started.
"""
import argparse
from pathlib import Path

from rsi_core.archive import Archive, verify_chain
from rsi_core.budget import Ledger
from rsi_core.evaluation import Evaluator, ServiceEvaluator
from rsi_core.fixtures import ArithmeticFixtureAdapter
from rsi_core.isolation import DockerWorker
from rsi_core.packages import (PackageProvider, PackageRegistration,
                               ServiceTaskProvider, ServiceTaskRegistration,
                               TaskProof)
from rsi_core.period import run_period
from rsi_core.programs import (DesignerSnapshot, ExperienceArtifact,
                               ProgramArtifact, ProgramStore, ServiceSnapshot)
from rsi_core.protocol import (AdaptationPackage, Completion, FrozenModels,
                               Limits, ModelSnapshot, canonical, digest)
from rsi_core.runtime import ResearchHost


IMAGE = "sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf"
DOMAIN = ArithmeticFixtureAdapter.domain_id
BAD_POLICY = "def step(view,state):\n    return {'kind':'ANSWER','value':0,'state':{}}\n"
GOOD_POLICY = "def step(view,state):\n    return {'kind':'ANSWER','value':sum(view['numbers']),'state':{}}\n"

M1_SOURCE = """def next_step(view, state):
    if view['mode'] == 'EVALUATE_ADAPT':
        if not state:
            return {'action': 'STAGE', 'state': {'phase': 1},
                    'kind': 'SERVICE_BUNDLE', 'policy_source': """ + repr(GOOD_POLICY) + """,
                    'experience': view['target']['experience'],
                    'parent_ref': view['target']['ref']}
        return {'action': 'SUBMIT', 'state': state,
                'candidate_ref': view['observations'][-1]['candidate_ref']}
    return {'action': 'SUBMIT', 'state': {}, 'candidate_ref': view['target']['ref']}
"""


def _initial_m_source():
    return """def next_step(view, state):
    mode = view['mode']
    phase = state.get('phase', 0)
    if mode == 'IMPROVE_SERVICE':
        if phase == 0:
            return {'action': 'PROPOSE_CHALLENGE', 'state': {'phase': 1},
                    'proposal': {'numbers': [13, 21]}}
        if phase == 1:
            return {'action': 'RUN_BASELINE', 'state': {'phase': 2},
                    'task_ref': view['capabilities']['challenge_refs'][0]}
        if phase == 2:
            return {'action': 'MODEL', 'state': {'phase': 3},
                    'request': {'purpose': 'service_candidate'},
                    'response_schema': {'type': 'object', 'required': ['policy_source', 'experience'],
                        'properties': {'policy_source': {'type': 'string'},
                                       'experience': {'type': 'object'}},
                        'additionalProperties': False}}
        if phase == 3:
            candidate = view['observations'][-1]['output']
            return {'action': 'STAGE', 'state': {'phase': 4},
                    'kind': 'SERVICE_BUNDLE', 'policy_source': candidate['policy_source'],
                    'experience': candidate['experience'], 'parent_ref': view['target']['ref']}
        if phase == 4:
            candidate_ref = view['observations'][-1]['candidate_ref']
            return {'action': 'PROBE', 'state': {'phase': 5},
                    'candidate_ref': candidate_ref,
                    'probe_ref': view['capabilities']['challenge_refs'][0]}
        return {'action': 'SUBMIT', 'state': {},
                'candidate_ref': view['observations'][-1]['candidate_ref']}
    if mode == 'SELF_EDIT':
        if phase == 0:
            return {'action': 'MODEL', 'state': {'phase': 1},
                    'request': {'purpose': 'designer_self_edit'},
                    'response_schema': {'type': 'object', 'required': ['source'],
                        'properties': {'source': {'type': 'string'}},
                        'additionalProperties': False}}
        if phase == 1:
            return {'action': 'STAGE', 'state': {'phase': 2}, 'kind': 'M',
                    'source': view['observations'][-1]['output']['source'],
                    'parent_ref': view['target']['ref']}
        if phase == 2:
            return {'action': 'PROBE', 'state': {'phase': 3},
                    'candidate_ref': view['observations'][-1]['candidate_ref'],
                    'probe_ref': view['capabilities']['probe_refs'][0]}
        return {'action': 'SUBMIT', 'state': {},
                'candidate_ref': view['observations'][-1]['candidate_ref']}
    return {'action': 'SUBMIT', 'state': {}, 'candidate_ref': view['target']['ref']}
"""


class ScriptedResearchModel:
    """Contract-shaped deterministic responses; token metadata is synthetic."""

    def __init__(self):
        self.calls = []

    def complete(self, snapshot, request, *, max_tokens, seed):
        purpose = request['request']['purpose']
        self.calls.append({'model_ref': snapshot.ref, 'purpose': purpose, 'seed': seed})
        if purpose == 'service_candidate':
            output = {'policy_source': BAD_POLICY, 'experience': {'attempted_change': True}}
        elif purpose == 'designer_self_edit':
            output = {'source': M1_SOURCE}
        else:
            raise ValueError('unregistered fixture request purpose: ' + purpose)
        # These one-token IDs/logprobs only exercise RootTrainingRecord's shape
        # checks. They are not tokenizer output and must never train a model.
        return Completion(output, 1, 1, (seed,), (-0.01,), (seed,))


class ReplayCountingAdapter(ArithmeticFixtureAdapter):
    def __init__(self, tasks, archive):
        super().__init__(tasks, archive)
        self.replay_calls = 0

    def replay(self, run_ref):
        self.replay_calls += 1
        return super().replay(run_ref)


def _add_task(tasks, archive, task_ref, numbers, origin_ref):
    task = {'numbers': list(numbers)}
    tasks[task_ref] = task
    certificate_ref = archive.save({
        'kind': 'arithmetic_fixture_certificate_v1',
        'task_ref': task_ref,
        'origin_ref': origin_ref,
        'task': task,
        'reference_answer': sum(numbers),
    })
    return TaskProof(task_ref, origin_ref, certificate_ref)


def _verify_proof(archive, tasks, domain, proof):
    if domain != DOMAIN:
        return False
    certificate = archive.load(proof.certificate_ref)
    return (certificate['kind'] == 'arithmetic_fixture_certificate_v1'
            and certificate['task_ref'] == proof.task_ref
            and certificate['origin_ref'] == proof.origin_ref
            and certificate['task'] == tasks[proof.task_ref]
            and certificate['reference_answer'] == sum(tasks[proof.task_ref]['numbers']))


def _service_registry(tasks, archive):
    registrations = []
    for purpose, numbers in (
            ('service_probe', (2, 5)),
            ('service_select', (3, 8)),
            ('service_reward', (5, 11))):
        set_id = purpose + '-set'
        task_ref = purpose + '-task'
        proof = _add_task(tasks, archive, task_ref, numbers, purpose + '-source')
        registrations.append(ServiceTaskRegistration(
            set_id, DOMAIN, purpose + '-family', purpose + '-lineage',
            'meta-train', purpose, (proof,), seed=31))
    provider = ServiceTaskProvider(
        registrations, archive,
        lambda domain, proof: _verify_proof(archive, tasks, domain, proof))
    return provider, {purpose: provider.sets(purpose)[0] for purpose in
                      ('service_probe', 'service_select', 'service_reward')}


def _self_edit_context(host, service, tasks):
    registrations = []
    for purpose, numbers in (('C_probe', (7, 9)), ('C_select', (12, 15)),
                             ('C_reward', (17, 23))):
        package_id = 'fixture-' + purpose
        probe_ref, query_ref = purpose + '-probe', purpose + '-query'
        probe_proof = _add_task(tasks, host.archive, probe_ref, numbers,
                                purpose + '-probe-source')
        query_proof = _add_task(tasks, host.archive, query_ref, (numbers[0] + 1, numbers[1] + 2),
                                purpose + '-query-source')
        package = AdaptationPackage(
            package_id, DOMAIN, purpose + '-family', purpose + '-lineage',
            'meta-train', purpose, service.ref, (), (probe_ref,), (query_ref,),
            {'task_interface': 'return the sum of two nonnegative integers'}, seed=43)
        registrations.append(PackageRegistration(package, (), (probe_proof, query_proof)))
    provider = PackageProvider(
        registrations, host.archive,
        lambda domain, proof: _verify_proof(host.archive, tasks, domain, proof))
    sampled = provider.sample_training_context(
        20261024, counts={'C_probe': 1, 'C_select': 1, 'C_reward': 1})
    return {
        'probe_packages': sampled.probe,
        'select_packages': sampled.selection,
        'reward_packages': sampled.reward,
        'seeds': (101, 202),
        'phase_budgets': _self_budgets(),
        'sampling_ref': sampled.archive_ref,
        'public_view': {'fixture': True, 'domain': DOMAIN},
    }


def _service_budgets():
    return {
        'root': {'model_calls': 1, 'model_tokens': 100, 'episodes': 2,
                 'research_steps': 8, 'cpu_seconds': 60},
        'selection': {'episodes': 2, 'cpu_seconds': 120},
        'reward': {'episodes': 2, 'cpu_seconds': 120},
    }


def _self_budgets():
    return {
        'root': {'model_calls': 1, 'model_tokens': 100, 'episodes': 4,
                 'research_steps': 8,
                 'cpu_seconds': 60},
        'selection': {'episodes': 4, 'research_steps': 8, 'cpu_seconds': 120},
        'reward': {'episodes': 4, 'research_steps': 8, 'cpu_seconds': 120},
    }


def smoke(output, image=IMAGE):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    limits = Limits(model_calls=16, model_tokens=2000, episodes=64,
                    research_steps=128, cpu_seconds=1800, wall_seconds=900)
    behavior = ModelSnapshot('scripted-research-fixture', 'fixed-response-v1')
    evaluator_model = ModelSnapshot('scripted-evaluator-fixture', 'unused-v1')
    business = ModelSnapshot('arithmetic-reference-fixture', 'sum-two-integers-v1')
    models = FrozenModels(behavior, evaluator_model, business)
    archive, store = Archive(root / 'archive'), ProgramStore(root / 'programs')
    adapter = ReplayCountingAdapter({}, archive)
    model = ScriptedResearchModel()
    host = ResearchHost(store, archive, DockerWorker(image, limits), model, models,
                        Ledger(limits), max_steps=12, max_output_tokens=1000)

    task_provider, task_sets = _service_registry(adapter.tasks, archive)
    service_evaluator = ServiceEvaluator(host, adapter, task_provider)
    adaptation_evaluator = Evaluator(host, adapter)

    service0 = ServiceSnapshot(business.ref, ProgramArtifact('P', BAD_POLICY),
                               ExperienceArtifact())
    m0 = ProgramArtifact('M', _initial_m_source())
    designer0 = DesignerSnapshot(behavior, m0)
    store.publish_service(service0)
    store.publish_designer(designer0)

    def certify(proposal):
        if (set(proposal) != {'numbers'} or not isinstance(proposal['numbers'], list)
                or len(proposal['numbers']) != 2
                or any(type(number) is not int or number < 0 for number in proposal['numbers'])):
            return {'status': 'INVALID', 'reason_code': 'invalid_fixture_sum_task'}
        numbers = proposal['numbers']
        task_ref = 'challenge-' + digest({'numbers': numbers})[:16]
        if task_ref not in adapter.tasks:
            _add_task(adapter.tasks, archive, task_ref, numbers, 'designer-proposal-v1')
        certificate_ref = archive.save({
            'kind': 'arithmetic_fixture_challenge_certificate_v1',
            'task_ref': task_ref, 'task': adapter.tasks[task_ref],
            'reference_answer': sum(numbers), 'proposal': proposal,
        })
        if sum(adapter.tasks[task_ref]['numbers']) != archive.load(certificate_ref)['reference_answer']:
            raise ValueError('independent arithmetic challenge proof failed')
        return {'status': 'CERTIFIED', 'task_ref': task_ref,
                'certificate_ref': certificate_ref,
                'certification_scope': 'fixture_reference_sum_v1', 'frozen': True}

    def self_context(final_service):
        return _self_edit_context(host, final_service, adapter.tasks)

    hook_calls = []

    def identity_phi_update(groups, grouped_records):
        hook_calls.append({'group_refs': [group.archive_ref for group in groups],
                           'root_types': [group['root_type'] for group in grouped_records],
                           'root_counts': [len(group['records']) for group in grouped_records]})
        if [row['root_type'] for row in grouped_records] != ['r_service', 'r_self']:
            raise AssertionError('period-end hook did not receive separately grouped root types')
        if any(not row['records'] for row in grouped_records):
            raise AssertionError('period-end hook received an empty root group')
        # Deliberately do not optimize φ: this exercises the update boundary,
        # while keeping the run a zero-training integration smoke.
        return behavior

    result = run_period(
        host, service_evaluator, adaptation_evaluator, designer0, service0,
        ({'probe_tasks': task_sets['service_probe'],
          'select_tasks': task_sets['service_select'],
          'reward_tasks': task_sets['service_reward'],
          'seeds': (11, 22), 'phase_budgets': _service_budgets(),
          'certify_challenge': certify,
          'public_view': {'fixture': True, 'domain': DOMAIN}},),
        self_context, phi_update=identity_phi_update)

    service_group = archive.load(result['service_rounds'][0]['group_ref'])
    self_group = archive.load(result['self_edit_group_ref'])
    service_roots = [archive.load(ref) for ref in service_group['root_refs']]
    self_roots = [archive.load(ref) for ref in self_group['root_refs']]
    for run in service_roots + self_roots:
        verify_chain(run['events'])

    if result['status'] != 'COMPLETED':
        raise AssertionError('v0.2 period did not complete')
    if (service_group['status'] != 'USABLE' or len(service_roots) != 2
            or any(run['status'] != 'SUBMITTED' for run in service_roots)):
        raise AssertionError('Service root collection did not complete as a two-root group')
    if result['output_service_ref'] != service0.ref:
        raise AssertionError('zero-gain Service fixture should retain its parent snapshot')
    if (self_group['status'] != 'USABLE' or len(self_roots) != 2
            or any(run['status'] != 'SUBMITTED' for run in self_roots)):
        raise AssertionError('SELF_EDIT root collection did not complete as a two-root group')
    if result['output_designer_ref'] == designer0.ref:
        raise AssertionError('the accepted M child was not published in the Designer snapshot')
    if result['training_hook_calls'] != 1 or result['training_updates'] != 0:
        raise AssertionError('identity update hook must run once without changing model weights')
    if len(model.calls) != 4 or len(hook_calls) != 1:
        raise AssertionError('unexpected scripted-model or period-update call count')

    summary = {
        'kind': 'rsi_v02_period_smoke_v1',
        'fixture_only': True,
        'status': result['status'],
        'period_archive_ref': result['archive_ref'],
        'service': {'context_ref': service_group['context_ref'],
                    'collection_ref': result['service_rounds'][0]['group_ref'],
                    'root_count': len(service_roots), 'root_statuses': [r['status'] for r in service_roots],
                    'selected_ref': service_group['selected_ref'],
                    'selection_decisions': list(service_group['selections'].values()),
                    'parent_retained': result['output_service_ref'] == service0.ref},
        'designer_self_edit': {'group_ref': result['self_edit_group_ref'],
                               'root_count': len(self_roots), 'root_statuses': [r['status'] for r in self_roots],
                               'selection_decisions': list(self_group['selections'].values()),
                               'selected_program_ref': result['selected_m_ref'],
                               'published_designer_ref': result['output_designer_ref']},
        'period_end_hook': {'calls': result['training_hook_calls'],
                            'status': result['training_status'],
                            'training_updates': result['training_updates'],
                            'synthetic_token_records': True},
        'scripted_model_calls': len(model.calls),
        'scripted_model_request_purposes': [call['purpose'] for call in model.calls],
        'native_task_replay_calls': adapter.replay_calls,
        'research_root_event_chains_verified': len(service_roots) + len(self_roots),
        'usage': host.ledger.snapshot(),
        'claim_boundary': 'v0.2 period protocol exercised with deterministic fixtures; no LLM capability or RSI gain claim',
    }
    archive_ref = archive.save(summary)
    summary['summary_archive_ref'] = archive_ref
    (root / 'summary.json').write_text(canonical(summary) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New local run directory; must not already exist')
    parser.add_argument('--image', default=IMAGE,
                        help='Existing pinned Docker image SHA256; worker never pulls it')
    args = parser.parse_args()
    result = smoke(args.output, args.image)
    print(canonical({'output': str(Path(args.output).resolve()),
                     'status': result['status'],
                     'service_roots': result['service']['root_count'],
                     'self_edit_roots': result['designer_self_edit']['root_count'],
                     'designer_child_published': result['designer_self_edit']['published_designer_ref'],
                     'service_parent_retained': result['service']['parent_retained'],
                     'model_calls': result['scripted_model_calls'],
                     'training_updates': result['period_end_hook']['training_updates'],
                     'fixture_only': result['fixture_only']}))


if __name__ == '__main__':
    main()
