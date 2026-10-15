"""Offline audit of actual wire requests. Never changes/replays requests or calls an LLM.

Provider usage is exact; component sizes are UTF-8 JSON bytes, NOT model tokens.
Whitespace candidates are measurements only, not a runtime compression policy.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo = int(pos)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (pos - lo)


def compact_json_text(text):
    """Whitespace-only JSON candidate; exclude duplicate keys and nonfinite values."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    try:
        value = json.loads(text, object_pairs_hook=pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError):
        return text


def measure(request):
    parts = Counter()
    messages = request.get('messages', [])
    last_user = max((i for i, m in enumerate(messages) if m.get('role') == 'user'), default=-1)
    seen_tools = set()
    repeated = whitespace = 0
    tool_results = 0
    skill_ids = []
    for i, message in enumerate(messages):
        content = message.get('content')
        if message.get('role') == 'system':
            category = 'skill' if isinstance(content, str) and '<VAST_SKILLS>' in content else 'system'
        elif message.get('role') == 'tool':
            category = 'tool_results'
        elif message.get('role') == 'user' and i == last_user:
            category = 'latest_user'
        else:
            category = 'conversation_history'
        parts[category] += len(encoded(message))
        if category == 'skill':
            skill_ids += re.findall(r'<VAST_SKILL id="([^"]+)"', content)
        if category == 'tool_results' and isinstance(content, str):
            tool_results += 1
            # Payload equality alone is NOT sufficient to safely delete a tool message.
            if content in seen_tools:
                repeated += len(content.encode())
            seen_tools.add(content)
            whitespace += max(0, len(content.encode()) - len(compact_json_text(content).encode()))
    parts['tool_definitions'] = len(encoded(request.get('tools', []))) if 'tools' in request else 0
    # Account for every byte including separators, framing and model/options.
    parts['request_framing_and_options'] = len(encoded(request)) - sum(parts.values())
    return dict(component_bytes=dict(parts), wire_json_bytes=len(encoded(request)),
                message_count=len(messages), tool_result_count=tool_results,
                repeated_tool_payload_bytes=repeated,
                tool_json_whitespace_candidate_bytes=whitespace, skill_ids=skill_ids)


def records(root, kind):
    if kind == 'native':
        paths = sorted((root / 'native' / 'episodes').glob('*/calls/*.completed.json'))
        for path in paths:
            outer = json.loads(path.read_text()); call = outer['call']
            yield path, call['id'], call['role'], call['request'], call.get('response'), call.get('error')
        for path in sorted(root.glob('*reflection.response.json')):
            start = path.with_name(path.name.replace('.response.', '.started.'))
            if start.exists():
                yield path, path.stem, 'reflection_service', json.loads(start.read_text())['request'], json.loads(path.read_text()), None
    else:
        for start in sorted((root / 'wire-ledger' / 'calls').glob('*.started.json')):
            row = json.loads(start.read_text())
            path = start.with_name(start.name.replace('.started.', '.completed.'))
            done = json.loads(path.read_text()) if path.exists() else {}
            yield start, row['id'], row['role'], row['request'], done.get('response'), done.get('error')


def audit(root, kind):
    rows = []
    for path, key, role, request, response, error in records(root, kind):
        usage = (response or {}).get('usage') or {}
        ordinal = re.search(r'\.' + re.escape(role) + r'\.(\d+)$', key)
        row = dict(id=key, role=role, call_ordinal=int(ordinal.group(1)) if ordinal else None, source=str(path.relative_to(root)),
                   source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   request_sha256=hashlib.sha256(encoded(request)).hexdigest(),
                   model=request.get('model'), input_tokens=usage.get('prompt_tokens', usage.get('input_tokens')),
                   output_tokens=usage.get('completion_tokens', usage.get('output_tokens')),
                   total_tokens=usage.get('total_tokens'),
                   reasoning_tokens=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                   error=bool(error), **measure(request))
        rows.append(row)
    if not rows:
        raise ValueError('no original calls found')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate call IDs: do not silently deduplicate real executions')
    groups = {}
    for role in sorted({r['role'] for r in rows}):
        selected = [r for r in rows if r['role'] == role]
        parts = Counter()
        for row in selected:
            parts.update(row['component_bytes'])
        groups[role] = dict(calls=len(selected),
            **{key: sum(r[key] for r in selected if r[key] is not None)
               for key in ['input_tokens','output_tokens','total_tokens','reasoning_tokens',
                           'wire_json_bytes','repeated_tool_payload_bytes','tool_json_whitespace_candidate_bytes']},
            missing_usage_calls=sum(r['input_tokens'] is None or r['output_tokens'] is None for r in selected),
            p50_input_tokens=percentile([r['input_tokens'] for r in selected if r['input_tokens'] is not None], .5),
            p90_input_tokens=percentile([r['input_tokens'] for r in selected if r['input_tokens'] is not None], .9),
            component_bytes=dict(parts), injected_skills=dict(Counter(s for r in selected for s in r['skill_ids'])),
            by_call_ordinal=[dict(call_ordinal=n, calls=len(sub),
                mean_input_tokens=sum(r['input_tokens'] for r in sub)/len(sub),
                p90_input_tokens=percentile([r['input_tokens'] for r in sub], .9))
                for n in sorted({r['call_ordinal'] for r in selected if r['call_ordinal'] is not None and r['input_tokens'] is not None})
                if (sub := [r for r in selected if r['call_ordinal']==n and r['input_tokens'] is not None])],
            by_message_count=[dict(message_count=n, calls=len(sub),
                mean_input_tokens=sum(r['input_tokens'] for r in sub)/len(sub))
                for n in sorted({r['message_count'] for r in selected if r['input_tokens'] is not None})
                if (sub := [r for r in selected if r['message_count']==n and r['input_tokens'] is not None])])
    return dict(schema_version=1, source_root=str(root.resolve()), source_kind=kind,
                component_unit='UTF-8 canonical JSON bytes, NOT tokens',
                usage_source='original provider response; reasoning is a subset of output, never added again',
                online_calls=0, runtime_modified=False, groups=groups, calls=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--kind', choices=['native','ledger'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite audit evidence')
    result=audit(args.root,args.kind)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['groups'],ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
