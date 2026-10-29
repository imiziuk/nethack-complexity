#!/usr/bin/env python3
"""R_report.py -- print the summary tables of build/realgame/*_summary.json (Markdown) for R-realgame.md."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'build', 'realgame')


def load(n):
    p = os.path.join(OUT, n)
    return json.load(open(p)) if os.path.exists(p) else {}


S, Wk, Sc = load('steps_summary.json'), load('walks_summary.json'), load('screen_summary.json')
names = [n for n in ['diode', 'G_D', 'G_D_tile', 'SLOT1', 'UTURN2', 'proto_precursor', 'precursor', 'toggle', 'G_C',
                     'G_X', 'SCD'] if n in S or n in Wk or n in Sc]
print('| gadget | local states | hero states | step queries (state x key) | mismatches | walks replayed (keys) | walk FAIL | typed in tty: items (keys) | tty FAIL |')
print('|---|---|---|---|---|---|---|---|---|')
for n in names:
    s, w, c = S.get(n, {}), Wk.get(n, {}), Sc.get(n, {})
    print(f"| {n} | {s.get('local_states', w.get('local_states', '-'))} | {s.get('reachable_hero_states', '-')} | "
          f"{s.get('queries', '-')} | {s.get('mismatches', '-')} | {w.get('walks', '-')} ({w.get('keys_total', '-')}) | "
          f"{w.get('fails', '-')} | {c.get('items', '-')} ({c.get('keys_typed', '-')}) | {c.get('fail', '-')} |")
print()
print('speed:', S.get('_speed'), 'walks wall', Wk.get('_wall_s'), 's; screen wall', Sc.get('_wall_s'), 's')
for n in names:
    s = S.get(n, {})
    if s.get('mismatch_examples'):
        print('\nMISMATCHES', n)
        for e in s['mismatch_examples']:
            print('  ', e)
    w = Wk.get(n, {})
    if w.get('fail_examples'):
        print('\nWALK FAILS', n)
        for e in w['fail_examples']:
            print('  ', e)
msgs = {}
for n in names:
    for m, k in Sc.get(n, {}).get('messages', {}).items():
        msgs[m] = msgs.get(m, 0) + k
print('\nmessages seen in tty:')
for m, k in sorted(msgs.items(), key=lambda kv: -kv[1]):
    print(f'  {k:4d}  {m}')
