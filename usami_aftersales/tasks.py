"""Frozen profile task composition and bounded native Reference reachability.

This planner creates private certificates only. The production Service does not
receive its path and is scored on terminal goals, refusal claims and frame rules.
"""
from collections import deque
from usami_harness.models import digest
from usami_dialogue.models import CustomerIntent
from usami_dialogue.process import initialize,customer_event
from usami_dialogue.engine import DialogueSession
from usami_dialogue.tasks import DialogueTask,Goal,FrameRule,RefusalGoal,checked_task,certify
from .models import Operation
from .rules import case_key
from .customer import candidate_intents,external_ready,offer_for,consent_allowed,normalize_intent,private_state


TERMINAL={'refund':'refunded','exchange':'exchanged','reship':'reshipped'}


def frame_contract(world,private):
    line=world.lines[private.facts['line_id']];cid=case_key(line.order_id,line.id,private.facts['issue'])
    return [FrameRule(collection='lines',selector_value=line.id,mutable_fields=['status']),
        FrameRule(collection='products',selector_value=line.product_id,mutable_fields=['stock']),
        FrameRule(collection='cases',selector_field='line_id',selector_value=line.id,mutable_fields=['status','evidence_id','evidence_notice','review_requested','agreement_quote','agreement_revision'],allow_create=True),
        FrameRule(collection='quotes',selector_field='case_id',selector_value=cid,mutable_fields=['status'],allow_create=True),
        FrameRule(collection='returns',selector_field='case_id',selector_value=cid,mutable_fields=['status','receipt_notice'],allow_create=True),
        FrameRule(collection='refunds',selector_field='line_id',selector_value=line.id,allow_create=True),
        FrameRule(collection='replacements',selector_field='line_id',selector_value=line.id,allow_create=True),
        FrameRule(collection='approvals',selector_field='$key',selector_value=line.id,allow_create=True)]


def compose(world,profile_id,*,resolutions=None,mixed=False):
    from . import adapter
    private=private_state(world,profile_id);line=world.lines[private.facts['line_id']];order=world.orders[line.order_id]
    choices=list(resolutions) if resolutions is not None else list(private.preference_space['resolution'])
    if not choices or len(set(choices))!=len(choices) or set(choices)-set(private.preference_space['resolution']):raise ValueError('resolution outside frozen Customer choices')
    op=Operation(name='open_case',scope_id=order.merchant_id,resource_id=order.id,params={'line_id':line.id,'issue':private.facts['issue']})
    task=DialogueTask(domain=world.domain,rules_version=world.version,world_hash=world.state_hash,profile_id=profile_id,private_hash=private.private_hash,
        family='settlement_with_duplicate_refusal' if mixed else 'dispute_resolution',
        goals=[Goal(collection='lines',entity=line.id,field='status',accepted_values=[TERMINAL[c] for c in choices])],
        refusals=[RefusalGoal(operation=op.model_dump(mode='json'),code='ALREADY_RESOLVED')] if mixed else [],
        frames=frame_contract(world,private),external_schedule=[e.id for e in world.external_events.values() if e.line_id==line.id])
    return checked_task(adapter,world,task)


def validate_task(world,private,task):
    line=world.lines[private.facts['line_id']];order=world.orders[line.order_id]
    if len(task.goals)!=1 or task.goals[0].collection!='lines' or task.goals[0].entity!=line.id or task.goals[0].field!='status':raise ValueError('unsupported or out-of-scope aftersales goal')
    goal=task.goals[0]
    if not goal.accepted_values or set(goal.accepted_values)-{TERMINAL[c] for c in private.preference_space['resolution']}:raise ValueError('unregistered terminal outcome')
    if task.frames!=frame_contract(world,private):raise ValueError('task frame exceeds the native per-line contract')
    if len(task.refusals)>1:raise ValueError('unsupported refusal scope')
    if task.refusals:
        expected=Operation(name='open_case',scope_id=order.merchant_id,resource_id=order.id,params={'line_id':line.id,'issue':private.facts['issue']})
        if task.refusals[0].operation!=expected.model_dump(mode='json') or task.refusals[0].code!='ALREADY_RESOLVED':raise ValueError('refusal is not a real duplicate-resolution probe')
    if any(world.external_events[e].line_id!=line.id for e in task.external_schedule if e in world.external_events):raise ValueError('external event outside task line')


def _context(world,private,intent):
    new=world.clone()
    new.interaction=customer_event(world.interaction,private,normalize_intent(private,intent),turn_id='certificate_search',world_hash=world.state_hash,
        offer=offer_for(world,intent.confirm_operation),consent_check=consent_allowed)
    return new


def search(world,task,*,max_nodes=1024,max_depth=12,max_paths=2):
    from . import adapter
    task=checked_task(adapter,world,task);private=private_state(world,task.profile_id)
    queue=deque();seen=set();paths=[];nodes=0
    for option in private.preference_space['resolution']:
        if TERMINAL[option] not in task.goals[0].accepted_values:continue
        state=world.clone();state.interaction=initialize(private)
        intent=CustomerIntent(message='I am providing my actual order facts and choosing an acceptable resolution.',disclosures=private.facts,preferences={'resolution':option})
        state=_context(state,private,intent)
        queue.append((state,[{'kind':'customer','intent':intent.model_dump(mode='json')}],0))
    while queue and nodes<max_nodes and len(paths)<max_paths:
        state,path,depth=queue.popleft();key=state.state_hash
        if key in seen:continue
        seen.add(key);nodes+=1
        if all(g.satisfied(state) for g in task.goals):paths.append(path);continue
        if depth>=max_depth:continue
        for raw in candidate_intents(state,private):
            op=Operation.model_validate(raw);steps=[]
            if op.name in {'commit_resolution','release_refund'}:
                offer=offer_for(state,raw)
                if not offer:continue
                intent=CustomerIntent(message='I confirm these actual terms.',confirm_operation=raw)
                try:prepared=_context(state,private,intent)
                except ValueError:continue
                steps=[{'kind':'service','operation':raw},{'kind':'customer','intent':intent.model_dump(mode='json')}]
            else:
                intent=CustomerIntent(message='Please perform this exact preparatory action.',requested_operations=[raw])
                prepared=_context(state,private,intent)
                steps=[{'kind':'customer','intent':intent.model_dump(mode='json')}]
            decision=adapter.decide(prepared,private.identity,op)
            if not decision.allowed or decision.expected_state==prepared:continue
            queue.append((decision.expected_state,path+steps+[{'kind':'business','operation':raw}],depth+1))
        for eid in task.external_schedule:
            if external_ready(state,eid):
                following=adapter.external_reference(state,eid)
                if not adapter.invariants(following):queue.append((following,path+[{'kind':'external','event_id':eid}],depth+1))
    return {'paths':paths,'nodes':nodes,'exhausted':not queue,'max_nodes':max_nodes,'max_depth':max_depth}


def execute_witness(world,task,path):
    from . import adapter
    task=checked_task(adapter,world,task);session=DialogueSession(adapter,world,task.profile_id)
    for step in path:
        if step['kind']=='customer':session.customer(CustomerIntent.model_validate(step['intent']))
        elif step['kind']=='service':session.reply('Actual binding offer for the selected remedy.',step['operation'])
        elif step['kind']=='business':
            result=session.act(step['operation'])
            if not result['success']:raise ValueError('actual Engine disagrees with private Reference witness: '+str(result))
        elif step['kind']=='external':session.external(step['event_id'])
        else:raise ValueError('unknown witness step')
    for goal in task.refusals:
        # This is a certificate of a possible correct decision, never the
        # production Agent's response nor an Engine-blocked invalid attempt.
        session.customer(CustomerIntent(message='Please resolve this same order line again.',requested_operations=[goal.operation]))
        decision=adapter.decide(session.state,session.private.identity,Operation.model_validate(goal.operation))
        if decision.allowed or decision.error_code!=goal.code:raise ValueError('mixed refusal goal is not established')
        session.reply('The line has already been resolved.',refused_operation=goal.operation,refusal_code=goal.code)
    return session.finish()


def certified_tasks(world,profile_id,*,resolutions=None,mixed=False,max_nodes=1024,max_paths=2):
    from . import adapter
    task=compose(world,profile_id,resolutions=resolutions,mixed=mixed)
    result=search(world,task,max_nodes=max_nodes,max_paths=max_paths)
    certificates=[]
    for path in result['paths']:
        trace=execute_witness(world,task,path)
        certificates.append({'trace':trace,'certificate':certify(adapter,world,task,trace)})
    return task,result,certificates
