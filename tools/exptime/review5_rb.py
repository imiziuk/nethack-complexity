#!/usr/bin/env python3
"""review5_rb.py -- review 5 item 4: C-audit's Z1 over-approximation R_B on the concrete crossover map.
R_B = closure of boulder cells under: c in R_B, c-d and c+d floor (walls are the only obstruction) => c+d in R_B.
Reports how many R_B cells lie outside every tile (corridors) and their distance to external ports."""
import json, os
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'build', 'xover')
rows = open(os.path.join(d, 'crossover.txt')).read().split('\n')
j = json.load(open(os.path.join(d, 'crossover.json')))
W, H = j['W'], j['H']
def floor(x, y):
    return 0 <= y < len(rows) and 0 <= x < len(rows[y]) and rows[y][x] != '#' and rows[y][x] != ' '
tilecells = set()
for t in j['tiles'].values():
    for c in t['cells']:
        tilecells.add(tuple(c))
B = {(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == '0'}
R = set(B); st = list(B)
while st:
    x, y = st.pop()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if floor(x - dx, y - dy) and floor(x + dx, y + dy) and (x + dx, y + dy) not in R:
            R.add((x + dx, y + dy)); st.append((x + dx, y + dy))
out = [c for c in R if c not in tilecells]
print('boulders', len(B), 'R_B cells', len(R), 'R_B cells outside tiles', len(out))
print('sample', sorted(out)[:10])
print('external ports', j['ext'])
print('sanity: boulders inside tile cells', sum(b in tilecells for b in B), '/', len(B),
      '; tile cells that are floor in the text map', sum(floor(*c) for c in tilecells), '/', len(tilecells))
