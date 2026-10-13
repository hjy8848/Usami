"""Deterministic human-review layers drawn from the complete example appendix."""
import argparse
import json
from pathlib import Path
from usami_fulfillment.benchmark import write_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('release',type=Path);args=parser.parse_args()
    rows=json.loads((args.release/'review-examples.json').read_text())
    rows.sort(key=lambda item:(item['request'].startswith('Continue'),item['id']))
    selected=[];seen=set()
    def depth(item):return max((w['causal_depth'] for w in item['certificate']['legal_witnesses']),default=0)
    for layer in [lambda e:(e['family'],e['split']),lambda e:(e['identity'],depth(e),bool(e['certificate']['refusal_code']),e['split']),
                  lambda e:(e['id'],)]:
        layers=set()
        for item in rows:
            key=layer(item)
            if key in layers:continue
            layers.add(key)
            if item['id'] in seen:continue
            selected.append(item);seen.add(item['id'])
            if len(selected)==55:break
        if len(selected)==55:break
    if len(selected)<55:raise ValueError('insufficient distinct reviewer cases')
    write_json(args.release/'review-sample-55.json',selected)
    lines=['# FulfillmentOps stratified review sample','','AWAITING HUMAN REVIEW. No human realism rating has been performed.',
           '', '55 cases selected by family/split first, then identity/causal depth/refusal layers; base business goals are preferred over progress variants.','']
    for index,item in enumerate(selected):
        lines += [f'## {index+1}. {item["family"]} ({item["split"]}, {item["identity"]}, depth {depth(item)})',
                  '', '```json',json.dumps(item,ensure_ascii=False,indent=2),'```','']
    (args.release/'REVIEW_SAMPLE.md').write_text('\n'.join(lines),encoding='utf-8')
    print('55 stratified examples; AWAITING HUMAN REVIEW',flush=True)


if __name__=='__main__':main()
