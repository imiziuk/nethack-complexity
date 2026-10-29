# Review 4 (adversarial, final): NP-hardness of L_ON* (hu-on-lower.md §2-§5, Revision 3)

Reviewer sub-agent, 2026-10-29. Read: phase2-spec.md (incl. Rev. 3), hu-on-lower.md (§1-§8), review-2.md,
review-3-pspace.md, citations.md, tools/gen_on_instance.py, tools/check_small.py; source NetHack 5.0.0 @ 16ff591
(`src/src/<f>:line`), read-only. Game binary not run. Nothing committed.

## Verdicts

| # | Target | Verdict |
|---|---|---|
| 1 | Lemma 4.1 isolation (diagonals, holes, boulders leaving gadget windows, S-bend wires) | **HOLDS**; one missing paragraph ("foreign boulders", §1.3 below) should be added to the text |
| 2 | Lemma 4.2 planarity / crossover bound | **HOLDS** (hand case analysis re-done with explicit depth inequalities, §2; 660 new random instances up to m = 46, nesting level 5, no assertion failure) |
| 3 | §5 soundness, completeness, hunger margin | **HOLDS** (modulo [ext] T1 and the §6 prayer/ball items already marked [conj]); checker exhaustive on 18/23 small UNSAT levels, 0 counterexamples (§5) |
| 4 | Polynomial reduction + Rev. 3 branch-stair pocket | **REPAIRABLE → repaired**: the generator did NOT emit the pocket or `des.levregion`; minimal edit made (§3) |

No counterexample found to any claim. Weakest remaining points (unchanged): de Berg–Khosravi statement (P4, PARTIAL in
citations.md), §6 ball/prayer [conj], no level loaded in the real game.

## 1. Lemma 4.1 (isolation) — HOLDS

1.1 *Cell geometry.* Every pattern (X, Cl, door, wire incl. S-bend, junction, start, goal, sentinel+pocket) has all
non-port floor cells in tile-local [1,9]²; ring corners are stone; ports are side midpoints. Two cells of different
tiles that are 8-adjacent both lie on rings ⇒ both are ports ⇒ they face each other orthogonally. The argument is
per pattern and per dihedral image, so it is a complete proof, not a sample; `check_separation` re-checks it on
every built level (393 small + 660 random large levels this session, all pass). Consequently no diagonal step,
no corner-rule interaction and no push crosses a tile boundary except orthogonally through a port pair.

1.2 *Holes.* Every hole is s1 of an X tile: neighbours S and (7,5) (tile-local, K-in-W frame), the other six are
stone (pattern rows 4 and 6 have floor only at x ∈ {1,3,5}). So (i) no diagonal has s1 as a corner with both
end cells floor (Rule R, Lemma 2.1 correct), and (ii) a boulder can enter s1 only by an E–W push: from the west
with the hero on n1 and the boulder on S, or from the east with the hero on (8,5) and the boulder on (7,5). The
hero reaches n1 only after δ left n2, i.e. after a push from k (Lemma 3.5(a)); (8,5) is downstream K. Hence
**every hole plug is preceded by the opening of that crossover's gate from upstream** — whatever boulder is used
(τ or a foreign one). This is exactly what Claim A needs.

1.3 *Boulders leaving gadget windows / S-bends (attack on "only interfaces are ports").* Boulders CAN cross
ports, e.g. W of a Cl pushed from Q down the T-lane (hero on Q, a K→P move), or τ pushed from S along the P line
of an X tile, or any boulder pushed through a junction. The text says the proof "does not need" the S-bends, but
it never states why foreign boulders are harmless. The missing argument (I checked it; it holds):
- Under F1-F4 a boulder only ever *removes* hero moves (it is bad rock for F3 and an obstacle for steps), except
  through its own pushes; the only push effect that *adds* moves is plugging a hole (simulation argument: a play
  with boulder set B' ⊇ B is matched step-by-step by the play with B as long as no boulder of B' \ B is pushed into
  a hole; pushes of B'\B become plain steps).
- By 1.2 a hole is plugged only after its gate opened from upstream. Foreign boulders can also never enter a door
  pocket from the q side (pocket's only orthogonal neighbour is X) nor make Kd movable, nor enter Z_σ from P except
  through N (blocked by W) — they can only block (close σ, jam a door, block a lane), which only hurts the hero.
- S-bend corners: a boulder entering a straight wire through a port stops at (2,5)/(8,5) (next cell stone,
  perpendicular push needs a stone cell); L-wires stop it at the centre; only junctions let it turn. True, but
  only a state-space convenience, as the text says.
Recommended text: add 1.3's first two bullets as "Lemma 4.1(b) (foreign boulders)". With it, Claim A's
"a segment touches the rest of the map only at its gates" is correct for boulders as well as for the hero.

1.4 *Witnessed vs. tile gadgets.* I compared the 8-neighbourhoods of n2, n1, S, s1, k, p (X), N, T, Q, (5,4), C,
U-turn cell (Cl) and e, X, q, pocket (door) with the §3 maps: identical up to the dihedral image; the extra
bends are at Chebyshev distance ≥ 2. Holds. The exhaustive model check (§4) covers all interactions inside the
small levels independently of this hand check.

## 2. Lemma 4.2 (planarity, crossover bound) — HOLDS

Re-derived with explicit inequalities (Λ = 7, ℓ = level of X, L ≤ 3 legs, depths on X's side):
- X's band: q_k = 1 + 7ℓ − 2(k−1) ∈ [7ℓ−3, 7ℓ+1], f = 7ℓ+2, d = q_L − 1 ≥ 7ℓ−4. A child C: f(C) = 7ℓ(C)+2 ≤ 7ℓ−5 < d.
  Lanes of X span depths [2, q_k − 1] ⊆ [2, 7ℓ]; an ancestor A has d(A) ≥ 7(ℓ+1) − 4 = 7ℓ+3, so none of A's K pieces
  reaches X's lanes, and A's entry rows that pass over I(X) are at depth ≥ 7ℓ(A)−2 > 7ℓ.
- Entry row of leg k' (depth q_{k'}+1 ≤ q_k − 1 for k < k') runs hL → u_{k'}−1 and crosses both lanes of every
  leg k < k' strictly inside (u_k+1 ≤ u_{k'}−2): straight-straight, as (c) requires. It never meets children
  (depth ≥ 7ℓ−2 > f(C)) nor door/Cl tiles of other legs (those sit at depth q_k ≠ q_{k'}+1).
- Dive of X at depth d crosses exactly X's lanes right of a(first child), strictly between its corners hR, a(C);
  forward verticals (depths ≥ q_k) and doors (q_k, q_k+1) are above d.
- A step run starts at a leaf Z (pre-order: a non-leaf is followed by its first child = dive), so it is at depth
  9; the tokens between hR(Z) and a(N) are only closing tokens (legs, hR) of ancestors; lanes of level-1 clauses end
  at depth ≤ 7 < 9, lanes of level ≥ 2 reach ≥ 10 > 9 (crossed, allowed); dive verticals at hR(A) span
  [d(A), f(A)] ⊆ [10, ∞) (not crossed); no a/hL token lies between, so no forward row at depth 9 is met.
- Start/switch/end: rows at D_s = 7ℓ_s+3 (outward of every band), verticals at x_E, x_c (right of every token
  and of join_n), end row at depth 9 to goal col = ends_pos < x_c. Main line crossed once, at x_c.
- Count: per lane ≤ 2 entry rows + 1 dive + (m+1) depth-9 runs ⇒ #X ≤ 1 + 2L(m+4). Correct.
Mechanical evidence (this session, `scratchpad/stress.py`: random non-crossing leg orders generated directly,
up to 40 legs per side, variable sharing, deep nesting): 660 levels, m ≤ 46, n ≤ 29, nesting level ≤ 5,
#X ≤ 197, tiles ≤ 322×70: every generator assertion (4.1, 4.2 overlap/orientation rules) held, every §4.6
bound held (W_t ≤ 12m+2n+4, H_t ≤ 7m+7, #X ≤ 1+2L(m+4), F ≤ 37·W_t·H_t), and all 379 instances found
satisfiable (brute-force SAT, run when n ≤ 18) were won by the replayed intended play (≤ 2 visits per cell, longest cookie-less run 2, min hunger 858, max 28,048 moves).
(The earlier stress test reached nesting level ≤ 2 only.) Suggest keeping the proof as "[conj → proved by hand,
review-4 §2]".

## 3. Polynomiality and the Rev. 3 branch-stair pocket — REPAIRABLE (repaired)

- Sizes (§4.6) are polynomial; leg order is part of the input (P2), so the generator is linear given the drawing.
  The brute-force order search is only a convenience for small inputs. Holds.
- **Gap:** `gen_on_instance.py` did not emit Rev. 3 item 8 (no pocket, no `des.levregion`), so its levels were
  exposed to the review-3 §4.1 hole (branch stair on s, stale hero position, prayer `safe_teleds` to g).
- **Edit made (minimal):** the sentinel tile now also holds a 1-cell pocket at tile-local (2,2) (map char `b`,
  written as `.` in `des.map`, no cookie, no trap), 8 stone neighbours, 3 cells from the pit; the Layout asserts it
  is sealed and `check_small.Model` asserts it is not in the hero's floor graph. The script now contains
  `des.levregion({ region = {bx,by,bx,by}, region_islev = true, type = "branch" })` (absolute coordinates, same
  convention as the existing `des.teleport_region`). Source check: `lspo_levregion` → `l_get_lregion` reads
  `region_islev` [sp_lev.c:5410-5428, 5475-5491]; `finalize_level` → `fixup_special` [sp_lev.c:6050] places
  LR_BRANCH lregions via `place_lregion` and sets `added_branch`, so the default random branch placement
  [mkmaze.c:640-645] is skipped; a 1-cell region is `oneshot` [mkmaze.c:393]; the cell is ROOM with no trap, so
  `bad_location` passes [mkmaze.c:341-351] and `place_branch` puts the stair there. The pocket is unreachable
  (no floor neighbour, `non_passwall`, `non_diggable`), so no proof changes. Stone instead of walls around P is
  enough: both are impassable, and STONE is not a valid lregion target.
- Re-run after the edit: all 393 small levels build; 370/370 satisfiable replays reach g (min hunger 859); the
  exported BFS models are byte-identical to the pre-edit ones (pocket is not floor in the model). Stats: cookies =
  F − #X − 2 now (pit and pocket), Lua lines +1. hu-on-lower §4.6/§4.7 updated accordingly.

## 4. §5 soundness / completeness / hunger — HOLDS

Soundness, attacked points:
- Claim B's P graph: from s0, x_E needs every fork_i → join_i (no main-line tile between fork_i and join_i: the
  route goes join_{i−1} → fork_i, join_i → fork_{i+1}); a branch passed fork→join pushes each W into Q (T→(6,6)
  diagonal refused: corners N=W, (6,7) stone); from the join side the U-turn blocks (push into stone, both
  diagonals have corners N, stone). Before t_1 no K pass happened, so no S shortcut into a lane. Holds.
- Z_σ entered from N after closing (W pushed to Q, (5,4), C): door q side is dead (q→e and q→pocket diagonals have
  corner Kd), forward exit blocked for each W position. Holds.
- Reopening a closed σ by pushing W back from C needs the hero on the forward part = on E_j, i.e. C_j already
  passed: harmless. K→P after passes only closes more. Main-line crossover at x_c and the goal tile are gated
  by s1 (P on S stepping toward K downstream falls). Holds.
- Foreign boulders: see §1.3 (only blocking, except hole plugs, which need the gate opened).
Completeness: intended play is deterministic; the chosen σ's W is on N; K route is a simple path, each crossover
used once; P phase never touches δ/τ/Kd. Replayed on 370/370 small + 379 large satisfiable levels.
Hunger: start 900, −1/turn (speed 12, unencumbered, no rings/amulets), eat at ≤ 860 (+40, meal charged 2 turns),
≤ 2 consecutive cookie-less moves ⇒ u.uhunger ∈ [857, 900] (observed min 858 on large, 859 on small levels):
never Hungry (≤ 150) or Satiated (> 1000); turns ≤ 4F, polynomial. NO side does not use hunger at all (pure
movement argument, valid for every horizon). Holds.

## 5. Checker: the 7 timed-out UNSAT levels

New exact search `tools/fastbfs/` (Rust, no dependencies): same state space and transition rules as
`check_small.Model.solve` (state = boulder set, unplugged holes, min node of the hero's free region; diagonals with
their corner conditions; no pruning). Input = the compressed model written by the new
`check_small.py --only '<json list of clause lists>' --export DIR`. Keys are a lossless mixed-radix code (boulders
never leave their push-component, so each component's boulder subset is ranked exactly; 24 bytes/state) and the
visited set compares full keys (no hash-only membership, no symmetry or dominance pruning).
**Validation:** on all 36 previously solved BFS levels (16 UNSAT + 20 SAT) it reproduces the Python result AND the
exact state count (e.g. 734,784 for [2][-2][-1,-2]); the debug build also asserts encode/decode round-trip on
every generated state (30 levels). ~100x faster than Python.

| Level | Result |
|---|---|
| [2][-2][1,3] | **g unreachable, exhaustive**: 1,175,464 states (27 s) |
| [2][-2][-1,-3] | **g unreachable, exhaustive**: 2,139,544 states (53 s) |
| [3][-3][1,2,3], [1][-1][-1,-2,-3], [3][-3][-1,-2,-3] | not finished at hand-back: > 26-34 M states after 24 min each (g not reached); run stopped at hand-back (memory) |
| [2][-2][1,2,3], [2][-2][-1,-2,-3] | not finished: > 34 M states (earlier 48-byte-key run, capped); queued runs not started (memory) |

So the exhaustive UNSAT side is now **18/23**, 0 mismatches. The 5 open levels are the largest (D = 248-321
dynamic cells, 21-32 boulders); their state spaces exceed ~35 M states, and with 24 B/state + table the laptop's
free RAM (~2-4 GB beside other apps) limits 3 parallel runs to ~75 M states each. To finish: run them one or two at
a time overnight with `--max-states 250000000` (~8 GB). None of this affects the proof, which does not rely on
the checker.
