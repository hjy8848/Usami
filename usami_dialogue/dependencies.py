"""Executable, trace-bound interaction counterfactuals, never rewards for turn count.

Counterfactual worlds are evaluator-only copies. They cannot enter a session or
World Pool. Only the declared process intervention is permitted, and both native
Reference decisions are recalculated whenever the certificate is verified.
"""
from typing import Literal
from pydantic import Field
from usami_harness.models import Model,digest
from .models import DependencyProof
from .process import initialize,customer_event
from .replay import replay


class DependencyCertificate(Model):
    protocol:Literal['dialogue-dependency-v1']='dialogue-dependency-v1'
    trace_hash:str
    event_id:str
    proof:DependencyProof
    intervention:dict
    control_world:dict
    changed_world:dict
    certificate_hash:str=''
    def computed_hash(self):return digest(self.model_dump(mode='json',exclude={'certificate_hash'}))


def event_states(adapter,trace):
    """Recover actual pre/post states after checking Engine/process/external replay."""
    replay(adapter,trace)
    world=adapter.World.model_validate(trace.initial_world)
    rows=[]
    for event in trace.events:
        before=world.clone();p=event.payload
        if event.kind=='customer':
            if p.get('setup'):world.interaction=initialize(trace.private)
            else:
                from .models import CustomerIntent
                intent=CustomerIntent.model_validate(p['intent'])
                world.interaction=customer_event(world.interaction,trace.private,adapter.normalize_intent(trace.private,intent),
                    turn_id=p['turn_id'],world_hash=world.state_hash,
                    offer=adapter.offer_for(world,intent.confirm_operation),consent_check=adapter.consent_allowed)
        elif event.kind=='business':world=adapter.World.model_validate(p['trace']['final_state'])
        elif event.kind=='external':world=adapter.World.model_validate(p['after'])
        rows.append((event,before,world.clone()))
    return rows


def intervene(adapter,private,control,kind,intervention):
    """A closed list of process interventions; no business state editing allowed."""
    changed=control.clone();ctx=changed.interaction
    if kind=='missing_information':
        if set(intervention)!={'fact'}:raise ValueError('invalid missing-information intervention')
        key=intervention['fact']
        if key not in ctx.known_facts or ctx.known_facts[key]!=private.facts.get(key):raise ValueError('fact was not actually disclosed')
        del ctx.known_facts[key]
    elif kind=='explicit_consent':
        if intervention:raise ValueError('invalid consent intervention')
        ctx.consents=[]
    elif kind=='preference_resolution':
        if set(intervention)!={'preference','value'}:raise ValueError('invalid preference intervention')
        key=intervention['preference'];value=intervention['value']
        if value not in private.preference_space.get(key,[]) or value==ctx.preferences.get(key):raise ValueError('not a genuine permitted alternate preference')
        ctx.preferences[key]=value;ctx.revision+=1;ctx.consents=[];ctx.commitments={}
    else:raise ValueError('unsupported process intervention')
    return changed


def _certificate(adapter,trace,event,control,changed,operation,kind,intervention):
    op=adapter.Operation.model_validate(operation);a=adapter.decide(control,trace.private.identity,op);b=adapter.decide(changed,trace.private.identity,op)
    if a.allowed==b.allowed:return None
    proof=DependencyProof(kind=kind,operation=op.model_dump(mode='json'),control_hash=control.state_hash,changed_hash=changed.state_hash,
        expected_control_code=a.error_code,expected_changed_code=b.error_code,control_allowed=a.allowed,changed_allowed=b.allowed,
        reason='Independent native Reference decisions differ under the recorded, bounded intervention.').checked()
    row=DependencyCertificate(trace_hash=trace.trace_hash,event_id=event.id,proof=proof,intervention=intervention,
        control_world=control.model_dump(mode='json'),changed_world=changed.model_dump(mode='json'))
    row.certificate_hash=row.computed_hash()
    return row


def certify_dependencies(adapter,trace):
    result=[]
    for event,before,after in event_states(adapter,trace):
        if event.kind=='business':
            ops=[e['payload']['operation'] for e in event.payload['trace']['events'] if e['kind']=='operation']
            op=adapter.Operation.model_validate(ops[0])
            if op.is_query or not adapter.decide(before,trace.private.identity,op).allowed:continue
            interventions=[('missing_information',{'fact':key}) for key in before.interaction.known_facts]
            interventions+=[('explicit_consent',{})]
            interventions+=[('preference_resolution',{'preference':k,'value':v}) for k,values in trace.private.preference_space.items() for v in values if v!=before.interaction.preferences.get(k)]
            for kind,intervention in interventions:
                changed=intervene(adapter,trace.private,before,kind,intervention)
                row=_certificate(adapter,trace,event,before,changed,op,kind,intervention)
                if row:result.append(row)
        elif event.kind=='external':
            # The paired states are actual replayed states, not invented outcomes.
            candidates=adapter.candidate_intents(before,trace.private)+adapter.candidate_intents(after,trace.private)
            seen=set()
            for op in candidates:
                if digest(op) in seen:continue
                seen.add(digest(op))
                row=_certificate(adapter,trace,event,before,after,op,'state_update',{'external_event_id':event.payload['event_id']})
                if row:result.append(row)
    return sorted(result,key=lambda row:row.certificate_hash)


def verify_dependency(adapter,trace,certificate):
    c=DependencyCertificate.model_validate(certificate.model_dump(mode='json') if isinstance(certificate,DependencyCertificate) else certificate)
    if c.certificate_hash!=c.computed_hash() or c.trace_hash!=trace.trace_hash:raise ValueError('dependency certificate integrity/source mismatch')
    rows={e.id:(e,b,a) for e,b,a in event_states(adapter,trace)}
    if c.event_id not in rows:raise ValueError('dependency has no source event')
    event,control,actual_after=rows[c.event_id]
    if c.proof.kind=='state_update':
        if event.kind!='external' or c.intervention!={'external_event_id':event.payload['event_id']}:raise ValueError('state update lacks actual external source')
        allowed=adapter.candidate_intents(control,trace.private)+adapter.candidate_intents(actual_after,trace.private)
        if c.proof.operation not in allowed:raise ValueError('external dependency operation outside frozen Customer scope')
        changed=actual_after
    else:
        if event.kind!='business':raise ValueError('process dependency lacks business source')
        operations=[e['payload']['operation'] for e in event.payload['trace']['events'] if e['kind']=='operation']
        if c.proof.operation!=operations[0]:raise ValueError('dependency operation differs from actual source action')
        changed=intervene(adapter,trace.private,control,c.proof.kind,c.intervention)
    if c.control_world!=control.model_dump(mode='json') or c.changed_world!=changed.model_dump(mode='json'):raise ValueError('counterfactual edits exceed the declared intervention')
    rebuilt=_certificate(adapter,trace,event,control,changed,c.proof.operation,c.proof.kind,c.intervention)
    if rebuilt is None or rebuilt!=c:raise ValueError('Reference dependency does not reproduce')
    return True
