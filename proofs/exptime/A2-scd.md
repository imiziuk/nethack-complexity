# A2: checkable self-closing door (Push-1F / NetHack boulders) + planar SCD crossover

Workstream A2, 2026-10-29. Game not run, nothing committed. Files: this file, `tools/exptime/A2_scd.py`,
`tools/exptime/A2_xover.py` (both import `A_core` / `A_check` / `D_game` read-only; A's files untouched).
Labels as in A-gadgets.md: **VERIFIED** = machine-checked this session · **STRONG** · **NEGATIVE** · **CONJECTURE**.

## 0. Results

| Item | Status | Notes |
|---|---|---|
| Proto-precursor (Ani Fig. 36a), checks [A→D, C→G, B→A, B→C], L′={A,B,C,E,F} | **VERIFIED** | 28 reachable states; clean = exactly the paper's 3 (both blocks in the 4 centre cells, not adjacent); broken absorbing w.r.t. L′ (not w.r.t. D, G, as the paper says) |
| Precursor = proto-precursor, A,B,C joined to T | **VERIFIED** sound+complete vs a 3-state refinement of Fig. 36d (both initial states) | raw (no postselection) is NOT sound |
| 1-toggle = precursor with T closed | **VERIFIED** sound+complete, both initial states | |
| Diode = protodiode (Fig. 35a), C–D joined | **VERIFIED** (re-check of A's `diode_ck`) | |
| **Checkable SCD (Fig. 37)** = precursor + 1-toggle + 2 diodes, check [O→O, I→J] | **VERIFIED** postselected = ideal directed open-buttoned SCD (`A_check.T_scd_button`), initially open AND initially closed; broken absorbing | 2 precursors + 2 protodiodes = **6 boulders** |
| Same, flat over RAW concrete components (D/G pockets) | **VERIFIED**: 10,927 reachable raw states, 12 clean; broken absorbing in the raw network (G3); postselected = ideal SCD | game-safety G1-G5 below |
| SCD-level check alone ([O→O, I→J], ×1 or ×2) on the raw network | **NEGATIVE** (4,138 "clean", not absorbing, unsound) | the component checks (hidden D, G, diode C/D) are mandatory |
| D_game `--relation` cross-check, proto-precursor window, 3 clean states | **VERIFIED** 360 entries, 0 mismatches | |
| Opening tunnel = button SCD + 2 diodes; Lemma 2.5 two-button door; button+tunnel door | **VERIFIED** abstract | |
| **Planar directed crossover (ABD+20 Lemma 2.6, Figs. 11-12)** | **VERIFIED** abstract: Fig. 11 pair (all 4 initial states), Fig. 12 with ideal pairs, and **fully flat** (66 gadgets: 20 base SCDs + diodes) sound+complete vs directed crossover; negative controls (undirected / leaky target) fail as they should | planarity itself read off the figures, not machine-checked |

**Bottom line:** the published Push-1F SCD works exactly in our model (= NetHack boulder rules with the corner rule;
diagonal moves add nothing without holes), as a *checkable* gadget, and so does the SCD crossover on top of it. What is
still missing is B's side: the global check path (§5).

## 1. Transcription (from the PDF's vector drawings)

Method: PyMuPDF `get_drawings()` on PDF pages 29-30 (0-based 28-29): every grid square is a stroked 18.9 pt square
at pitch 19.2 pt, bricks are small tan rectangles, blocks are grey 12 pt squares. A cell is wall iff bricks cover
>40% of it; letters placed by the label coordinates. Re-checked visually against 250-330 dpi renders. The protodiode
transcribes to exactly A's `PROTODIODE` (independent confirmation). Port cells (capital letters) are added one row
outside the figure frame.

**Fig. 35a protodiode** (checks [A→C, D→B]; clean = block on x=2 or 3):
```
#A#B##
#.0..#
##C#D#
######
```
**Fig. 36a checkable proto-precursor** (figure rows y=1..3; B is a 2-wide opening x=4,5; its location cell sits
above x=4; no block can ever enter row 1, so this is the same location):
```
x: 0123456789
y0 ##A#B##C##
y1 ##.#..#.##
y2 #...0.0..#      track y=2, x=1..8; blocks on x=4 and x=6
y3 #.#.##.#.#
y4 #D#E##F#G#
```
Fig. 36b (proto-precursor) = the same with D, G as 1-cell pockets and E, F extended one row; Fig. 36c (precursor) adds
two rows above joining A, B, C into one 2-wide top exit:
```
####..####
##......##
##.#..#.##
#...0.0..#
#.#.##.#.#
###.##.###
```
(36b/36c draw "magic tracks"; the real gadget is 36a with A, B, C joined outside and D, G attached to the check
machinery, which is what A2_scd.py models.)

**Fig. 36d precursor** (locations top T, left E, right F): state 1: T–E free both ways, T→F goes to 2; state 2: T–F
free, T→E goes to 1. Closing T gives a 1-toggle E⇄F.

**Fig. 37 checkable SCD** (abstract figure): `I —diode→ E[precursor]F —diode→ J`; `O —1-toggle(points down)→ T`.
Opening location O (top), entrance I (left), exit J (right). Postselection check [opening→opening, entrance→exit].

## 2. Machine-checked behaviour (A2_scd.py)

**Proto-precursor, postselected relation** (track x of the two blocks):

| blocks | role | traversals in L′ (→ new state) |
|---|---|---|
| (4,6) | precursor state 1 | A→E, E→A, B→B ⇒(3,6) |
| (3,6) | middle m (E, F both sealed) | A→A/A→E ⇒(4,6), C→C/C→F ⇒(3,5) |
| (3,5) | precursor state 2 | C→F, F→C, B→B ⇒(3,6) |

So with A,B,C joined, T→F from state 1 is two traversals T→T (into m) then T→F. The exact single-traversal ideal is
the 3-state automaton 1 —T→T→ m —T→T/T→F→ 2 (and back); the paper's 2-state precursor is this with T→T→X chained,
which is harmless because the hero stands on T in between and nothing else acts there. 25 broken states (blocks
outside x=3..6 or adjacent); broken is absorbing for L′ but **not** if D or G are usable (e.g. blocks (2,5): D→A gives
(3,5)), exactly the paper's remark.

**SCD composite** (components postselected, then [O→O, I→J]): 14 states, 12 clean. Clean ⇔ toggle in state r (4,6):
precursor (4,6) = **open** (I→J ⇒ closed (3,5)); (3,5) = **closed**; (3,6) = closed-like middle (O→O can reach open).
Diode half-states (block on the second track cell after an I→I or J→J bounce) are clean and harmless. **Broken** =
toggle (3,5) + precursor (3,5): reached only by O→J (opening→exit, the paper's "exactly once" leak); afterwards only
I→I / J→J bounces exist: fully untraversable, absorbing. Raw composite: not sound (the O→J leak).

**Flat check:** the same network over the RAW explored boards (28-state proto-precursors with D, G as private
pockets, 4-state protodiodes with C–D joined): 10,927 reachable states. Clean := every component clean (own checks)
and SCD-clean. Then: broken absorbing in the raw network (no traversal from O, I or J leads broken→clean), and
raw-restricted-to-clean = ideal SCD (sound + complete), for both initial states.

Model note: `A_core.Network` drops a walk that returns to its start with an unchanged state; A2's `Net2` keeps it
(otherwise the button check O→O is wrongly illegal in states where opening is a no-op). Concrete boards are unaffected.

## 3. Game-safety (G1-G5, INTERFACE.md / A-gadgets §1-2)

- **G1** no boulder ever reaches a port cell (A_core LEAK check passes for both boards); blocks stay on their tracks
  (proto-precursor: row y=2 only; vertical pushes all hit brick) — VERIFIED by exploration.
- **G2/G4** = sound+complete simulation of the postselected gadget against the ideal SCD (strategy transfer, A §1) —
  VERIFIED, both initial states, RNG-free (no traps, pits or monsters inside).
- **G3** broken absorbing in the raw flat network with D, G as dead-end pockets — VERIFIED. Breaking only removes hero
  options (broken SCD = fully untraversable), so by A's pruning lemma it only hurts the hero, **provided every route
  to g runs all checks of this SCD** (§5).
- **G5** boulders only: no HP, no consumables, unboundedly reusable — by construction.

## 4. Crossover from SCDs (ABD+20 = arXiv 2006.01256, Lemma 2.6) — A2_xover.py

Base: ideal button SCD (verified above) + ideal diode; opening tunnel X→Y := X→diode→button→diode→Y.
- **Fig. 10 / Lemma 2.5** (two buttons O1, O2 on one door 0): doors 1, 2 with opening tunnel O_i→N and self-closing
  N→O_i, door 0 has button N and tunnel A→B. VERIFIED (= 2-button SCD).
- **Fig. 11** (overlapping pair; doors numbered as in the figure; nodes V, M, Nt, Nb): door 1 open O2→V, close
  Nt→O2; door 2 open O1→V, close Nb→O1; door 3 button V, close M→Nt; door 4 button V, close M→Nb; diode V→M;
  door 5 button O′1, open Nt→M, close A1→B1; door 6 button O′2, open Nb→M, close A2→B2. Target: two independent
  doors (O1, O′1 open A1→B1; O2, O′2 open A2→B2). VERIFIED for all 4 initial states, also with Fig. 10 expanded.
- **Fig. 12** (nodes P, U, Q, S, R, V′; W = P via the bottom loop): pair (1,2): door 1 open A1→P and U→Q, close Q→S;
  door 2 open P→U, close R→B2. Pair (3,4): door 3 open A2→P and V′→Q, close S→R; door 4 open P→V′, close R→B1.
  O′2 of each pair unused. VERIFIED vs directed crossover A1→B1, A2→B2 (pairs ideal: 1 reachable state; fully flat,
  66 gadgets / 20 base SCDs: 7 reachable states). Matches the paper's prose walk-through.
- Not machine-checked: planarity (read off the figures; Fig. 11's two door tunnels cross inside the pair, which is the
  point), and the composition theorem "simulation inside a network = simulation" (STRONG; the flat run covers it here).

## 5. What B (B-reduction.md) still needs

1. **Check path per SCD (mandatory, NEGATIVE without it):** order = SCD check [O→O, I→J] first, then the component
   checks: each of the 2 proto-precursors [A→D, C→G, B→A, B→C] (needs A, B, C as three separate hallways into the
   T junction with check entries on each, and D, G wired only to the check machinery), each of the 2 protodiodes
   [A→C, D→B] (check access at both ends of the joined C–D corridor). The SCD-level check alone does not suffice
   (raw network: 4,138 "clean" states, not absorbing, unsound).
2. **Guards** for those check entries in a 2-player game (A-gadgets §3.3 gap: the main-game hero must not enter D, G,
   or the check hallways before t). Ani Thm 5.3 does it with SO/MSC + dicrumblers (Push-1F versions in Ani Figs. 32-33,
   not transcribed here); B must re-prove them under the pruning lemma (misuse ⇒ Doom only).
3. **Interface shape:** our SCD has an opening *button* O; B's A-SCD uses an opening tunnel — use X→diode→O→diode→Y
   (VERIFIED). Both initial states (open/closed) VERIFIED. Multi-opener doors: Lemma 2.5 construction VERIFIED.
4. **Crossover:** Lemma 2.6 crossover = 20 SCDs + diodes, exact (no extra postselection), so its "check" is just the
   checks of its 20 SCDs; all must be on the check path, which itself needs (single-use) crossovers.
5. Coin constraints Z1-Z4 (C-audit) are unaffected: SCD boulders are confined to their tracks, so their closure
   R_B is inside each gadget window.

## 6. Reproduce
```
cd tools/exptime
python A2_scd.py      # ~5 min (flat raw network dominates); prints per-state tables, ends ALL AS EXPECTED
python A2_xover.py    # < 1 s; ends ALL AS EXPECTED
```
PDF figures: pages 29-30 (0-based 28-29) of arXiv 2412.20079; pages 10-11 of arXiv 2006.01256.
