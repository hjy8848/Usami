import json,hashlib
from pathlib import Path
from usami_benchmark.worlds import FrozenWorld
from usami_benchmark.designer_exploration import verify_failed_journal
r=Path('experiments/vast_coevo/results/designer-event-links-live-002')
f=FrozenWorld.model_validate_json((r/'world.json').read_text())
j=json.loads((r/'designer-journal.json').read_text())
replay=verify_failed_journal(f,j)
assert replay['verified'] and replay['model_calls']==9 and replay['actual_online_calls']==0
rows=[json.loads(p.read_text()) for p in sorted((r/'model-calls').glob('*.json'))]
assert len(rows)==9 and all(x['status']=='completed' for x in rows)
assert all('max_tokens' not in x['request'] for x in rows)
assert all(x['response']['choices'][0]['finish_reason']!='length' for x in rows)
(r/'live-replay.json').write_text(json.dumps(replay,ensure_ascii=False,indent=2))
usage=json.loads((r/'manifest.json').read_text())['usage'];jex=j['exchanges']
submissions=[e for e in jex if e['stage']=='submission']
linked=[t['data'] for e in jex for t in e['tool_results'] if t.get('data',{}).get('registered_external_events')]
allid=[event['id'] for data in linked for event in data['registered_external_events']]
summary={'status':'BLOCKED','model':'deepseek-v4.1-flash','max_tokens_in_requests':False,'actual_calls':9,'designer_queries':j['queries'],'proposal_attempts':len(submissions),'certified_tasks':0,'service_tasks':0,'reflections':0,'skill_updates':0,'all_responses_ended_before_provider_length':True,'usage':usage,'failure':json.loads((r/'manifest.json').read_text())['failure'],'failed_session_offline_replay':replay,'events_visible_to_designer':allid,'report':'designer-event-links-validation-001/REPORT.zh.md'}
(r/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
