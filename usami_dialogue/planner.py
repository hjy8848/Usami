"""Bounded private Reference search shared by native dialogue domains.

This is proof construction, never a production Customer or Service policy.
Search failure at a bound is not a claim of task impossibility.
"""
from collections import deque
from .models import CustomerIntent
from .process import initialize,customer_event
from .engine import DialogueSession
from .tasks import checked_task,certify


def _context(adapter,world,private,intent):
    new=world.clone()
    new.interaction=customer_event(world.interaction,private,adapter.normalize_intent(private,intent),turn_id='certificate_search',world_hash=world.state_hash,
        offer=adapter.offer_for(world,intent.confirm_operation),consent_check=adapter.consent_allowed)
    return new


def search(adapter,world,task,preference_options,*,max_nodes=1024,max_depth=12,max_paths=2,refusal_code_options=None):
    task=checked_task(adapter,world,task);private=adapter.private_state(world,task.profile_id)
    from .tasks import frame_preserved
    codes=None
    if refusal_code_options is not None:
        if task.goals or len(task.refusals)!=1 or not refusal_code_options:raise ValueError('code discovery requires one pure native refusal probe')
        codes=set(refusal_code_options)
        for code in codes:
            candidate=task.model_copy(deep=True);candidate.refusals[0].code=code;candidate.task_hash=''
            checked_task(adapter,world,candidate)
    queue=deque();seen=set();paths=[];nodes=0;matched=[]
    for preferences in preference_options:
        state=world.clone();state.interaction=initialize(private)
        intent=CustomerIntent(message='I am providing my actual facts and choosing an acceptable option.',disclosures=private.facts,preferences=preferences)
        state=_context(adapter,state,private,intent)
        queue.append((state,[{'kind':'customer','intent':intent.model_dump(mode='json')}],0))
    while queue and nodes<max_nodes and len(paths)<max_paths:
        state,path,depth=queue.popleft();key=state.state_hash
        if key in seen:continue
        seen.add(key);nodes+=1
        decisions=[adapter.decide(state,private.identity,adapter.Operation.model_validate(g.operation)) for g in task.refusals]
        refusal_ready=all(not d.allowed and d.error_code in (codes if codes is not None else {g.code}) for g,d in zip(task.refusals,decisions))
        if all(g.satisfied(state) for g in task.goals) and refusal_ready and (codes is None or frame_preserved(world,state,task.frames)):
            paths.append(path);matched.append([d.error_code for d in decisions]);continue
        if depth>=max_depth:continue
        for raw in adapter.candidate_intents(state,private):
            op=adapter.Operation.model_validate(raw)
            offer=adapter.offer_for(state,raw)
            if offer is not None:
                intent=CustomerIntent(message='I confirm these actual terms.',confirm_operation=raw)
                try:prepared=_context(adapter,state,private,intent)
                except ValueError:continue
                steps=[{'kind':'service','operation':raw},{'kind':'customer','intent':intent.model_dump(mode='json')}]
            else:
                intent=CustomerIntent(message='Please perform this exact preparatory action.',requested_operations=[raw])
                prepared=_context(adapter,state,private,intent)
                steps=[{'kind':'customer','intent':intent.model_dump(mode='json')}]
            decision=adapter.decide(prepared,private.identity,op)
            if not decision.allowed or decision.expected_state==prepared:continue
            if codes is None or frame_preserved(world,decision.expected_state,task.frames):queue.append((decision.expected_state,path+steps+[{'kind':'business','operation':raw}],depth+1))
        for eid in task.external_schedule:
            if adapter.external_ready(state,eid):
                following=adapter.external_reference(state,eid)
                if not adapter.invariants(following) and (codes is None or frame_preserved(world,following,task.frames)):queue.append((following,path+[{'kind':'external','event_id':eid}],depth+1))
    result={'paths':paths,'nodes':nodes,'exhausted':not queue,'max_nodes':max_nodes,'max_depth':max_depth}
    if codes is not None:result['matched_refusal_codes']=matched
    return result


def execute_witness(adapter,world,task,path):
    task=checked_task(adapter,world,task);session=DialogueSession(adapter,world,task.profile_id)
    for step in path:
        if step['kind']=='customer':session.customer(CustomerIntent.model_validate(step['intent']))
        elif step['kind']=='service':session.reply('Actual binding offer for the selected option.',step['operation'])
        elif step['kind']=='business':
            result=session.act(step['operation'])
            if not result['success']:raise ValueError('actual Engine disagrees with private Reference witness: '+str(result))
        elif step['kind']=='external':session.external(step['event_id'])
        else:raise ValueError('unknown witness step')
    for goal in task.refusals:
        session.customer(CustomerIntent(message='Please perform this exact requested action.',requested_operations=[goal.operation]))
        decision=adapter.decide(session.state,session.private.identity,adapter.Operation.model_validate(goal.operation))
        if decision.allowed or decision.error_code!=goal.code:raise ValueError('mixed refusal goal is not established')
        session.reply('This requested action is disallowed for the stated business reason.',refused_operation=goal.operation,refusal_code=goal.code)
    return session.finish()


def certified_paths(adapter,world,task,search_result):
    rows=[]
    for path in search_result['paths']:
        trace=execute_witness(adapter,world,task,path)
        rows.append({'trace':trace,'certificate':certify(adapter,world,task,trace)})
    return rows
