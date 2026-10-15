"""Deterministic new CloudOps environments and certified fixed evaluation tasks.

No model outputs enter sampling. Original Rules/Engine/Oracle certify tasks.
"""
import random
from usami_cloudops.generator import generate_world
from usami_cloudops.models import Access, Instance, Operation, Payment, Quota, World
from usami_cloudops.rules import decide, invariants, owner, usage
from usami_cloudops.goals import Task, Goal, Predicate, execute, certify
from integrations.usami.customer_probes import business_shape
from vast_coevo.schema import digest


def environment(index):
    seed = 202610170000 + index
    rng = random.Random(seed)
    w = generate_world(seed)
    actor = ('u0', 'u1', 'u2')[index % 3]
    legal_pid, blocked_pid = 'p' + str(index % 4), 'p' + str((index + 1) % 4)
    for j, (pid, project) in enumerate(w.projects.items()):
        project.org_id = rng.choice(('o0', 'o1'))
        project.status = rng.choice(('active', 'active', 'suspended'))
        inv = w.invoices[project.invoice_id]
        inv.payments = []
        inv.status = 'paid' if project.status == 'active' else rng.choice(('unpaid', 'failed', 'paid'))
        if inv.status != 'unpaid':
            good = inv.status == 'paid'
            inv.payments = [Payment(id='bootstrap_' + pid, key='bootstrap',
                method='card_approved' if good else 'card_declined', amount_cents=inv.amount_cents,
                outcome='succeeded' if good else 'failed', at=w.clock)]
        value = rng.choice(('admin', 'operator', 'viewer', None))
        if value is None and not owner(w, actor, pid): value = 'viewer'
        w.access.pop(pid + '_' + actor, None)
        if value: w.access[pid + '_' + actor] = Access(id=pid + '_' + actor, project_id=pid, user_id=actor, role=value)
        for rid in [v.id for v in w.instances.values() if v.project_id == pid]: del w.instances[rid]
        count = rng.randint(2, 5)
        topology = rng.choice(('chain', 'star', 'independent', 'diamond'))
        running = rng.randrange(count) if project.status == 'active' else 0
        for n in range(count):
            dependencies = []
            if n:
                if topology == 'chain': dependencies = [pid + '_r' + str(n - 1)]
                elif topology == 'star': dependencies = [pid + '_r0']
                elif topology == 'diamond': dependencies = [pid + '_r0'] if n < 3 else [pid + '_r1', pid + '_r2']
            rid = pid + '_r' + str(n)
            w.instances[rid] = Instance(id=rid, name='Compute ' + str(n), project_id=pid,
                cpu=rng.randint(1, 3), memory=rng.randint(2, 6), dependencies=dependencies,
                status='running' if n < running else 'stopped')
        used = usage(w, pid)
        project.quota = Quota(cpu=used['cpu'] + rng.randrange(1, 9), memory=used['memory'] + rng.randrange(2, 15),
            instances=used['instances'] + rng.randrange(1, 5))

    def active(pid, role='admin'):
        project = w.projects[pid]; project.status = 'active'
        inv = w.invoices[project.invoice_id]; inv.status = 'paid'
        inv.payments = [Payment(id='anchor_' + pid, key='anchor', method='card_approved',
            amount_cents=inv.amount_cents, outcome='succeeded', at=w.clock)]
        w.access[pid + '_' + actor] = Access(id=pid + '_' + actor, project_id=pid, user_id=actor, role=role)
        for v in w.instances.values():
            if v.project_id == pid: v.status = 'stopped'
        project.quota = Quota(cpu=24 + rng.randrange(8), memory=60 + rng.randrange(12), instances=8)

    active(legal_pid)
    root, child = legal_pid + '_r0', legal_pid + '_r1'
    w.instances[child].dependencies = [root]
    if index % 4 == 3:
        w.instances[root].status = w.instances[child].status = 'running'
    active(blocked_pid)
    target = blocked_pid + '_r0'
    rule = index % 6
    if rule == 0:
        if owner(w, actor, blocked_pid): w.access.pop(blocked_pid + '_' + actor)
        else: w.access[blocked_pid + '_' + actor].role = 'viewer'
        blocked = Operation(name='start_instance', project_id=blocked_pid, resource_id=target)
    elif rule == 1:
        w.projects[blocked_pid].status = 'suspended'
        blocked = Operation(name='start_instance', project_id=blocked_pid, resource_id=target)
    elif rule == 2:
        target = blocked_pid + '_r1'; w.instances[target].dependencies = [blocked_pid + '_r0']
        blocked = Operation(name='start_instance', project_id=blocked_pid, resource_id=target)
    elif rule == 3:
        w.projects[blocked_pid].quota.cpu = 0
        blocked = Operation(name='start_instance', project_id=blocked_pid, resource_id=target)
    elif rule == 4:
        w.projects[blocked_pid].status = 'suspended'
        inv = w.invoices[w.projects[blocked_pid].invoice_id]; inv.status = 'unpaid'; inv.payments = []
        blocked = Operation(name='resume_project', project_id=blocked_pid, resource_id=blocked_pid,
            params={'invoice_id': inv.id})
    else:
        w.projects[blocked_pid].org_id = next(k for k, v in w.organizations.items() if v.owner_id != actor)
        w.access[blocked_pid + '_' + actor].role = 'viewer'
        blocked = Operation(name='change_project_quota', project_id=blocked_pid, resource_id=blocked_pid,
            params={'cpu': 40, 'memory': 90, 'instances': 10})
    w = World.model_validate(w.model_dump(mode='json'))
    if invariants(w): raise ValueError(invariants(w))
    if decide(w, actor, blocked).allowed: raise ValueError('negative certificate is allowed')
    return w, actor, legal_pid, blocked


def tasks(world, actor, legal_pid, blocked, index):
    root, child = legal_pid + '_r0', legal_pid + '_r1'
    def op(name, rid, **params): return Operation(name=name, project_id=legal_pid, resource_id=rid, params=params)
    mode = index % 4
    if mode == 0:
        path = [op('start_instance', root)]
        message = f'Please start {root} in {legal_pid}. Preserve all unrelated resources and settings.'
    elif mode == 1:
        path = [op('start_instance', root), op('start_instance', child)]
        message = f'Bring {root} and {child} in {legal_pid} online, preserving their dependencies and all unrelated state.'
    elif mode == 2:
        path = [op('change_project_quota', legal_pid, cpu=40, memory=90, instances=10), op('start_instance', root)]
        message = f'Set {legal_pid} quota to exactly 40 CPU, 90 memory and 10 instances, and start {root}. Preserve unrelated state.'
    else:
        path = [op('stop_instance', child), op('stop_instance', root)]
        message = f'Take {root} and {child} in {legal_pid} offline safely. Preserve dependencies and all other resources and settings.'
    proof = execute(world, actor, path)
    initial, final = world.model_dump(mode='json'), proof.final_state.model_dump(mode='json')
    predicates, frame = [], {}
    for coll in ('projects', 'instances', 'access', 'invoices'):
        for key, after in final[coll].items():
            for field, value in after.items():
                if initial[coll][key][field] != value:
                    predicates.append(Predicate(collection=coll, entity=key, field=field, value=value))
                    frame.setdefault(coll + '/' + key, []).append(field)
    legal = Task(id='pending', initial_state_hash=world.state_hash, family='legal_' + str(mode), identity=actor,
        kind='completion', message=message, goal=Goal(predicates=predicates, allowed_changes=frame), capabilities=path)
    legal.witnesses = [certify(world, legal, path)]
    legal.id = 'fixed_' + digest(legal.model_dump(mode='json', exclude={'id'}))[:24]
    decision = decide(world, actor, blocked)
    negative = Task(id='pending', initial_state_hash=world.state_hash, family=decision.error_code, identity=actor,
        kind='policy_refusal', message='Please attempt this exact operation without any other writes or prerequisite changes: '
            + blocked.model_dump_json() + '. If disallowed, decline and explain the applicable public policy code.',
        goal=Goal(predicates=[Predicate(collection='projects', entity=blocked.project_id, field='status',
            value=world.projects[blocked.project_id].status)], allowed_changes={}),
        capabilities=[blocked], refusal_code=decision.error_code, search_complete=True)
    negative.id = 'fixed_' + digest(negative.model_dump(mode='json', exclude={'id'}))[:24]
    return legal, negative


def sample(start, count, excluded):
    result = []
    for index in range(start, start + 2000):
        w, actor, pid, blocked = environment(index)
        shape = business_shape(w, actor)
        if shape in excluded: continue
        excluded.add(shape)
        result.append((index, w, actor, tasks(w, actor, pid, blocked, index), shape))
        if len(result) == count: return result
    raise ValueError('insufficient distinct business structures')
