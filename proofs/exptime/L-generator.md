# L: layout generator for G6 ≤_p L_OFF^{W+C} (review 5 repair 2)

Workstream L, 2026-10-30. Game not run, nothing committed. Files: this note, `tools/exptime/L_gen.py` (imports
`review5_t1`, `X_build`, `A_core`, `A_check`, `A2_scd`, `B2_ani`, `B2_e2e`, `D_game` read-only), outputs in
`build/lgen/` (gitignored). One fix outside L: `X_build.diode_tile` (§6). Labels: **VERIFIED** = machine-checked
this session · **STRONG** = complete argument, not reviewed · **CONJECTURE** · **FAILED**.

## 0. Results

| Item | Status | Evidence |
|---|---|---|
| Generator: G6 instance → whole level (bus layout, v2 SCD/diode tiles, coin, crossovers, G′ wrappers + Lemma 5.6 chain as a routed planar curve, s, g) | **built** | `L_gen.py --run 20 3`: 20 instances, 14 YES / 6 NO, 77-1,926 crossovers, 2m50s with cached templates |
| S1 netlist attractor = G6 | **VERIFIED** | 0 mismatches on 20 (seed 3) + 300 (seed 11, 185 YES) + 20 (seed 1) instances |
| S2 network re-read from the concrete blocks (placed crossover flips) = G6 | **VERIFIED** | 0 mismatches on 20 + 20 instances; NC2 (all crossovers flipped) disagrees on 14/20 |
| NC1 (write paths without forced closes) | caught | 50/300 mismatches (seed 11); 0/20 on seed 3, so the 20-instance run alone would not show it |
| Static locality / planarity (block contract incl. diagonals, arm matching, tile-block adjacency, edge trace) | **VERIFIED** | every instance, every block type |
| Check path: every crossover flip × lane parity (8 templates), every tile block type | **VERIFIED** routed + independent replay (`validate`) ok | crossover: 20 level-1 + 126 level-2 G′, all 604 legs crossed once at Wt and once at Wb, 1,554-1,620 floor crossings, 364-431 SX, 36,364-38,490 chain points, 80-940 s each |
| Coverage: G′ routed = expected (level 1: SCDs incl. 20 per crossover; level 2: 4 per SCD + 1 per diode) and Wt = Wb = #legs | **VERIFIED** | all 20 instances (e.g. 77 crossovers: 1,545 + 9,743 G′, 52,877 check locations) |
| Z2 lint + Z1 (D_game `coin_lint`) on the generated coin tile; Z1 distance rule; no chain point within Chebyshev 4 of Z ∪ {E} | **VERIFIED** | all 16 instances with a coin (Z1 ok, Z2 ok, rule ok); 4 instances have n_Y = 0, no coin |
| Exact per-window boulder reach (C-audit Z1 step 1) | **VERIFIED** | protodiode 4 states / 4 cells, proto-precursor 28 / 8 cells, no port cell reached |
| S3 SCD-level postselection end to end on the generated network (one leaky SCD per run) | **VERIFIED** (abstract) | 10 instances on seed 3 + 9 on seed 1 (5-34 SCDs): winner = G6 in every run; without the check path the leak wins 2 + 5 NO instances |
| Full boulder-level attractor | not attempted | ≈ 10⁴-10⁵ main-layer boulders and ≈ 10⁷-10⁸ machinery boulders (estimate); infeasible |
| Machinery drawn as boards | **not done** | §7.1: certified planar curve + crossing list only (STRONG) |
| `crossover.json` diode `checks` off by one | **fixed** | §6; map, routes byte-identical; X_verify ALL AS EXPECTED |

**Verdict.** The main layer is generated concretely and checked. Its network equals the abstract game on
every instance tested. For every block type, the check path through all 684 locations of every crossover, all 25 of
every SCD tile and all 4 of every diode tile is routed as a planar curve, with the delimiters on the v2 legs. Z1/Z2
hold on the generated coin. What remains STRONG, not VERIFIED, is the cell-level realization of the machinery
gadgets on that curve (§7).

## 1. What was built

`python L_gen.py --run K SEED` builds, for K random G6 instances (review5_t1's distribution: |X|, |Y| ≤ 2, ≤ 3
clauses, both first movers), the whole level and checks it. Pipeline:

1. **Arena.** review5_t1's own `build` (B §3 with Lemma TS: plain SCDs only) is run with its `Arena` class swapped
   for a recorder, so the generator uses exactly the arena that review 5 verified (T1, 700 instances).
2. **Netlist.** Every arena edge is realized with B's base pieces: plain u→v = diode; O-tunnel = diode, the SCD's
   button O on a private node, diode; S-tunnel = diode, I…J, diode. Diode chains through degree-2 nodes are merged.
   The coin is one tile with ports E (entry; T's only neighbour), A, B. The diode c_m→g is removed: t = c_m and the
   check path ends in g.
3. **Bus layout (B §6.2).** One bottom row of tiles, all ports on top; every route edge is a directed 2-terminal
   corridor with its own track row (shorter spans lower, disjoint spans share rows); nodes of degree ≥ 3, start and
   t become junction tiles (combs); the bidirectional button link is kept inside an "SCD compound" tile (v2 SCD
   tile + a junction on O with ports Oin, Oout), so no bidirectional corridor ever meets a crossover. Tile order:
   DFS + barycentre sweeps + adjacent swaps minimizing interleaving pairs; crossings = interleaving pairs exactly.
4. **Concrete blocks.** Macro pitch P = 469 (the 453 × 432 crossover fits under every flip with its ports on the
   block midlines). Block types: empty, V, H, two corners, crossover (`build/xover/crossover.txt`, flipped
   horizontally if the track runs right→left, vertically if the column runs bottom→top), and per tile a k·P-wide
   block (v2 SCD tile under symmetry 7 = ports O, I, J on top, open or closed boulders; v2 diode tile; coin tile;
   comb) with nested L-shaped stubs to the column midlines. The level is the macro grid of these blocks; it is not
   written as one flat text (≈ 40k × 7k cells already for the smallest instance), but every block type is drawn
   concretely and checked, and the composition is checked through the block interfaces (§2).
5. **Check path.** B2 §3 order: t → level 1 (one Thm 5.3 G′ per SCD: tile-row SCDs and the 20 SCDs of every
   crossover, L′ = {O, I, J}, checks [O→O, I→J]) → level 2 (one G′ per raw component: every proto-precursor,
   L′ = {A, B, C, E, F}, checks [A→D, C→G, B→A, B→C]; every protodiode, L′ = {A, B, C, D}, checks [A→C, D→B]) → g.
   Global route: a boustrophedon through the macro rows on lane rows 2 and P−3 of every block (level 1 forward,
   level 2 back as a hairpin on the other lane: the two never cross in the lanes), with one excursion per block for
   each level; the lanes cross every arm they meet (CHX). Inside a block the excursions are routed on the
   concrete cells (§4).
6. **Checks** (§2, §3) and outputs: per instance `build/lgen/inst<seed>_<k>.json` (all numbers below) and `.txt`
   (macro map: `S` SCD, `d` diode, `j` junction, `C` coin, `X` crossover, `|-+` corridors), crossover templates
   `xtemplate_<fx><fy><parity>.json`, `summary_<seed>.json`.

## 2. Static checks on the generated level

- **Block contract** (`check_block`, every block type used): floor on the 1-cell border ring only at arm
  midpoints; every arm straight for 3 cells with walls beside it. Hence floor cells of two different blocks are
  8-adjacent only along a matched arm pair, diagonals included.
- **Arm matching** (`Level.check_static`): for every macro cell and every arm, the neighbour has the opposite arm.
- **Tile blocks** (`check_tile_block`): stubs, tile body, button junction, comb are 8-adjacent only at the intended
  join (a stub touches only its own port).
- **Inside tiles / crossovers**: the v2 tile contract `check_tile_legs` (asserted by X_build on every tile type) and
  `X_build.check_map` + X_verify (a)-(d) on the crossover map, re-run after the §6 fix: ALL AS EXPECTED.
- **Trace** (`Level.trace`): every route edge followed block by block from its source port arrives exactly at its
  target port; every crossover is used by exactly two edges, each straight through.
- **Z1/Z2** (coin): the coin tile [A # T # B] with E below T, exits above A and B, run through `D_game.coin_lint`
  (Z1 R_B, Z2 isolation); Z1 sufficient rule: no window within Chebyshev 3 of Z ∪ {E} (windows exist only in other
  blocks; distance from Z ∪ {E} to its block border is checked); the check-path router never uses a point within
  Chebyshev 4 of Z ∪ {E} (no machinery there, H4). Exact per-window reach (C-audit Z1 step 1) re-run for the two
  window types of the main layer.

## 3. Semantic checks

- **S1** (netlist): exact hero-vs-coin attractor on the netlist with ideal gadgets vs `review5_t1.g6`.
- **S2** (layout): the network is re-read from the concrete blocks (trace), every crossover as an ideal directed
  crossover whose passages follow the *placed* flips (a wrongly oriented copy would block its edge); attractor vs G6.
  Negative control NC2: all crossovers flipped → must disagree on some instance. NC1: B's write paths without the
  forced closes (review5_t1 `noforce`).
- **S3** (check path, abstract, B2_e2e style): the S2 network with every tile-row SCD wrapped in a Thm 5.3 G′
  (ideal SO/SD/WCX from B2_ani, `B2_e2e.Builder.gprime`), the SCD-level Lemma 5.6 chain t → … → g, a CHX on every
  diode input hallway, and in each run ONE SCD made checkable-with-leak (abstract: O→J leak to a broken state that
  is absorbing, keeps the leak and fails the check — Def. 5.2). Required: winner = G6 in every run. Control: the
  same leak without the check path (goal t).

## 4. The check-path router (`Router`, `block_template`, `validate`)

- **Grid.** Doubled resolution: cell (x, y) → point (2x+1, 2y+1); the point between two 4-adjacent floor cells is a
  floor *link*; a corner point is floor (never crossable) if a diagonal hero move or a 2×2 floor patch passes it.
  The chain is a 4-connected curve of non-floor points. It crosses floor only by a straight jump w1–f–w2 over one
  floor point f whose floor 8-neighbours all lie on the two sides of the jump line (both sides non-empty): this
  cuts exactly that corridor in two, where the crossing gadget goes.
- **Crossing kinds.** Delimiter WCX = jump over a leg's Wt (pass 1) or Wb (pass 2) slot, only by its own G′; CHX
  (= WCX) over any other corridor point; GX = WCX on the stub between a location and its Wb (only after that leg's
  G′ is done in time — Ani Fig. 23's crossings of dead segments); SX = jump over a straight piece of the chain
  itself. Never crossed: window cells, check locations (component port cells, pockets D/G, gsO/gsI/gsJ), coin
  cells, corner points, the coin halo. Level 1 never crosses the interior of an SCD whose level-1 G′ has not been
  done yet (its I→J / O→O check uses it); level 2 may cross SCD interiors except slots/windows/locations.
- **One G′** (`Router.gprime`): legs in angular order around the component (start after the widest gap); pass 1
  crosses every Wt sweeping one way, pass 2 every Wb sweeping back, with a clearance penalty on pass 1; then every
  check location must be reachable from the head without forbidden crossings (hooks; their curves are NOT drawn —
  any crossing with them is an SX in time order, counted only as a bound).
- **Both levels of a block** are routed tile by tile with two chain heads in the same tile order (so "SCD finished
  at level-1 time" is consistent), with undo/retries (ring sense, gap, clearance, permutations of a tile's
  components, rewinds); if that fails, the whole level-1 curve is drawn first, else the level-2 curve first. Drawing
  order is not time order: crossings between the two curves are SX either way, and the time-dependent permissions
  above are applied by time, not by drawing order.
- **Clearance halos.** Level-1 routing pays a penalty near component-leg delimiter points, and level-2 routing pays
  one near SCD tile-leg delimiter points. Without them, 3 of the 8 crossover templates failed (one SCD's level-1
  J/I leg boxed in by the other curve: tiles g019, g046, g018 / g028). With them all 8 route by the joint strategy.
  Templates 000/001/010 were routed by the earlier version without the level-2 halo. All 8 pass the same validator.
  A per-tile search deadline (90 s) and a per-strategy budget (25 min) keep failed searches bounded.
- **Validator** (independent replay of the stored trace, every template): pieces 4-connected; each floor point
  crossed once, straight, from non-floor neighbours; no forbidden point; every point used ≤ 2 times, twice only as a
  straight perpendicular self-crossing; every slot of every tile in the block crossed exactly once and only by its
  delimiter; Wt before Wb on every leg.

## 5. Sizes vs O(N⁴)

Per instance (seed 3; N = Σ|C_j| + |X| + |Y| + m; "machinery blocks" = 222·WCX + 50·SO + 11·SD + 83·SX, WCX
counting delimiters, every CHX incl. the lanes' crossings of every arm, and GX):

| N | crossovers | G′ (L1 / L2) | check locations | main layer (cells) | main floor / boulders | WCX / SO=SD / SX | machinery blocks |
|---|---|---|---|---|---|---|---|
| 3 | 77 | 1,545 / 9,743 | 52,877 | 40,334 × 7,043 | 1.31 M / 12,833 | 124k / 28.8k / 30.7k | 3.2·10⁷ |
| 3 | 248 | 4,974 / 31,359 | 170,202 | 104,118 × 14,078 | 5.06 M / 41,307 | 399k / 92.6k / 99.7k | 1.0·10⁸ |
| 7 | 486 | 9,744 / 61,423 | 333,388 | 171,654 × 17,830 | 10.1 M / 80,911 | 783k / 181k / 195k | 2.0·10⁸ |
| 10 | 1,176 | 23,561 / 148,491 | 806,013 | 284,214 × 33,307 | 27.3 M / 195,613 | 1.89 M / 438k / 472k | 4.9·10⁸ |
| 14 | 1,926 | 38,581 / 243,141 | 1,319,793 | 415,534 × 41,280 | 47.0 M / 320,303 | 3.10 M / 718k / 772k | 8.0·10⁸ |

Log-log fit over the 20 instances: crossovers, check locations and machinery all grow like ≈ N^1.5 on this
range (N ≤ 14). This is consistent with the O(N⁴) bound and does not test its exponent: the bound comes from
crossovers ≤ (#edges)² = O(N²), O(1) G′ per crossover, and the lanes crossing O(#columns) arms in each of
O(#rows) rows. Everything is dominated by the crossover blocks (126 + 20 G′ each). A hand-drawn smaller
crossover, or a layout with fewer crossings, would shrink it by large constants.

## 6. Bug fixed on the way: diode `checks` in crossover.json

`X_build.diode_tile` built `checks` from `cp` captured before `b.size()` (= `finish()`, which shifts all
coordinates), so all 184 diode entries of `crossover.json` `tiles.<gid>.checks` pointed one cell off (at the wall
between A and B, etc.). Legs (`legs.<name>.gside`) were correct, and neither X_verify (d) nor review5_abc/cd read
the diode `checks` field, so no verified claim depended on it. Fix: re-read `b.cport` after `finish()`. Rebuilt with
`python X_build.py` (seed 2): `crossover.txt` and `routes.json` byte-identical, json differs only in those 184
entries (now = the legs' g-sides, 0 mismatches of 544 component legs); `X_verify.py --moves 100000` re-run:
ALL AS EXPECTED (same c1 61,112 moves, same c2 counts). L_gen uses leg g-sides in any case.

## 7. Honest limits

1. **Machinery is not drawn.** WCX / SO / SD / SX exist only as verified networks of Fig. 32 boards (B2_ani); there is
   no concrete WCX board (≈ 222 boulders). The check path is a certified planar curve on the concrete main layer
   plus a classified list of crossings; turning it into cells needs a redraw that gives every crossing a box
   (standard orthogonal/box drawing of a planar graph in polynomial area): **STRONG**, not VERIFIED. The same
   redraw supplies room the 1-cell geometry lacks (e.g. between a location and its Wb).
   **Update 2026-10-30 (M-machinery.md):** WCX / SO / SD / SX / MSC are now drawn as concrete boards (WCX 478 × 608,
   276 boulders) with exact port behaviour = ideal (VERIFIED), plus one SO/SD + hook unit (HK); placement on the
   curve stays STRONG.
2. **Hook curves** (SD exit → a_i, b_i → SO entrance, and the SO/SD placement) are checked for reachability only;
   their crossings (SX in time order) are counted as a bound, not drawn.
3. **S3 is abstract** at the component level: components are postselected (B2_e2e "scdlevel"), the leak is an
   abstract O→J, the crossovers' SCDs and the crossing gadgets inside G′ are ideal, the CHX are on diode inputs
   rather than at the routed positions, and leaks are tested one SCD at a time (all at once: 3^#SCD positions).
   B2_e2e remains the only end-to-end run on raw components (one SCD).
4. **No boulder-level attractor**: the smallest instance has ≈ 13k main-layer boulders plus ≈ 2·10⁶ machinery
   boulders (estimate); D_game handles ~10⁶ positions of a few dozen boulders. Not attempted.
5. **Router success is empirical** (search with retries), not a theorem: it is VERIFIED for the block types it
   produced (every crossover flip/parity, every tile block); a different crossover map could need re-running.
6. Sizes are those of this generator (bus layout, P = 469, one crossover = 453 × 432); a hand layout would be far
   smaller. Polynomial bound: crossovers ≤ (#edges)², every crossover a constant-size block, check-path
   machinery O(#blocks · P) per lane plus O(1) per G′.

## 8. Reproduce

`python L_gen.py --xblock FX FY PARITY` (one crossover template, 1-16 min; the 8 are cached in
`build/lgen/xtemplate_*.json`) · `python L_gen.py --run 20 3` (20 instances with cached templates, ~3 min; writes
`inst3_*.json/.txt`, `summary_3.json`) · `python L_gen.py --tile` (tile-block templates) · S1/NC1 on 300 instances:
`L_gen.netlist` + `solve_net` + `noforce_winner` (seed 11, a few minutes).
