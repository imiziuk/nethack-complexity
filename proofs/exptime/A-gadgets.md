# A: reusable boulder gadgets for the R3 (EXPTIME) reduction

Workstream A, 2026-10-29. Source @16ff591 read-only, game not run, nothing committed. Files written: this file,
`tools/exptime/A_core.py` (model + checks), `A_check.py` (library check), `A_library.py` (layouts),
`A_search.py` / `A_anneal.py` (gadget search), an append to `INTERFACE.md`.
Labels: **VERIFIED** = machine-checked by running the tools this session · **STRONG** = complete argument, not
reviewed · **CONJECTURE** · **NEGATIVE** = searched, nothing found (not an impossibility proof).

## 0. Results

| Gadget | Status | Size | Notes |
|---|---|---|---|
| Checkable diode `diode_ck` (Ani et al. protodiode, C–D joined) | **VERIFIED** (exhaustive, A_check; port relation cross-checked against D_game.py `--relation`) | 4×2 interior, 1 boulder, 4 states (2 clean) | postselected + wired = ideal diode (sound + complete); raw is NOT a diode; broken absorbing (G3) |
| Pure (locally exact) reusable diode | **NEGATIVE** | — | random search 4×4…6×5 (~1.4 M boards, 1-4 boulders) + annealing (Python, Rust scratch annealer) found none; §4 explains the obstruction |
| Self-closing door (pure) | **NEGATIVE / not built** | — | same obstruction (closing must happen behind the hero); §5 |
| Self-closing door (checkable) | not built | — | Ani et al. Fig. 37 (precursor + 2 diodes + 1-toggle) exists for 1-player; layout figures not readable via WebFetch |
| Reusable crossover | **not built** | — | §6: the naive 2-door crossover is non-planar; the planar SCD crossover (ABD+20 Lemma 2.6) needs a working SCD first |
| Variable / toggle | not needed by B (B-reduction §0) | — | — |
| Engine sanity: hu-on-lower G_D single-use door | VERIFIED | 2 states | matches Lemma 3.3 |

**Bottom line for B:** only the *checkable* route exists so far, and only for the diode. B's §5.2 global check path
is therefore mandatory, and it has an open gap (§3.3: the check path shares cells with the main game, so its entry
must be guarded). A pure reusable Push-1F diode/SCD is exactly what the Push-1F literature never had (Ani et al. 2022
needed postselection even for the diode), and our searches agree.

## 1. Model and the game-safety criterion (machine-checkable)

**Movement (A_core.py; = hu-off §B.4 M1-M3, hu-on-lower F1-F3, check_small, D_game):** hero 8-moves; orthogonal step
into a boulder pushes it iff the cell beyond is floor without a boulder (heavy hero, no squeeze); diagonal step needs a
boulder-free target and a corner that is floor without boulder (Sokoban corner rule); no diagonal push. No pits, holes
or traps in any reusable part. Without holes, a legal diagonal step a→b always has a free corner k, so it equals a→k→b
(hu-on-lower Lemma 2.1): the model is exactly Push-1F.

**Gadget = window** with port cells (capital letters). Local state = boulder set. A *traversal* from port p is a hero
walk that starts on p and ends the first time the hero stands on a port again (continuing = a new traversal).
T(B, p) = {(q, B')}. **G1 (locality)** is enforced: if any boulder can ever be pushed onto a port cell the gadget is
rejected (LEAK); ports are 1-wide openings in the frame, so nothing outside can touch a boulder.

**Game-safety = two simulations** (A_core.check). Inside a gadget only the hero acts; the coin is outside every
gadget. So a concrete gadget can replace the ideal one in the R3 game iff
- *sound* (concrete ≤ ideal): greatest relation R with: (c, a) ∈ R ⇒ every concrete traversal p→q (c→c') is matched by
  an ideal traversal p→q (a→a') with (c', a') ∈ R, **or** q = p and (c', a) ∈ R (the hero only looked in);
- *complete* (ideal ≤ concrete): every ideal traversal is realised with related successors;
- and (init_c, init_a) is in both relations.
Strategy transfer (STRONG): the hero of the ideal game copies a concrete winning strategy traversal by traversal via
R (nature's coin moves are identical in both games); conversely via the complete relation. This is B's G2+G4 with
"broken" made precise; dead/stuck states are fine automatically (a state with fewer traversals is simulated).

## 2. Checkable gadgets in a game (the lifting lemma)

**Pruning lemma (STRONG, elementary).** In a reachability game (hero vs nature), let Doom = positions from which the
goal is unreachable in the underlying graph (ignoring who moves). Deleting **hero** edges into Doom does not change
the winner from any position outside Doom. (A winning strategy never enters Doom; deleting hero edges only removes
options; nature's edges are untouched.)

**Application.** Gadget k is *clean* iff its checking sequence (Ani et al. Def. 5.2) is legal. If (i) broken is
absorbing (G3, machine-checked: no traversal from any port leads broken → clean) and (ii) every route to g passes
gadget k's check traversals, then a broken gadget is in Doom, and only the hero's own pushes can break a gadget. So the
R3 game equals the game with all breaking traversals deleted = the postselected gadget (A_core.postselect), which A_check
then compares with the ideal automaton. This is B §5.2's argument; A_check verifies (i) and the postselected behaviour.

## 3. The checkable diode `diode_ck` — VERIFIED

```
x: 0 1 2 3 4 5
y0 # A # B # #      A above e1, B above m2
y1 # . 0 . . #      track e1=(1,1) m1=(2,1) m2=(3,1) e2=(4,1); boulder X on m1
y2 # # C # D #      C below m1, D below e2; C and D are joined by a free corridor
y3 # # # # # #
```
States (all 4 reachable): X ∈ {m1, m2} clean; X ∈ {e1, e2} broken. Checking sequence [A→C, D→B] (as in Ani et al.).
Intended diode play: A → e1, push X east (m1→m2), hero on m1 → C → corridor → D → e2, push X west (m2→m1), hero on
m2 → B. Port relation per state (A_check, identical to D_game `--relation` on the same window):

| X on | status | traversals |
|---|---|---|
| m1 | clean | A→B, A→C, B→C, B→D, D→B, D→C |
| m2 | clean | A→B, A→C, C→A, C→B, D→B, D→C |
| e1 | broken (A sealed: dead) | B→C, B→D, C→B, C→D, D→B, D→C |
| e2 | broken (**B→A open**) | A→B, A→C, B→A, B→C, C→A, C→B |

e2 is the overshoot: hero on m1 after the first push presses east again. Broken is absorbing (X on e1/e2 can never
return: e1/e2 have walls behind and beside). **Postselected + C–D joined = ideal diode, sound and complete; raw
(without postselection) is not sound.** Boulders never reach a port. 1 boulder, 8 floor cells.

### 3.3 Open gap for B's check path (important)
The checks use the gadget's own ports (A→C, D→B), and C, D are main-game cells (the internal C–D corridor). So the
check path must attach to main-game cells. Then a hero *in the main game* can step onto the check path at such an
attachment and walk along it: to the next gadget's main cells (a shortcut) and, if all later checks pass, to g
**without ever passing t**. B §5.2 (i)-(ii) assumes the check path is entered only after t; that needs guards. Ani et
al. solve the 1-player version with SO/MSC and dicrumblers (their Thm 5.3, "nonlocal simulation"); those guards must
be re-proved for games (by the pruning lemma, any guard whose misuse leads only to Doom is fine). Not done here.
Single-use pieces are allowed on the check path (it is used once), e.g. hu-on-lower G_D (VERIFIED sanity gadget) and
G_X (K over P: unlimited for the main route, once for the check route), but G_X(d) merges the routes after the pass.

## 4. Why no pure reusable diode (NEGATIVE, explanation STRONG, impossibility CONJECTURE)

**Overshoot lemma (STRONG).** If a boulder X is moved p→q = p+d by a push and later back q→p, the second push is made
from q+d, so q+d is floor. Right after the first push the hero stands on p with X on q, and pressing d again sends X
to q+d unless a boulder already sits on q+d. Hence every back-and-forth track has an overshoot state; it is harmless
only if it is dead, and a guard boulder Y on q+d must leave q+d before the return push and come back afterwards, which
creates the same problem for Y. Square cycles (4 pushes in 4 directions) remove the collinear overshoot but create
perpendicular pushes from inside the 2×2 block.

**Backward-following argument (STRONG).** After an A→B traversal, the B-hero can retrace the A-hero's walk backwards
(the cell the hero leaves after a push is always free) until some later push put a boulder on an earlier walked cell.
So every diode traversal must push a boulder *behind* the hero, and the next A-traversal must clear it from the A side;
clearing and re-blocking along one line is again a back-and-forth track.

Counterexamples kept in A_library (A_check expects them to FAIL): `slot1` (1 boulder, return push from the far end:
overshoot e2 opens B→A) and `uturn2` (2 boulders, Z behind-blocker on a U-turn + Y interlock, 115 states: complete,
but the interlock's own perpendicular push leaks).

Search coverage (no passing board): A_search random boards 4×4 (80 k), 5×4 (1.2 M), 5×5 (partial), 1-4 boulders;
A_anneal (Python) 6×5; scratch Rust annealer (same model, not kept in the project) 12 × 40 k steps from `uturn2` and
an open 7×7 box (stopped early to free CPU for A2), score = complete + fraction of unsound states. Result of the
finished run (12 × 40 k annealing steps from `uturn2`, 8×8 box): **0 passing boards**; best score 63.8 = complete but
with a B→A-leaking reachable state. Scratch source: scratchpad `dsearch/src/main.rs` (not in the project; A_core.py is
the reference model, the scratch scorer agreed with it on `uturn2`).

## 5. Self-closing door

Pure SCD: the closing push must leave a boulder on the tunnel behind the hero (§4 argument applies verbatim), and the
opening push always leaves the hero on the cell the gate boulder vacated, i.e. **on the tunnel**: so a button that moves
a tunnel boulder connects the button to the tunnel (O→I and O→J leaks) unless further one-way pieces are added. No
pure design found. Checkable SCD: Ani et al. Fig. 37 (precursor + 2 diodes + 1-toggle, check [O→O, I→J]) is the
candidate; A_core.postselect + A_check can verify it once the layout is transcribed (the figure is an image; WebFetch
returned only captions). Next step: get the PDF figures (arXiv 2412.20079 §7, Figs. 35-37) and transcribe.

## 6. Crossover

- Naive door crossover (STRONG, VERIFIED reasoning): A→O-tunnel(d1)→M, C→O-tunnel(d2)→M, M→S(d1)→B, M→S(d2)→D is
  sound and complete as an abstract gadget (invariant "all doors closed outside M"; declining to open = stuck), but it
  is **not planar** with point-like SCDs: d1 must touch both A and B, d2 both C and D, and two vertex-disjoint paths
  A–B, C–D inside a disk with boundary order A, C, B, D do not exist. It needs an SCD with an internal crossing
  (ABD+20 Lemma 3.3).
- Planar SCD crossover (ABD+20 Lemma 2.6, Figs. 11-13): its proof uses "stuck"/dominance arguments, which are game-safe
  under §1's simulation criterion; A_core.Network can verify it at the abstract level once the figures are transcribed.
- Push-1F crossover: none in the literature (Ani et al. avoid crossovers via planar SCD reachability); none here.
So B's crossover requirement reduces to "a game-safe SCD" + the abstract Lemma 2.6 network (check with A_core.Network).

## 7. How to reproduce
```
cd tools/exptime
python A_check.py            # sanity G_D, diode_ck (checkable), negative examples; prints per-state relations
python A_search.py diode --w 5 --h 4 --boulders 1-4 --iters 1200000 --workers 12
python A_anneal.py diode --grid "<rows,comma,separated>" --iters 2000 --runs 12
```
