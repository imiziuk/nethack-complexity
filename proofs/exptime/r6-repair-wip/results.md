**Results (run 2026-10-29, `python tools/check_small.py --workers 11`, Windows, 12-core CPU, Python 3.14;
37 min wall, 11 workers, < 2 GB total memory; the 10-minute target was not met because exhaustive search of the larger unsatisfiable levels is inherently slow in Python):**

| Check | Result |
|---|---|
| levels built (generator asserts Lemma 4.1 isolation and Lemma 4.2 overlap rules on every tile) | 393/393 distinct levels (covering all 513 instances), no assertion failure |
| satisfiable levels: intended play replayed in the exact model reaches g | 370/370 levels (all 455 satisfiable instances) |
| hunger along the intended play (start 900, −1 per move, eat ≤ 860, 2 turns per meal) | min 859 (never Hungry); ≤ 2 visits per cell; longest cookie-less run 2 |
| satisfiable levels: exhaustive BFS finds g (sanity check of the search, 20 smallest) | 20/20 |
| unsatisfiable levels: exhaustive BFS, no pruning, g unreachable | UN20/20 |
| largest exhaustive search | 734,784 states (BFS states = boulder set × unplugged holes × hero free region) |
| largest level / most crossovers / longest intended play | 440×286 cells / 23 / 4,241 moves |
| mismatches (reach ≠ sat) | 0 (no level where g is reachable but φ is unsatisfiable, or vice versa) |

Not covered: levels were never loaded in the real game (they exceed 80×21); the exhaustive part covers n, m ≤ 3
only (larger instances: layout + replay only, below).
- **Layout stress test (beyond n, m ≤ 3):** 767 random planar monotone instances with 2 ≤ n ≤ 6, 1 ≤ m ≤ 6 (seed 7,
  4 minutes): every level built with all Lemma 4.1/4.2 assertions holding, within the §4.6 bounds on w, h and #X
  (max 41 crossovers), and every satisfiable one won by the replayed intended play with ≤ 2 visits per cell
  [auto-experimentally verified; no exhaustive search at that size].
