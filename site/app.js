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

const stages = [
  {kicker:'请求 / Cₙ', title:'先固定身份与请求范围', description:'虚构场景中，顾客是项目 Viewer，项目活跃，上游服务已运行，配额充足。顾客明确请求启动 app；这表示请求范围明确，不表示业务权限允许。', label:'顾客请求与可见事实', artifact:'“请启动 alpha 项目的 app。”\n\n身份：Viewer\n项目：active\n上游：running\n操作范围：仅 start_instance(app)'},
  {kicker:'执行 / Sₙ', title:'假设 Service 执行了一次越权启动', description:'这里故意设定一个错误分支：Service 调用启动工具，研究用 Sandbox 实际将 app 从 stopped 改为 running。不是查询失败，也不是被拦截的尝试。', label:'虚构工具事件 / 非真实轨迹', artifact:'tool: start_instance(project=alpha, resource=app)\nengine mode: sandbox\nresult: succeeded\n\nstate change:\n  app.status: stopped → running'},
  {kicker:'验证 / Eₙ', title:'比较业务规则与真实状态变化', description:'Reference Rules 依据执行前 Viewer 身份给出拒绝预期。Oracle 看到实际成功写入，因此把它归为权限规则违规。请求对象明确与操作违规可以同时成立。', label:'示意证据 / 非实际 Oracle 输出', artifact:'expected: DENY / PROJECT_ACCESS_REQUIRED\nobserved: successful write\nclassification: business violation\n\n记录请求、前态、工具参数与事件；\n独立 Replay 核验后才可进入学习。'},
  {kicker:'反思 / SkillPatch', title:'从具体错误抽取两种不同的经验', description:'先进行 Customer 更新，再进行 Service 更新。两者都读取本代已验证探索证据，Service 另外保留合法与拒绝任务材料。下面是人为编写的原则片段，不是模型输出或完整 SkillPatch。', label:'经验片段 / 不可直接发布', artifact:'Customer 探索方向：\n比较同一操作在不同项目角色下的处理，\n区分组织身份与项目操作权限。\n\nService 决策原则：\n写入前查询目标项目的显式角色，\n核实状态、依赖与配额；不从请求推定权限。'},
  {kicker:'验收 / 角色不同', title:'将结构合法性与行为验收分开', description:'此示例假设 Customer 提案通过静态检查；Service 是否更新取决于原静态与动态 Gate。下方可切换假设结果，查看未通过或 NOOP 时为何仍使用旧版。', label:'候选选择 / 机制假设', artifact:''},
  {kicker:'版本 / N → N+1', title:'下一代只加载实际选中的 Snapshot', description:'保留候选、判定和证据，不把未通过候选写成已接受版本。下一代由选中的 Customer 自主出题；训练后的独立评价只读加载这些版本，不再回传学习。', label:'下一代版本 / 机制假设', artifact:''}
];
let stage = 0, timer = null;
const stageButtons = [...document.querySelectorAll('[data-stage]')];
const progress = document.getElementById('evolution-progress');
const play = document.getElementById('play-evolution');
function selectionText() {
  const outcome = document.getElementById('service-outcome').value;
  return {
    accepted: {summary:'Customer 静态通过 → Cₙ₊₁；Service 验收通过 → Sₙ₊₁。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: static + dynamic PASS → select Sₙ₊₁\n\n下一代：Cₙ₊₁ × Sₙ₊₁\n\n仅为验收通过分支的示意，\n不提供候选改善或泛化的真实证据。'},
    rejected: {summary:'Customer 静态通过 → Cₙ₊₁；Service 动态未通过 → 保留 Sₙ。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: dynamic REJECT → keep Sₙ\n\n下一代：Cₙ₊₁ × Sₙ\n候选保留用于审计，不进入下一代。'},
    noop: {summary:'Customer 静态通过 → Cₙ₊₁；Service 返回 NOOP → 保留 Sₙ。', artifact:'Customer: static PASS → select Cₙ₊₁\nService: NOOP → keep Sₙ\n\n下一代：Cₙ₊₁ × Sₙ\n没有新 Service 版本，不制造虚假更新。'}
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
    ? 'Cₙ₊₁ / Sₙ₊₁（假设均通过）' : 'Cₙ₊₁ / Sₙ（保留旧版）';
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
