#!/usr/bin/env python3
"""review5_rb2.py -- R_B (C-audit Z1 over-approximation) for every small window used: does it reach a port cell?"""
import A2_scd as S, B2_ani as BA, inspect
boards = {'protodiode': S.PROTODIODE, 'proto_precursor': S.PROTO_PRECURSOR}
for n, v in vars(BA).items():
    if isinstance(v, list) and v and all(isinstance(r, str) for r in v) and any('0' in r for r in v):
        boards[n] = v
for name, rows in boards.items():
    fl = lambda x, y: 0 <= y < len(rows) and 0 <= x < len(rows[y]) and rows[y][x] not in '# '
    B = {(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == '0'}
    R, st = set(B), list(B)
    while st:
        x, y = st.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if fl(x - dx, y - dy) and fl(x + dx, y + dy) and (x + dx, y + dy) not in R:
                R.add((x + dx, y + dy)); st.append((x + dx, y + dy))
    hit = sorted((rows[y][x], (x, y)) for x, y in R if rows[y][x].isupper())
    print(f'{name:16s} boulders {len(B)} R_B {len(R)} port cells in R_B: {hit}')
