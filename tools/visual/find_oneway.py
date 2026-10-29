"""Random search for a small Push-1F one-way gadget: a -> b possible, b -> a impossible, and no way back
after crossing (design aid for scene c)."""
import random, sys
sys.path.insert(0, '.')
from push1f import solve, play

W, H, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
random.seed(seed)
res = []
for it in range(int(sys.argv[4]) if len(sys.argv) > 4 else 40000):
    free = {(x, y) for x in range(1, W + 1) for y in range(1, H + 1) if random.random() > 0.35}
    a, b = random.sample([(x, y) for x in range(1, W + 1) for y in range(1, H + 1)], 2)
    free |= {a, b}
    cand = [c for c in free if c not in (a, b)]
    nb = random.randint(1, 3)
    if len(cand) < nb:
        continue
    blocks = frozenset(random.sample(cand, nb))
    sol = solve(free, blocks, a, b)
    if not sol or solve(free, blocks, b, a):
        continue
    h, bb = play(free, blocks, a, sol)
    if solve(free, bb, h, a):
        continue
    res.append((len(free) + len(sol) * 0.2, free, blocks, a, b, sol))
res.sort(key=lambda t: t[0])
seen = set()
for sc, free, blocks, a, b, sol in res[:40]:
    rows = []
    for y in range(0, H + 2):
        rows.append(''.join('a' if (x, y) == a else 'b' if (x, y) == b else 'B' if (x, y) in blocks else
                            '.' if (x, y) in free else '-' for x in range(0, W + 2)))
    t = '\n'.join(rows)
    if t in seen: continue
    seen.add(t)
    print(sc, sol); print(t); print()
