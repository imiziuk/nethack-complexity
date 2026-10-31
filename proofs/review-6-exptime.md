# Review 6 (adversarial): EXPTIME-hardness of L_OFF^{W+C} under R3 (G6 reduction)

Reviewer: review-6 agent, 2026-10-30. Game NOT run, nothing committed, no file outside this note and three new
scripts edited. Read: phase2-spec.md (Rev. 1-4), problem-definition.md, exptime/{B-reduction, B2-checkpath, X-crossover,
C-audit, INTERFACE, L-generator, M-machinery, R-neighbourhood}.md, then review-5-exptime.md. Source spot reads:
src/src/{hack,pray,trap,eat,makemon,nhlua,minion,teleport}.c. Code read: A_core, L_gen (Router, gprimes, assemble,
build_tile_block, coin_lint), R_neigh (Lua harness). New scripts (read-only imports): `tools/exptime/review6_hooks.py`,
`review6_hooks2.py`, `review6_weak.py`.
Severities: **FATAL** (the approach cannot work) · **SERIOUS** (a proof step or artefact is wrong; repairable) ·
**MINOR** (overclaim / gap in an otherwise sound step) · **NOTE**.

## 0. Verdict

- **Abstract chain: I could not break it.** T1 (G6 → 𝒢_F, incl. Lemma TS, Lemma N, Inv-L, infinite plays), the
  game lift GL of postselection (B2 §2), C's adversary audit and the movement model all survived my attacks
  (§2-§3).
- **Concrete check path: one real soundness bug (F1), caused by a missing design rule (F2).** L_gen's hook curves
  cross the **g-side stubs of the component's own legs** with WCX boards ("GX"). Those stubs are joined to the
  component, so the WCX leak Bt→L/R lets a check a→b be passed as X→b or a→X. That is review 5's joined-port bug
  again, in a new form. Machine-checked on Ani's boards:
  - protodiode: clean set 2 → 3. The extra state allows **B→A, i.e. the diode runs backwards**.
  - proto-precursor: clean set 3 → 4. The extra state is review 5's adjacent-block state (3,4).
  - Both crossings occur on the generated SCD and diode tile templates, which every instance uses.
- No existing test can see this:
  - `validate` checks geometry only.
  - B2_e2e and S3 leave the crossings inside G′ out.
  - HK draws only an SX crossing.
- **Hardness cannot move from CONJECTURE to STRONG yet.**
  - With F1/F2 repaired, the remaining gaps are drawing steps that already have a complete argument (box redraw,
    hook drawing). Ani's own planar construction avoids F1.
  - After the repair, and an abstract end-to-end run that models the crossings inside G′, STRONG is justified.

## 1. Findings

### F1 — SERIOUS: GX crossings (WCX on an own leg's g-side stub) weaken the component checks

**Evidence.**
- `L_gen.py:1128-1129`: `can_cross` returns `'GX'` for a g-side link whose leg is in `dead`.
- `L_gen.py:1362-1363`: every hook is routed with `dead=own | dl`, where `own` is the legs of the G′ being checked.
  `own` is added to `self.dead` only after the hooks (`:1369`). So hooks may cross the stubs of the component's own
  legs, during that component's own checks.
- `L-generator.md:104-106` states the intended rule: GX "only after that leg's G′ is done in time". The code allows
  GX once the two delimiter passes are done, which is before the checks.
- B2-checkpath.md:244-245 and §3.4 mean WCX on **dead middle** segments, i.e. between Wb and Wt. After both passes
  those segments are isolated. The g-side stub (location to Wb) is not dead: it stays joined to the component.

**What the generated templates contain** (`review6_hooks2.py`: scdc and dio tile blocks, parity 0, final routing):

| tile | G′ | location | its route crosses |
|---|---|---|---|
| dio | d | B | GX on own stub d.A |
| dio | d | D | GX on own stub d.C |
| scdc | d1 / d2 | A | GX on own stub d1.B / d2.B |
| scdc | d1 / d2 | C | GX on own stub d1.D / d2.D |
| scdc | prec | B | GX on own stub prec.A |
| scdc | prec | C | GX on own stubs prec.A and prec.B |
| scdc | tog | B | GX on own stub tog.A |
| scdc | tog | C | GX on own stubs tog.A and tog.B |
| scdc | prec, tog | G | CHX on own mids E, F (dead: safe) + SX |
| scdc | scd (level 1) | O, I | CHX on own mid tile.O (safe) + SX |

`review6_hooks.py` gives the totals for both parities:
- scdc: 12 of 21 hook paths have a non-SX crossing;
- dio: 2 of 4.

**Mechanism.** The ideal WCX in state 1 allows Bt→L and Bt→R (the leak, giving state 2). State 2 allows L→Tp and
R→Tp. Take a GX on own leg X's stub, sitting on the curve that brings the check walk to location a_i (under Ani's
placement this is the chain edge Op_i→SD_i; under HK placement it is the a-hook SD_i→a_i). At check time the hero
leaks Bt→L onto X's stub. He enters the component at X, skips SD_i and a_i, walks X→b_i inside, then b_i→SO_i, and
the check passes. So check (a_i→b_i) also accepts X→b_i. The symmetric case, a GX on a b-hook, gives a_i→X.

**Minimal counterexample** (`review6_weak.py`, exact A_core traversal relation, check sequence legal = clean):
- **Protodiode** (Fig. 35a, checks [A→C, D→B]). On the dio tile the D-route crosses C's stub, so check 2 accepts
  {D, C}→B. The clean set grows from 2 to **3**.
  - The extra state is the boulder on x=4 (`#...0#`). Its port moves are A→B, A→C, **B→A**, B→C, C→A, C→B, so the
    diode is bidirectional.
  - That state is reachable from the clean state `#..0.#` with one push.
  - With the weakened checks it passes: A→C is legal, then the leak gives C→B.
  - So a hero can break any route-edge diode or SCD-internal diode before t, walk it backwards, and still pass its
    level-2 check.
- **Proto-precursor** (Fig. 36a, checks [A→D, C→G, B→A, B→C]). The generated crossings are B-route over A's stub
  and C-route over A's and B's stubs. Under Ani placement the starts become {A,B,C}→G, {B,A}→A and {B,A}→C. The
  clean set grows from 3 to **4**.
  - The extra state is blocks at (3,4). That is exactly the state that made the postselected SCD SOUND = False in
    review 5 §3a.
- Single-substitution table, upper bound for any routing: precursor up to 13 of 28 states "clean", protodiode 4 of 4.

**Why nothing caught it.**
- `validate` (`L_gen.py:1893ff`) is geometric only.
- S3 and B2_e2e omit the crossings inside G′ (L-generator.md:170-172; B2-checkpath.md:244-245).
- HK draws only an SX hook crossing (M-machinery.md:20).
- The hook jumps are only counted, as "SX" (`L_gen.py:1364`; L-generator.md:168-169).

**Repair.**
1. Forbid GX on any leg whose component still has checks to do, including the own G′.
2. Let hooks cross only:
   - (i) chain segments, by SX in time order;
   - (ii) own middle segments (between Wb and Wt, dead after both passes);
   - (iii) legs of components whose G′ is completely finished.
3. Route between sectors through the annulus between the two delimiter passes, as Ani's Fig. 23 does.
4. Re-run the 8 crossover templates and the tile templates.
5. Add a B2_e2e-style abstract test with the crossings inside G′ modelled. On one protodiode, a GX should make the
   "lose" variant WIN, and its removal should give LOSE.

### F2 — SERIOUS: guard argument (B2 §3.3) incomplete. Hooks hang off main-game locations; their crossings need a placement rule

**Evidence.**
- B2-checkpath.md:165 says "O_i (SO) entrance at b_i: dead end until O_i's button is pressed". That holds only if
  the b-hook b_i→In_i crosses nothing that can be entered from the b_i side.
- b_i is a component location that is reachable in clean play before t, e.g. diode output B, or precursor A and C.
- With HK placement (SO and SD together, M-machinery.md:20), a b-hook that crosses a live corridor with a WCX gives
  a **wormhole before t**: from b_i to Bt, leak Bt→L/R onto that corridor.
- The leak leaves the WCX in state 2, from which L→Tp can later be used to reach SO_i's entrance from outside. That
  can skip a check altogether if the hero can re-enter from the hallway side.
- Neither B2, M nor L states which curve segments may carry which crossing kinds, or where SO_i and SD_i sit.

**Counterexample status.** In the generated templates the only live crossings are the GX of F1. The general
pattern is exploitable as soon as a b-hook needs to leave its sector.

**Repair.** Add the rule:
- Use Ani's placement: SO_i next to b_i, SD_i next to a_i. Then the b-hook and a-hook have length 0.
- Only chain-only edges cross anything: Out_{i-1}→Op_i and Op_i→X_i, reachable only after t.
- Crossing kinds on those edges as in F1's repair.
- Prove the guard lemma for this rule: every crossing's Bt side is reachable only after t, and its hallway leads to
  no component whose check is still pending.

### F3 — MINOR: Z1 near the coin is "VERIFIED" only for the main layer

- L-generator.md:19 marks Z1/Z2 VERIFIED.
- The coin halo is Chebyshev 4 original cells (`L_gen.py:1075-1081`).
- The machinery boards placed at chain crossings are 478×608 (WCX) or 181×312 (SX) cells. Their placement is
  undrawn (M-machinery.md:145-147).
- So Z1 for the final level is a design rule, not a check.
- **Repair:** after the box redraw, take the halo in the redrawn coordinates, and check the exact reach of every
  board window against Z ∪ {E} ∪ N8.

### F4 — MINOR: polynomial-time computability rests on a heuristic search

- The router is a search with deadlines and budgets:
  - per-tile 90 s deadline (`L_gen.py:1391-1393`);
  - 25 min budget, with rewinds (`:1445-1450`);
  - the instance fails by assertion (`:1825`).
- Junction-comb templates are keyed by kind, width and arms (`:1810-1811`), so new instances can trigger new
  searches.
- X_build needed a seed change to route at all (X-crossover.md:143).
- B §6.3 ("all of these run in polynomial time") therefore claims more than the code shows.
- For ≤_p hardness what is needed is a constructive layout argument: Ani's planar Thm 5.3 / Lemma 5.6 drawing,
  constant-size crossover and machinery boards, and an orthogonal box drawing in polynomial area. STRONG at most.
- **Repair:** state that argument in B §6, and treat L_gen as evidence.

### F5 — MINOR: the generator never emits the instance

- No Lua script is produced. The level is a macro grid of blocks (L-generator.md:52-54).
- Whitelist conformance of a real output has never been checked: sentinel pit, branch-pocket `levregion`, the single
  `teleport_region` with `exclude` (zx1 ≥ 1, every T in Z), s ∉ Z, P ∉ Z.
- Smaller: R_neigh's harness places boulders with `des.object("boulder", x, y)` without the explicit curse state the
  whitelist asks for (phase2-spec.md:12-13; R_neigh.py:761). This is harmless (boulder BUC is inert), but the
  spec text and the harness disagree.
- **Repair:** emit the script for one small instance (windowed if needed), and lint it against Rev. 1-4.

### F6 — MINOR: "VERIFIED" used for finite tests

- S1/S2 (340 / 40 instances), X (c2) random walks, and the R-neighbourhood coin row ("landings A 73, B 87, T 0") are
  tests of ∀-claims.
- The ∀-claim for the coin rests on the C-audit source reading (C-audit §2.2), which is fine, but the row should
  say so.
- M's "VERIFIED SOUND + COMPLETE" for SO/SX/WCX depends on two standard facts: bisimulation is a congruence for Net2,
  and nested = flat. These were checked only on MSC; the flat SD run did not finish (M-machinery.md:98-99, 148-149).
- **Repair:** label these as "VERIFIED on the tested set" or "VERIFIED modulo congruence".

### F7 — NOTE: C-audit's prayer row omits divine minions; harmless

- `angrygods` case 7-8 calls `summon_minion` (pray.c:760-771); for a neutral god that is an elemental (minion.c:207-208).
- Angering is reachable by praying too soon: `p_type` 0 → `gods_upset` → `angrygods` (pray.c:2316-2321, 1436-1442).
  Repeated, `ugangr` makes maxanger ≥ 8.
- `makemon` returns NULL whenever `iflags.debug_mongen` is set (makemon.c:1168; set by `mongen=false`,
  nhlua.c:1470-1481). So J1 (no monsters) holds.
- Add this line to C-audit J1 / §2.5: it is the only route to a monster on the level.

### F8 — NOTE: `hunger=false` blocks only `gethungry`

- `iflags.debug_hunger` is tested only at eat.c:3167. `morehungry` (eat.c:3283) still works.
- Its callers are unreachable in W+C: spells (spell.c:1367), jumping (apply.c:2121, 2161), vomiting (timeout.c:245),
  `^T` without a trap (teleport.c:1160, refused), fountains/sit/eat (absent).
- J13 is right, but its justification should name eat.c:3167.

### F9 — NOTE: wrap width depends on the data model

- `svm.moves` is `long`. That is 2^63 under LP64 but 2^31 under LLP64 (Windows builds).
- N1's dead phase and Z4 waits are correct either way.
- The theorem should name the data model, since SC3 wrap of signed `long` is UB in C and part of the spec.

### F10 — NOTE: citation

The SC79 G6 text and the first-mover convention are still open (review 5 repair 6).

## 2. Game-theoretic correctness (a) — no break found

- **T1.** I re-derived Fact R, Lemma N, Inv-L, and the soundness strategy ν_τ against every cheat:
  - declined opens;
  - partial write paths;
  - wrong demux branch;
  - re-roll;
  - checker with F false;
  - stalling.
  Lemma TS's context-door invariant J_TS holds across different sharing regions, because every region restores all
  its K's to closed. Infinite plays are losses, consistent with G6's "draw = II".
- **GL** (B2 §2.2). The single-play lemma uses only the legality of one traversal sequence plus "broken absorbing
  under L′". So leaks after t (WCX state 2, coin re-use) are harmless, and σ is well-defined by replay against the
  same coin outcomes.
- The two-level composition holds: from the prefix to t₁, components are postselected; from the prefix to t, the
  SCDs are ideal.
- **The one gap is F1/F2**, which breaks GL's hypothesis H2 for the drawn G′. "Postselect(G, C) ≅ ideal" is true for
  Ani's C, but the drawn G′ realizes a weaker C′.
- **Dead coin.** Under Z2 a dead coin is a bounce. With boots off, nature's escape at T is also a bounce. In the YES
  direction the hero wears the boots and waits while `moves ≤ 0`, so neither helps nature.

## 3. Model vs C code (b) — no mismatch found; spot checks

| Item | Reading | Verdict |
|---|---|---|
| Diagonal corner rule | `bad_rock` = Sokoban boulder or obstructed (hack.c:938-945). `cant_squeeze_thru` gives 3 under Sokoban for the hero; weight 520 < WT_TOOMUCH_DIAGONAL check first (hack.c:952-978, 1152-1173) | = A_core |
| Push | `moverock_core` reads sx, rx: obstructed, iron bars, boulder, trap, monster, door (hack.c:420-600). Sokoban refuses diagonal pushes (:430-436) | = A_core |
| Failed push / squeeze | `could_move_onto_boulder` → `squeezeablylightinvent` needs inv_weight ≤ −850. With 520 carried and wc ≤ 1000 that is unreachable (hack.c:145-162, 304-308) | holds |
| `m` prefix into a boulder | the nopick branch never pushes; it moves only when poly'd or squeezeable (hack.c:383-414) | no-op |
| Run, rush, travel | `context.run ≥ 2` refuses boulders. TEST_TRAV never goes through boulders in Sokoban (hack.c:1218-1236). Rush is single `domove` steps | subset of the model |
| Kick, throw near boulders | kicked boulder → `kick_ouch` (dokick.c:517). No object except a boulder reacts to TELEP_TRAP (grep: hack.c:578, trap.c:3469 rolling boulders only) | holds |
| Trap entry under Fumbling | the escape test short-circuits on `!Fumbling` before `rn2(5)` (trap.c:3035-3038) | no RNG |
| Prayer | off-altar `action ≤ 3`, and `rn1(Luck+2,1)` ∈ {1,2} at Luck 0 (pray.c:1125-1130). Case 2 fixes only major troubles (:1148-1152), so loadstone and boots stay cursed. p_type ladder at pray.c:2148-2161 | holds |
| Minions, hunger | F7, F8 | holds |
| Sokoban flag | cleared only by `maybe_finish_sokoban` when no PIT/HOLE remains (trap.c:7059-7082); the sentinel pit keeps it | holds |

C-audit's command table (search, wait, #sit, #force, kick, throw, pray, engrave, apply, travel/run, eating, dropping,
boots/loadstone curse rules, holes and trapdoors, luck and prayer timeout) matches my reading. I found no command that
moves the hero or a boulder outside P/K/N/R.

## 4. Composition (c)

- Fine:
  - block contract;
  - arm matching;
  - window non-adjacency;
  - the WCX frame-port rule (M §3);
  - coin tile Z2. I checked the COIN map at L_gen.py:541-550: T's only free 8-neighbour is E, and A's and B's are
    X_A and X_B.
- **Not fine:** the crossings inside G′ (F1, F2).
- Lanes cross only plain corridors (asserted at `_block_template`), so they are fine.

## 5. Size and time (d), instance language (e), labels (f)

- Size O(N⁴): accepted.
- Time: F4.
- Instance language: F5. Nothing the reduction uses is forbidden by Rev. 4; the boulder BUC mismatch is cosmetic.
- Labels: F6.

## 6. Required repairs (priority order)

1. **F1 + F2:**
   - router rule: no GX before the component's G′ is finished;
   - hooks cross only the chain (SX), own middles, or finished legs;
   - Ani placement of SO_i and SD_i, with a guard lemma for crossings on chain-only edges;
   - re-route all templates;
   - abstract end-to-end test with the crossings inside G′ (positive and negative control).
2. F4: write the constructive layout argument in B §6.
3. F3, F5: Z1 on redrawn boards; emit and lint one instance script.
4. F6-F10: label and text fixes; SC79 citation.

After 1-2, I would accept EXPTIME-hardness as **STRONG**, with the remaining drawing steps (box redraw, hook drawing)
labelled STRONG.

## 7. Reproduce

- `python tools/exptime/review6_weak.py` (~5 s): clean sets under endpoint substitution, protodiode detail, and the
  precursor with the generated crossings.
- `python tools/exptime/review6_hooks.py` (~2 min): crossing kinds on hook paths for the scdc and dio tile templates,
  both parities.
- `python tools/exptime/review6_hooks2.py dio scdc` (~1 min): which leg each hook crosses, per location.

## 8. Review-6 repairs (2026-10-31)

| Finding | Repair | Evidence | Status |
|---|---|---|---|
| F1 GX on own legs during own checks | `Router`: GX only on legs of G′s finished earlier in time (`LGEN_GX_RULE=own` = old rule, control); own middles only after both passes; never the own SCD interior at level 1. `validate_rules` replays it by time order | tile templates dio/scdc (both parities) and crossover 011: `validate_rules` clean, every GX on a finished leg; `review6_hooks.py` / `review6_hooks2.py`: no own or pending GX; `review6_weak.py --generated`: every clean set = the true one | REPAIRED (router); VERIFIED on the tile templates and 1 of 8 crossover templates |
| F2 guard argument needs a placement rule | Ani placement drawn on the chain (`Router._checks`: Out_{i−1} → Op_i next to the SO_i box at b_i → SD_i box at a_i; wires from boxes to the locations' wire-tree roots, reserved, crossing no floor; wire × chain only as SX with the wire the later line: WSX / XW). Placement rule P1-P4, Lemma G (guard, incl. wire SX) and Lemma C (check walk): B2-checkpath.md §3.7 | `validate_rules` P2 contact geometry on the same templates; L_e2e (next row) | STRONG (argument); drawn placement VERIFIED on the same templates |
| (routing room, found while repairing F1/F2) | The r5 SCD tile cannot be routed under F1/F2 in either parity; SCD tile scaled (g-side stubs SCD_SV = 3, spread legs SCD_SP = 6; windows unchanged), stub cells role GXR; crossover rebuilt (569 × 550); macro pitch P = 469 → 597. Router search: greedy-then-DFS over level-2 variants, lane lookahead, far rewind, leg-body penalty, XW, level-1 keep-out (L-generator.md §9) | X_verify --moves 100000 ALL AS EXPECTED on the new map; review5_abc / review5_cd pass; tile templates dio/scdc both parities validate + validate_rules clean | VERIFIED (tiles); FAILED for 7 of 8 crossover flips (only xtemplate_r6_011 routes; level 1 cannot finish one SCD per flip after level 2 is drawn; needed geometry in L-generator.md §9) |
| Abstract e2e with the crossings inside G′ | `L_e2e.py` (repaired / no-delimiter control / old GX rule / review-6 HK placement / two-player diode game) | tiles: repaired 12/12 G′ exact, no-delimiter control 12/12 not exact, old GX rule + Ani placement 4 not exact (protodiode 2 → 3), review-6 HK + old rule 11 not exact, diode game repaired LOSE/WIN vs review-6 WIN/WIN; crossover 011: 146/146 exact | VERIFIED on the tiles and crossover 011; the other 7 crossover flips untested (not routed) |
| F3 Z1 near the coin only for the main layer | not repaired (needs the box redraw) | — | OPEN |
| F4 polynomial time rests on a heuristic search | not repaired; the repaired router leans even more on search (deadlines, DFS, l2first). A constructive layout argument (Ani Thm 5.3 / Lemma 5.6 drawing + constant-size boards + orthogonal box drawing) is still to be written in B §6; L_gen is evidence only | — | OPEN |
| F5 no Lua instance emitted | not repaired | — | OPEN |
| F6 "VERIFIED" for finite tests | not relabelled in the other docs; new labels in B2 §3.7 / L-generator §9 say "on the generated templates" | — | OPEN (text) |
| F7 prayer row omits divine minions | not edited (C-audit J1 line still to add) | — | OPEN (note) |
| F8 `hunger=false` blocks only `gethungry` | not edited (J13 should cite eat.c:3167) | — | OPEN (note) |
| F9 wrap width depends on the data model | not edited | — | OPEN (note) |
| F10 SC79 citation | unchanged | — | OPEN (note) |

**Where hardness stands after these repairs: CONJECTURE (unchanged).** F1/F2 are repaired in the argument (B2 §3.7)
and in the router, and the repaired drawing passes every check on the tile templates and one crossover flip. But
(i) 7 of the 8 crossover templates cannot be routed under the repaired rules yet, so no full generated instance
exists under them (`--run` blocked), and (ii) F4 (a constructive polynomial layout argument in place of the
heuristic router) is still open; review 6 asked for F1-F2 **and** F4 before STRONG.

