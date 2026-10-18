import json,hashlib
from pathlib import Path
from usami_benchmark.worlds import FrozenWorld
from usami_benchmark.designer_exploration import verify_failed_journal
from usami_aftersales import adapter as a
from usami_aftersales.rules import eligibility
r=Path('experiments/vast_coevo/results/aftersales-coevo-inferai-v41-001')
f=FrozenWorld.model_validate_json((r/'world/frozen_world.json').read_text())
j=json.loads((r/'designer/task-1-journal.json').read_text())
v=verify_failed_journal(f,j)
(r/'verification').mkdir(exist_ok=True)
(r/'verification/designer-failure-replay.json').write_text(json.dumps(v,ensure_ascii=False,indent=2))
w=a.World.model_validate(f.world)
rows=[]
for p in sorted((r/'model-calls').glob('*.json')):
 x=json.loads(p.read_text());resp=x.get('response') or {}
 for t in resp.get('choices',[{}])[0].get('message',{}).get('tool_calls',[]):
  if t['function']['name']!='submit_frozen_world_task':continue
  q=json.loads(t['function']['arguments']);selected=[]
  for pid in q['profile_ids']:
   pr=w.profiles[pid];line=w.lines[pr.facts['line_id']];order=w.orders[line.order_id]
   selected.append({'profile_id':pid,'initial_eligibility':eligibility(w,order,line),'clock':w.clock.isoformat(),'delivered_at':order.delivered_at.isoformat() if order.delivered_at else None,'return_days':w.products[line.product_id].return_days})
  rows.append({'call':p.name,'proposal':q,'offline_initial_checks':selected})
audit={'note':'Post-run native eligibility checks only; never fed back to model. Initial eligibility is not a complete proof of task reachability.','proposals':rows}
(r/'verification/offline-proposal-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
s=json.loads((r/'source/registration.json').read_text());checks={k:hashlib.sha256((r/'source'/k).read_bytes()).hexdigest()==h and hashlib.sha256(Path(k).read_bytes()).hexdigest()==h for k,h in s['files'].items()}
(r/'verification/source-integrity.json').write_text(json.dumps({'all_verified':all(checks.values()),'files':checks},indent=2))
print(json.dumps({'replay':v,'source':checks,'proposal_count':len(rows),'eligibility':[[z['initial_eligibility'] for z in q['offline_initial_checks']] for q in rows]},ensure_ascii=False))
