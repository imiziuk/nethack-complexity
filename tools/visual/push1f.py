"""Tiny Push-1F solver (orthogonal moves, push one block, no pull) used to design and check the demo puzzles.

Board text: '-' or '|' or '#' = fixed (wall), '.' = empty, 'B' = movable block, '@' = robot start, 'g' = goal.
"""
from collections import deque
import sys

DIRS = {'h': (-1, 0), 'l': (1, 0), 'k': (0, -1), 'j': (0, 1)}


def parse(text):
    rows = [r for r in text.strip('\n').split('\n')]
    free, blocks, start, goal = set(), set(), None, None
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in '.B@g':
                free.add((x, y))
            if c == 'B':
                blocks.add((x, y))
            if c == '@':
                start = (x, y)
            if c == 'g':
                goal = (x, y)
    return free, frozenset(blocks), start, goal


def step(free, hero, blocks, k):
    dx, dy = DIRS[k]
    s = (hero[0] + dx, hero[1] + dy)
    if s not in free:
        return None
    if s in blocks:
        r = (s[0] + dx, s[1] + dy)
        if r not in free or r in blocks:
            return None
        return s, (blocks - {s}) | {r}, True
    return s, blocks, False


def solve(free, blocks, start, goal):
    """BFS over (hero, blocks); returns the shortest key string to reach goal, or None."""
    q = deque([(start, blocks)])
    prev = {(start, blocks): None}
    while q:
        h, b = q.popleft()
        if h == goal:
            path = []
            st = (h, b)
            while prev[st]:
                st, k = prev[st]
                path.append(k)
            return ''.join(reversed(path))
        for k in DIRS:
            n = step(free, h, b, k)
            if n:
                st = (n[0], n[1])
                if st not in prev:
                    prev[st] = ((h, b), k)
                    q.append(st)
    return None


def play(free, blocks, start, keys):
    h, b = start, blocks
    for k in keys:
        n = step(free, h, b, k)
        if n:
            h, b = n[0], n[1]
    return h, b


if __name__ == '__main__':
    free, blocks, start, goal = parse(open(sys.argv[1]).read())
    print('solution:', solve(free, blocks, start, goal))
    for keys in sys.argv[2:]:
        h, b = play(free, blocks, start, keys)
        print(keys, '-> hero', h, 'on goal' if h == goal else '', '| goal still reachable:',
              solve(free, b, h, goal) is not None)
