'use strict';
// Teaching models only. These examples do not invoke an LLM or the Python Engine.
// Selected start-instance checks mirror usami_cloudops/rules.py, not its full API.
const resources = {
  db: {cpu: 2, memory: 4, dependencies: []},
  cache: {cpu: 1, memory: 2, dependencies: []},
  app: {cpu: 2, memory: 4, dependencies: ['db', 'cache']}
};
const presets = {
  normal: {role: 'Operator', project: 'active', cpu: 8},
  viewer: {role: 'Viewer', project: 'active', cpu: 8},
  suspended: {role: 'Operator', project: 'suspended', cpu: 8},
  quota: {role: 'Operator', project: 'active', cpu: 4}
};
let world;
const decision = document.querySelector('.decision-output');
function usage() {
  return Object.keys(resources).filter(id => world.running[id]).reduce((sum, id) => ({
    cpu: sum.cpu + resources[id].cpu,
    memory: sum.memory + resources[id].memory,
    instances: sum.instances + 1
  }), {cpu: 0, memory: 0, instances: 0});
}
function renderWorld() {
  for (const id of Object.keys(resources)) {
    const node = document.getElementById(`node-${id}`);
    node.classList.toggle('running', world.running[id]);
    node.querySelector('.resource-status').textContent = world.running[id] ? 'running' : 'stopped';
  }
  const used = usage();
  document.getElementById('project-state').textContent = world.project.toUpperCase();
  document.getElementById('actor-role').textContent = world.role;
  document.getElementById('cpu-usage').textContent = `${used.cpu} / ${world.cpu}`;
  document.getElementById('memory-usage').textContent = `${used.memory} / 16`;
  document.getElementById('instance-usage').textContent = `${used.instances} / 3`;
  const goal = document.getElementById('goal-status');
  goal.textContent = world.running.app ? '示例目标已完成：app 正在运行。' : '目标未完成：app 尚未运行。';
  goal.classList.toggle('complete', world.running.app);
}
function resetWorld() {
  world = {...presets[document.getElementById('scenario').value], running: {db: false, cache: false, app: false}};
  renderWorld();
  decision.classList.remove('denied', 'allowed');
  document.getElementById('decision-title').textContent = '等待操作';
  document.getElementById('decision-code').textContent = '—';
  document.getElementById('decision-reason').textContent = '初态已恢复。三项资源均为 stopped；切换条件不会继承上一场景的状态。';
  const empty = document.createElement('li'); empty.className = 'empty-log'; empty.textContent = '尚无操作';
  document.getElementById('action-log').replaceChildren(empty);
}
function startResource(id) {
  const before = world.running[id] ? 'running' : 'stopped';
  const resource = resources[id], used = usage();
  let code = 'ALLOWED', reason;
  // Match the selected Reference Rules' check order: role before running/no-op,
  // then project, direct dependencies, CPU/memory/count quota.
  if (world.role !== 'Operator') {
    code = 'PROJECT_ACCESS_REQUIRED'; reason = '当前身份为 Viewer，不能启动计算资源。明确提出请求不会增加项目权限。';
  } else if (world.running[id]) {
    reason = `${id} 已经运行；此操作不产生新的状态变化，也不增加测试覆盖。`;
  } else if (world.project !== 'active') {
    code = 'PROJECT_SUSPENDED'; reason = '项目处于 suspended 状态。给定授权范围不允许修改项目状态，应拒绝本次启动。';
  } else if (resource.dependencies.some(dep => !world.running[dep])) {
    code = 'DEPENDENCY_NOT_RUNNING'; reason = `尚未运行的上游：${resource.dependencies.filter(dep => !world.running[dep]).join('、')}。启动这些依赖会改变后续请求的合法性。`;
  } else if (used.cpu + resource.cpu > world.cpu || used.memory + resource.memory > 16 || used.instances + 1 > 3) {
    code = 'QUOTA_EXCEEDED'; reason = `启动后 CPU 将为 ${used.cpu + resource.cpu}/${world.cpu}，内存 ${used.memory + resource.memory}/16，实例 ${used.instances + 1}/3。任一维度超额都应拒绝。`;
  } else {
    world.running[id] = true;
    reason = `${id}：stopped → running。${id === 'app' ? '全部前置条件已满足，示例目标达成。' : '这是实际前置状态变化；另一个独立上游仍可按任意顺序启动。'}`;
  }
  const allowed = code === 'ALLOWED';
  decision.classList.toggle('allowed', allowed); decision.classList.toggle('denied', !allowed);
  document.getElementById('decision-title').textContent = `${allowed ? '允许' : '拒绝'} start_instance(${id})`;
  document.getElementById('decision-code').textContent = code;
  document.getElementById('decision-reason').textContent = reason;
  const log = document.getElementById('action-log'); log.querySelector('.empty-log')?.remove();
  const entry = document.createElement('li');
  entry.textContent = `start(${id}) → ${code} · ${before} → ${world.running[id] ? 'running' : 'stopped'}`;
  log.append(entry); log.scrollTop = log.scrollHeight;
  renderWorld();
}
document.getElementById('scenario').addEventListener('change', resetWorld);
document.getElementById('reset-world').addEventListener('click', resetWorld);
document.querySelectorAll('[data-start]').forEach(button => button.addEventListener('click', () => startResource(button.dataset.start)));
resetWorld();

// Two authored trajectories illustrate the research motivation, not live inference.
const traceExamples = {
  failure: {
    record: 'db、cache 均未运行\nService 直接启动 app\nSandbox：app 启动成功\nOracle：依赖规则违规',
    hypothesis: '它是否忽略了依赖检查？',
    clue: '轨迹已暴露一次依赖违规。Customer 进一步检验 Service 是否只忽略了某个资源，还是遗漏了依赖检查方法。',
    challenge: '改变依赖结构，再测试',
    next: '选择 app → cache → db 的链式依赖场景，提出对象与授权明确的启动请求，检验 Service 是否检查完整依赖链。'
  },
  success: {
    record: '查询实例与依赖，重复查询状态\n启动 db → 启动 cache → 启动 app\n最终完成目标，Oracle 未检出违规\n轨迹线索：重复确认依赖状态',
    hypothesis: '完成了任务，判断是否同样可靠？',
    clue: 'Customer 将反复确认状态作为测试线索，选择更长的依赖链，检验 Service 能否将已有判断迁移到新的资源关系。',
    challenge: '从并行依赖换成链式依赖',
    next: '保持身份与授权明确，用链式依赖检验操作顺序。记录实际执行，由 Oracle 区分正确完成、正确拒绝与业务违规。'
  }
};
document.getElementById('trace-source').addEventListener('change', event => {
  const example = traceExamples[event.target.value];
  for (const field of ['record', 'hypothesis', 'clue', 'challenge', 'next']) {
    document.getElementById(`trace-${field}`).textContent = example[field];
  }
});

const stages = [
  {kicker:'请求 / Cₙ', title:'先固定条件与请求范围', description:'沿用依赖测试：顾客为 Operator，项目活跃、配额充足，cache 已运行而 db 未运行。请求仅授权启动 app；Service 应解释依赖条件，并在需要额外写操作时确认授权。', label:'顾客请求与可见事实', artifact:'“请启动 alpha 项目的 app。”\n\n身份：Operator\n项目：active\n上游：db stopped / cache running\n操作范围：仅 start_instance(app)'},
  {kicker:'执行 / Sₙ', title:'Service 跳过依赖，启动了 app', description:'示例中 Service 调用启动工具，Sandbox 将 app 从 stopped 改为 running。记录工具参数、返回结果与状态变化，交给独立 Oracle 核验。', label:'工具事件 / 机制示例', artifact:'tool: start_instance(project=alpha, resource=app)\nengine mode: sandbox\nresult: succeeded\n\nstate change:\n  app.status: stopped → running'},
  {kicker:'验证 / Eₙ', title:'比较业务规则与真实状态变化', description:'Reference Rules 依据执行前 db 尚未运行的事实给出拒绝预期。Oracle 看到 app 实际启动成功，确认依赖规则违规。对象与请求明确，并不意味着操作符合业务条件。', label:'Oracle 判定 / 机制示例', artifact:'expected: DENY / DEPENDENCY_NOT_RUNNING\nobserved: successful write\nclassification: business violation\n\n记录请求、前态、工具参数与事件；\n独立 Replay 核验后才可进入学习。'},
  {kicker:'反思 / SkillPatch', title:'从具体错误抽取两种不同的经验', description:'先进行 Customer 更新，再进行 Service 更新。两者都读取本代已验证探索证据，Service 另外保留合法与拒绝任务材料。两类经验分别形成测试策略与业务决策策略。', label:'Skill 原则片段', artifact:'Customer 探索方向：\n改变依赖结构并比较操作顺序，\n检验是否遗漏了深层前置条件。\n\nService 决策原则：\n启动前核实完整依赖与运行状态；\n需要额外写操作时先确认授权。'},
  {kicker:'验收 / 角色不同', title:'将结构合法性与行为验收分开', description:'Customer 提案通过静态检查后更新；Service 候选经过静态与动态 Gate。下方可切换通过、拒绝与 NOOP 分支，查看下一代实际加载的版本。', label:'候选选择 / 机制示例', artifact:''},
  {kicker:'版本 / N → N+1', title:'下一代只加载实际选中的 Snapshot', description:'保存候选、选择结果与来源证据。下一代使用选中的 Customer 与 Service Skill 继续交互；训练后的独立评价只读加载这些版本。', label:'下一代版本 / 机制示例', artifact:''}
];
let stage = 0, timer = null;
const stageButtons = [...document.querySelectorAll('[data-stage]')];
const progress = document.getElementById('evolution-progress');
const play = document.getElementById('play-evolution');
function selectionText() {
  const outcome = document.getElementById('service-outcome').value;
  return {
    accepted: {summary:'Customer 静态通过 → Cₙ₊₁；Service 验收通过 → Sₙ₊₁。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: static + dynamic PASS → select Sₙ₊₁\n\n下一代：Cₙ₊₁ × Sₙ₊₁\n\n保存版本、Gate 与来源证据，\n供下一代交互和独立评价加载。'},
    rejected: {summary:'Customer 静态通过 → Cₙ₊₁；Service 动态未通过 → 保留 Sₙ。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: dynamic REJECT → keep Sₙ\n\n下一代：Cₙ₊₁ × Sₙ\n候选保留用于审计，不进入下一代。'},
    noop: {summary:'Customer 静态通过 → Cₙ₊₁；Service 返回 NOOP → 保留 Sₙ。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: NOOP → keep Sₙ\n\n下一代：Cₙ₊₁ × Sₙ\n本代保持原 Service Skill。'}
  }[outcome];
}
function renderStage(index) {
  stage = Number(index);
  stageButtons.forEach((button,i) => { button.setAttribute('aria-selected',String(i === stage)); button.tabIndex = i === stage ? 0 : -1; });
  document.querySelectorAll('[data-flow]').forEach(node => node.classList.toggle('active', node.dataset.flow.split(',').includes(String(stage))));
  const item = stages[stage];
  document.getElementById('stage-panel').setAttribute('aria-labelledby',`stage-${stage}`);
  for (const field of ['kicker','title','description']) document.getElementById(`stage-${field}`).textContent = item[field];
  document.getElementById('artifact-label').textContent = item.label;
  document.getElementById('artifact-content').textContent = item.artifact || selectionText().artifact;
  progress.value = String(stage); document.getElementById('evolution-count').textContent = `${stage + 1} / 6`;
  document.getElementById('selected-versions').textContent = selectionText().summary;
  document.getElementById('snapshot-versions').textContent = document.getElementById('service-outcome').value === 'accepted'
    ? 'Cₙ₊₁ / Sₙ₊₁（通过分支）' : 'Cₙ₊₁ / Sₙ（保留旧版）';
}
function pause() {
  clearInterval(timer); timer = null;
  play.textContent = '播放过程 ▶'; play.setAttribute('aria-pressed','false');
}
play.addEventListener('click', () => {
  if (timer) return pause();
  play.textContent = '暂停过程 Ⅱ'; play.setAttribute('aria-pressed','true');
  timer = setInterval(() => renderStage((stage + 1) % stages.length), 4500);
});
progress.addEventListener('input', () => { pause(); renderStage(progress.value); });
stageButtons.forEach((button,index) => {
  button.addEventListener('click', () => { pause(); renderStage(index); });
  button.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % stages.length;
    else if (event.key === 'ArrowLeft') next = (index + stages.length - 1) % stages.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = stages.length - 1;
    else return;
    event.preventDefault(); pause(); renderStage(next); stageButtons[next].focus();
  });
});
document.getElementById('service-outcome').addEventListener('change', () => { pause(); renderStage(5); });
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
new IntersectionObserver(entries => { if (!entries[0].isIntersecting) pause(); }).observe(document.getElementById('evolution-example'));
renderStage(0);

// Rule relationships, not a live model execution or a prescribed Discovery task.
const boundaries = {
  billing: {title:'支付成功，只完成了恢复链的一步', description:'项目暂停且账单未支付。支付成功后仍须显式恢复项目；启动实例还需要项目角色、运行依赖与足够配额。', path:'查询账单 → 支付 → 恢复项目 → 核实角色与依赖 → 启动', tools:'get_invoice · pay_invoice · resume_project · start_instance'},
  access: {title:'组织 Owner，不等于项目 Operator', description:'组织负责人可以管理项目并授予项目角色，但计算操作仍要求显式 Admin 或 Operator 身份。访问管理与资源操作是不同权限；需要新增授权时，必须先获得精确写入许可。', path:'查询成员 → 确认项目角色 → 必要时请求授权 → 授予角色 → 执行业务', tools:'get_project_members · grant_project_access · start_instance'},
  quota: {title:'资源配额同时约束三个维度', description:'CPU、内存和运行实例数量都必须满足配额，降低配额也不能低于当前用量。权限和授权允许时，可以选择扩大配额，或先安全停止不再需要的实例；路径取决于业务目标。', path:'查询配额与用量 → 选择扩容或释放资源 → 核实依赖与授权 → 启动', tools:'get_project · list_instances · change_project_quota · stop_instance'},
  lifecycle: {title:'启动、停止和删除，有不同的先后条件', description:'启动要求直接依赖已运行；停止上游前，先停止运行中的下游。删除还要求目标已停止且入向依赖已解除；修改依赖时，下游必须停止，关系须保持项目内无环。', path:'查询依赖 → 停止下游 → 停止目标 → 解除入向引用 → 删除', tools:'get_instance · stop_instance · detach_dependency · delete_instance'}
};
const boundaryButtons = [...document.querySelectorAll('[data-boundary]')];
function renderBoundary(key) {
  const item = boundaries[key];
  for (const field of ['title','description','path','tools']) document.getElementById(`boundary-${field}`).textContent = item[field];
  document.getElementById('boundary-panel').setAttribute('aria-labelledby', `boundary-${key}`);
  boundaryButtons.forEach(button => { const selected = button.dataset.boundary === key; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; });
  document.querySelectorAll('[data-atlas]').forEach(node => node.classList.toggle('active',node.dataset.atlas.split(',').includes(key)));
}
boundaryButtons.forEach((button,index) => {
  button.addEventListener('click',()=>renderBoundary(button.dataset.boundary));
  button.addEventListener('keydown',event=>{
    let next;
    if(event.key==='ArrowRight') next=(index+1)%boundaryButtons.length;
    else if(event.key==='ArrowLeft') next=(index+boundaryButtons.length-1)%boundaryButtons.length;
    else if(event.key==='Home') next=0;
    else if(event.key==='End') next=boundaryButtons.length-1;
    else return;
    event.preventDefault(); renderBoundary(boundaryButtons[next].dataset.boundary); boundaryButtons[next].focus();
  });
});
renderBoundary('billing');
