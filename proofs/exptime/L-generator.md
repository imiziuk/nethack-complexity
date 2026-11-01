# L: layout generator for G6 ≤_p L_OFF^{W+C} (review 5 repair 2)

Workstream L, 2026-10-30. Game not run, nothing committed. Files: this note, `tools/exptime/L_gen.py` (imports
`review5_t1`, `X_build`, `A_core`, `A_check`, `A2_scd`, `B2_ani`, `B2_e2e`, `D_game` read-only), outputs in
`build/lgen/` (gitignored). One fix outside L: `X_build.diode_tile` (§6). Labels: **VERIFIED** = machine-checked
this session · **STRONG** = complete argument, not reviewed · **CONJECTURE** · **FAILED**.

## 0. Results

| Item | Status | Evidence |
|---|---|---|
| Generator: G6 instance → whole level (bus layout, v2 SCD/diode tiles, coin, crossovers, G′ wrappers + Lemma 5.6 chain as a routed planar curve, s, g) | **built** | `L_gen.py --run 20 3`: 20 instances, 14 YES / 6 NO, 77-1,926 crossovers, 2m50s with cached templates |
| S1 netlist attractor = G6 | **VERIFIED on the tested set** (F6) | 0 mismatches on 20 (seed 3) + 300 (seed 11, 185 YES) + 20 (seed 1) instances |
| S2 network re-read from the concrete blocks (placed crossover flips) = G6 | **VERIFIED on the tested set** (F6) | 0 mismatches on 20 + 20 instances; NC2 (all crossovers flipped) disagrees on 14/20 |
| NC1 (write paths without forced closes) | caught | 50/300 mismatches (seed 11); 0/20 on seed 3, so the 20-instance run alone would not show it |
| Static locality / planarity (block contract incl. diagonals, arm matching, tile-block adjacency, edge trace) | **VERIFIED** | every instance, every block type |
| Check path: every crossover flip × lane parity (8 templates), every tile block type | **VERIFIED** routed + independent replay (`validate`) ok | crossover: 20 level-1 + 126 level-2 G′, all 604 legs crossed once at Wt and once at Wb, 1,554-1,620 floor crossings, 364-431 SX, 36,364-38,490 chain points, 80-940 s each |
| Coverage: G′ routed = expected (level 1: SCDs incl. 20 per crossover; level 2: 4 per SCD + 1 per diode) and Wt = Wb = #legs | **VERIFIED** | all 20 instances (e.g. 77 crossovers: 1,545 + 9,743 G′, 52,877 check locations) |
| Z2 lint + Z1 (D_game `coin_lint`) on the generated coin tile; Z1 distance rule; no chain point within Chebyshev 4 of Z ∪ {E} | **VERIFIED** | all 16 instances with a coin (Z1 ok, Z2 ok, rule ok); 4 instances have n_Y = 0, no coin |
| Exact per-window boulder reach (C-audit Z1 step 1) | **VERIFIED** | protodiode 4 states / 4 cells, proto-precursor 28 / 8 cells, no port cell reached |
| S3 SCD-level postselection end to end on the generated network (one leaky SCD per run) | **VERIFIED on the tested set** (abstract) | 10 instances on seed 3 + 9 on seed 1 (5-34 SCDs): winner = G6 in every run; without the check path the leak wins 2 + 5 NO instances |
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
4. **Concrete blocks.** Macro pitch P = 597 since review 6 (§9; r5: P = 469 for the 453 × 432 crossover); the 569 × 550 crossover fits under every flip with its ports on the
   block midlines. Block types: empty, V, H, two corners, crossover (`build/xover/crossover.txt`, flipped
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
6. Sizes are those of this generator (bus layout, P = 469, one crossover = 453 × 432; since §9: P = 597, 569 × 550); a hand layout would be far
   smaller. Polynomial bound: crossovers ≤ (#edges)², every crossover a constant-size block, check-path
   machinery O(#blocks · P) per lane plus O(1) per G′.

## 8. Reproduce

`python L_gen.py --xblock FX FY PARITY` (one crossover template, 1-16 min; the 8 are cached in
`build/lgen/xtemplate_*.json`) · `python L_gen.py --run 20 3` (20 instances with cached templates, ~3 min; writes
`inst3_*.json/.txt`, `summary_3.json`) · `python L_gen.py --tile` (tile-block templates) · S1/NC1 on 300 instances:
`L_gen.netlist` + `solve_net` + `noforce_winner` (seed 11, a few minutes).

## 9. Review-6 repairs (2026-10-31): drawn check walks, GX rule, scaled SCD tile, L_e2e

**What changed in `Router` (default; the old behaviour is kept only behind env flags for the positive controls).**
- **GX rule (F1).** A GX (WCX on a leg's g-side stub) is allowed only on a leg of a G′ that FINISHED earlier in time
  (`dead` without `own`). Before, every G′'s hooks were searched with `dead = own | finished`, i.e. they could cross
  the stubs of the component's own legs during its own checks. Own middle segments stay crossable after both passes
  (dead). `LGEN_GX_RULE=own` restores the old rule (positive control only).
- **Ani placement, drawn (F2).** After pass 2, `_checks` draws Ani's Fig. 23 walk on the chain itself, per check
  i = (a_i, b_i): Out_{i−1} → Op_i (the chain passes a point j next to the SO_i box p) → SD_i (the piece ends at the
  SD_i box q); a new piece starts at p (Out_i). Boxes are joined to their location by a **wire**: a path of
  reserved wall points from the box to the location's non-floor 4-neighbours (reserved for every location from the
  start, `reserve_locations`). A wire crosses no floor, no other wire, and is never used or crossed by any chain;
  it may cross an already drawn chain piece only by an SX in which the wire is the LATER line (`WSX` events; a level-1
  wire never crosses a level-2 piece). Wire length is penalized (`LGEN_WIRE_PEN`, default 4, ending cost only), so
  most wires have length 0. The old reachability-only hooks are `LGEN_PLACEMENT=hk` (positive control only).
- **Search.** `joint` checks after every tile that both chain heads can still reach their lane exits (lookahead);
  `_tile_solutions` enumerates the level-2 G′ routings depth-first over the variants of every G′ (`_route_seq`; the
  first leaf is the old greedy routing), so a lookahead rejection gets the next routing instead of the next
  permutation; with no earlier tile within 140 cells the rewind falls back to the latest tiles (`LGEN_FAR_REWIND`).
  Pass 1 now also keeps its distance from the leg bodies (Wb and g-side are penalty centres, `LGEN_PEN_LEGS`):
  with stubbed legs the window penalty alone let pass 1 hug a leg between Wt and Wb and seal pass 2 out.
  `LGEN_STRATS` overrides the strategy order of `block_template`; the SCD tile and the crossover templates route
  only with `l2first` (level-2 curve drawn first; time order is still level 1 then level 2) and long per-tile
  deadlines (`LGEN_TILE_SECS` 1500-3000). For `l2first` two drawing-order aids: **XW** (a level-1 piece drawn after
  a level-2 wire may cross it straight and perpendicular: an SX whose earlier line in time is the chain, i.e. the
  same gadget as WSX; `LGEN_XW=0` off; `validate_rules` checks each one) and a **level-1 keep-out**
  (`keepout_l1`: the side points of every tile-leg slot and a box/chain spot next to every level-1 wire-tree root
  stay reserved while level 2 is drawn and are released before level 1; `LGEN_L1_KEEP=0` off). Deadlines are
  wall-clock, so results depend on machine load: run few jobs in parallel.
- **Bookkeeping.** `Router.gseg` (one record per routed G′: trace and event range, own legs, checks, locations),
  `ev_ti` (trace index of every event), events `OP` / `SD` / `OUT` / `WSX`; `res` is now part of the snapshot;
  `dijkstra(..., tpen=)` charges a target's cost only when the path ENDS there.
- **`validate_rules`** (called by `validate`, every template): replays F1 by time order (level-1 G′s, then level-2,
  each in routing order), independently of the router's `dead` sets: every GX on a leg of a G′ finished earlier and
  never own; own middles crossed only after the G′'s last Wb; never the own SCD interior at level 1; F2 contact
  geometry: OP, SD, OUT per check in order; box–wire–location 4-paths (wire SX: straight perpendicular chain point,
  level rule); wires never on a chain point, floor or the coin halo.
- **`gprime_items` → `template_record['gseq']`**: every routed G′ as an item list for `L_e2e.py`.
- Crossover templates of the repaired router are `build/lgen/xtemplate_r6_<fx><fy><p>.json` (`LGEN_TPL_TAG`); the
  review-6 state's `xtemplate_<fx><fy><p>.json` are kept unchanged for comparison.
- `assemble`: `contacts_drawn` (OP = SD = OUT = #checks) is part of `coverage_ok`; wire SX count in machinery SX.

**Scaled SCD tile (needed for F1/F2 routing).** Under the repaired rules the r5 SCD tile (`X_build.scd_tile_r5`)
could not be routed in either parity (both chains, the check walks and their wires do not fit through the 1-cell
gaps between adjacent legs; failures at d1 Wt d1.A, prec Wb prec.E / Wt prec.F, prec SD A). `X_build.scd_tile`
now takes (sv, sp) = (`SCD_SV`, `SCD_SP`) = (3, 6): every component leg gets sv g-side stub cells between its port
and Wb (`_TB.sleg`; the g-side, i.e. the L_gen check location, is the stub's last cell), and the legs of ports one
cell apart (pp A|B, pd A|B, pd C|D) are bent apart to sp columns. Raw gadget windows, node structure and the leg
contract are unchanged (`check_tile_legs`; new `check_tile_spacing`: no unintended diagonal touch); sv = 0, sp = 2
reproduces the r5 tile cell for cell (all three variants). In `Router` the stub cells and the links inside a stub
have role GXR (crossing one is a GX on that leg) and a stubbed g-side is LOC. Smaller scales failed: (2, 4), (3, 4),
(2, 6), (2, 7) in at least one parity; (3, 6) is the smallest that routed in both. The tile grows from 19 × 37 to
29 × 55 (variants 0, 2; variant 1: 21 × 43 → 31 × 61), the crossover map from 453 × 432 to 569 × 550, and the macro pitch from P = 469 to **P = 597**
(MID 298; same 4-cell margin under every flip).

**Results (2026-10-31; Windows, 12 cores; routing is deadline-bound, so times depend on load).**

| Check | Result |
|---|---|
| r5 SCD tile under the repaired rules | FAILED both parities (pen 4 + lookahead, 120 s deadlines) |
| scaled tile, sv = 0, sp = 2 vs `scd_tile_r5` | identical cells / owners, variants 0-2 |
| crossover rebuilt with the scaled tile (`X_build`, seed 2) | 569 × 550, 66 tiles, 166 boulders, all map checks pass (r5 copy kept as `build/xover/*_r5.*`) |
| `X_verify.py --moves 100000` on the new map | ALL AS EXPECTED (map network SOUND + COMPLETE, 604 split legs, SCD tile 12 clean SOUND/COMPLETE, c2 random walk 100,000 moves) |
| `review5_abc.py`, `review5_cd.py` | v2 tile passes (clean set 3, broken absorbing, SOUND); v2 diode checks split |
| exact window reach (`window_reach`) | unchanged: the raw windows are unchanged |
| tile templates dio / scdc, parity 0 / 1 (P = 597, `l2first`) | all routed; `validate` ok, `validate_rules` no errors; scdc: 14 checks each, GX 8 / 2 (all on finished legs) |
| `L_e2e.py tiles` | ALL AS EXPECTED (repaired 12/12 exact; controls as required; diode game LOSE/WIN vs review-6 WIN/WIN) |
| `review6_weak.py --generated`, `review6_hooks.py`, `review6_hooks2.py` | every clean set = the true one; no own or pending GX |
| crossover templates `xtemplate_r6_<fx><fy><p>` | **011 routed** (146 G′, validate ok, rules clean, L_e2e 146/146 exact). **000, 001, 010, 100, 101, 110, 111 FAILED**: level 2 routes, then level 1 cannot finish one SCD (000/001: g045 tile.O Wb / SD contact at O; 010: g028 tile.J; 100: g041 tile.J Wb; 110: g056 Op contact at J; 111: g055 tile.O Wt), the same tile in two or three runs each; 101: level 1 stuck at g019 / g034 / g041 (tile.J, tile.O); second run stuck at g034 tile.O Wb again, stopped |
| `--run 20 3`, fresh seed | not run: blocked by the missing crossover templates (coverage would fail by construction) |

**Why the 7 crossover flips fail, and what geometry is needed.** In `l2first` the whole level-2 curve (component
G′s, their check walks, boxes and wires) is drawn first; the level-1 SCD composite must then still reach both
sides of its tile-leg slots and box spots next to O, I, J. Those slots sit right next to the junction cells gsO /
gsJ, which the scaled tile packs between tog.E's leg, the D pocket and prec's spread A leg (gsO) or between
prec.F / d2.B and the J approach (gsJ; in variant 2 the J approach also runs down the left side just above O).
Level 2 fills these pockets; level 1 may cross level-2 chains (SX) and wires (XW) but not boxes, own-SCD interior,
pending stubs or wire-tree roots. `joint` and `l1first` (level 1 first) did not route even the single SCD tile (old
search: level-2 G′ failures; current search: no result within 70 min). A level-1 keep-out reserved during level 2 (`LGEN_L1_KEEP=1`)
made level 2 fail. Needed: room at the tile legs too, e.g. g-side stubs on tile.O / tile.I / tile.J (between the gs
node and the tile-leg Wb, like the component stubs) so that the level-1 slots and box spots lie outside the packed
junction pockets, and the variant-2 J port moved up the left side away from O; then rebuild the crossover, update
P, and re-route all 8 flips.


## 10. Review-6 round 2 (r6b, 2026-10-31): tile-leg stubs, template library, constructive layout (F4)

### 10.1 What changed
- **Tile-leg stubs** (`X_build.scd_tile`, `SCD_TV` = 3, env `XB_SCD_TV`): tile.O / tile.I / tile.J get 3 g-side stub
  cells between the gs junction (gsO / gsI / gsJ) and the tile leg's Wb, built by the same `_TB.sleg` as the component
  stubs; the SCD locations scd.O / I / J are the stubs' last cells. In L_gen the stub cells and links have role GXR on
  leg tile.X and the stubbed g-side is LOC, so the level-1 delimiters and box spots of every SCD sit 3 cells outside
  the junction pockets (gsO between tog.E, the D pocket and prec's spread A leg; gsJ between prec.F / d2.B).
- **Variant-2 J port** at the top-left corner (approach: right side up, along the top, 2 cells down the left side)
  instead of 4 cells above O; the left side between J and O is now empty.
- **Reproducibility.** `XB_SCD_GEOM=r6a` (tv = 0, old J port) rebuilds the round-1 tile; checked cell for cell (cells,
  owners, ports) against the round-1 `X_build` for variants 0-2; (sv, sp, tv, geom) = (0, 2, 0, r6a) is still the r5 tile.
  Round-1 crossover kept as `build/xover/*_r6a.*`, its 011 template as `build/lgen/xtemplate_r6a_011.json`.
- **Bug found (round 1): crossover legs lost their stubs.** `X_build.main` serialised `legs` without `stub` / `port`, so
  in every crossover template of round 1 the component stubs were SCD interior (not GXR) and the stubbed g-sides were
  not LOC: `validate_rules` could not see a GX on a crossover stub. Fixed (json legs carry `stub`, `port`); the round-1
  result "011 routed, rules clean" is superseded by the r6b runs below.
- **Junction comb** (`L_gen`, `LGEN_JN=bar`, default; `fan` = old): one horizontal bar under all n port columns and one
  straight tooth per port. The old nested fan used turn row P − 20 − 2j for its j-th left-goer, which meets lane row 2
  for n ≳ 560; the bar uses the same rows for every n (checked: `check_block`, `check_tile_block` and the lane
  assertion for n = 1, 2, 3, 13, 600).
- **Template library on disk** (`template_for`): the G′-carrying tile templates are cached like the crossover
  templates (`build/lgen/ttemplate_r6_<kind>_<parity>.json`), every template carries `floor_hash` (sha256 of the
  block's floor cells and placed tiles; boulders ignored, the router never reads them) and a cached template is used
  only if the block's hash matches. A G′-carrying tile block outside {scdc 4P, dio 2P with all top arms} fails an
  assertion instead of starting a search.
- New crossover: `X_build` seed 2: **556 × 560**, 66 tiles, 166 boulders (77 s); macro pitch **P = 587, MID = 293**
  (smallest odd P with the old 4-cell margin under every flip).

### 10.3 Constructive layout argument (review 6 F4) — STRONG

Review 6 F4: polynomial time rested on a router with deadlines, budgets and rewinds that may fail on a new
instance. The answer is that **no routing search runs on the instance**: every search happened once, on a fixed
finite set of blocks, and its output is a constant of the reduction.

**Lemma Lib (finite library).** Every block of every generated level is one of: E, V, H, BL, BR (P × P); a crossover
flip X(fx, fy) (P × P, 4 flips); a tile block of kind scdc (4P × P), dio (2P × P), coin (3P × P) or jn (nP × P, any
n ≥ 1). Only scdc, dio and X contain placed tiles (components with G′s); E, V, H, BL, BR, coin and jn contain none.
*Proof.* `Level.__init__` / `Level.blocks` / `build_tile_block` (§1 step 4) produce exactly these kinds; tile kinds
come from `Bus` (`TILE_PORTS`: scdc = Oin, Oout, I, J; dio = 2 ports; coin = E, A, B; jn = one port per edge end). ∎
For a G′-carrying tile block the geometry is a closed formula of (kind, used ports): the tile body (`XB.scd_tile(0)`
under symmetry 7, or the diode tile) centred at a fixed offset, and one fan stub per USED port to that port's column
midline. Every port of an scdc / dio tile is used whenever `Bus.dead` is empty, and then all scdc blocks have one
floor and all dio blocks another (`floor_hash`; boulders differ between open and closed SCDs, the router ignores
them). `Bus.dead` was empty on all 320 instances of seeds 3 and 11; the generator asserts it (`template_for`), so an
instance with a dangling SCD tunnel stops with an error, never with a silently wrong level. **Lemma Mono** covers that
case without any search: deleting a straight stub (floor cells and links that are not slots, windows, locations,
stubs or wires of any G′) from a block with a valid routed template leaves a valid template: every chain point stays
non-floor, each former crossing of the deleted stub becomes a plain chain step, and every validator condition (on the
remaining floor points, the tile slots, the time-ordered GX/contact rules) is unchanged or vacuous. (STRONG; L_gen
asserts instead of implementing the restriction.)

So the check path needs exactly **12 templates**: scdc and dio, each in 2 parities, and the 4 crossover flips in 2
parities. They were routed once (the router's search, deadlines and strategy order are irrelevant to the reduction:
only their output is used), stored with their floor hash, and each is verified by the independent replay `validate`
+ `validate_rules` (P1-P4 by time order) and by `L_e2e.py` (every G′ rebuilt with its crossings: c_out reachable ⇔
clean). Blocks without tiles carry only the two lanes, and `_block_template` asserts for every one of them that each
lane row meets only CORR floor, perpendicularly, away from every halo; for E, V, H, BL, BR, coin this is one finite
check each, and for jn (bar comb, §10.1) the lane rows 2 and P − 3 meet only the n vertical teeth for every n, since
the bar and the tile body lie in rows P − 16 .. P − 14 and the teeth are straight.

**Theorem L (uniform polynomial assembly).** Given a G6 instance of size N, `assemble` computes the level (main layer +
check-path curve + crossing list) in time polynomial in N, without search, and the output satisfies P1-P4 and the
coverage condition whenever the 12 library templates do.
*Proof.* Steps and bounds (E = #route edges, T = #tiles; E, T = O(N) after `contract`):
1. netlist + contraction: linear in the arena (review5_t1's `build`, O(N) gadgets).
2. `Bus.order`: DFS, then 80 barycentre sweeps with a FIXED seed (deterministic), then adjacent-swap descent; each
   accepted swap lowers the interleaving count, which is ≤ E², so ≤ E² rounds of T swaps, each scored in O(E²):
   O(E⁵) worst case. Any order is correct (crossings = interleaving pairs, each realized by one crossover block);
   only the size depends on its quality.
3. `Bus.rows`: greedy track assignment O(E³); crossings listed O(E²·T).
4. Macro grid: C ≤ 2E + T columns, R ≤ E rows; each macro cell gets a block by table lookup (crossover flip from the
   two edge directions, corner kinds from the edge ends). Concrete size ((C + 2)·P) × ((R + 1)·P + 8) cells, P = 587.
5. Check path: for each block in boustrophedon order, its library template (or the two lanes) is placed by
   translation; the lanes of neighbouring blocks meet at the shared border rows 2 and P − 3; the margins (columns
   −1 and C) carry the hairpins and the descent t → bottom strip by a fixed rule. Output size O(C·R·|template|).
Composition: a template's chain stays inside its block except the two lanes, and its crossings are of its own
block's floor; GX permission (P4) refers only to legs of the block's own tiles. In the global Lemma 5.6 order all
level-1 excursions precede all level-2 excursions, and the excursions of one block at one level are consecutive and
in the template's tile order, so the time order restricted to any block equals the template's own time order, and
`validate_rules` on the template implies P1-P4 in the glued level. Lane crossings are CHX on plain corridor floor
(never a slot, window, location, coin cell or halo point, asserted). Coverage (every SCD / component has its G′, every
leg Wt = Wb = 1) is additive over blocks (`coverage_ok`). ∎
What is still not drawn is the box redraw (every crossing point blown up into its constant-size machinery board by
inserting rows and columns): a polynomial, search-free standard step (#boards ≤ #events, each ≤ 478 × 608 cells),
STRONG, not implemented (§7.1, F3 below).

**F3 by the same blow-up (Z1 after the redraw).** Inserting k rows (columns) at a crossing point p moves every cell
beyond p by k and puts the board into the inserted strip, so for any original cell c and any cell b of p's board,
Chebyshev(c, b) ≥ Chebyshev(c, p) in original coordinates. Windows exist only in boards and in the component windows
of the main layer. The router keeps every chain point (hence every crossing point) out of the Chebyshev-4 halo of
Z ∪ {E}, and the coin block carries no G′, only the two lanes, which cross the coin block's stubs in row 2 (≥ 550 rows
from Z) and nothing in row P − 3. Hence after the redraw no board window lies within Chebyshev 3 of Z ∪ {E}: Z1's
sufficient rule holds in redrawn coordinates. (STRONG; the exact per-window reach of the boards, C-audit Z1 step 1,
then follows as for the main-layer windows because every board window is ≥ 4 cells from Z ∪ {E}.)
