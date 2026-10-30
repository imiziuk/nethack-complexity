# Review 5 (adversarial): EXPTIME-completeness of L_OFF^{W+C} under R3

Reviewer: review-5 agent, 2026-10-29. Game NOT run, nothing committed. Read: proofs/exptime/* (INTERFACE, A, A2, B, B2,
C, D, R, X), exptime-feasibility.md (§3, §9), exptime-sources.md §1, exptime-model.md (§2), phase2-spec.md, plus
src/src/{allmain,hack,pray,timeout}.c spot reads. New scripts (all read-only imports of the existing tools):
`tools/exptime/review5_t1.py`, `review5_abc.py`, `review5_cd.py`, `review5_rb.py`, `review5_rb2.py`.
Verdicts: **HOLDS** · **REPAIRABLE** (repair given) · **BROKEN**.

## 0. Overall verdict

**Abstract reduction (G6 → 𝒢_F, Thm T1) and the game lift of the check path (B2 Thm GL): HOLD.** I could not break
them; the new exhaustive test agrees with G6 on 700 random instances, including the Lemma TS version.
**Concrete realization: one real bug + several missing pieces.** The X crossover tile (the SCD tile reused 20 times)
exposes only *joined* check ports (`*.ABC`, `*.CD`). Through joined ports the component checks are **unsound**
(machine-checked below). So the map as drawn cannot be wired to B2's check path. B2's design (split legs, each with
its own delimiters) is the correct one, and B2_e2e verifies it. The repair is a tile redraw, not a new idea.
So the theorem is **not broken, but not yet proved at the NetHack level**: it is still conditional on a layout
generator, and on the spec Rev. 4 being adopted.

## 1. Source problem G6 and Lemma L1 — HOLDS (citation PARTIAL)

- **Statement.** It matches the Hearn/Demaine–Hearn verbatim restatement: CNF F, flip ≤ 1 own variable, passing
  allowed, I wins iff F ever becomes true, and an infinite play is not an I-win (Chung). Two conventions are left
  open: who moves first, and whether the initial position counts. B §1.1 covers every reading: s = h or s = N_in,
  plus pre-processing.
- **Test.** `review5_t1.py` solves G6 with the initial position counted, for both first movers, and compares it
  with the game built on that convention. 0 mismatches (§2).
- **L1** (F checked only after I's moves) is correct. Proof: I may pass after a II-move that made F true. The test
  confirms it, since its checker is reachable only from P.
- **Citation.** It rests on secondary sources: SC79 is paywalled (PARTIAL). Before publication, read the SIAM
  original, or Hearn–Demaine *Games, Puzzles, and Computation* App. A. In the theorem statement, say which first
  mover is used. Both work.

## 2. Reduction logic (T1) — HOLDS

**New test: `review5_t1.py`.** It builds B §3 literally:
- literal doors MSCD(2,2) (O open-optional, S forced close);
- write paths, hub, P, the dead-end checker;
- the nature tree, with context doors and one coin;
- all edges directed.

It then computes the exact hero-vs-coin attractor (infinite = loss) and compares it with G6:

| realization | instances | mismatches |
|---|---|---|
| ideal MSCD | 300 (seed 5) + 400 (seed 11) | **0** |
| Lemma TS: every shared tunnel = SCD + context SCDs + merge/split | 700 | **0** |
| negative control (write path without the forced closes) | 700 | 42 + 67 |

Instances: |X|, |Y| ≤ 2, ≤ 3 clauses, both first movers. The largest game has 249 k positions.

The attractor covers every abstract cheat at once:
- skip nature's turn, re-roll the coin, choose the leaf, take two I-moves;
- partial write paths, declined openings, entering the checker at the wrong time, stalling.

Nature's only power is the coin, which is in the model. **HOLDS.** Gaps outside this item: the realization side
(§3, §4), and the test sizes are small.

## 3. Gadgets, check path, postselection lift

**(a) `*.ABC` joined hallway in the reused SCD tile — BROKEN as drawn; REPAIRABLE.**
`review5_abc.py`: when A, B and C of the Fig. 36a proto-precursor are joined, Ani's check [A→D, C→G, B→A, B→C]
degrades to [T→D, T→G, T→T, T→T].
- The clean set grows from {(3,5),(3,6),(4,6)} to 6 states. The new ones are adjacent-block states (3,4), (4,5),
  (5,6), all reachable.
- In the flat raw SCD (10,927 states), the joined checks give 40 "clean" states. Broken is **not absorbing**.
- Postselected vs ideal SCD: **SOUND = False** (COMPLETE True), for both initial states.

`review5_cd.py`: the same holds for the diode's joined `d.CD` port. The broken state "block on x=4" passes
[A→CD, CD→B] (3 of 4 states pass instead of 2; this is B2 §3.2's D→C→B detour).

So X's 206 check ports cannot be used as listed. B2_e2e attaches the checks to *separate* A, B, C (and C, D) legs,
each with its own WCX_b/WCX_t, joined only beyond the top delimiter. That version is VERIFIED (lose variant: LOSE).

**Repair:** redraw the SCD and diode tiles so that each leg has its own corridor, long enough for two delimiter WCX,
before the junction T (or before the C–D join). Regenerate X, and re-run X_verify on it.

**(b) O→J leak never exercised in X's random walk — HOLDS.** The leak is covered exhaustively at the abstract level:
- A2 flat raw network: broken absorbing, postselected = ideal;
- B2_e2e raw/complevel/checked modes;
- in the real engine: R-realgame saw 82 raw O→J walks.

X's walk *prunes* breaking moves, so it was never meant to exercise them.

**(c) Check-path order and delimiters — HOLDS in B2's design; REPAIRABLE in the artefacts.**
- The order is t = c_m → SCD-level G′ → component G′s → g. Both levels are needed, per the B2_e2e
  scdlevel/complevel negatives.
- B2 §3.2 requires the C–D corridor and the A/B/C legs to be separate e_l with delimiters, and B2_e2e implements
  this.
- Only X's port list contradicts it (item a).
- No generated layout exists yet, so the guard argument (B2 §3.3) is checked only on the one-SCD e2e instance.

**(d) Fig. 32 boards not sound vs the Fig. 31 reading — HOLDS (harmless).**
- Every composite that is actually used was checked SOUND + COMPLETE against its ideal:
  - SD as a flat concrete board (18,336 states);
  - SO and MSC from concrete WO/WMC + the verified SD;
  - SX;
  - WCX from concrete SO/MSC.
- The base boards never occur alone.
- Residual: replacing a verified SD by its ideal inside SO/WCX uses "simulation is a precongruence" (standard,
  STRONG).
- No concrete flat WCX (≈ 222 blocks) was ever explored.

**GL lift (B2 §2) — HOLDS.**
- Postselection is a per-play property, and nature only picks coin outcomes outside every gadget.
- So projecting a winning concrete strategy onto 𝒮 is sound. Leaks after t (WCX state 2, re-playing the coin) are
  cut off by "first visit of t".
- I found no history-dependence problem: σ′ is deterministic, and the coin outcomes fix the replay.

## 4. Model fidelity

- **Movement — HOLDS.** R-realgame: 0 mismatches, with negative controls. The model is generic, so the Fig. 32 boards
  are covered by it, although they were not themselves replayed in the engine (worth a cheap R run).
- **Fumbling during push-heavy play — HOLDS.**
  - The only reads of Fumbling on intended plays are timeout.c:902-924 (`slip_or_trip` + `nomul(-2)`,
    re-arm `rnd(20)`) and the door/untrap/kick sites. `moverock` has none, and `bldrpushtime` is messages only.
  - Fumbling only costs time, and nature cannot freeze the hero (C §2.3).
- **Z1 — REPAIRABLE (the criterion is too coarse).**
  - `review5_rb.py`: on the X map, C's over-approximation R_B stays inside the tiles (664 cells, 0 outside). Good.
  - `review5_rb2.py`: for Ani's **WO** board (inside every SO/SD/MSC/WCX), R_B reaches the location cell T (4,0).
    From there it can spread along corridors, although exact exploration shows no block ever reaches it.
  - A CHX/WCX on a coin corridor could therefore fail Z1 *as stated*.
  - **Repair:** state Z1 as "exact per-window boulder reach (G1, VERIFIED per board) ∪ R_B of boulder-carrying
    windows only, and no window within Chebyshev distance 3 of Z ∪ {E}". Compute it on the generated instance.
- **Z2/Z4 (dead coin after the `moves` wrap) — HOLDS, but REPAIRABLE in the text.**
  - The [A # T # B] tile passes the D_game lint (Z1/Z2 OK).
  - B's T2 proof and §4.3's H_σ do not yet say "wait while moves ≤ 0" (Z4 lives only in C/INTERFACE). Add it to B §5.4.
  - Note: unmodified 5.0.0 ends the game at moves ≥ 10^9 ("The dungeon capitulates", allmain.c:253). The result
    therefore holds only for the spec's cap-deleted, wrapping variant (phase2-spec common part). Say so in the
    theorem title.
- **Prayer / kick / #untrap / boots — HOLDS.** Re-read pray.c:1126-1158:
  - At Luck 0 off-altar, action = rn1(2,1) ∈ {1,2}, so minor troubles (cursed loadstone, boots) are never fixed.
  - pat_on_head needs trouble = 0. So the loadstone can never be uncursed, and the hero can never empty his
    inventory and squeeze past boulders (that would be a real soundness break).
  - Even an uncursed and removed pair of boots would only add a nature escape at T, which is a bounce under Z2.
- **Wizard-mode witness caveat — HOLDS, but the spec needs one sentence.**
  - In wizard mode, `scrolltele` prompts for the destination, so the *hero* would choose the coin's outcome. That
    makes the game one-player and kills the reduction.
  - The source path for a normal game is VERIFIED (C §2.2).
  - phase2-spec only says "non-wizard commands". **Add:** "the game runs in normal mode (`flags.debug` = false)".

## 5. Membership and size — HOLDS (bookkeeping repairs)

- **Thm M.** C1-C6 hold for every instance of the Rev. 4 language (C §4), so the problem is in EXPTIME through the
  attractor on ≤ 2^{p(n)} configurations; the `moves` counter is part of the state. HOLDS.
- **But Rev. 4 is only a "candidate".** It is in C-audit §1, not in phase2-spec.md. The language the theorem is about
  must be adopted formally there. It adds:
  - the TELEP_TRAP form with `seen=true`;
  - one `teleport_region` with `exclude`, `dir="both"`;
  - the cursed +0 fumble boots;
  - `noteleport` dropped.
- **Spec inconsistency.** The spec's "Str+Con ≥ 18" contradicts R3 setup (`vary_init_attr` can give 8/8). The
  consequence is harmless (Burdened only; Stressed needs Str+Con ≤ 11, checked: wc ≤ 346 ⇔ s ≤ 11.84), but fix
  the text.
- **Size.** O(N⁴) cells (B2 §3.6) is plausible and polynomial. B §0/§6 still says O(N²): update it.
- **Computability.** "Log space" is not justified once X's Tutte placement and rip-up routing are in the pipeline,
  but poly time suffices for EXPTIME-hardness. Claim poly time, or hard-code the constant-size crossover tile and
  use a regular bus layout.

## 6. Other attacks

- **Stalling forever** is a loss (REACH semantics), so it is fine. Exponentially long plays use only reusable
  gadgets and WCX state-1 hallways. HOLDS.
- **Counters.**
  - Prayer timeout and Luck timeout: irrelevant (never pray, Luck 0).
  - `exerchk` near LONG_MAX: `next_attrib_check` may wrap and fire every turn, but on a play without self-abuse
    exercise only *raises* Str/Con.
  - Dex abuse from Fumbling: Dex enters no intended rule.

  HOLDS.
- **Attribute drift / encumbrance.** The minimum start is Str = Con = 8 ⇒ wc = 450 ⇒ at most Burdened (speed only).
  Str/Con are non-decreasing without kicks. HOLDS.
- **Fumbling helplessness.** There are no monsters, and nature's only positional power is the coin. HOLDS.

## 7. Required repairs (priority order)

1. **Redraw the SCD and diode tiles with split check legs.** A, B, C into the precursor/toggle T junction, and C, D
   of every protodiode, each get their own delimiter-ready corridor. Regenerate X and attach checks per leg. Without
   this the check path is unsound (`review5_abc.py`, `review5_cd.py`).
2. **Layout generator** for the B bus layout + the Thm 5.3 G′ wrappers + the Lemma 5.6 chain on a small F. Re-run on
   it: X-style tile/corridor locality, planarity assertions, Z1 (repaired form), Z2 lint. Ideally also an abstract
   network-level attractor in the style of B2_e2e (gadget-level, not NetHack-level).
3. **Adopt spec Rev. 4** in phase2-spec.md. Add "normal (non-wizard) mode", and fix the Str+Con template line.
4. **Restate Z1** with the exact per-window boulder reach (R_B over-approximation leaks through WO's T).
5. **Text fixes in B:** add Z4 waits to H_σ/T2; size O(N⁴); poly-time (not log-space) unless justified; theorem
   title says "cap removed, wrapping counters".
6. **Citations:** obtain the SC79 G6 text, and state the first-mover convention used.
7. Optional: run the Fig. 32 boards (WMC, NR, WO) through R_run in the real engine; enumerate one concrete flat WCX.

## 8. Repairs applied (2026-10-29/30)

Repair agent; game not run, nothing committed. Scripts in `tools/exptime/`, outputs in `build/xover/`.

| # | Repair | Status | Evidence |
|---|---|---|---|
| 1 | Split check legs in the SCD and diode tiles; rebuild + re-verify the crossover | **DONE** | see below |
| 2 | Layout generator (B bus layout + Thm 5.3 G′ wrappers + Lemma 5.6 chain), Z1/Z2 on it | **DONE (main layer + check-path curve); machinery cells STRONG** | `L_gen.py`, `exptime/L-generator.md`. On 20 + 20 generated instances (77-1,926 crossovers): concrete main layer, static locality/planarity checks, network re-read from the blocks = G6 (S2; flipped crossovers disagree 14/20). The check path is routed through every check location of every block type (8 crossover templates: 604 legs, both delimiters each; validator replay ok). Z1/Z2 lint pass on the generated coin. S3 (SCD-level postselection, abstract leak) = G6 on 19 instances. Not done: the WCX/SO/SD/SX boards drawn in cells (no concrete WCX board exists), hook curves, boulder-level attractor. Side fix: crossover.json diode `checks` were off by one (X_build), now rebuilt; X_verify ALL AS EXPECTED |
| 3 | Spec Rev. 4 adopted (normal mode, Str+Con line) | **DONE** | `phase2-spec.md` Rev. 4 items 10-13; common-part template line now "start Str+Con ≥ 12 for every setup outcome"; commands line + item 11 require `flags.debug` = false (wizard prompt at `scrolltele`, teleport.c:872-873); witness caveat in `exptime-feasibility.md` §9 note 1 |
| 4 | Z1 restated with exact boulder reach | **DONE** | `C-audit.md` §1 (Z1 exact: R_B^ex = ⋃ windows' explore reach, G1 LEAK-free + window locality; sufficient rule: no window within Chebyshev 3 of Z ∪ {E}; how to check on a generated map); §6 item 1 updated |
| 5 | B text: Z4 waits, O(N⁴), poly time, cap removed | **DONE** | `B-reduction.md`: title + scope box + result table (T2, S, ⇒) say "10^9 cap removed, counters wrap"; H_σ (§4.3) and T2 (§5.4, both directions) have the Z4 waits / dead-phase bounce; §6.2-6.3 size O(N⁴) citing B2 §3.6; computability = polynomial time, log space not claimed |
| 6 | SC79 original text, first-mover convention | **OPEN** | not attempted |

**Repair 1 details.**
- `X_build.py`: new `scd_tile(variant)` (19×37 / 21×43) and `diode_tile()` (5×11). Every L′ location of every
  component and the SCD's O, I, J has its own 3-cell leg (Wb, mid, Wt) before its junction, as in `B2_e2e.gprime`;
  contract `check_tile_legs` asserted. v1 tiles kept as `scd_tile_v1`/`diode_tile_v1`; v1 map saved as
  `build/xover/crossover_v1.{txt,json,png}`, `crossover_small_v1.png`, `routes_v1.json`.
- Attacks re-run on the NEW tiles, check map read off the tile geometry (component Wb slots walled):
  - `review5_abc.py`: v2: ports sharing a check region: none; precursor clean set [(3,5),(3,6),(4,6)] (3), toggle 3,
    diodes 2/4; flat SCD (10,927 raw states) → 12 clean, **broken absorbing True, postselected vs ideal SCD SOUND True
    COMPLETE True** for both initial states. v1 (control): A, B, C (+E, F) share regions, prec clean 5, 36 clean,
    absorbing False, SOUND False.
  - `review5_cd.py`: v2 diode tile and both SCD diodes: C, D in different regions, clean 2 of 4 = split set,
    broken absorbing. v1: joined, clean 3 of 4.
- New map (`python X_build.py`, seed 2, scale 453 after the build's own enlargement): 453×432, 11,760 floor cells,
  166 boulders, 66 tiles (SCD variants 5×v0, 1×v1, 14×v2), 46 corridors; `check_map` passes. Getting the bigger
  tiles routed needed a de-degenerated drawing, a vertex-edge clearance pass, port-order variants placed by the
  widest-sector rule and negotiated-congestion routing (X-crossover.md §7).
- `X_verify.py` (adapted: per-variant canonical tiles, new part (d)): grid symmetries isomorphic; (a) 7 states, SOUND
  + COMPLETE vs directed crossover, negative controls fail; (b) only A1→B1, A2→B2; **(d) 66 placed tiles: every check
  location alone with all Wb (or Wt) walled, intended joins only; 604 legs, 684 check locations**; tile systems:
  SCD 12 clean = ideal, diode 2 clean = ideal; (c1) 8 scripted crossings reach their exits (61,112 moves); (c2)
  100k moves no assertion failed; `--ext-only` 100k moves, 2,772 external returns all strictly reachable. ALL AS
  EXPECTED.
- Found while re-running: X_verify's global-vector check was not an invariant of its own random walk (episodes that
  start at an internal corridor cell drop the hero at an internal junction); fixed (strict check until the first drop,
  plus the `--ext-only` mode). Not a map bug.
- `review5_rb.py` on the new map: closure R_B 664 cells, 0 outside the tiles. `X_render.py` re-run
  (`crossover.png`, `crossover_small.png`).
- Docs: `X-crossover.md` (§0 table, §3 drops note, §5 check ports v2, §6 size, §7 v1 bug + fix), `INTERFACE.md`
  ("X v2" entry).

**Repair 4 evidence** (`review5_rb2.py`, part 2 added): exact reach per window, broken states included, no LEAK:
protodiode 4 states / 4 cells, proto-precursor 28 / 8, WMC 6 / 6, NR 147 / 16, WO 123 / 17; no port cell reached
(the R_B closure reaches WO's T (4,0); exact exploration does not).

**Repair 2 (2026-10-30, L-generator.md).** The guard argument and Z1/Z2 are now checked on generated instances,
not only on B2_e2e's one-SCD example. That covers the main layer concretely, the check path as a certified planar
curve, and the abstract S3 attractor. The remaining gap is local: replacing each classified crossing on that curve
by a drawn WCX/SO/SD/SX board (STRONG, a standard planar redraw).

**Theorem status after the repairs.** The joined-port soundness bug (§3a) is fixed at the tile level and on the
assembled crossover map. EXPTIME-hardness at the NetHack level stays conditional on repair 2 (no generated instance
yet, so the guard argument and Z1/Z2 are still checked only on the B2_e2e one-SCD instance and the coin tile) and on
the SC79 citation (repair 6).

