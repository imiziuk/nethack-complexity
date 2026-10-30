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

# ---- repair 4 (2026-10-29): exact per-window boulder reach (G1).  K.explore enumerates every boulder set reachable by
# traversals from every port (all hero strategies, broken states included); it raises LeakError if any push could put
# a boulder on a port cell. Exact reach = union of boulder cells over all reachable states.
import A_core as K
print('-- exact boulder reach (A_core.explore, all ports, broken states included)')
for name, rows in boards.items():
    bd = K.Board(rows)
    try:
        C = K.explore(bd)
    except K.LeakError as e:
        print(f'{name:16s} LEAK {e}'); continue
    reach = {bd.cells[i] for B in C.states for i in range(len(bd.cells)) if B >> i & 1}
    ports = {bd.cells[i] for i in bd.ports.values()}
    near = sorted(c for c in reach for p in ports if max(abs(c[0] - p[0]), abs(c[1] - p[1])) <= 1)
    print(f'{name:16s} states {len(C.states):6d} exact reach {len(reach):3d} cells; port cells reached: '
          f'{sorted(reach & ports)}; cells 8-adjacent to a port: {near}')
