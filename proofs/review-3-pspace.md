# Review 3 (adversarial): PSPACE side — Lean bridge, Push-1F enclosure, variants (b)/(c), projection

Reviewer sub-agent, 2026-10-29. Source NetHack 5.0.0 @ 16ff591 read-only (`src/src/<f>:line`); game not run; nothing
committed. Paper: arXiv 2412.20079v1 PDF, text extracted and read (§1, §2, §5 defs, §7, §9).

## Verdicts

| # | Target | Verdict |
|---|---|---|
| 1 | `nhMove` (NetHackPush.lean) vs. hack.c | **HOLDS** for its stated fragment; omissions listed in 1.2, none adds a move |
| 2 | Push-1F hardness for the enclosed board | **REPAIRABLE**: paper is silent; one-directional lemma below + one figure check + a 1-cell margin in f |
| 3 | variants.md (b) PSPACE-complete, (c) NP-hard and ∈ PSPACE | **HOLDS** (same status as hu-off; mechanics re-read) — but inherits the NEW issue 4.1 |
| 4 | Full state → projection π | **REPAIRABLE, one real hole (4.1, setup RNG + branch stairs)**; everything else HOLDS |

## 1. Lean bridge

1.1 Branch-by-branch check (all match):
- destination `!isok || IS_OBSTRUCTED || IRONBARS` → FALSE [hack.c:1003-1073] = `x ∉ B.free`.
- corner rule `dx&&dy && bad_rock(ux,y) && bad_rock(x,uy)` [hack.c:1153-1154]; `bad_rock` = Sokoban∧boulder ∨
  obstructed [hack.c:939-946]; `cant_squeeze_thru` returns 2 (weight > 600) or 3 (Sokoban) for the hero, never 0
  without Passes_walls [hack.c:953-979]. Lean's corners `robot+(0,dy)`, `robot+(dx,0)` = `(ux,y)`, `(x,uy)`. ✓
  Order (corner before boulder) matches [hack.c:1153 vs 1216]. ✓
- boulder at x: `moverock` [hack.c:1216-1230]; `rx = ux+2dx` [hack.c:376]; destination test [hack.c:432-435];
  Sokoban diagonal → `cannot_push` [hack.c:441-448]; blocked → `cannot_push_msg; cannot_push` [hack.c:632-635];
  `cannot_push` = −1 because not giant and `could_move_onto_boulder` false: `inv_weight() ≤ −850` impossible with
  the 500-wt stone since `weight_cap ≤ 1000` [hack.c:138-163, 4295-4365; weight.h:24-25]. Diagonal into a boulder
  with blocked r goes to the `else` branch, also −1: Lean returns `c` either way. ✓
- `while (sobj_at(BOULDER,sx,sy))` runs once: one boulder per cell initially and pushes require `!sobj_at(rx,ry)`. ✓

1.2 Real-code behaviour omitted by `nhMove` (fragment constants) and why it does not matter:
| Omitted | Where | Matters? |
|---|---|---|
| `carrying_too_much` before the move | hack.c:2615-2636, 2733 | only refuses moves (Lemma C: never triggers) |
| impaired_movement / ice / turbulence / u.utrap / ustuck / steed / rooted | hack.c:2735-2790, 2828-2840 | unreachable sources (I8); refusals only |
| monster at x, pet swap, `F` prefix | hack.c:2795-2820 | no monsters (pettype:none + mongen) |
| `m` prefix (nopick) | hack.c:380-410 | "boulder in your way" = no-op; walk otherwise = same as Lean |
| run ≥ 2 / travel refuse boulder squares | hack.c:1216-1222, 1232-1235 | refusals only; each executed step is a `domove` = nhMove |
| Punished: `drag_ball` after the push | hack.c:2846-2849 | can refuse the hero step AFTER the push: result = push + walk back (Push-1F-legal, a is empty). Outside the Lean fragment; hu-off M6 paper proof is correct |
| `spoteffects`/autopickup | hack.c:2950 | only ball/chain can be picked up |
| traps/pools/doors/bars in moverock | hack.c:450-631 | absent in f (sentinel pit unreachable) |
| branch STAIRS on a board cell (review-2 N2) | mklev.c:1731-1738 | not obstructed, no moverock test: Lean treats it as free. ✓ (but see 4.1) |
Conclusion: the transcription is faithful for the L_OFF^W fragment. Two non-movement routes that move the hero —
iron-ball throw (`drop_ball`, ball.c:931-941, with per-square `test_move(TEST_MOVE)` + boulder stop, zap.c:4096-4117)
and Punished drag — are outside Lean and stay paper-proved; both re-checked: they compose legal steps only.
Suggested (optional) Lean addition: a `throwBall` relation proven ⊆ NHStep* so the README's trust list shrinks.

## 2. Push-1F on an enclosed board

2.1 What the paper says (read in the PDF): grid "unit-square" (finite/infinite not stated); §2 hallways are abstract
("an agent can traverse freely between a and b (outside the gadgets)"); §7 only gives gadget figures and ends
"planar reachability through systems of self-closing doors is PSPACE-complete … so is Push-1F". No board boundary,
no wall frame, no statement on embedding the hallways. So enclosure must be argued, not cited.

2.2 Lemma E (self-contained, one direction is free). Let P be a Push-1F instance with finitely many blocks, start s,
goal g; let R be the bounding box of the paper's drawing (all specified cells incl. empty gadget/hallway cells, s, g);
B = R grown by ONE empty layer; P_B = P restricted to B with every cell outside B fixed.
(a) P_B solvable ⇒ P solvable: a legal P_B move needs the target (and push-beyond) cell in B and empty, which is the
same in P. So P_B's moves ⊆ P's moves. **The NO direction of hardness transfers unconditionally.**
(b) P solvable by a solution σ in which no block ever leaves R ⇒ P_B solvable: the margin layer of B is always empty
and is a 4-connected cycle around R; every excursion of the agent outside B leaves and re-enters through that layer,
so replace it by a walk along the cycle. Pushes happen at blocks in R from a cell in B. ∎
(c) For the paper's reduction, (b)'s hypothesis is "in the intended YES traversal every block stays inside its
gadget's drawn footprint". This holds by design (gadget state = block position on its track, Figs 32, 35-37;
postselected solutions only perform legal gadget traversals), but **must be confirmed once against Figs 32-37**
(the block-carry figures in Push-k §8 are not used). If a figure lets a block exit its gadget, use margin
k+2 (k = #blocks) and redo (b) — not attempted.

2.3 Required repairs: (i) hu-off B.1/B.2: define the board as R + one empty margin layer before adding the wall ring
(currently the ring is directly on the a×b board, which under the infinite-grid reading deletes outside detours);
(ii) state Lemma E in hu-off B.1 and in the Lean README (replace "padding changes nothing" with Lemma E (a)+(b));
(iii) claims.md F15/ext: "PSPACE-hard for enclosed boards via Lemma E + figure check".

## 3. variants.md (b) and (c)

3.1 Mechanics re-read: `gethungry` [eat.c:3163-3196], `newuhs` FAINTING branch [eat.c:3410-3446], `unfaint`
[eat.c:3335-3343], `ublesscnt--` each tick [allmain.c:275-276], `can_pray` [pray.c:2124-2175], `pleased` action rule
[pray.c:1118-1150], TROUBLE_STARVING → `init_uhunger` [pray.c:404-411], timeout `rnz(350)` + capped incr
[pray.c:1356-1377]. All as variants.md §1 states, including the F12 correction (starvation roll also while fainted).
- (b) B.1: faint branch exists for every h ≤ 0 (`rn2(20−hd) ≥ 19` possible), duration 10 − hd; with record < STRIDENT
  forever (no alignment sources; `adjalign(1)` only when trouble ≤ 0) action ∈ {0,1}, R2 picks 1 → h := 900; the
  cursed loadstone is only a minor trouble (`worst_cursed_item` loadstone path, pray.c:291-345) so never uncursed.
  Arithmetic (k ≈ 714 cycles, h ≥ −720, d ≤ 82) re-derived. Extra point checked: if multi < 0 for another reason
  (prayer: `uinvulnerable` → gethungry returns; ball-drag delay: neither faint nor starve branch) nothing new happens.
- (b) B2 (∈ PSPACE): fine; reachability needs no horizon.
- (c) C2: Lemma K is the standard fact that a universal node with a losing successor is losing in a reachability game;
  the horizon bound then only needs Lemma H on non-kill plays. Sound modulo Lemma N (free actions) [conj] as stated.
- (c) C1: YES play RNG-free (aware decrement each tick, no accessorytime cost unencumbered, no abuse source);
  hu-on-lower §5.2 NO argument is structural (checked: rule S is used only in §6 "fainting" remark, not in §5.2).
Verdict HOLDS. Caveat: f_ON and hu-on-lower's g(φ) inherit issue 4.1 below (same harness).

## 4. Full state → projection

4.1 **NEW HOLE (setup RNG + branch stairs).** In `finalize_level`, `fixup_special` runs BEFORE hero placement
[sp_lev.c:6046-6061]. DL1 is a branch level (review-2 N2), `made_branch` is reset by `clear_level_structures`
[mklev.c:919], so `place_lregion(0,…,LR_BRANCH)` puts STAIRS on a random ROOM cell that `bad_location` accepts —
**including s** [mkmaze.c:366-410, 341-351]. Then `u_on_rndspot` tries the one-cell teleport region: STAIRS is
furniture → `occupied` → `bad_location` [mklev.c:1806-1811]; oneshot cannot fix it, 200 tries + the deterministic
scan fail, `impossible("Couldn't place lregion")` [mkmaze.c:393-410, 418-433] — not fatal in a normal build — and
the hero keeps the **stale** `u.ux,u.uy` from newgame's random DL1 (nothing in `makemap_prepost(TRUE)` resets it).
That cell is RNG-chosen and typically wall/stone in f(I). Then `stuck_in_wall()` holds [pray.c:160-181]; after
≤ 100 turns ublesscnt ≤ 200, a p_type-3 prayer with action 1 (R2: `rnl(2)=0`) fixes TROUBLE_STUCK_IN_WALL via
`safe_teleds` [pray.c:461-465], which works on noteleport levels and can land on g. So under R2 every f(I) whose g
starts empty becomes YES (and hero starts elsewhere even when the stale cell is floor); Thm B (⇐), Thm C (DET), f_ON (b), g(φ) (hu-on-lower, (c)) all break.
Probability per seed ≈ 1/#ROOM, which is why 3/3 witness runs passed; the testmove.lua stairway deletion runs too late.
**Repair:** add a second sealed pocket (a '.' cell with 8 wall neighbours, Chebyshev distance ≥ 2 from the board,
like the sentinel) and `des.levregion({ region={px,py,px,py}, type="branch" })` (supported: sp_lev.c:5475-5479,
used by dat/Arc-strt.lua:58); `fixup_special` then places the branch only there (added_branch, mkmaze.c:586-608,
641). Add to the whitelist; harness asserts hero on s and stairs on the pocket after finalize. Alternative: declare
"impossible() during setup = instance invalid", but the pocket is cleaner.

4.2 Checked and closed (no move outside π):
- **#force**: needs a box [lock.c doforce]; none. **Kick**: boulder/ball/chain never move [dokick.c:517-519]; every
  `hurtle` needs Levitation or air level [dokick.c:876-877, 904-905, 1428-1439, 1457-1458]; wounded legs only lower
  `weight_cap` by 100/side [hack.c:4330-4335; weight.h:16] → only restricts.
- **Throw loadstone**: `canletgo` refuses (I2). **Iron ball**: as 1.2.
- **#pray**: majors fixable at Luck 0 = HIT, COLLAPSING, STUCK (I7 holds: left cell always empty; `blocked_boulder`
  is false for an empty cell [pray.c:2677-2719]) — except via 4.1. Minor (loadstone) never: action ≤ 2 off-altar, or
  ∈ {0,1} with record < STRIDENT [pray.c:1125-1130]; pat_on_head needs `!trouble` [pray.c:1105].
- **Encumbrance/attributes/Luck/timers/hunger(off)/RNG**: only change refusals (`carrying_too_much`) or messages;
  squeeze needs inv_weight ≤ −850, impossible.
- **Digging, levitation, polymorph, teleport, Elbereth**: no source / no monsters. **Holes**: none in f; in W_ON
  falling = leaving level = loss. **Up stairs**: `<` on DL1 ends the game = loss.

## 5. Required edits (summary)
1. Spec/f/g/f_ON: branch pocket + `des.levregion type="branch"` (4.1); add to whitelist; harness assertion. Update
   claims.md (Thm B, C, (b), (c), L_ON* rows stay STRONG only after this repair).
2. hu-off B.1/B.2: one-cell empty margin before the wall ring; state Lemma E; confirm Figs 32-37 (2.3).
3. Lean README: "trusted" item 3 → "Push-1F hard on enclosed boards (Lemma E, figure check pending)".
