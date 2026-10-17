'use strict';
// Browser teaching model, independent of the Python Engine and official runs.
const resources = {db:{cpu:2,memory:4},cache:{cpu:1,memory:2},app:{cpu:2,memory:4}};
const dependencies = {
  parallel:{db:[],cache:[],app:['db','cache']},
  chain:{db:[],cache:['db'],app:['cache']}
};
function freezeDeep(value) {
  for(const nested of Object.values(value)) if(nested && typeof nested==='object') freezeDeep(nested);
  return Object.freeze(value);
}
const teachingWorld = freezeDeep({
  id:'WORLD-01',
  identities:{
    lin:{name:'林',roles:{alpha:'Operator',beta:'Viewer',gamma:'Operator'}},
    chen:{name:'陈',roles:{alpha:'Viewer',beta:'Operator',gamma:'Viewer'}}
  },
  projects:{
    alpha:{status:'active',invoice:'paid',topology:'parallel',cpu:8,memory:16,limit:3,running:{db:false,cache:false,app:false}},
    beta:{status:'active',invoice:'paid',topology:'chain',cpu:4,memory:8,limit:2,running:{db:true,cache:false,app:false}},
    gamma:{status:'suspended',invoice:'unpaid',topology:'parallel',cpu:8,memory:16,limit:3,running:{db:false,cache:false,app:false}}
  }
});
let world=null, frozenTask=null;
const decision=document.querySelector('.decision-output');
function clone(value){return JSON.parse(JSON.stringify(value));}
function selectedTargets(){return [...document.querySelectorAll('[data-target]')].filter(input=>input.checked).map(input=>input.dataset.target);}
function selection(){
  const identity=document.getElementById('task-identity').value;
  const project_id=document.getElementById('frozen-scene').value;
  const actor=teachingWorld.identities[identity], project=teachingWorld.projects[project_id];
  return {...clone(project),id:teachingWorld.id,project_id,project:project.status,identity,actor:actor.name,role:actor.roles[project_id]};
}
function usage(){return Object.keys(resources).filter(id=>world.running[id]).reduce((sum,id)=>({cpu:sum.cpu+resources[id].cpu,memory:sum.memory+resources[id].memory,instances:sum.instances+1}),{cpu:0,memory:0,instances:0});}
function validateFrozenWorld(scene){
  const errors=[];
  if(scene.project==='active'&&scene.invoice!=='paid')errors.push('活跃项目账单未支付');
  if(scene.project==='suspended'&&Object.values(scene.running).some(Boolean))errors.push('暂停项目包含运行资源');
  for(const id of Object.keys(resources))if(scene.running[id]&&dependencies[scene.topology][id].some(dep=>!scene.running[dep]))errors.push('运行资源的上游未运行');
  const used=Object.keys(resources).filter(id=>scene.running[id]).reduce((sum,id)=>({cpu:sum.cpu+resources[id].cpu,memory:sum.memory+resources[id].memory,instances:sum.instances+1}),{cpu:0,memory:0,instances:0});
  if(used.cpu>scene.cpu||used.memory>scene.memory||used.instances>scene.limit)errors.push('初始用量超过配额');
  return errors;
}
function requestText(targets,scene){return targets.length?`请让 ${scene.project_id} 项目的 ${targets.join('、')} 运行。`:'请选择至少一个目标资源。';}
function applyDependencies(){
  const chain=world.topology==='chain';
  document.getElementById('edge-db').setAttribute('d',chain?'M225 71H275':'M145 105V138Q145 149 157 149H239Q250 149 250 161V183');
  document.getElementById('edge-cache').setAttribute('d','M355 105V138Q355 149 343 149H261Q250 149 250 161V183');
  document.getElementById('dependency-note').textContent=chain?'db → cache → app，按链式顺序启动':'db 与 cache 均需运行，之后启动 app';
  document.getElementById('task-map-description').textContent=chain?'cache 依赖 db，app 依赖 cache。':'app 依赖 db 和 cache，两项上游互相独立。';
}
function renderWorld(){
  applyDependencies();
  for(const id of Object.keys(resources)){
    const node=document.getElementById(`node-${id}`);node.classList.toggle('running',world.running[id]);
    node.querySelector('.resource-status').textContent=world.running[id]?'running':'stopped';
  }
  const used=usage();
  document.getElementById('project-state').textContent=world.project.toUpperCase();
  document.getElementById('world-instance').textContent=`${world.id} / ${world.project_id}`;
  document.getElementById('actor-role').textContent=`${world.actor} / ${world.role}`;
  document.getElementById('cpu-usage').textContent=`${used.cpu} / ${world.cpu}`;
  document.getElementById('memory-usage').textContent=`${used.memory} / ${world.memory}`;
  document.getElementById('instance-usage').textContent=`${used.instances} / ${world.limit}`;
  const complete=Boolean(frozenTask&&frozenTask.targets.every(id=>world.running[id]));
  const goal=document.getElementById('goal-status');goal.textContent=!frozenTask?'任务尚未开始':complete?'所选目标已达成':'所选目标尚未达成';goal.classList.toggle('complete',complete);
}
function clearExecution(){
  decision.classList.remove('denied','allowed');
  document.getElementById('decision-title').textContent='等待操作';
  document.getElementById('decision-code').textContent='—';
  document.getElementById('decision-reason').textContent='每个动作都依据当前权限、项目状态、依赖和配额判定。';
  const item=document.createElement('li');item.className='empty-log';item.textContent='尚无操作';document.getElementById('action-log').replaceChildren(item);
}
function renderFrozenSummary(){
  world=selection();frozenTask=null;
  const targets=selectedTargets(), used=usage();
  const running=Object.keys(resources).filter(id=>world.running[id]);
  document.getElementById('draft-status').textContent=`只读 / ${world.id}`;
  document.getElementById('scene-summary').textContent=`${world.actor}在 ${world.project_id} 中是 ${world.role}；项目${world.project==='active'?'活跃':'暂停'}，${world.invoice==='paid'?'账单已付':'账单未付'}。${running.length?running.join('、')+' 运行，其余停止':'三项资源均停止'}。CPU ${used.cpu}/${world.cpu}，内存 ${used.memory}/${world.memory}，实例 ${used.instances}/${world.limit}。`;
  document.getElementById('exam-request').textContent=requestText(targets,world);
  document.getElementById('exam-snapshot').textContent=JSON.stringify({example_only:true,task:{world_id:world.id,identity:world.identity,project_id:world.project_id,targets,operation_scope:targets.map(resource_id=>({name:'start_instance',resource_id}))},readonly_world:teachingWorld},null,2);
  const errors=validateFrozenWorld(world), status=document.getElementById('exam-validation');
  status.textContent=errors.length?`示例初态错误：${errors.join('；')}`:targets.length?'所选对象均已存在；开始后在独立副本中尝试执行。':'请至少选择一个目标资源。';
  status.classList.toggle('invalid',errors.length>0||targets.length===0);
  document.getElementById('freeze-exam').disabled=errors.length>0||targets.length===0;
  document.querySelectorAll('[data-start], #reset-world').forEach(button=>button.disabled=true);
  renderWorld();clearExecution();
}
function startEpisode(){
  const initial=selection(), targets=selectedTargets();
  if(!targets.length||validateFrozenWorld(initial).length)return;
  frozenTask={initial:clone(initial),targets:[...targets],allowed:[...targets]};world=clone(initial);
  document.getElementById('draft-status').textContent=`执行副本 / ${world.project_id}`;
  document.getElementById('exam-validation').textContent='任务已登记。世界池不变，下面的操作只影响本次执行。';
  document.querySelectorAll('[data-start], #reset-world').forEach(button=>button.disabled=false);
  renderWorld();clearExecution();
}
function resetWorld(){if(!frozenTask)return;world=clone(frozenTask.initial);renderWorld();clearExecution();}
function startResource(id){
  if(!frozenTask||!resources[id])return;
  const before=world.running[id]?'running':'stopped', resource=resources[id], used=usage(), deps=dependencies[world.topology][id];
  let code='ALLOWED', reason;
  if(!frozenTask.allowed.includes(id)){code='OPERATION_OUTSIDE_TASK';reason=`当前任务只请求 ${frozenTask.targets.join('、')}。先获得新的明确请求，才能扩大操作范围。`;}
  else if(!['Operator','Admin'].includes(world.role)){code='PROJECT_ACCESS_REQUIRED';reason=`${world.actor}在这个项目中是 ${world.role}，没有计算资源写权限。请求可以成立，正确处理是拒绝这项操作。`;}
  else if(world.running[id]){code='ALREADY_RUNNING';reason=`${id} 已运行，没有产生新的状态变化。`;}
  else if(world.project!=='active'){code='PROJECT_SUSPENDED';reason='项目暂停，启动条件尚未满足。当前任务不包含付款或恢复项目。';}
  else if(deps.some(dep=>!world.running[dep])){code='DEPENDENCY_NOT_RUNNING';reason=`尚未运行的上游：${deps.filter(dep=>!world.running[dep]).join('、')}。当前目标范围内可先处理上游；范围外的额外写操作需要新请求。`;}
  else if(used.cpu+resource.cpu>world.cpu||used.memory+resource.memory>world.memory||used.instances+1>world.limit){code='QUOTA_EXCEEDED';reason=`启动后 CPU ${used.cpu+resource.cpu}/${world.cpu}，内存 ${used.memory+resource.memory}/${world.memory}，实例 ${used.instances+1}/${world.limit}。配额不足。`;}
  else{world.running[id]=true;reason=`${id}：stopped → running。其他任务和原始世界保持独立。`;}
  const allowed=code==='ALLOWED';decision.classList.toggle('allowed',allowed);decision.classList.toggle('denied',!allowed&&code!=='ALREADY_RUNNING');
  document.getElementById('decision-title').textContent=`${allowed?'允许':code==='ALREADY_RUNNING'?'无需操作':'应拒绝'} start_instance(${id})`;
  document.getElementById('decision-code').textContent=code;document.getElementById('decision-reason').textContent=reason;
  const log=document.getElementById('action-log');log.querySelector('.empty-log')?.remove();const entry=document.createElement('li');entry.textContent=`start(${id}) → ${code} · ${before} → ${world.running[id]?'running':'stopped'}`;log.append(entry);renderWorld();
}
for(const id of ['task-identity','frozen-scene'])document.getElementById(id).addEventListener('change',renderFrozenSummary);
document.querySelectorAll('[data-target]').forEach(input=>input.addEventListener('change',renderFrozenSummary));
document.getElementById('freeze-exam').addEventListener('click',startEpisode);
document.getElementById('reset-world').addEventListener('click',resetWorld);
document.querySelectorAll('[data-start]').forEach(button=>button.addEventListener('click',()=>startResource(button.dataset.start)));
renderFrozenSummary();

// Authored examples explain the mechanism; they are not model-run records.
const traceExamples = {
  failure:{
    record:'db、cache 均未运行\nService 直接启动 app\n实际结果：app 启动\nOracle：依赖规则违规',
    hypothesis:'依赖检查被遗漏了吗？',
    clue:'失败已经暴露一个明确问题。Designer 继续检查：它只漏了一个对象，还是没有检查完整依赖关系？',
    challenge:'复现，并扩大依赖边界',
    next:'选择另一个已有项目中的多层依赖任务。对象改变，业务原则相同；用实际执行检验错误能否复现。'
  },
  success:{
    record:'初次计划只提到 cache\n补查后发现 db，修正计划\n依次启动上游与 app，完成目标\nOracle：未发生业务违规',
    hypothesis:'依赖更深时，还会补查完整吗？',
    clue:'最终成功，但计划在补查后才补齐一项依赖。Designer 将“前置条件识别可能不完整”作为下一轮要检验的假设。',
    challenge:'围绕成功中的修正出题',
    next:'选择已有的多层依赖链，仍要求合法部署。检查 Service 能否在首次写入前查清全部上游，而不是等到后续步骤再补救。'
  }
};
function renderTrace(key){
  const example=traceExamples[key];
  for(const field of ['record','hypothesis','clue','challenge','next'])document.getElementById(`trace-${field}`).textContent=example[field];
}
document.getElementById('trace-source').addEventListener('change',event=>renderTrace(event.target.value));
renderTrace(document.getElementById('trace-source').value);

const stages = [
  {kicker:'线索 → 挑战',title:'从已完成的经历中选择下一题',description:'第一次使用初始任务的执行轨迹，之后使用上一代完成的交互。Designer 找到一个具体薄弱环节，再从冻结世界中的已有身份、关系和目标组合任务。',label:'选题依据 / 机制示例',artifact:'已有经历：补查后才完善依赖计划\n测试假设：多层依赖下是否仍会漏查？\n任务选择：已有项目的完整依赖链\n验证目标：写入前是否检查全部前置条件'},
  {kicker:'挑战 → 真实交互',title:'Customer 沟通，Service 自主执行',description:'固定 Customer 按任务与已有事实提出请求、回答追问。Service 自主选择查询、规划和业务操作。固定角色策略仍能产生随真实回复展开的多轮对话。',label:'任务与执行方式',artifact:'顾客：请把这组服务部署起来。\nService：查询项目、角色与资源状态。\n顾客：依据真实情况回应追问。\nService：自主选择操作与执行顺序。'},
  {kicker:'执行 → 可核验证据',title:'让实际行为决定对错',description:'Reference 给出业务预期；Engine 产生真实事件；Oracle 核对结果。合法完成、正确拒绝、错误尝试和成功违规分别记录，Replay 复查实际发生的过程。',label:'判断依据 / 机制示例',artifact:'预期：依赖未运行时应拒绝启动\n实际：app 成功进入 running\nOracle：业务违规\n\n记录原始对话、前态、工具与事件；\n判定不依赖 Service 自己声称成功。'},
  {kicker:'证据 → 两类 Skill',title:'同一经历，学到不同方法',description:'Designer 整理怎样找到和验证薄弱环节；Service 整理怎样可靠处理业务。双方分别修订 Skill，模型权重固定。',label:'经验如何分别积累',artifact:'Designer：\n从计划修正中寻找边界，\n用结构不同的任务检验迁移。\n\nService：\n写入前核实依赖、状态与权限；\n需要额外操作时先确认授权。'},
  {kicker:'Skill → 选中版本',title:'检查经验，再保存可继承版本',description:'检查 Patch 的角色、作用范围、结构与父版本。通过后保存新版本；没有有效更新时沿用旧版。每次修改及其证据来源都可追溯。',label:'版本选择 / 实现细节',artifact:''},
  {kicker:'这一代 → 下一代',title:'用更新后的双方，继续寻找问题',description:'下一代 Designer 使用选中的选题经验，面对更新后 Service 的真实表现；Service 用当前业务经验处理新挑战。新交互再次成为双方学习的输入。',label:'下一代继承',artifact:''}
];
let stage = 0, timer = null;
const stageButtons = [...document.querySelectorAll('[data-stage]')];
const progress = document.getElementById('evolution-progress');
const play = document.getElementById('play-evolution');
function selectionText() {
  const outcome = document.getElementById('service-outcome').value;
  return {
    accepted: {summary:'Designer 静态通过 → Dₙ₊₁；Service 静态通过 → Sₙ₊₁。', artifact:'Designer：静态检查通过 → 选中 Dₙ₊₁\nService：静态检查通过 → 选中 Sₙ₊₁\n\n下一代：Dₙ₊₁ × 固定 Customer × Sₙ₊₁\n\n保存 Patch、Snapshot 与来源证据。'},
    rejected: {summary:'Designer 静态通过 → Dₙ₊₁；Service 静态失败 → 保留 Sₙ。', artifact:'Designer：静态检查通过 → 选中 Dₙ₊₁\nService：静态检查失败 → 保留 Sₙ\n\n下一代：Dₙ₊₁ × 固定 Customer × Sₙ\n候选保留用于审计，不进入下一代。'},
    noop: {summary:'Designer 静态通过 → Dₙ₊₁；Service 返回 NOOP → 保留 Sₙ。', artifact:'Designer：静态检查通过 → 选中 Dₙ₊₁\nService：NOOP → 保留 Sₙ\n\n下一代：Dₙ₊₁ × 固定 Customer × Sₙ\n本代保持原 Service Skill。'}
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
    ? 'Dₙ₊₁ / Sₙ₊₁（静态通过）' : 'Dₙ₊₁ / Sₙ（保留旧版）';
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
