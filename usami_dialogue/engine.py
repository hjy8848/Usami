"""Actual persistent interaction, interleaving trusted Customer and native business events."""
import copy
from typing import Optional
from pydantic import Field
from usami_harness.models import Model,Request,digest
from usami_harness.engine import Engine
from .models import CustomerPrivateState,CustomerIntent,DialogueEvent
from .process import initialize,customer_event


class ExecutionTrace(Model):
    protocol:str='business-dialogue-v1'
    domain:str
    rules_version:str
    profile_id:str
    private:CustomerPrivateState
    initial_world:dict
    final_world:dict
    max_operations:int=Field(strict=True,ge=1,le=2000)
    events:list[DialogueEvent]=Field(default_factory=list)
    trace_hash:str=''
    def computed_hash(self):return digest(self.model_dump(mode='json',exclude={'trace_hash'}))


class DialogueSession:
    def __init__(self,adapter,world,profile_id,*,max_operations=64):
        self.adapter=adapter;self.profile_id=profile_id;self.private=adapter.private_state(world,profile_id)
        adapter.validate_private(world,self.private)
        if adapter.invariants(world):raise ValueError('invalid original dialogue world')
        self.initial=world.clone();self._state=world.clone();self.grants=[];self.turn=0;self.operations=0;self.closed=False;self.presented_offer=None
        self.trace=ExecutionTrace(domain=adapter.name,rules_version=world.version,profile_id=profile_id,private=self.private,
            initial_world=world.model_dump(mode='json'),final_world=world.model_dump(mode='json'),max_operations=max_operations)
        before=self.state.state_hash;self._state.interaction=initialize(self.private)
        self._append('customer',{'setup':True,'private_hash':self.private.private_hash},before)
    @property
    def state(self):return self._state.clone()
    def _append(self,kind,payload,before):
        if self.closed:raise ValueError('closed dialogue session')
        row=DialogueEvent(id='dialogue_'+str(len(self.trace.events)),kind=kind,payload=copy.deepcopy(payload),before_hash=before,
            after_hash=self.state.state_hash,previous_hash=self.trace.events[-1].event_hash if self.trace.events else '')
        row.event_hash=row.computed_hash();self.trace.events.append(row);self.trace.final_world=self.state.model_dump(mode='json')
        return row.model_copy(deep=True)
    def customer(self,intent):
        if self.closed:raise ValueError('closed dialogue session')
        intent=CustomerIntent.model_validate(intent.model_dump(mode='json') if isinstance(intent,CustomerIntent) else intent)
        before=self.state;turn='turn_'+str(self.turn+1)
        offer=self.adapter.offer_for(before,intent.confirm_operation)
        if intent.confirm_operation is not None and (offer is None or offer!=self.presented_offer):raise ValueError('Customer cannot confirm an offer that Service has not actually presented')
        normalized=self.adapter.normalize_intent(self.private,intent)
        context=customer_event(before.interaction,self.private,normalized,turn_id=turn,world_hash=before.state_hash,offer=offer,consent_check=self.adapter.consent_allowed)
        requested=list(intent.requested_operations)
        if intent.confirm_operation is not None:requested.append(intent.confirm_operation)
        grants=[];seen=set()
        for raw in requested:
            op=self.adapter.Operation.model_validate(raw)
            if not self.adapter.intent_allowed(before,self.private,op.model_dump(mode='json')):raise ValueError('intention exceeds frozen Customer action/object scope')
            if digest(op) not in seen:grants.append(op.model_dump(mode='json'));seen.add(digest(op))
        self._state.interaction=context;self.grants=grants;self.turn+=1;self.presented_offer=None
        return self._append('customer',{'intent':intent.model_dump(mode='json'),'turn_id':turn,'grants':grants},before.state_hash)
    def act(self,operation,mode='reference'):
        if self.closed:raise ValueError('closed dialogue session')
        if self.operations>=self.trace.max_operations:raise ValueError('dialogue business operation budget exhausted')
        op=self.adapter.Operation.model_validate(operation.model_dump(mode='json') if hasattr(operation,'model_dump') else operation)
        canonical=op.model_dump(mode='json');authorized=op.is_query
        if not op.is_query and canonical in self.grants:self.grants.remove(canonical);authorized=True
        before=self.state;request=Request(id='action_'+str(self.operations),identity=self.private.identity,operation=canonical,granted=authorized)
        engine=Engine(self.adapter,before,1);engine.register(request);event=engine.execute(self.private.identity,op,request.id,mode)
        native=engine.finish();self._state=engine.state;self.operations+=1
        self._append('business',{'trace':native.model_dump(mode='json'),'requests':{request.id:request.model_dump(mode='json')},'turn_id':'turn_'+str(self.turn)},before.state_hash)
        return event.payload['result']
    def reply(self,message,offered_operation=None,*,refused_operation=None,refusal_code=None):
        if not isinstance(message,str):raise ValueError('service reply must be text')
        offer=self.adapter.offer_for(self.state,offered_operation)
        if offered_operation is not None and offer is None:raise ValueError('Service offer has no actual business quote')
        if (refused_operation is None)!=(refusal_code is None) or (refused_operation is not None and offered_operation is not None):raise ValueError('refusal requires one operation/code and cannot also offer')
        refused=self.adapter.Operation.model_validate(refused_operation).model_dump(mode='json') if refused_operation is not None else None
        if refusal_code is not None and (not isinstance(refusal_code,str) or not refusal_code):raise ValueError('refusal code required')
        self.grants=[];self.presented_offer=offer
        return self._append('service',{'message':message,'offered_operation':offered_operation,'offer':offer,'refused_operation':refused,'refusal_code':refusal_code},self.state.state_hash)
    def external(self,event_id):
        before=self.state;after=self.adapter.external_apply(before,event_id)
        if self.adapter.invariants(after):raise ValueError('external simulator produced invalid state')
        self._state=after
        return self._append('external',{'event_id':event_id,'after':after.model_dump(mode='json')},before.state_hash)
    def finish(self):
        if self.closed:raise ValueError('closed dialogue session')
        self.trace.final_world=self.state.model_dump(mode='json');self.trace.trace_hash=self.trace.computed_hash();self.closed=True
        return self.trace.model_copy(deep=True)
