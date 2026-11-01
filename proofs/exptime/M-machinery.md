# M: the check-path machinery (WCX, SO, SD, SX) as concrete boulder boards

Workstream M, 2026-10-30. Game not run, nothing committed. Files: this note, `tools/exptime/M_build.py` (boards),
`tools/exptime/M_verify.py` (checks), optional block type in `tools/exptime/L_gen.py` (`m_block`, `check_mblock`,
`machinery_boards`, `--mblock`). Outputs in `build/machinery/` (gitignored): `<G>.txt` (map: `#` wall, `.` floor,
`0` boulder; external ports = the frame openings), `<G>.json` (ext cells, every base-board copy with its cell map
from the canonical Fig. 32 board, flat wiring), `level_*.pkl` (cached level systems), `build.log`, `verify_main.log`.
Imports B2_ani, A_core, A2_scd, X_build read-only. Labels: **VERIFIED** = machine-checked this session ·
**STRONG** = complete argument, not reviewed · **CONJECTURE** · **FAILED**.

## 0. Results

Review 6 F6 (label scope): the SO / SX / WCX rows below are **VERIFIED modulo congruence**: they compose verified base boards, and rely on two standard facts (bisimulation is a congruence for Net2 composition; nested = flat exploration) that were machine-checked on MSC only (the flat SD run did not finish).

| Board | Size (cells) | Boulders | Base copies (WMC/NR/WO) | Exact port behaviour vs ideal (Fig. 19) | Map checks | Concrete play |
|---|---|---|---|---|---|---|
| **SD** dicrumbler | 44 × 17 | 14 | 1 / 2 / 1 | **VERIFIED** SOUND + COMPLETE (5,306 states, 3 bisim. classes) | **VERIFIED** | c1 X→Y (140 moves); c2 30k moves |
| **SO** single-use opening | 142 × 79 | 62 | 4 / 8 / 5 | **VERIFIED** SOUND + COMPLETE (20 states, 4 classes) | **VERIFIED** | c1 Op→Op, In→Out (751); c2 30k |
| **MSC** merged single-use closing | 20 × 60 | 16 | 2 / 2 / 1 | **VERIFIED** SOUND + COMPLETE (3 states) | **VERIFIED** | c1 L→R, R→L, L→R, T→R (390); c2 30k |
| **SX** single-use crossover | 181 × 312 | 166 | 11 / 22 / 13 | **VERIFIED** SOUND + COMPLETE (14 states, 6 classes) | **VERIFIED** | c1 L→R, Tp→Bt (2,374); c2 30k |
| **WCX** weak closing crossover | 478 × 608 | 276 | 21 / 36 / 21 | **VERIFIED** SOUND + COMPLETE with frame-cell ports (107 states, 19 / 14 classes); see §3 for the corridor-port caveat | **VERIFIED** | c1 3 scripts incl. hallway reuse, Bt→Tp, both leaks (8-10k moves each); c2 30k |
| **HK** one check unit (SO + SD placed together, both hook curves, the b-hook crossing a delimiter-pass segment through an SX) | 238 × 480 | 242 | 16 / 32 / 19 | **VERIFIED** SOUND + COMPLETE vs the same wiring of ideal SX/SO/SD (48 states, 12 classes) | **VERIFIED** | c1 wi→wo, op→op, op→a, b→out (4,088); c2 30k |
| Orientations (all 8 grid symmetries of every board) | | | | same network ⇒ same behaviour | **VERIFIED** (all 8 images pass part a) | |
| L_gen optional block `m_block` (WCX / SX / SO / SD, 8 symmetries) | pitch 865 / 325 / 157 / 57 | | | | **VERIFIED** block contract (`check_mblock`) | |
| Machinery count of a generated instance backed by real boards | | | | | **done** (`machinery_boards` in every `inst*.json`) | |
| Hook curves and SO/SD placement inside every G′, on the level | | | | | **not drawn** (STRONG) | §5 |

Verdict: all four check-path gadgets are now concrete cell-level boards built only from Ani's three Fig. 32 boards
(no new tiles) and corridors. Each board's port behaviour equals its ideal Fig. 19 automaton. This is computed
exactly from the drawn map (bottom-up through bisimulation quotients), not taken from B2_ani's networks. One SO/SD
placement with both hook curves (HK) is drawn too, including one hook crossing a chain segment through an SX. What
stays STRONG is placing these boards along L_gen's routed curve, i.e. the redraw that gives every crossing a box,
and the hook curves of every G′ on the level.

## 1. Construction (`M_build.py`, ~1 min, deterministic)

Hierarchy, each level = the wiring of B2_ani's composition function. M_verify (w) checks this by recording what
`sd_from` … `wcx_from` actually build: equal for all 5.
- SD = WMC + NR + NR + WO (Fig. 33a)
- SO = WO + 4 SD (33b)
- MSC = SD + WMC (33c)
- SX = 2 SO + 3 SD (Fig. 20)
- WCX = 3 SO + 3 MSC + 3 SD (Fig. 21). B2_ani's free hallway L–a is one corridor: node a is L's corridor, see §3.
- HK = SX + SO + SD (B2_e2e `gprime`'s check unit + one SX).

Per level:
1. Wiring graph + rim (external ports in the required cyclic order) planar (networkx). For SX and WCX the
   non-crossing order L, R, Tp, Bt is NON-planar, so the boards really cross.
2. Tutte drawing with the ports pinned on the frame. Every inner face gets a virtual vertex, because SD's interior
   hangs on the rim at only 2 vertices. Then a spreading pass that rejects crossing moves and angles under 10°.
3. Every sub-board is copied under the grid symmetry matching the drawing's rotation (`X_build.choose_sym`), with
   port stubs.
4. Corridors: negotiated-congestion routing (`X_build.Layout.route_negotiated`).
5. `X_build.check_map`, then `X_build.compact` + crop, then `check_map` again.
6. The finished board becomes a tile of the next level (cells = its floor, ports = its frame openings).

Boulder counts: SD 14, SO 62, MSC 16, SX 166, WCX 276. B2 §3.6 / L_gen `MACHINE_BLOCKS` used 11 / 50 / – / 83 /
222. Those were arithmetic slips: SD = 2 + 3 + 3 + 6 = 14, and SX has two SOs, not one. `MACHINE_BLOCKS` is left
unchanged so old outputs stay comparable. The real counts come from `machinery_boards()`.

## 2. Verification (`M_verify.py`; ~6 min with the cached SD level, ~11 min cold)

- **0. Model symmetry.** WMC (6 states), NR (147), WO (123): all 8 grid symmetries give isomorphic A_core systems.
- **a. Map, from the saved files only, per board:**
  - Every base copy equals its canonical board cell by cell (walls included) under one symmetry + translation.
  - Copies do not overlap, and every boulder of the map belongs to a copy.
  - `check_map` with the base copies as tiles: copies pairwise not 8-adjacent; one corridor per flat node; corridors
    8-touch copies only at their port cells; frame closed except the external ports.
  - Flat wiring == the flattened composition network, up to renaming.
  - Exact boulder reach of every copy (union over its reachable states, C-audit Z1 step 1) stays inside the copy and
    off its port cells: SD 55 cells, SO 237, MSC 61, SX 639, WCX 1,059, HK 931. No boulder ever enters a corridor.
  - The same checks pass for the 7 other symmetric images (the orientations the generator needs).
- **b. Exact port behaviour, bottom-up.**
  - Base systems come from `A_core.explore`.
  - Each level is A2's `Net2` network of its children's **bisimulation quotients** (NR 95 classes, WO 99, SD 3,
    SO 4, MSC 3, SX 6, WCX 19), then its own quotient, then `A_core.check` (SOUND + COMPLETE) vs B2_ani's I_SD /
    I_SO / I_MSC / I_SX / I_WCX.
  - This replaces B2_ani's step "concrete SO with the *ideal* SD (precongruence)": the concrete SD's exact behaviour
    is carried up. What remains is two standard facts: bisimulation is a congruence for Net2, and nested Net2 = flat
    Net2. The hierarchy step is checked on MSC: flat Net2 of its 5 base boards (5,306 states) is bisimilar to the
    nested one.
  - SD level: 5,306 states, 5 min, cached.
- **c1. Scripted play.**
  - Every ideal sequence in the table is realized move by move on ONE A_core board holding all boulders of the map.
  - Planning is top-down: BFS over child quotient states at each level, then a BFS inside the copy for each base
    traversal.
  - "Jumps" = leaving at one external port and re-entering at another (the walk outside is not part of the board).
- **c2. Random play.** 30,000 uniform random legal moves per board, in 8 episodes from fresh boards, with random
  jumps at the external ports.
- **Tracker (c1 + c2), after every move:**
  - A push onto any port cell (base or external) raises LeakError: none occurred.
  - Every base-copy traversal is a transition of its canonical system.
  - At every port arrival, every instance at every level projects to an explored state of its level system.
  - Every instance traversal at every level is a transition of its level system.
  - Every return to an external port keeps a non-empty set of SOUND-related ideal states.
  - Counts (c2): SD 588 base / 49 external; SO 444 / 260 instance / 13; MSC 468 / 59 / 21; SX 297 / 228 / 10;
    WCX 69 / 65 / 0; HK 141 / 165 / 6.
  - Limit: random walks on the big boards stay near their start (WCX: no external return in 30k moves). The scripted
    runs carry the global coverage there, and the exact computation (b) carries the proof.
- **Direct flat SD exploration** (`--flat-sd`: `A_core.explore` of the whole SD map, no composition at all): started,
  still unfinished after ~60 min in Python. Not part of the evidence.

Reproduce: `python M_build.py`, then `python M_verify.py --moves 30000` (`ALL AS EXPECTED`), then
`python L_gen.py --mblock`.

## 3. Finding: where a board's external port is (WCX)

- With external ports = the whole external *corridor* (a traversal ends as soon as the hero touches it), WCX is
  SOUND but **not COMPLETE**.
- Reason: the ideal Bt→Tp passes through node a = L's corridor (sda → b → sdb → a → sdc → u …). In that model it
  splits into Bt→L (leak, state 2) followed by L→Tp. The trace is the same, but there is no single traversal.
- With ports = the **frame cells** at the ends of the external stubs, which is how the board is used as a gadget
  (`m_block` puts its arms there), the corridor is an inner node joined to the port by a free hallway. This is
  exactly B2_ani's `hall` gadget, and WCX is SOUND + COMPLETE.
- Consequence for placement (STRONG, rule for the redraw): a WCX's L arm must enter it through its stub. The check
  walk passes through L's corridor inside the board. It must not be treated as leaving the gadget, so a placed WCX's
  L port must not be merged with a junction of the surrounding level *inside* the board's frame. `m_block` respects
  this.
- HK is compared under the same frame-cell convention (ideal parts + halls). With corridor ports its ideal would
  forbid op→op→a as one walk.
- No other board is affected (all SOUND + COMPLETE in both conventions, except WCX as stated and HK's corridor-port
  COMPLETE False for the same reason).

## 4. L_gen integration

- `machinery_boards()` reads `build/machinery/*.json`. `assemble` adds `machinery_boards` to every instance:
  per-board size, and Σ count × boulders / floor / board cells.
- Example: on the smallest instance of `--run 20 3` (inst3_13, 77 crossovers: 124,302 WCX, 28,756 SO = SD,
  30,687 SX), the real boards give **41.6 M machinery boulders** and 0.90·10⁹ floor cells, where the old estimate
  was 3.19·10⁷ "blocks".
- `m_block(kind, s)` / `check_mblock` is the optional block type: one board under symmetry s, ports on the block
  midlines, straight 3-cell arms, stubs touching the board only at their port.
- These blocks have their own pitch (WCX 865 > P = 469), so the P-pitch macro grid does not place them.
- `python L_gen.py --run 20 3` re-run after the change: identical verdicts (all_ok, 14 YES / 6 NO,
  coverage_all, S3_all_ok, NC1 0/20, NC2 14/20, window reach unchanged); log `build/lgen/run20_3_after_M.log`.

## 5. What stays open

1. **Placement on the curve: STRONG.** L_gen's check path is a certified planar curve with a classified crossing list.
   Turning every crossing into an `m_block` needs the box redraw of L §7.1 (each crossing gets a box of ≥ 865 cells,
   or a board re-routed to fit P), plus the frame-port rule of §3. Not drawn.
2. **Hook curves of every G′: STRONG.** HK draws one SO/SD placement, both hooks, and the hook-over-chain crossing
   (SX, chain first, hook later). The per-G′ hook curves on the level (which sectors, how many SX/GX) are still
   counted, not drawn. A full concrete G′ (e.g. protodiode: 8 WCX + 2 SO + 2 SD + SX/GX, ≈ 2.4k boulders) would be
   the next step. Its spec is Def. 5.5 rather than a plain simulation, and it needs a planarization of B2_e2e's
   non-planar `gprime` wiring.
3. **Z1 near the coin.** The boards are windows. Their exact reach is inside the copies (§2a), so the layout rule
   "no window within Chebyshev 3 of Z ∪ {E}" is what must hold where a WCX crosses a coin corridor. That is not
   checked on a placed board.
4. **Compositionality** (bisimulation congruence; nested = flat Net2; isolated copies compose as Net2, X §4) is
   standard and STRONG. It was checked on MSC; the flat SD exploration did not finish.
5. **Sizes:** an automatic layout, not optimised (WCX 478 × 608 for 276 boulders). A hand layout would be much
   smaller.
