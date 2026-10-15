'use strict';
// This site is a static research presentation. No API, model calls or telemetry.
const steps = [
  ['01 / EXPLORATION', '挑战来自 Customer，而非逐代人工命题。', 'Customer 依据允许观察的信息自主提问，组合业务请求，并根据 Service 的真实回复调整探索。隐藏的 Oracle 答案不进入 Customer 上下文。'],
  ['02 / EXECUTION', '每次工具调用，都进入真实 World Engine。', 'Service 自主决定查询和操作顺序。身份与精确写授权独立建立，不能根据 Service 的工具参数倒推出 Customer 授权。完整世界状态不会直接暴露给 Agent。'],
  ['03 / VERIFICATION', '区分一次错误尝试，和一次真正执行的违规。', 'Reference Rules 给出合法行为预期，Oracle 检查实际状态变化。保存正常、拒绝与失败交互；查询失败和被拦截的非法尝试不能冒充漏洞。'],
  ['04 / REFLECTION', '同一代的真实交互，成为双方的学习材料。', '本代正常自主探索产生的可验证 Episode 进入双方 Reflection。每个角色最多一次真实 Reflection 生成一个 SkillPatch；Service 同时保留原有合法与拒绝任务证据。'],
  ['05 / SELECTION', 'Customer 静态选择，Service 保留动态验收。', 'Customer 候选通过静态与内容完整性检查后即可更新，诊断不控制选择。Service 必须继续通过原静态和动态 Gate；拒绝或 NOOP 则保留原版本。'],
  ['06 / NEXT GENERATION', '保存真实选中的版本，递归继续。', '候选、最终 Snapshot、Reflection、Gate、Oracle、Evidence 和成本均归档。下一代加载选中的 Customer 与 Service；训练后再独立比较版本，不向训练回流测试结果。']
];
let step = 0;
let timer = null;
const nodes = [...document.querySelectorAll('[data-step]')];
const progress = document.getElementById('loop-progress');
const play = document.getElementById('play-loop');
function showStep(index) {
  step = Number(index);
  nodes.forEach((node, i) => { node.classList.toggle('active', i === step); node.setAttribute('aria-pressed', String(i === step)); });
  const [label, title, description] = steps[step];
  document.getElementById('step-label').textContent = label;
  document.getElementById('step-title').textContent = title;
  document.getElementById('step-description').textContent = description;
  document.getElementById('step-count').textContent = `${String(step + 1).padStart(2, '0')} / 06`;
  progress.value = String(step);
}
function pause() {
  clearInterval(timer); timer = null;
  play.innerHTML = '播放流程 <span>▶</span>';
  play.setAttribute('aria-pressed', 'false');
}
nodes.forEach(node => node.addEventListener('click', () => { pause(); showStep(node.dataset.step); }));
progress.addEventListener('input', () => { pause(); showStep(progress.value); });
play.addEventListener('click', () => {
  if (timer) return pause();
  play.innerHTML = '暂停流程 <span>Ⅱ</span>';
  play.setAttribute('aria-pressed', 'true');
  timer = setInterval(() => showStep((step + 1) % steps.length), 3500);
});
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
const loopObserver = new IntersectionObserver(entries => { if (!entries[0].isIntersecting) pause(); });
loopObserver.observe(document.querySelector('.loop-figure'));
const worlds = {
  cloudops: {kicker:'CLOUD INFRASTRUCTURE', title:'启动一台服务器，\n需要满足多少前置条件？', description:'组织负责人不一定拥有项目操作权限。启动应用前，还要确认项目活跃、配额足够，以及它依赖的服务器已经运行。', tags:['项目角色','依赖 DAG','三维配额','账单与恢复'], doc:'benchmarks/cloudops-v0.1/README.md', map:['Organization','Identity & roles','Project state','Compute instance','Quota','Dependencies']},
  saas: {kicker:'SUBSCRIPTIONS & ACCESS', title:'一个席位的变化，\n牵动怎样的业务链？', description:'成员生命周期、订阅、席位与账单彼此关联。一个合法请求可能有多条解决路径；操作顺序会改变后续步骤的可行性。', tags:['成员生命周期','订阅与席位','模拟支付','部分退款'], doc:'benchmarks/v0.2.0/README.md', map:['Organization','Membership','Subscription','Seats & access','Invoices','Payments']},
  fulfillment: {kicker:'WAREHOUSE & FULFILLMENT', title:'从库存到签收，\n每一步都要守恒。', description:'仓库、库存、订单与运输构成可执行的履约世界。库存守恒和运输生命周期决定操作能否执行，真实状态变化由独立 Oracle 检查。', tags:['库存守恒','订单履约','运输生命周期','多步依赖'], doc:'benchmarks/fulfillment-v0.1/README.md', map:['Warehouse','Inventory','Orders','Fulfillment','Stock','Shipping']},
  stayops: {kicker:'HOSPITALITY OPERATIONS', title:'有可售库存，\n就一定能安排入住吗？', description:'按日期计算的房型库存与具体物理房间分配是不同概念。预订和入住需要同时考虑时间、资源关系与业务前置条件。', tags:['日期库存','物理房间','预订生命周期','资源分配'], doc:'benchmarks/stayops-v0.1/README.md', map:['Property','Dated inventory','Reservations','Room assignment','Room type','Physical rooms']}
};
function selectWorld(key) {
  const world = worlds[key];
  document.querySelectorAll('[data-world]').forEach(button => { const selected = button.dataset.world === key; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; });
  const panel = document.getElementById('world-panel');
  panel.setAttribute('aria-labelledby', `tab-${key}`);
  document.getElementById('world-kicker').textContent = world.kicker;
  document.getElementById('world-title').innerText = world.title;
  document.getElementById('world-description').textContent = world.description;
  document.getElementById('world-tags').replaceChildren(...world.tags.map(tag => { const span = document.createElement('span'); span.textContent = tag; return span; }));
  document.getElementById('world-source').href = `https://github.com/hjy8848/Usami/blob/main/${world.doc}`;
  document.getElementById('map-label').textContent = `${key.toUpperCase()} / RELATION MAP`;
  ['map-root','map-left','map-right','map-target','map-dep-left','map-dep-right'].forEach((id,i) => document.getElementById(id).textContent = world.map[i]);
}
const studies = {
  paired: {
    code:'CUSTOMER-PAIRED-001', title:'新 Customer 找到了更多真实违规。', description:'同一 Service、相同的 20 个初始世界与预算，每个世界由 C0 / C1 分别自主探索一次。只有 Customer Skill 不同。',
    label:'Oracle 确认的成功业务违规次数',unit:'次 · 越高表示发现越多',max:20,bars:[['C0 × S0',0],['C1 × S0',20]],
    takeaway:'20 次违规涉及权限、项目暂停、依赖三类首要规则，不能称为 20 种独立错误。查询失败增加，且部分目标上下文重复；未证明跨场景泛化。',
    caveat:'历史候选比较，C1 当时未正式选中。有效测试采用当时的代理定义，不等于当前探针质量评价。', source:'customer-paired-001/REPORT.md'
  },
  repair: {
    code:'SERVICE-REPAIR-001 / ISOLATED DIAGNOSTIC', title:'候选减少部分违规，却没有通过正式验收。', description:'116 场总实验中的 80 场独立交叉诊断：20 个新世界 × 四种组合。C1 和 S1 均未通过当时的动态 Gate；候选只用于隔离比较。',
    label:'Oracle 确认的成功业务违规次数',unit:'次 · 此处减少才是修复方向',max:20,bars:[['C0 × S0',8],['C1 × S0',15],['C0 × S1',3],['C1 × S1',12]],
    takeaway:'C0 下违规从 8 次降至 3 次，C1 下从 15 次降至 12 次；但 S1 未稳定修复原始错误，并出现新的问题。候选数字改善不能代替 Gate 通过。',
    caveat:'这是历史协议下的候选诊断，不能表述为正式共进化成功，也不能事后按新规则重新选择历史候选。',source:'service-repair-001/REPORT.md'
  },
  heldout: {
    code:'MULTIGEN-HELDOUT-RECOVERY-002', title:'三组标签，同一个 Service Snapshot。', description:'历史 v2 训练 A/B 各完成两代；最终 12 个陌生世界、每个世界一项合法与一项拒绝任务，三个 Service 标签共 72 场。四次正式 Service Reflection 均为 NOOP。',
    label:'正确完成任务数（每组 24 场）',unit:'任务 · 越高越好',max:24,bars:[['S0',17],['A final',15],['B final',14]],
    takeaway:'三组合法任务均为 12/12；正确拒绝分别为 5/12、3/12、2/12。实际使用同一 Skill 的运行波动不能解释成学习差异。没有形成新版 Service。',
    caveat:'136 个完整 Trace 精确 Replay 通过。后续审计确认两条训练后交叉执行的依赖违规未进入 Reflection；见下方证据流向审计。当前 v3 已将这些交叉评估移出训练。',source:'multigen-heldout-recovery-002/FINAL_REPORT.md'
  }
};
function selectStudy(key) {
  const study = studies[key];
  document.querySelectorAll('[data-study]').forEach(button => { const selected = button.dataset.study === key; button.setAttribute('aria-selected',String(selected)); button.tabIndex = selected ? 0 : -1; });
  document.getElementById('study-panel').setAttribute('aria-labelledby',`tab-${key}`);
  ['code','title','description','takeaway','caveat'].forEach(field => document.getElementById(`study-${field}`).textContent = study[field]);
  document.getElementById('chart-label').textContent = study.label;
  document.getElementById('chart-unit').textContent = study.unit;
  document.getElementById('chart-max').textContent = study.max;
  document.getElementById('study-source').href = `https://github.com/hjy8848/Usami/blob/main/experiments/vast_coevo/results/${study.source}`;
  const rows = study.bars.map(([label,value],i) => {
    const row = document.createElement('div'); row.className = 'bar-row';
    const name = document.createElement('span'); name.textContent = label;
    const track = document.createElement('div'); track.className = 'bar-track';
    const bar = document.createElement('div'); bar.className = `bar${i % 2 ? ' accent' : ''}`; bar.style.width = `${value / study.max * 100}%`; track.append(bar);
    const count = document.createElement('strong'); count.textContent = value;
    row.append(name,track,count); return row;
  });
  document.getElementById('chart-bars').replaceChildren(...rows);
}
// Standard keyboard navigation for both tab lists, including Home / End.
function wireTabs(selector, attribute, select) {
  const buttons = [...document.querySelectorAll(selector)];
  buttons.forEach((button,index) => {
    button.addEventListener('click', () => select(button.dataset[attribute]));
    button.addEventListener('keydown', event => {
      let next;
      if(event.key === 'ArrowRight') next = (index + 1) % buttons.length;
      else if(event.key === 'ArrowLeft') next = (index + buttons.length - 1) % buttons.length;
      else if(event.key === 'Home') next = 0;
      else if(event.key === 'End') next = buttons.length - 1;
      else return;
      event.preventDefault(); select(buttons[next].dataset[attribute]); buttons[next].focus();
    });
  });
}
wireTabs('[data-world]', 'world', selectWorld);
wireTabs('[data-study]', 'study', selectStudy);
