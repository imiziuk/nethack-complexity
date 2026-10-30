# X: the reusable directed crossover as one concrete planar boulder map

Workstream X, 2026-10-29. Game not run, nothing committed. Files: this note, `tools/exptime/X_build.py` (map),
`X_verify.py` (checks), `X_render.py` (PNG); outputs in `build/xover/` (`crossover.txt`, `crossover.json`,
`routes.json`, `crossover.png`, `crossover_small.png`). Imports A2_xover, A2_scd, A_core, A_check and
`tools/visual/animate_gadgets.scd_build` read-only. Labels: **VERIFIED** = machine-checked this session · **STRONG** ·
**CONJECTURE**.

## 0. Results

| Item | Status | Notes |
|---|---|---|
| Wiring graph of the flat Fig. 12 network (66 gadgets, 46 junction nodes) planar with A1, A2, B1, B2 on the outer face in interleaved order | **VERIFIED** (networkx) | same graph with order A1, B1, A2, B2 is **non-planar**: the gadget genuinely crosses |
| One concrete map: 20 SCD tiles (A2's flat Fig. 37 tile, closed) + 46 protodiode tiles + 46 corridors | **VERIFIED** built + asserted | 358 × 332 = 118,856 cells, 7,773 floor, **166 boulders** (20·6 + 46·1) |
| Planarity / locality of the map | **VERIFIED** (asserted from the saved map alone) | tiles pairwise not 8-adjacent; corridors pairwise not 8-adjacent; each corridor 8-touches tiles only inside the intended port zones; 1 corridor per junction node; frame closed except the 4 external ports |
| (a) map-derived network = A2's VERIFIED Fig. 12 network | **VERIFIED** | gadget-by-gadget wiring equal up to node renaming; Net2 of ideal SCDs/diodes on the map wiring: 7 reachable states, SOUND + COMPLETE vs directed crossover; negative controls (undirected, leaky A1→B2) fail |
| (b) exact port relation, every reachable network state | **VERIFIED** | only A1→B1, A2→B2 (+ bounces); both available in all 7 states (unbounded reuse) |
| Tile copies under rotation/reflection | **VERIFIED** | all 8 grid symmetries of proto-precursor and protodiode give isomorphic systems; every placed tile equals its canonical tile cell by cell |
| (c1) concrete play: A1→B1, A2→B2, 8 crossings in mixed order (incl. repeats), move by move on the full board | **VERIFIED** | 46 gadget traversals / ~4,750 hero moves per crossing, every step legal in `A_core.Board.moves` on the whole map |
| (c2) random-walk differential test on the full board, 100k committed moves | **VERIFIED** (no assertion failed) | 66 episodes, 1,351 tile + 3,162 component traversals checked, 1,004 external returns (all bounces), 3,800 breaking moves pruned, 0 tile-breaking traversals, 2 trapped excursions abandoned |
| SCD + diode tile systems used by the tracker | **VERIFIED** (re-run of A2 §5b, closed init: 10,927 raw states, 12 clean, = ideal SCD) | |
| Game-safety G1-G5 of the assembled map | **STRONG** | per-tile VERIFIED (A2) + compositional argument §4; whole-board state space not enumerated |

## 1. Construction (X_build.py)

1. Network: `A2_xover.xover(depth=3)` (fully flat: 20 button-SCDs, 46 diodes; all SCDs start closed).
2. Graph G: one vertex per gadget and per junction node, an edge per gadget port. Planarity test as above
   (hub vertex + rim cycle trick).
3. Straight-line planar drawing: rim A2-TR-B1-BR-B2-BL-A1-TL pinned on a square, Tutte barycentric placement, then a
   spreading pass where every vertex move is rejected if it creates an edge crossing; final drawing asserted
   crossing-free.
4. Tiles: SCD = the 17×20 tile of `animate_gadgets.scd_build` (it asserts its own internal adjacency), precursor
   blocks moved to track x=3,5 (= closed); diode = Ani protodiode with the C–D corridor underneath. Each copy gets the
   grid symmetry whose port cyclic order equals the drawing's rotation at that vertex (always possible: ≤ 3 ports +
   reflection). Port stubs run straight out of the tile to even/even cells.
5. Corridors: one Steiner tree per junction node on the even/even sub-grid (coarse cells + connectors), so corridors
   are 1 wide; a net may only use cells whose 8-neighbourhood holds no other net or tile; sequential routing with
   reordering on failure (enlarge the drawing if needed). Then pass-through rows/columns are deleted (each deletion
   re-checked) and the whole map is re-checked from scratch.

## 2. Planarity proof sketch (VERIFIED assertions → planar)

Contract every tile and every corridor component of the finished map to a point. Assertions: (i) distinct tiles are
not 8-adjacent; (ii) distinct corridor components are not 8-adjacent (so no diagonal step joins them either);
(iii) a corridor 8-touches a tile only inside the zone of one of that tile's ports, and every port zone touches exactly
one corridor. So the only hero-passable contacts between regions are the intended port contacts, the regions are
disjoint connected sets of the plane, and drawing each gadget-port edge inside its corridor gives a crossing-free
drawing of exactly the wiring graph: the map *is* a plane embedding. No corridor crosses another because two crossing
grid paths must share a cell, which (ii) excludes. The SCD tile itself is planar internally (its O, I, J sit on its
boundary; its internal corridors tT, T, O, X, Y, I, J, cd1, cd2 are disjoint, checked by `scd_build`).

## 3. Verification (X_verify.py)

- **Tracker** (runs on every concrete move, scripted and random): A_core movement on ONE board with all 166 boulders;
  every component port cell and external port is a LEAK cell (a push onto it raises); a push must keep the boulder on
  its own component's cells; moves that would break a component are pruned (pruning lemma, A-gadgets §2: such a
  move only leads to Doom); a tile traversal ending tile-broken (the SCD's O→J leak) is undone and counted (same
  lemma). Asserted: every observed component traversal is a transition of the raw component system (A_core.explore of
  Fig. 36a / 35a), every observed tile traversal is a transition of the tile's postselected system (A2 §5b flat
  network restricted to clean) and keeps a nonempty set of sound-related ideal states, and every external traversal
  is A1→B1, A2→B2 or a bounce with the projected ideal vector a reachable state of the ideal network.
- **c1 scripted crossings**: plan by BFS in the ideal network on the map wiring, realise each gadget traversal by BFS
  inside its tile (goal: target port zone, tile state related to the target ideal state by the COMPLETE relation),
  corridors by BFS. Sequence: A1→B1, A2→B2 twice, then A1→B1 ×2, A2→B2 ×2. Every crossing reaches its exit.
- **c2 random walk** (`--moves 100000`, seed 7, after c1): episodes start at a random corridor cell or (30%) an
  external port, uniform over legal non-breaking moves, ~1,500 moves each and ending on a corridor cell. 100,000
  committed moves in 27 s; 3,162 component traversals and 1,351 tile traversals checked against their systems, 1,004
  external returns checked (all bounces: a random walk never completes a 46-traversal crossing, which is why c1 exists),
  3,800 component-breaking moves pruned, 0 tile-breaking traversals, 2 excursions abandoned after 5,000 moves sealed
  inside a tile (undone, not counted). Limits: coverage is local (random walks stay near their start); the SCD O→J leak
  never occurred, so the Doom branch is exercised only by construction, not by this run.

## 4. Game-safety of the assembled map

- **G1** VERIFIED per component (A_core LEAK, A2) and observed globally (no push onto any port in all runs); since tiles
  touch corridors only at port cells and boulders never reach port cells, no boulder can reach a corridor.
- **G2/G4** per tile VERIFIED (A2); for the map: compositional (A2 notes "simulation inside a network = simulation",
  STRONG) and checked exactly at the network level (a, b) with A2's flat run covering the composition of ideal parts.
- **G3** per tile VERIFIED (broken absorbing in A2's raw flat network).
- **G5** boulders only, no traps / holes / items in the map.
- **Not done here**: the global check path. Every one of the 206 check ports (below) must be on B's check path after
  t, with guards (A2 §5 items 1-2); the crossover's checks are just its 20 SCDs' and 46 diodes' checks.

## 5. Check ports for B2 (in `build/xover/crossover.json`, `tiles.<gid>.checks`, global (x, y) cells)

Per SCD tile (20): `tog.D`, `tog.G`, `prec.D`, `prec.G` (1-cell pockets), `tog.ABC` (toggle's closed A/B/C hallway),
`prec.ABC` (precursor's T junction joining A, B, C), `d1.CD`, `d2.CD` (diode C–D corridors). Per diode tile (46):
`d.CD`. 206 ports, all dead ends inside their tile; none is routed to the map boundary (attaching them needs the
guarded, single-use check-path crossovers of A2 §5, B2's job). Note: A2 §5 says the precursor checks need A, B, C as
three separate hallways; the reused tile joins them (`*.ABC`), so B2 must either split them in the tile or argue the
joined version.

## 6. Size and scope

358 × 332 grid, 7,773 floor cells, 166 boulders; NetHack's real level is 80 × 21, so this lives in the generalized
(unbounded) map the whole EXPTIME reduction assumes. The layout is automatic, not optimised (the corridors are long);
a hand layout could be several times smaller. Reproduce: `python X_build.py` (~2-3 min, seed 1),
`python X_verify.py --moves 150000`, `python X_render.py`.
