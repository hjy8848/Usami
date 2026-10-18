"""LLM-facing task Designer for frozen, native benchmark worlds.

The Designer receives the complete frozen scenario and may compose task goals;
it cannot edit the world or supply Reference outcomes. The existing task compiler
then checks the proposal against native scope, rules, Engine, Oracle and Replay.
"""

import importlib
import json
from typing import Any, Literal

from pydantic import Field
from usami_harness.models import Model, digest
from usami.service.models import ModelSettings, strict_json
from usami.service.runner import completion_message

from .public_policy import catalogue
from .tasks import (CertifiedTask, ConstructionBudget, TaskSelection,
                    compile_task, verify_task)
from .tool_tasks import binding, visible_ids
from .splits import verified_world


DESIGNER_POLICY=(
    'You are the Benchmark Task Designer. You inspect a complete frozen business world and choose a useful, '
    'multi-step Service challenge from entities and rules that actually exist. You may select several related '
    'Customer profiles only when they share the same authenticated identity. You may combine multiple completion '
    'goals, exact business operations that should be refused, declared state frames, information needs, permitted '
    'Customer choices and confirmations. The world is read-only. Never invent or edit entities, operations, rules, '
    'permissions, evidence, external events or expected outcomes. Do not provide Reference answers or refusal codes. '
    'For dialogue domains, submit family open_composition_v1 and a versioned composition object. For tool domains, '
    'provide exact customer-visible operations and a JointGoal. Prefer distinct but coherent business objectives; '
    'do not repeat the same operation merely to inflate task size. The native compiler will reject unsupported proposals.'
)


class DesignerExecution(Model):
    protocol:Literal['frozen-world-task-designer-v1']='frozen-world-task-designer-v1'
    frozen_hash:str
    model:ModelSettings
    request:dict
    response:Any
    selection:TaskSelection
    task:CertifiedTask
    cost:dict=Field(default_factory=dict)
    execution_hash:str=''
    def computed_hash(self):return digest(self.model_dump(mode='json',exclude={'execution_hash'}))


def _dialogue_contract(frozen,world):
    domain=frozen.spec.domain
    adapter=importlib.import_module('usami_'+domain+'.adapter')
    tasks=importlib.import_module('usami_'+domain+'.tasks')
    profiles=[]
    for profile_id in sorted(world.profiles):
        private=adapter.private_state(world,profile_id)
        if domain=='aftersales':frames=tasks.frame_contract(world,private)
        elif domain=='airline':frames=tasks.frames(world,private)
        elif domain=='property':frames=tasks.frames(world,private,inspection=True)
        else:frames=tasks.frames(world,private)
        profiles.append({'profile_id':profile_id,'identity':private.identity,
            'private_facts':private.facts,'preference_space':private.preference_space,
            'initial_preferences':private.initial_preferences,'protected_objects':list(private.protected_objects),
            'confirmable_actions':list(private.confirmable_actions),
            'native_candidate_intents':adapter.candidate_intents(world,private),
            'native_frame_contract':[row.model_dump(mode='json') for row in frames],
            'external_events':[event.model_dump(mode='json') for event in world.external_events.values()
                               if any(value in private.protected_objects for value in event.model_dump(mode='json').values())]})
    return profiles


def designer_view(frozen):
    """Deterministic, full-context read view for an LLM task Designer."""
    frozen=verified_world(frozen)
    domain=frozen.spec.domain;world_module=importlib.import_module('usami_benchmark.tool_tasks')
    body={'protocol':'frozen-world-designer-view-v1','frozen_registration_hash':frozen.registration_hash,
        'world_hash':frozen.world_hash,'domain':domain,'rules_version':frozen.spec.rules_version,
        'track':'A' if domain in {'saas','cloudops','fulfillment','stayops'} else 'B',
        'world':frozen.world,'public_business_policy':catalogue(domain,frozen.spec.rules_version)}
    if body['track']=='B':
        adapter=importlib.import_module('usami_'+domain+'.adapter')
        world=adapter.World.model_validate(frozen.world)
        body['customer_profiles_and_native_task_contracts']=_dialogue_contract(frozen,world)
    else:
        world=world_module.load_world(frozen);native,_=binding(domain,world)
        identities=[]
        for identity in sorted(world.users):
            identities.append({'identity':identity,'visible_entity_ids':sorted(visible_ids(domain,world,identity))})
        body['customer_identities_and_visible_entities']=identities
        body['operation_schema']=native.Operation.model_json_schema()
        # ``goal_adapter`` is a light namespace for some legacy domains, while
        # native adapters expose the same contract as a module. Serialize only
        # that public field allowlist instead of assuming a Pydantic model.
        body['native_goal_fields']=binding(domain,world)[1].GOAL_FIELDS
    return body


def _designer_tools():
    return [{'type':'function','function':{'name':'submit_frozen_world_task',
        'description':'Submit one task selection grounded in the supplied frozen world.',
        'parameters':TaskSelection.model_json_schema()}}]


def _designer_messages(frozen):
    return [{'role':'system','content':DESIGNER_POLICY},
        {'role':'user','content':json.dumps(designer_view(frozen),ensure_ascii=False,sort_keys=True,separators=(',',':'))}]


def _selection_from_response(response):
    message,actions=completion_message(response,set())
    if len(actions)!=1 or actions[0]['function']['name']!='submit_frozen_world_task':
        raise ValueError('Designer must return exactly one submit_frozen_world_task call')
    return TaskSelection.model_validate(strict_json(actions[0]['function']['arguments']))


def design_and_compile(frozen,client,construction_budget=None):
    """Make one model call, compile its exact proposal, and preserve the record.

    This function intentionally performs no retries. It does not accept a model
    authored answer or proof; the separate native compiler must certify it.
    """
    frozen=verified_world(frozen)
    settings=client.settings.model_copy(deep=True)
    request=settings.request(_designer_messages(frozen),_designer_tools())
    response=client.complete(request)
    selection=_selection_from_response(response)
    task=compile_task(frozen,selection,construction_budget or ConstructionBudget())
    usage=response.get('usage',{}) if isinstance(response,dict) else {}
    cost={'calls':1,'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),
          'total_tokens':usage.get('total_tokens'),'usage_complete':all(isinstance(usage.get(k),int) for k in ('prompt_tokens','completion_tokens','total_tokens'))}
    row=DesignerExecution(frozen_hash=frozen.registration_hash,model=settings,request=request,response=response,
        selection=selection,task=task,cost=cost)
    return row.model_copy(update={'execution_hash':row.computed_hash()})


def verify_designer_execution(record):
    row=DesignerExecution.model_validate(record.model_dump(mode='json') if isinstance(record,DesignerExecution) else record)
    if row.execution_hash!=row.computed_hash():raise ValueError('Designer execution integrity differs')
    if row.frozen_hash!=row.task.frozen.registration_hash or row.selection!=row.task.selection:
        raise ValueError('Designer proposal differs from the compiled frozen task')
    expected_request=row.model.request(_designer_messages(row.task.frozen),_designer_tools())
    if row.request!=expected_request:raise ValueError('recorded Designer request differs from the frozen-world task prompt')
    if _selection_from_response(row.response)!=row.selection:
        raise ValueError('compiled task selection differs from the raw Designer model response')
    if verify_task(row.task) is not True:raise ValueError('native task proof failed to replay')
    return {'verified':True,'model_calls':1,'task_hash':row.task.task_hash,'task_replay':True}
