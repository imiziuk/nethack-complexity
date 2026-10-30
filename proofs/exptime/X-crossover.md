# X: the reusable directed crossover as one concrete planar boulder map

Workstream X, 2026-10-29; **map rebuilt with v2 tiles 2026-10-30 (review 5 repair 1, §7)**. Game not run, nothing committed. Files: this note, `tools/exptime/X_build.py` (map),
`X_verify.py` (checks), `X_render.py` (PNG); outputs in `build/xover/` (`crossover.txt`, `crossover.json`,
`routes.json`, `crossover.png`, `crossover_small.png`). Imports A2_xover, A2_scd, A_core, A_check and
`tools/visual/animate_gadgets.scd_build` read-only. Labels: **VERIFIED** = machine-checked this session · **STRONG** ·
**CONJECTURE**.

## 0. Results

| Item | Status | Notes |
|---|---|---|
| Wiring graph of the flat Fig. 12 network (66 gadgets, 46 junction nodes) planar with A1, A2, B1, B2 on the outer face in interleaved order | **VERIFIED** (networkx) | same graph with order A1, B1, A2, B2 is **non-planar**: the gadget genuinely crosses |
| One concrete map: 20 SCD tiles (Fig. 37, closed, **v2: split delimited check legs**, 3 port-order variants) + 46 protodiode tiles (v2) + 46 corridors | **VERIFIED** built + asserted | v2: 453 × 432 = 195,696 cells, 11,760 floor, **166 boulders** (20·6 + 46·1); v1 (unsound checks): 358 × 332, kept as `crossover_v1.*` |
| Planarity / locality of the map | **VERIFIED** (asserted from the saved map alone) | tiles pairwise not 8-adjacent; corridors pairwise not 8-adjacent; each corridor 8-touches tiles only inside the intended port zones; 1 corridor per junction node; frame closed except the 4 external ports |
| (a) map-derived network = A2's VERIFIED Fig. 12 network | **VERIFIED** | gadget-by-gadget wiring equal up to node renaming; Net2 of ideal SCDs/diodes on the map wiring: 7 reachable states, SOUND + COMPLETE vs directed crossover; negative controls (undirected, leaky A1→B2) fail |
| (b) exact port relation, every reachable network state | **VERIFIED** | only A1→B1, A2→B2 (+ bounces); both available in all 7 states (unbounded reuse) |
| Tile copies under rotation/reflection | **VERIFIED** | all 8 grid symmetries of proto-precursor and protodiode give isomorphic systems; every placed tile equals its canonical tile cell by cell |
| (d) split check legs on every placed tile (v2) | **VERIFIED** (from the saved map) | 66 tiles: intended joins only; with all component Wb (resp. Wt) slots walled every component port is alone; SCD O/I/J delimited; 604 legs, 684 check locations |
| (c1) concrete play: A1→B1, A2→B2, 8 crossings in mixed order (incl. repeats), move by move on the full board | **VERIFIED** | v2: 46 gadget traversals / ~7,640 hero moves per crossing (61,112 moves, 368 tile + 1,792 component traversals), every step legal in `A_core.Board.moves` on the whole map |
| (c2) random-walk differential test on the full board, 100k committed moves | **VERIFIED** (no assertion failed) | v2 default: 60 episodes, 692 tile + 2,241 component traversals, 913 external returns, 2,995 breaking moves pruned, 0 tile-breaking traversals. v2 `--ext-only`: 65 episodes, 453 tile + 1,769 component traversals, **2,772 external returns, all passing the strict external-reachability vector check**. See the §3 note on drops |
| SCD + diode tile systems used by the tracker | **VERIFIED** (re-run of A2 §5b, closed init: 10,927 raw states, 12 clean, = ideal SCD) | |
| Component checks through the tile's own check legs (review 5 attack re-run) | **VERIFIED** v2 / **BROKEN** v1 | `review5_abc.py`, `review5_cd.py` read the check map off the tile geometry: v2 = split (precursor clean set 3, diode 2/4, SCD broken absorbing, SOUND + COMPLETE); v1 = joined (5-6 clean, not absorbing, SOUND False) |
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
- **Drops (found in the v2 re-run, 2026-10-30).** 70% of the default episodes start at a random *internal* corridor
  cell, i.e. the hero is dropped at an internal junction; the old check "projected ideal vector is a state reachable
  from the external ports" is then not an invariant of the experiment (v1 passed it by luck). Now: strict check until
  the first drop; afterwards the vector must lie in the closure under single gadget traversals from any node, which
  turns out to be all 2^20 SCD combinations (vacuous). So the meaningful global check is the `--ext-only` run (every
  episode starts at A1/A2/B1/B2): 2,772 external returns, all strictly reachable. The per-traversal checks (component
  and tile transitions, related ideal states) do not depend on drops and ran in both modes.

## 4. Game-safety of the assembled map

- **G1** VERIFIED per component (A_core LEAK, A2) and observed globally (no push onto any port in all runs); since tiles
  touch corridors only at port cells and boulders never reach port cells, no boulder can reach a corridor.
- **G2/G4** per tile VERIFIED (A2); for the map: compositional (A2 notes "simulation inside a network = simulation",
  STRONG) and checked exactly at the network level (a, b) with A2's flat run covering the composition of ideal parts.
- **G3** per tile VERIFIED (broken absorbing in A2's raw flat network).
- **G5** boulders only, no traps / holes / items in the map.
- **Not done here**: the global check path. Every one of the 206 check ports (below) must be on B's check path after
  t, with guards (A2 §5 items 1-2); the crossover's checks are just its 20 SCDs' and 46 diodes' checks.

## 5. Check ports for B2 (in `build/xover/crossover.json`, `tiles.<gid>.checks` + `tiles.<gid>.legs`, global cells)

**v2 (2026-10-30, review 5 repair 1).** Every check location has its own delimited hallway ("leg"), as in B2_e2e's
`gprime`: g-side -- Wb slot -- mid -- Wt slot -- junction. Per SCD tile (20): component locations `tog.A..G`,
`prec.A..G` (D, G = 1-cell pockets, no leg), `d1.A..D`, `d2.A..D`, plus the SCD-level `scd.O`, `scd.I`, `scd.J`
(g-side = gsO/gsI/gsJ, leg towards the tile port) = 25 locations and 21 legs. Per diode tile (46): `d.A..D`, 4 legs.
Total **684 check locations, 604 legs**; `legs.<name>` gives `gside`, `cells`, `Wb`, `mid`, `Wt`, `node`. Junctions
(tT, T, X, Y, cd1, cd2, gsO/I/J) lie beyond every Wt slot. None is routed out (the guarded check-path entries are the
layout generator's job, review 5 repair 2, open).

The v1 list below (kept in `crossover_v1.json`) was **unsound**: see §7.
## 6. Size and scope

v2: 453 × 432 grid, 11,760 floor cells, 166 boulders (v1: 358 × 332, 7,773 floor); NetHack's real level is 80 × 21, so this lives in the generalized
(unbounded) map the whole EXPTIME reduction assumes. The layout is automatic, not optimised (the corridors are long);
a hand layout could be several times smaller. Reproduce: `python X_build.py` (~5 min; defaults seed 2, scale 420),
`python X_verify.py --moves 100000` (and `--ext-only`), `python X_render.py`.

## 7. Review 5 bug in v1 and the v2 repair (2026-10-30)

**Bug (review-5-exptime.md §3a).** The v1 SCD tile (animate_gadgets.scd_build) joined the precursor's and toggle's
A, B, C legs in one hallway (`*.ABC`) and each protodiode's C, D in one corridor (`*.CD`); X, Y, T also joined legs of
*different* components with no room for delimiters. Through a joined port Ani's precursor check [A→D, C→G, B→A, B→C]
degrades to [T→D, T→G, T→T, T→T]: 6 instead of 3 clean states (adjacent-block states pass), broken not absorbing, flat
SCD postselected ≠ ideal (SOUND False); the diode's joined C–D lets "block on x=4" pass (3 of 4 instead of 2). So the
206 v1 check ports could not be wired to B2's check path.

**Repair (X_build v2 tiles).**
- `scd_tile(variant)`: every L′ location of every component (pp: A, B, C, E, F; pd: A, B, C, D) and the SCD's O, I, J
  get their own LEG = 3 cell hallway (Wb slot, mid, Wt slot) before the junction (tT, T, X, Y, cd1, cd2, gsO/gsI/gsJ):
  the e_l edges of B2_e2e `gprime` (g-side -- WCX_b -- mid -- WCX_t -- outer). D, G stay pockets. 19×37 (variant 1:
  21×43).
- `diode_tile()`: A, B (to the tile ports) and C, D (to the cd junction) each on their own leg; 5×11.
- Contract `check_tile_legs` (asserted on the canonical tiles and, by X_verify (d), on all 66 placed copies): no-cut
  hero regions join exactly the intended nodes; with all component Wb (resp. Wt) slots walled every component port is
  alone in its region; the tile-level legs delimit O, I, J.
- Evidence: `review5_abc.py` / `review5_cd.py` now also read the check map off the tile geometry (Wb slots walled):
  v1 reproduces the failure; v2 gives precursor clean set {(3,5),(3,6),(4,6)}, toggle 3, diodes 2/4, SCD 12 clean,
  broken absorbing, postselected = ideal SCD (SOUND + COMPLETE, both initial states).

**Layout changes needed for the bigger tiles** (the v1 greedy router could not route them at any scale):
1. Drawing: de-degeneration (no two incident edges at a gadget or junction within 4°; the Tutte drawing had collinear
   edges, so the rotation there was undefined) and a clearance pass (no drawing edge passes within R of a gadget it
   does not touch; otherwise the tile body covers that edge and its corridor must pick a side the drawing does not
   fix). Both keep the drawing planar (every move checked).
2. SCD ports all on one side, in 3 variants of top-to-bottom order (O,I,J / I,J,O / J,O,I: one approach hallway wraps
   the tile). `choose_sym` picks variant + symmetry so that the cyclic order matches the drawing AND the tile body lies
   in the drawing's widest sector at that gadget (same body rule for diodes). Map: 5 × v0, 1 × v1, 14 × v2.
3. Routing: negotiated congestion (PathFinder: rip up all nets each round, history cost on shared coarse nodes)
   instead of sequential greedy BFS; the old router stays as a fallback. Seed 1 still leaves one unroutable face
   (nets b25/o8) at every scale tried; seed 2 routes at scale 453.
The finished map is re-checked from scratch by `check_map` (unchanged) and X_verify (a)-(d), (c1), (c2).

**Still open:** attaching the 684 check locations to B2's check path (guards, WCX/SX crossings) = the layout
generator, review 5 repair 2.
