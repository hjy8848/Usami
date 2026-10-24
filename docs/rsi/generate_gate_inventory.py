import ast,csv,hashlib,json,subprocess
from pathlib import Path
from collections import Counter
OUT=Path('docs/rsi')
FILES=['integrations/rsi_usami/open_world.py','integrations/rsi_usami/adapter.py','integrations/rsi_usami/packages.py','usami_v2/scenarios/designer.py','usami_v2/scenarios/grounding.py','usami_benchmark/grounder.py','usami_v2/scenarios/schema.py','usami_v2/scenarios/distribution.py','usami_v2/scenarios/builder.py','usami_v2/scenarios/solver.py','usami_v2/scenarios/certification.py','usami_v2/scenarios/task_certification.py','usami_v2/scenarios/tasks.py','usami_v2/runtime/agents.py','usami_v2/runtime/customer.py','usami_v2/runtime/runner.py','usami_v2/contracts.py','usami_v2/commerce/models.py','usami_v2/commerce/adapter.py','usami_v2/commerce/observations.py','usami_v2/commerce/reference.py','usami_v2/commerce/transitions.py','usami_v2/commerce/invariants.py','usami_v2/commerce/external.py','usami_v2/evaluation/outcomes.py','usami_v2/evaluation/communication.py','usami_harness/engine.py','usami_harness/models.py','usami_harness/oracle.py','rsi_core/runtime.py','rsi_core/period.py','rsi_core/collection.py','rsi_core/evaluation.py','rsi_core/packages.py','rsi_core/programs.py','rsi_core/protocol.py','rsi_core/archive.py','rsi_core/budget.py','rsi_core/isolation.py','rsi_core/worker.py','rsi_core/training.py','rsi_core/verl_backend.py','experiments/rsi/seeds/M0.py','experiments/rsi/seeds/P0.py','experiments/rsi/examples/open_world_usami.py','usami/service/client.py','usami/service/models.py','vast_coevo/schema.py']
# Module coverage is a deliberate superset; outside-root branches are labelled.
def scope(file,symbol):
 if file=='usami_benchmark/grounder.py':return 'BOUNDARY: only GroundingBudget schema is reused; legacy grounder execution OUTSIDE'
 if file=='usami_v2/scenarios/designer.py' and symbol.split('.')[0] in {'design_and_certify','_quality','post_run_quality','_structure_signatures','all_rows_raw','ChallengeQualityVector','ChallengeQualityVectorV1','PostRunQualityVector','DesignerRun','TaskDesignAttempt','CandidateConsequenceDiagnostic'}:return 'OUTSIDE run_open_period; historical combined Designer/quality path'
 if file=='rsi_core/training.py':return 'CONDITIONAL phi_update/training export; DIAGNOSTIC must not call'
 if file=='rsi_core/verl_backend.py':return 'CONDITIONAL configured verl backend; no current live period factory'
 if file in ['experiments/rsi/examples/open_world_usami.py','usami/service/client.py','usami/service/models.py']:return 'ENTRY/PROVIDER conditional on configured factory/client'
 if file=='vast_coevo/schema.py':return 'BOUNDARY: FrozenModel base schema; other legacy skill classes OUTSIDE'
 return 'ROOT/DEPENDENCY; actual activation follows factory, protocol and branch condition'
def policy(f,s,text):
 c='C';why='保持身份、业务状态、证据或独立评价的可信绑定';recover='不接受当前输入；修复配置或产生新合法工件后重开尝试，不改写原记录';essential='是：正确性/安全/评价或证据完整性'
 if any(x in f for x in ['budget.py','isolation.py','worker.py','client.py']) or 'Budget' in s or any(x in text for x in ['budget exhausted','allocation','max_attempts','max_candidates','max_steps','max_model_calls','max_tokens','max_plan_candidates','max_bindings']):
  c='B';why='约束资源、运行环境或外部调用，具体额度不是业务真值';recover='保留失败；新预算版本/检查点或有界新调用继续；不得重置已消费成本';essential='否：额度/恢复策略是工程要求；资源上限本身需保留'
 if any(x in text for x in ['MODEL_OUTPUT_INVALID','EMPTY_TOOL_ARGUMENTS','DESIGNER_SCHEMA_INVALID','Tool arguments','model output violates','response schema','complete structured function','nonempty message','JSON object','MODEL request/schema','decision fields','explicit object state','unregistered research action','unregistered task decision','Field required']):
  c='B';why='机器可执行结构必须有效，但单次格式错误不应结束整次诊断';recover='记录原始响应和校验结果；仅格式纠错后作为新尝试重新解析，不执行无效动作';essential='否：立即终止策略不是业务要求；动作结构仍须验证'
 if any(x in text for x in ['public_request_span','verbatim','subject_mention','public product mention','request_names_remedy','request_names_fact','_public_day','_public_charge','_public_quantity','_validate_public_remedy_bounds','public_line_match_ids','normalized_request','normalized_message','delegation_request_spans','_explicit_consent_intent','clear affirmative','clear negative']):
  c='A';why='用自由文本词法/子串/唯一匹配代理结构化语义，存在误拒绝；语义一致性要求本身保留';recover='改为可信结构化请求/来源绑定或澄清，不补答案；成交前仍需精确有效同意';essential='否：此匹配机制非业务必需；公开目标/授权一致性是 C'
 if f.endswith('grounding.py') and any(x in text for x in ['max_bindings','max_matches','max_worlds','truncated','NO_MATCH']):
  c='B';why='有限 Grounding 搜索/采样结果，不是系统错误或非法挑战的同义词';recover='记录搜索范围；扩大预先声明预算或另提挑战/新 World';essential='否：边界可配置；真实对象与身份仍 C'
 if f.endswith('open_world.py') and any(x in text for x in ['repeated a frozen World','consistent native certifier contract','required_hashes']):
  c='B';why='采样或批次能力组织约束，不是业务规则';recover='保留槽位失败；新采样或按能力分批，不改旧世界';essential='否：去重/单批一致性是实验组织'
 if f.endswith('task_certification.py') and any(x in text for x in ['budget','UNKNOWN','blockers.append','no_remedy_goals','minimum_witnesses','failures.append']):
  c='B';why='证明器覆盖能力/搜索限制/候选淘汰；不能把未证明当已证明';recover='换支持的挑战或合法配置/增加证明预算后新证书；保留 UNKNOWN/UNSAT 区别';essential='否：停止整个诊断非必需；禁止伪造获证是 C'
 if f.endswith('designer.py') and any(x in text for x in ['not configured for certification','information goals require','supported_target_stages','this run has no configured','target_stage','1 <= max_attempts <= 3']):
  c='B';why='运行认证能力或纠错配额限制，属于配置边界';recover='明确 CAPABILITY_UNSUPPORTED；配置真实事件或改提案后再认证';essential='否：能力可扩展；不能绕过未配置事件'
 if f.endswith('runtime.py') and f.startswith('rsi_core') and any(x in text for x in ['frozen by the first PROBE','max_candidates','max_steps','staged >=','RUN_BASELINE must precede','baseline already ran','registered only once','max_output_tokens']):
  c='B';why='正式研究回合/候选阶段和可重复性组织约束，非商业规则';recover='正式模式不变；诊断按新 revision/epoch 或独立 root 继续，评价依旧隔离';essential='否：阶段限制属于科研协议，诊断可分离'
 if f.endswith('collection.py') and any(x in text for x in ['seeds','phase_budgets','sampling group','reserve_group','usable','USABLE','UNUSABLE','InfrastructureError','BudgetExceeded']):
  c='B';why='完整 on-policy 训练研究组条件不应成为单条诊断的前置条件';recover='正式组继续判无效；诊断记录部分结果并在不污染正式组的分支继续';essential='否：单 root 诊断不需要 GRPO 完整组；正式训练要求保留'
 if f.endswith('period.py') and any(x in text for x in ['USABLE','ABORTED','TRAINING_FAILED','phi_update']):
  c='B';why='正式 Period 聚合/训练编排状态，决定能否采集训练，不等同能否观察下一诊断阶段';recover='诊断单列状态，保留选中父版本并继续可运行阶段；不调用训练钩子';essential='否：不训练诊断可与训练采集结束条件分离'
 if f.endswith('evaluation.py') and any(x in text for x in ['NO_PAIRED_GAIN','PACKAGE_REGRESSION','TASK_REGRESSION','UNRESOLVED','CANDIDATE_FORBIDDEN_BEHAVIOR','comparison.mean_delta','comparison.usable','comparison.safe']):
  c='C';why='独立评价与既定选代规则：无提升/回退/安全问题不得发布为改进';recover='保留父版本，诊断继续；不得更改得分/阈值以接受候选';essential='是：科研评价不改变；它阻止发布，不应阻止诊断结束'
 if f.endswith('tasks.py') and any(x in s for x in ['_positive_remedy_request','request_names_remedy','request_names_fact','public_line_match_ids','_issue_is_named','_contains_public_phrase','_public_','_validate_public_remedy_bounds']):
  c='A';why='文本解析代替目标与对象的可信绑定，具体词法规则不是业务真值';recover='结构化需求来源/受控请求渲染替换，保留冻结对象/数量/期限的真实验证';essential='否：文本硬匹配实现非必需；业务边界 C 保留'
 if 'communication.py' in f and s in ['extract_explicit_claims','_value']:
  c='A';why='有限文本抽取影响可评分性；不可把未识别表达默认为真或错误';recover='诊断保留原消息和未决状态；本次不改科研通信评分';essential='否：抽取策略可研究；事实真值和评价结果 C 不动'
 return c,essential,recover,why
rows=[];fields=[];branches=[];manifest=[]
for file in FILES:
 p=Path(file)
 if not p.exists():continue
 source=p.read_text();tree=ast.parse(source);parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
 def ancestry(node):
  arr=[]
  while node in parents:node=parents[node];arr.append(node)
  return arr
 def symbol(n):return '.'.join(a.name for a in reversed(ancestry(n)) if isinstance(a,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))) or '<module>'
 def conditions(n):
  out=[];child=n
  for a in ancestry(n):
   if isinstance(a,ast.If):
    # Locate immediate child in the if suite, not a descendant.
    out.append(('IF ' if child in a.body else 'ELSE NOT ')+ast.unparse(a.test))
   child=a
  return ' AND '.join(reversed(out)) or '入口/循环中无额外 if 前置条件'
 for n in ast.walk(tree):
  sym=symbol(n)
  if isinstance(n,ast.If):
   branches.append({'file':file,'line':n.lineno,'symbol':sym,'condition':ast.unparse(n.test),'scope':scope(file,sym)})
  gate=False;kind='';signal=''
  if isinstance(n,(ast.Raise,ast.Assert)):
   gate=True;kind=type(n).__name__;signal=ast.unparse(n)
  elif isinstance(n,ast.Call):
   fun=ast.unparse(n.func)
   if fun.endswith(('.append','.extend')) and isinstance(n.func,ast.Attribute) and any(x in ast.unparse(n.func.value) for x in ['errors','blockers','failures','reasons','codes','uncertain']):gate=True;kind='failure/uncertainty accumulator';signal=ast.unparse(n)
   elif fun in ['deny','error']:
    gate=True;kind='denial/audit error';signal=ast.unparse(n)
  elif isinstance(n,(ast.Break,ast.Continue)):
   gate=True;kind=type(n).__name__;signal=ast.unparse(n)
  elif isinstance(n,(ast.Assign,ast.AnnAssign,ast.Return)):
   val=n.value
   text=ast.unparse(n)
   if val and (('status' in text or 'success' in text or 'usable' in text or 'decision' in text) and any(x in text for x in ['FAILED','UNKNOWN','UNSAT','UNVERIFIED','BLOCKED','KEEP_PARENT','UNRESOLVED','FAIL','INVALID','UNUSABLE','False','ABORTED','NOOP','budget_exhausted','protocol_error','runner_error'])):
    gate=True;kind='status/selection gate';signal=text
  if gate:
   cond=conditions(n);c,essential,recover,why=policy(file,sym,cond+' '+signal)
   rows.append({'file':file,'line':n.lineno,'end_line':n.end_lineno,'symbol':sym,'kind':kind,'condition':cond,'failure_signal_exact':signal,'class':c,'business_or_evaluation_required':essential,'recovery':recover,'why':why,'scope':scope(file,sym)})
  if isinstance(n,ast.AnnAssign) and isinstance(parents.get(n),ast.ClassDef):
   text=ast.unparse(n);c,e,r,w=policy(file,sym,text)
   fields.append({'file':file,'line':n.lineno,'symbol':sym,'declaration_exact':text,'class':c,'business_or_evaluation_required':e,'failure':'Pydantic ValidationError / dataclass post-init / contract consumer; see symbol guards','recovery':r,'why':w,'scope':scope(file,sym)})
 manifest.append({'file':file,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':len(source.splitlines()),'branches':sum(r['file']==file for r in branches),'blocking_sites':sum(r['file']==file for r in rows),'fields':sum(r['file']==file for r in fields)})
for name,data in [('GATE_REGISTER.csv',rows),('SCHEMA_REGISTER.csv',fields),('SOURCE_BRANCHES.csv',branches)]:
 data.sort(key=lambda x:(x['file'],x['line']))
 for i,row in enumerate(data,1):row['id']=name.split('_')[0]+'-'+str(i).zfill(4)
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['id']+[k for k in data[0] if k!='id'],lineterminator='\n');w.writeheader();w.writerows(data)
(OUT/'GATE_AUDIT_SOURCE_MANIFEST.json').write_text(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'date':'2026-10-24','files':manifest,'counts':{'blocking_sites':len(rows),'schema_fields':len(fields),'source_branches':len(branches)},'gate_classes':dict(Counter(r['class'] for r in rows))},ensure_ascii=False,indent=2)+'\n')
print(len(manifest),'modules',len(rows),'sites',len(fields),'fields',len(branches),'branches')
