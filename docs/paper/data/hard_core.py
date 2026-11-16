#!/usr/bin/env python3
# Run from the repo root: python3 docs/paper/data/hard_core.py
"""Bugs missed by both Sonnet and Sol: who else caught them, how deep agents went, and bug metadata."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, '.')
from tools import changelog_coverage as cc
cfg = json.load(open('docs/paper/data/configs.json'))
notes = json.loads(cc.NOTES.read_text()); anchors = json.loads(cc.ANCHORS.read_text())
found = {}; present = collections.defaultdict(set); depth = collections.defaultdict(dict); ep_of = {}
for c in cfg:
    f = set()
    for r in c['runs']:
        run = Path(r); keep = cc.scored_run_ids(run)
        for p in run.glob('episodes/*/*/result.json'):
            d = json.load(open(p))
            if d['run_id'] not in keep: continue
            f |= set(d['found'] or [])
            for b in d['required']: present[c['key']].add(b); ep_of[b] = d['item_id']
        for x in cc.episode_lines(run, notes, anchors):
            if x['kind'] == 'real':
                depth[c['key']][(x['episode'], x['line'])] = x['actions_on_screen']
    found[c['key']] = f
line_of = {}
for ep, n in notes.items():
    for bug, line in n['real'].items(): line_of[bug] = line
allbugs = sorted(present['sonnet'])
hard = [b for b in allbugs if b not in found['sonnet'] and b not in found['sol']]
others = ['haiku', 'deepseek', 'luna-max', 'luna-med']
rows = []
for b in hard:
    m = json.load(open(f'dataset/bugs/{b}/bug.json'))
    ref = json.load(open(f'dataset/bugs/{b}/reference_reports.json'))['correct']
    ep = ep_of[b]; line = line_of.get(b, '?')
    rows.append(dict(bug=b, ep=ep, family=m['family'], symptom=m['symptom_type'], issta=m['issta_class'],
                     fix=m['fix_date'], source=m['source'], port_conf=(m.get('head_port') or {}).get('confidence'),
                     caught_by=[k for k in others if b in found[k]],
                     depth={k: depth[k].get((ep, line)) for k in ('sonnet', 'sol', 'haiku', 'deepseek')},
                     line=line, expected=ref['expected'], observed=ref['observed'], screen=ref['screen']))
json.dump(rows, open('docs/paper/data/hard28.json', 'w'), indent=1)
def dist(key, pool):
    return dict(collections.Counter(json.load(open(f'dataset/bugs/{b}/bug.json'))[key] for b in pool))
easy = [b for b in allbugs if b not in hard]
print('hard', len(hard), 'of', len(allbugs))
for k in ('family', 'symptom_type', 'source'):
    print(k, 'hard', dist(k, hard), '| rest', dist(k, easy))
pc = lambda pool: dict(collections.Counter((json.load(open(f'dataset/bugs/{b}/bug.json')).get('head_port') or {}).get('confidence') for b in pool))
print('port confidence hard', pc(hard), '| rest', pc(easy))
print('recent(2026+) hard', sum(json.load(open(f'dataset/bugs/{b}/bug.json'))['fix_date'] >= '2026' for b in hard), '| rest', sum(json.load(open(f'dataset/bugs/{b}/bug.json'))['fix_date'] >= '2026' for b in easy), 'of', len(easy))
print('caught by some other model:', sum(1 for r in rows if r['caught_by']), collections.Counter(len(r['caught_by']) for r in rows))
print('apps', collections.Counter(r['ep'].split('-')[0] for r in rows))
for r in rows:
    print(f"\n{r['bug']} [{r['ep']}] {r['family']}/{r['symptom']} fix {r['fix']} port {r['port_conf']} others {r['caught_by']} depth {r['depth']}\n  NOTE: {r['line']}\n  BUG: expected {r['expected']} | observed {r['observed']}")
