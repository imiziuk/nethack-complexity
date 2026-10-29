# D: machine checker for hero-vs-nature boulder games (teleport coin)

Workstream D, 2026-10-29. Tools: `tools/exptime/D_game.py` (model, Python solver, export, lint),
`tools/exptime/D_game.rs` (fast solver, same rules), `tools/exptime/D_tests.py` (tests),
`tools/exptime/levels/*.txt` (coin test levels). Game not run, nothing committed.
Labels: **VERIFIED** = checked by running the tools this session; **DEFINITION** = modelling choice.

## 1. Model (DEFINITION)
Movement = `tools/check_small.py` (hu-on-lower §2), unchanged:
- hero steps to an 8-neighbour: floor, no boulder, not an unplugged hole (holes are never entered: loss);
  a diagonal step is refused iff both corner cells are bad (not floor, or boulder) [Sokoban corner rule];
- an orthogonal step into a boulder pushes it iff the cell beyond is floor without boulder (heavy hero, no squeeze,
  no diagonal pushes); a boulder pushed onto a hole plugs it (both vanish, cell becomes floor).

Coin (feasibility §3, W9 result "landing set = free non-trap cells of Z"):
- **T** = teleport trap (floor for the corner rule). A step onto T (same step rules) gives a **nature node**; nature
  picks the landing cell among T's landing set minus cells holding a boulder or an unplugged hole (`teleok` =
  goodpos and no trap). The hero is never left on T. `:zone` gives the NetHack set (all non-trap floor of Z);
  `:trap ... land ...` gives an explicit set.
- **Design violations** (reported, never silently used): a reachable push of a boulder onto a trap (NetHack: `rloco`,
  level-wide relocation; the move is removed from the game); a reachable trap entry with an empty free landing set
  (counted as a hero loss).
- **Lint** (static, from C-audit.md / INTERFACE.md): Z1 = boulder closure R_B avoids Z ∪ N8(Z) (Z = T + landing
  cells, N8(Z) ⊇ entry E); Z2 = T has exactly one floor 8-neighbour and T, landing cells are pairwise non-adjacent.
- Not modelled: the C-4 "dead coin" (`moves ≤ 0` after wrap → hero stays on T). It is a time window, and a timeless
  model with a permanent null option would make every coin a wall (nature repeats it); Z2 + Z4 handle it on paper.

Game (R3, exptime-model.md §1): full information, hero wins iff she can force a player position with the hero on g
(optionally: and boulders/holes equal to a named state); infinite plays lose (least fixed point).

## 2. State and why the region collapse is exact (DEFINITION + argument)
- Player position = (boulder set, unplugged-hole set, hero region); nature position = (boulder set, holes, trap).
- Hero region = connected component (8-moves, corner rule) of free **non-trap** cells. Trap cells are left out of the
  flood, so walking inside a region never triggers nature; walking is reversible (corner rule symmetric), so every
  cell of one region has the same successors: pushes whose hero cell is in the region, trap entries from a region
  cell, and "g in region" = win. Landings in the same region are merged into one nature option (the hero can walk
  between them anyway). Canonical key = min node of the region.
- This is exactly what the task warned about: regions are cut at every coin cell, never merged across it.
- Compression as check_small: static floor components + dynamic cells (boulder closure ∪ holes, seeds include holes
  since a plugged hole is floor a boulder can rest on) + one node per trap.
- Solver: build the full reachable graph (goal-independent), then the attractor by backward counting
  (player node: one winning successor; nature node: all successors winning; no successors = loss). Rank = attractor
  round; the printed hero strategy always moves to a strictly lower rank, so it terminates.

## 3. Level format
ASCII grid: `.` floor, `0`/`B` boulder, `^` hole, `@` start, `G`/`g` goal, `T` teleport trap, lowercase letter
(not g) = floor cell that is also a port named by the letter; anything else (`#`, `-`, `|`, space, ...) = wall.
x = column, y = row, 0-based. Directive lines (anywhere): `:zone x0 y0 x1 y1` · `:trap x y land x1 y1 x2 y2 ...` ·
`:port NAME x y` · `:state NAME x y x y ...` (boulder set; holes = all grid holes unplugged; `init` = the grid).
`//` = comment. Example `levels/coin_tile.txt` (B's tile [A wall T wall B], passes Z1/Z2):
```
###########
#a#T#b#####      Z = row 1, x 1..5;  E = (3,2)
#.#.#.#####
#.#.#.....#
#.#@......#
#.#########
#........G#
###########
:zone 1 1 5 1
```

## 4. Usage
```
cd tools/exptime
python D_game.py LEVEL [--start P] [--goal Q] [--state S] [--goal-state S] [--tree 60] [--json]
python D_game.py LEVEL --relation [--json]      # gadget traversal relation (for A)
python D_game.py LEVEL --rust [...]             # same query, solved by D_game.rs (auto-built into target/)
python D_game.py LEVEL --export M.dmodel        # D-model v1 file; then: target/D_game.exe M.dmodel [--relation] ...
python D_game.py LEVEL --lint                   # Z1/Z2 only
python D_tests.py [--fuzz 300] [--rust-every 3] [--seed 1] [--skip-a]
```
P/Q = port name, `@`, `G`, or `x,y` (Rust: port names only; `@`/`G` are always ports).
Output: `RESULT result=WIN|LOSE ... rank coop_reach violations ...`; then on WIN the hero's strategy tree in
macro-moves (`push boulder (x,y) E`, `step onto trap (x,y)`, `nature: k choice(s)` with one sub-tree per landing,
`goal reachable on foot`, `(same as [n])` for shared sub-trees; walking inside a region is free and not printed), on
LOSE nature's counter-strategy (every reachable nature position with the landing nature picks and the options).
`coop_reach=True` with LOSE means "reachable if nature cooperates" (R2 yes, R3 no): nature is what blocks.

**Relation mode (for A's gadget windows).** Ports = lowercase letters + `:port` + `@`/`G`; start states = every
`:state` (+ `init`). For every start state s, ports p ≠ q it prints `s p -> q exit=* WIN|lose` (hero can force reaching
q, any boulder state) and `exit=s'` for each named state s' (force reaching q with exactly boulders s'). One graph is
built from all (s, p) starts and one attractor is run per target, so a window costs one exploration. Model a window
with walls everywhere except the port cells; the hero standing on q is the exit event (she cannot leave the window).

## 5. Tests (VERIFIED, `python D_tests.py`)
| Test | What | Result |
|---|---|---|
| (a) | 8 smallest distinct L_ON* levels from check_small (1-2 vars), check_small BFS vs D_game.py vs D_game.rs | all agree (7 SAT WIN, 1 UNSAT LOSE) |
| (a') | all 23 UNSAT check_small levels exported both ways: tools/fastbfs vs D_game.rs | identical counts on all 18 that finish (§6) |
| (f) | fuzz: random 7×5 levels with 0-2 traps, 1-5 boulders, 0-2 holes, explicit landing sets; D_game.py vs an independent naive solver (exact hero cell, no region collapse, plain fixed-point iteration) vs D_game.rs; also checks the violation flag | 1000 + 1500 + 2000 + 600 levels (seeds 5, 7, 11, 3), 0 mismatches after the fix below; ~4% of levels are LOSE only because of nature |
| (b) | `levels/coin_lose` (landing b leads back: nature forces a loss), `coin_win` (both landings reach G), `coin_block` (hero first pushes a boulder onto landing cell b, so nature must land on a: WIN in 3 macro-moves), `coin_violation` (only route = boulder onto T: LOSE + violation), `coin_tile` (B's tile, LOSE) | all as expected in py, rust, naive |
| (c) | relation mode on `levels/coin_states.txt` (3 named states, 4 ports): Python vs Rust | 132 entries identical |

Bug found by the fuzz and fixed: pushes out of a plugged hole cell were missing (a hole cell can later hold a
boulder). check_small is not affected (its closure walks through hole cells as targets).

## 6. Performance (VERIFIED)
D_game.rs: limits 512 nodes / 384 dynamic cells / 64 holes / 64 ports (consts NW, DW); key 64 bytes; Fx hash;
bit-parallel region flood with the check_small incremental base after pushes; ports-in-region mask per position.
**(a') all 23 UNSAT check_small levels** (no traps), tools/fastbfs vs D_game.rs at a 4 M cap: on all 18 that finish,
the position counts are **identical** (364 ... 2,139,544) and both say unreachable; the other 5 hit the cap in both (same as
the earlier 25-min timeouts). Speed is the same as fastbfs: 2,139,544 positions in 47 s (fastbfs 42 s);
1,175,464 in 15-22 s. About 40-70 k positions/s, so tens of millions are feasible
(memory ≈ 120 B/position + 12 B/edge). D_game.py: ~2-10 k positions/s, fine for gadget windows.

## 7. Limits / notes for A, B, C
- One-shot semantics of a port: the checker does not model what lies outside a window; a gadget's G2/G3 (B §5.1)
  "returns to entry with same state or exits by an ideal transition or is broken" is a set of relation queries plus
  `--goal-state`; "broken" must be encoded as named states by A.
- Pits (Z3), HP, time, Fumbling, the dead coin and encumbrance are not modelled (C's audit covers them).
- Nature here only chooses landings. Everything else is deterministic, as C-1 requires.
