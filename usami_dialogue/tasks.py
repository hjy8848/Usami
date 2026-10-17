"""Declarative completion/refusal goals with explicit frames, independent of witnesses.

A witness establishes reachability. Evaluation never compares an Agent's path to
that witness: any legal, authorized, frame-preserving solution can succeed.
"""
from typing import Any,Literal,Optional
from pydantic import Field
from usami_harness.models import Model,digest
from usami_harness.goals import field_value
from .dependencies import DependencyCertificate,certify_dependencies,verify_dependency
from .oracle import evaluate
from .replay import replay


class Goal(Model):
    collection:str
    entity:str
    field:str
    accepted_values:list[Any]=Field(min_length=1)
    def satisfied(self,world):
        obj=getattr(world,self.collection).get(self.entity)
        if obj is None:return False
        try:return field_value(obj,self.field) in self.accepted_values
        except ValueError:return False


class FrameRule(Model):
    collection:str
    selector_field:str='id'
    selector_value:Any
    mutable_fields:list[str]=Field(default_factory=list)
    allow_create:bool=False


class RefusalGoal(Model):
    operation:dict
    code:str


class DialogueTask(Model):
    protocol:Literal['certified-dialogue-task-v1']='certified-dialogue-task-v1'
    domain:str
    rules_version:str
    world_hash:str
    profile_id:str
    private_hash:str
    family:str
    goals:list[Goal]=Field(default_factory=list)
    refusals:list[RefusalGoal]=Field(default_factory=list)
    frames:list[FrameRule]=Field(default_factory=list)
    external_schedule:list[str]=Field(default_factory=list)
    require_dependency:bool=True
    task_hash:str=''
    def computed_hash(self):return digest(self.model_dump(mode='json',exclude={'task_hash'}))


class TaskCertificate(Model):
    protocol:Literal['dialogue-task-certificate-v1']='dialogue-task-certificate-v1'
    task:DialogueTask
    witness_trace_hash:str
    oracle:dict
    evaluation:dict
    dependencies:list[DependencyCertificate]
    certificate_hash:str=''
    def computed_hash(self):return digest(self.model_dump(mode='json',exclude={'certificate_hash'}))


def checked_task(adapter,world,task):
    task=DialogueTask.model_validate(task.model_dump(mode='json') if isinstance(task,DialogueTask) else task)
    private=adapter.private_state(world,task.profile_id)
    if (task.domain!=adapter.name or task.rules_version!=world.version or task.world_hash!=world.state_hash or task.private_hash!=private.private_hash):raise ValueError('task source registration differs')
    if not task.goals and not task.refusals:raise ValueError('task needs an objective completion or refusal goal')
    adapter.validate_task(world,private,task)
    if len(set(task.external_schedule))!=len(task.external_schedule) or set(task.external_schedule)-set(world.external_events):raise ValueError('unregistered external schedule')
    value=task.computed_hash()
    if task.task_hash and task.task_hash!=value:raise ValueError('task content hash differs')
    return task.model_copy(update={'task_hash':value},deep=True)


def frame_preserved(initial,final,frames):
    left=initial.model_dump(mode='json');right=final.model_dump(mode='json')
    # These are controlled only by recorded Customer/external events. Their
    # correctness is separately verified by the full process/native Oracle.
    for raw in (left,right):
        raw.pop('interaction',None);raw.pop('clock',None);raw.pop('applied_events',None)
    for rule in frames:
        before=left.get(rule.collection);after=right.get(rule.collection)
        if not isinstance(before,dict) or not isinstance(after,dict):return False
        for key in list(set(before)|set(after)):
            a=before.get(key);b=after.get(key)
            def matches(obj):
                if obj is None:return False
                if rule.selector_field=='$key':return key==rule.selector_value
                try:return field_value(obj,rule.selector_field)==rule.selector_value
                except ValueError:return False
            if not matches(a) and not matches(b):continue
            if a is None:
                if rule.allow_create and matches(b):after.pop(key,None)
            elif b is not None:
                for field in rule.mutable_fields:
                    a.pop(field,None);b.pop(field,None)
    return left==right


def score(adapter,world,task,trace):
    task=checked_task(adapter,world,task)
    source_ok=(trace.initial_world==world.model_dump(mode='json') and trace.profile_id==task.profile_id and trace.private.private_hash==task.private_hash)
    report=evaluate(adapter,trace,initial_world=world,private=adapter.private_state(world,task.profile_id))
    replay_ok=False
    if report['trace_valid']:
        try:replay_ok=replay(adapter,trace)['verified']
        except ValueError:pass
    final=adapter.World.model_validate(trace.final_world)
    completed=[g.satisfied(final) for g in task.goals]
    refused=[any(r['classification']=='correct_refusal' and r['operation']==g.operation and r['reference_code']==g.code for r in report['service_decisions']) for g in task.refusals]
    frame=frame_preserved(world,final,task.frames)
    scheduled=all(e.payload['event_id'] in task.external_schedule for e in trace.events if e.kind=='external')
    success=source_ok and report['status']=='pass' and replay_ok and all(completed) and all(refused) and frame and scheduled
    return {'protocol':'dialogue-task-score-v1','success':bool(success),'source_verified':source_ok,'completion_subgoals':completed,'refusal_subgoals':refused,
        'frame_preserved':frame,'external_schedule_compliant':scheduled,'oracle_status':report['status'],'replay_verified':replay_ok,
        'actual_business_operations':len(report['operations']),'actual_customer_turns':sum(e.kind=='customer' and not e.payload.get('setup') for e in trace.events),
        'metrics':report['metrics']}


def certify(adapter,world,task,trace):
    task=checked_task(adapter,world,task);result=score(adapter,world,task,trace)
    if not result['success']:raise ValueError('witness fails objective task, frame, Oracle or Replay: '+str(result))
    dependencies=certify_dependencies(adapter,trace)
    if task.require_dependency and not dependencies:raise ValueError('claimed dialogue task has no actual information/consent dependency')
    row=TaskCertificate(task=task,witness_trace_hash=trace.trace_hash,oracle=evaluate(adapter,trace),evaluation=result,dependencies=dependencies)
    row.certificate_hash=row.computed_hash();return row


def verify_certificate(adapter,world,certificate,trace):
    c=TaskCertificate.model_validate(certificate.model_dump(mode='json') if isinstance(certificate,TaskCertificate) else certificate)
    if c.certificate_hash!=c.computed_hash() or c.witness_trace_hash!=trace.trace_hash:raise ValueError('task certificate integrity/source differs')
    # Rebuild the entire canonical proof set from replayed source below. Equality
    # checks every intervention/state/decision, without replaying the same full
    # trace once again for each individual certificate.
    if c!=certify(adapter,world,c.task,trace):raise ValueError('task certificate does not reproduce')
    return True
