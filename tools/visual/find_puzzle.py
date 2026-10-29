"""Random search for a small Push-1F puzzle where push ORDER matters (design aid for scene b)."""
import random, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
from push1f import solve, step, DIRS

W, H = (int(sys.argv[1]), int(sys.argv[2])) if __name__ == "__main__" else (0, 0)
seed = int(sys.argv[3]) if __name__ == "__main__" else 0; random.seed(seed)


def pushes_of(free, blocks, start, keys):
    h, b, n, moved = start, blocks, 0, set()
    for k in keys:
        r = step(free, h, b, k)
        if r[2]:
            n += 1
            moved |= (b - r[1])
        h, b = r[0], r[1]
    return n, len(blocks - b)


def first_pushes(free, blocks, start):
    """all states after exactly one push (walking freely before it)"""
    seen, stack, out = {start}, [start], []
    while stack:
        h = stack.pop()
        for k in DIRS:
            r = step(free, h, blocks, k)
            if not r:
                continue
            if r[2]:
                out.append((h, k, r[0], r[1]))
            elif r[0] not in seen:
                seen.add(r[0]); stack.append(r[0])
    return out


if __name__ != "__main__": raise SystemExit
best = []
for it in range(20000):
    free = {(x, y) for x in range(1, W + 1) for y in range(1, H + 1) if random.random() > 0.3}
    start, goal = (1, random.randint(1, H)), (W, random.randint(1, H))
    free |= {start, goal}
    cand = [c for c in free if c not in (start, goal)]
    nb = random.randint(2, 3)
    if len(cand) < nb:
        continue
    blocks = frozenset(random.sample(cand, nb))
    sol = solve(free, blocks, start, goal)
    if not sol:
        continue
    npush, nmoved = pushes_of(free, blocks, start, sol)
    if npush < 3 or nmoved < 2:
        continue
    fp = first_pushes(free, blocks, start)
    dead = [f for f in fp if solve(free, f[3], f[2], goal) is None]
    if not dead:
        continue
    score = npush * 2 + nmoved * 2 - len(free) * 0.5 - max(0, len(sol) - 12) + 2 * (len(dead) >= 1) + (len(dead) < len(fp)) * 3
    best.append((score, free, blocks, start, goal, sol, len(dead), len(fp)))

best.sort(key=lambda t: -t[0])
for score, free, blocks, start, goal, sol, nd, nf in best[:6]:
    print(f'score {score:.1f} sol {sol} dead first pushes {nd}/{nf}')
    for y in range(0, H + 2):
        row = ''
        for x in range(0, W + 2):
            c = (x, y)
            row += '@' if c == start else 'g' if c == goal else 'B' if c in blocks else '.' if c in free else '-'
        print(row)
    print()
