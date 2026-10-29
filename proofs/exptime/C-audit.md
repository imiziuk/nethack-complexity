# C: adversary-power audit of L_OFF^{W+C} under R3

Workstream C, 2026-10-29. Source NetHack 5.0.0 @ 16ff591, read-only (`src/<f>` = `src/src/<f>`, `include/` =
`src/include/`). Game not run, nothing committed. Inputs: exptime-model.md (R3, Thm M, C1-C6, H1-H8, §3), exptime-
feasibility.md (§3 coin, §9 witnesses), exptime-mech-monsters-traps.md, exptime-mech-doors.md, hu-off.md (I1-I9,
Lemma S/C), phase2-spec.md (Rev. 1-3), exptime/B-reduction.md §5.3 and INTERFACE.md ("B → C" items C-1..C-4).
Labels: **VERIFIED** = lines read this session, direct reading · **STRONG** = complete argument, not reviewed ·
**CONJECTURE**. Nature = R3 adversary choosing every RNG value (incl. setup: model §1.1).

## 0. Results

| # | Claim | Status |
|---|---|---|
| R4 | Revision-4 spec text for L_OFF^{W+C} (§1) | proposal |
| N1 | **New hazard: the coin is wrap-sensitive.** `noteleport_level` is TRUE whenever `stasis_until (=0) >= moves`, i.e. for every `moves ≤ 0` after the W_C wrap; then T says "wrenching sensation" and the hero stays on T. Repair: tile isolation rule (T's only floor 8-neighbour is E) + the hero never enters T while `moves ≤ 0` (he waits) | VERIFIED (teleport.c:43, mklev.c:904, teleport.c:1503-1506); repair STRONG |
| N2 | **hu-off error:** Str+Con ≥ 20 is false under R3 setup: `vary_init_attr` can lower each by 2 → min Str = Con = 8, wc = 450 < 520 ⇒ hero may start **Burdened** (also with the loadstone alone, 500). Burdened is time-only; Stressed needs Str+Con ≤ 11, unreachable without hero self-abuse | VERIFIED (attrib.c:723-776, u_init.c:1390-1391, role.c:519-520, hack.c:4311-4388); harmlessness STRONG |
| J | Invariants J1-J13 for every reachable state of every instance (§2.1) | STRONG |
| S^C | Lemma S redone: every command changes π by Push-1F moves outside Z, coin moves E→T→{A,B} (nature), or a bounce at T (§2.3) | STRONG |
| C^C | Intended play (wear boots, then direction keys / waits) realizes every abstract move against every outcome; HP constant; ≥ 1 hero action per 3 turns | STRONG |
| D | No damage source on any intended play ⇒ nature can never kill the hero; all damage sources are hero-chosen (§3) | STRONG (each source VERIFIED) |
| M | C1-C6 hold for L_OFF^{W+C} ⇒ ∈ EXPTIME under R3 (Thm M) | STRONG |
| B | Answers to B's C-1..C-4 (§5): C-1 yes, C-2 yes (with N2 correction), C-3 yes under rule Z2, **C-4 no as stated → N1 repair** | STRONG |

## 1. Revision 4 candidate (spec text)

10. **L_OFF^{W+C} (R3 only).** Common part + L_OFF + Rev. 1-3, with these changes:
   a. Level flags: `noteleport` is **dropped** (forbidden); keep `noflip`, `sokoban`, `hardfloor`, `solidify`
      (`premapped`, `nomongen`, ... as in hu-off A.0 are allowed but unused).
   b. Traps: TELEP_TRAP only in the form `des.trap({ type = "teleport", coord = {x, y}, seen = true })` (or the
      positional `des.trap("teleport", x, y)` with an added rule that every T starts seen; the key `seen` defaults to
      FALSE, sp_lev.c:4406, 4432). Keys `teledest` and `launchfrom` are **forbidden** (they set a fixed destination,
      trap.c:566-574, which forces the trap, trap.c:3009-3012). `victim` is irrelevant (TELEP_TRAP ≥ HOLE is excluded
      from trap victims, mklev.c:2134-2141). PIT, HOLE, TRAPDOOR stay as in Rev. 1.
   c. Exactly **one** `des.teleport_region` call, this exact form (the Rev. 3 start call extended):
      `des.teleport_region({ region = {sx,sy,sx,sy}, region_islev = true, exclude = {zx1,zy1,zx2,zy2},
      exclude_islev = true, dir = "both" })` with zx1 ≥ 1 (`nlx > 0` is the "zone present" test, teleport.c:391),
      s ∉ Z, the branch pocket P ∉ Z. One call with `dir="both"` writes the same rectangle into `dndest` and
      `updest` (mkmaze.c:611-632); a second call would overwrite it, so it is forbidden. Every TELEP_TRAP lies in Z.
   d. Objects: add exactly one `u.giveobj(obj.new("cursed +0 fumble boots"))` (weight 20, delay 2,
      objects.h:722-724; "+0" fixes spe, which mksobj otherwise randomizes, mkobj.c:1087-1090; spe/erosion matter
      for AC only). Inventory = {cursed loadstone, cursed fumble boots}; the loadstone stays (it is what makes the
      hero unsqueezable before the boots are worn and after any drop of the boots).
   e. Mandatory prefix unchanged: `nh.debug_flags{mongen=false, hunger=false}`, `u.clear_inventory()`, `pettype:none`,
      Rev. 3 pocket; harness asserts: hero on s, stair in P, no monsters, every T `tseen`, boots cursed.
   f. Semantics R3; counters wrap (SC3) — the coin is then dead whenever `moves ≤ 0` (N1); gadget designs must obey
      Z1-Z4 below, which are **design rules for instances produced by the reduction**, not language restrictions
      (membership holds for every instance of the language, §4).
   g. Explicitly unchanged: no other teleport source exists (§2.2 J9).
   **Design rules (for A/B):** Let R_B be the least set ⊇ initial boulder cells closed under "c ∈ R_B, c−d and c+d
   both non-obstructed (orthogonal d) ⇒ c+d ∈ R_B" (an over-approximation of every cell a boulder can ever occupy:
   a push needs the hero on c−d and a non-obstructed target; walls never change, hu-off I6).
   - **Z1 (boulders)** (Z ∪ N8(Z) ∪ {E} ∪ N8(E)) ∩ R_B = ∅. In particular E ∉ R_B ⇒ T ∉ R_B (a boulder enters T
     only by a push from an orthogonal floor neighbour of T, and E is the only one).
   - **Z2 (isolation)** Z's only goodpos non-trap cells are A, B; T's only non-obstructed 8-neighbour is E (outside
     Z); A's (B's) only non-obstructed 8-neighbour is its exit cell X_A (X_B), outside Z; T, A, B pairwise
     non-adjacent (B's tile [A wall T wall B] meets this). X_A, X_B ∉ R_B (from Z1).
   - **Z3 (pits)** No intended play steps on an unfilled pit (pit damage rnd(6) is permanent, §3).
   - **Z4 (time)** The hero's intended strategy never steps onto T while `moves ≤ 0` (dead phase); it waits instead.

## 2. Invariants, coin RNG audit, Lemma S under R3

### 2.1 Invariants J1-J13 (every reachable state of every instance obeying Z1-Z2; any commands, any outcomes)
- **J1 = I1 no monsters** (unchanged; teleport/boots create none).
- **J2 = I2 loadstone in inventory** (unchanged).
- **J3 boots**: once worn they stay worn: Take-off/`A` refused by `cursed()` "You can't. They are cursed." (do_wear.c:
  1893-1915); uncursing needs TROUBLE_FUMBLING (minor, pray.c:249-252, fixed at pray.c:526-531) ⇒ prayer action ≥ 3
  ⇒ Luck ≥ 1, impossible by J6; `pat_on_head` needs trouble = 0, impossible (loadstone + boots are troubles). Before
  wearing they are an ordinary object (may be dropped/thrown/kicked: §2.3 row I2). [VERIFIED lines; STRONG]
- **J4 = I3 unsqueezable**: inventory weight ≥ 500 ⇒ inv_weight ≥ 500 − 1000 > −850 (hack.c:136-163, 4351-4366,
  MAX_CARR_CAP weight.h:25); diagonal squeeze `cant_squeeze_thru` returns 3 under Sokoban for every weight
  (hack.c:953-978). Independent of attributes. [VERIFIED]
- **J5 = I4 Sokoban stays on**: as hu-off, plus: no boulder ever reaches T (Z1), so `rloco` (hack.c:578-590 →
  teleport.c:2102-2145, global, ignores reachability) can never drop a boulder into the sentinel pit; teleport traps
  are never deleted (only `once` traps or digging delete them; `#untrap` refuses: "You cannot disable this trap",
  trap.c:5987-5990). [STRONG]
- **J6 = I5 Luck ≤ 0**: no Luck writer in teleport.c / trap.c tele path / timeout.c fumbling; do_wear.c Luck writers
  are the fedora (do_wear.c:437-439, 525). [VERIFIED by grep]
- **J7 terrain fixed; trap set fixed; every T stays `tseen`**: tseen is only cleared by digging (dig.c:695,
  unreachable); `seetrap` on every trigger (trap.c:2076). [VERIFIED by grep of `tseen =`]
- **J8 = I7' never stuck** at a P-node: after a step/push the left square is free (hu-off I7); after a coin landing at
  L ∈ {A,B} the cell X_L is floor and ∉ R_B (Z1, Z2), so `stuck_in_wall` (pray.c:161-181: needs all 8 neighbours
  obstructed or boulder-blocked; trap cells count as free) is false; after a dead-phase bounce the hero is on T with
  E free (Z1). Nothing moves a boulder while the hero stands still. Hence TROUBLE_STUCK_IN_WALL (pray.c:461-477, a
  `safe_teleds` = global relocation within the hero's zone class) is never fixed by prayer. [STRONG]
- **J9 only teleport = the coin**. Every hero-teleport entry point (grep of `tele()`, `safe_teleds(`, `level_tele(`,
  `scrolltele(`, `dotele(`): `^T` off a trap needs Teleportation or the spell, else "You don't know that spell", no time
  (teleport.c:1072-1085); `^T` on a **seen** TELEP_TRAP = the coin, no hunger cost (teleport.c:1041-1067, 1145-1160);
  Teleportitis per turn needs `Teleportation` (allmain.c:310; sources eat.c:1058 corpses, rings, polymorph: none);
  Teleport_control absent ⇒ no destination prompt (scrolltele teleport.c:874-905; **only `wizard` prompts**, the
  witness caveat); level teleport: scroll/artifact/LEVEL_TELEP/wizard only (read.c:2022, artifact.c:2160,
  teleport.c:1559, wizcmds.c:402); prayer: STUCK (J8), LAVA (pray.c:397-399, no lava), region (region.c:1387, no
  regions); throne/fountain/magic trap/wands/monsters: absent. [VERIFIED entry points; STRONG coverage]
- **J10 attributes**: Str, Con never decrease on any play without hero self-abuse (§2.4); start Str, Con ≥ 8.
- **J11 encumbrance**: on every play without self-abuse, wc ∈ [450, 1000] ⇒ encumbrance ∈ {Unencumbered, Burdened}
  (§2.4).
- **J12 = I8** XL1 human, not polymorphed/levitating/flying/blind-by-source/stunned/confused (teleport cures nothing
  relevant: `make_blinded(0L)` only when not already blinded, teleport.c:860-861).
- **J13 = I9 hunger inert**: `morehungry` in teleport.c only on `^T` without a trap (teleport.c:1159-1160): unreachable.

### 2.2 The coin path: every RNG call (VERIFIED, read in order)
Step onto T (hero Fumbling, T seen, not levitating): `domove` → `dotrap`: `nomul(0)`; not fixed-dest (no teledest);
not Sokoban pit/hole; escape test `already_seen && !Fumbling && ... && !rn2(5)` short-circuits **before** `rn2(5)`
(trap.c:3035-3038): **no RNG**. → `trapeffect_telep_trap`: `seetrap`, `tele_trap` (trap.c:2070-2085) → recursion guard
(teleport.c:1497-1500); not endgame, no Antimagic (Valkyrie has no MR), `noteleport_level` false **iff moves ≥ 1**
(N1); `next_to_u` true (no leashed pets, no steed: apply.c:919-928); `once` = 0 (maketrap trap.c:499); no teledest
(launchplace reset sp_lev.c:4467) → `tele()` → `scrolltele(NULL)` (teleport.c:849-915): no amulet / not W tower ⇒ the
`rn2(3)` "disoriented" test is not reached (short-circuit, teleport.c:863); no control, not wizard → `safe_teleds`
(teleport.c:717-770): ≤ 40 × {`rnd(COLNO−1)`, `rn2(ROWNO)`} accepted only if `teleok(..,FALSE)` (no trap, goodpos incl.
no boulder teleport.c:177-178, `tele_jump_ok` teleport.c:386-418 inside Z ⇒ target inside Z); then `collect_coords`
(one `rn2` per shuffled candidate, teleport.c:690-708) and an exhaustive scan with the same test; trap backup spot only
if no non-trap teleok cell exists (never: A, B qualify by Z1/Z2). `teleds` (teleport.c:448-575): no RNG; `fill_pit` of
the old square (no pit), vision, `spoteffects` at the landing (no trap, no object, no pool). Then the per-turn block.
**Outcome set = {A, B}, nature's choice; no other branch.** Dead phase (moves ≤ 0): "You feel a wrenching sensation",
no RNG, hero on T. Witnesses W9/W10/W11b/W11c (feasibility §9) agree in the live phase. Wizard-mode prompt: the
witness path differs (`getpos` then "Sorry..." then `safe_teleds`) but reaches the same `safe_teleds` call.

### 2.3 Lemma S^C (soundness, all outcomes) — redo of hu-off §B.4 for W+C
π = (hero cell, boulder set, alive). Abstract moves: (P) a Push-1F step/push on the floor graph, never touching Z
(Z1); (K) from E a step onto T then landing at A or B (nature), live phase; (N) dead phase: step onto T, stay; (R)
plain steps T→E, A↔X_A, B↔X_B. **Lemma S^C:** for every reachable X, command c and outcome vector, π(X') arises from
π(X) by a finite sequence of P/K/N/R moves, or the hero is dead or off-level (losses). [STRONG; rows below]

| Group | Commands | Effect on π (any outcome) | Evidence |
|---|---|---|---|
| M1-M4 | steps, F, m-prefix, diagonal tests | as hu-off; a step whose target is T is K (live) or N (dead); T, A, B reachable on foot only via E, X_A, X_B (Z2); diagonal entry into T/A/B impossible (all other 8-neighbours obstructed) | hu-off table; Z2 |
| M5 | run/rush/travel | sequences of single `domove` steps; each is M1/M2 or K/N; Fumbling's `nomul(-2)` only interrupts | hack.c:1216-1235 (hu-off) |
| M6 | Punished movement | as hu-off; ball/chain follow a teleport (`unplacebc`/`placebc`, teleport.c:459-505, 540-545), objects only | VERIFIED teleds |
| T1 | throw | loadstone refused (I2); boots (unworn) / ball: object flights; ball-pull lands the hero on the square before the ball after legal steps (hu-off T1); with Z2 any straight flight entering T, A or B ends there (walls behind), so the hero is pulled at most to E / X_A / X_B: no crossing of Z without K. Objects never trigger a teleport trap (grep: the only object TELEP_TRAP case is the boulder in `moverock`, hack.c:578) | STRONG |
| I1 | `W` boots | `Boots_on`: HFumbling timeout `rnd(20)` (do_wear.c:231-233), 2-turn delay: no π change | VERIFIED |
| I2 | `T`/`A`/`R` boots; d/D/t/kick unworn boots | worn: refused (J3); unworn: boots become a floor object (inert: objects block neither hero, boulders, nor teleport landing — `goodpos` tests boulders only, teleport.c:177-178) | VERIFIED/STRONG |
| I | other inventory, meta | as hu-off | — |
| U1 | `^T` | off-trap: refused, no time (J9); on a seen T (only in a dead-phase bounce, or without boots): "jump onto the teleportation trap" → `tele()` = K (live) / "mysterious force" (dead) | teleport.c:1041-1067, 849-856 |
| U2 | `#sit` on T | `dotrap(VIASITTING)` = same path as a step (escape test skipped under Fumbling) = K/N | trap.c:3035; sit.c:503 (monsters-traps §1.4) |
| U3 | `#untrap` T | "cannot disable", no RNG, no time | trap.c:5987-5990 |
| U4 | `s` search | T already seen (J7): no trap to find; no SDOOR/SCORR | detect.c (hu-off) |
| K | kick | as hu-off: no π change; self-damage, Str/Dex abuse, wounded legs (−100 wc per side, hack.c:4331-4336) | dokick.c:864-905 |
| P | pray | §2.5: never moves the hero (STUCK unreachable, J8) | pray.c |
| W | wait, per-turn block | + Fumbling expiry (§2.4); + nothing else new | timeout.c:902-924 |

Hero gains impossible: every displacement not in P/R is K or N, and in K the landing is nature's. Not wearing the
boots only adds nature's escape outcome (hero stays on T = an N-like bounce): the hero's winning region cannot grow.
Dropping the boots before wearing is likewise only a loss of the hero's own option. [STRONG]

**Lemma C^C (completeness).** Intended play: `W` boots at turn 1, then direction keys and waits, never kicking, praying,
throwing, entering an unfilled pit (Z3) or T in the dead phase (Z4). For every outcome vector each key realizes exactly
the intended abstract move (K's landing is nature's), HP stays 16/16 (§3), encumbrance ≤ Burdened (J11), and the hero
gets ≥ 1 action every 3 turns: after a fumble `nomul(-2)` the next two expiries see `u.umoved = 0` (helpless) and do
not slip (timeout.c:905), so nature cannot freeze him. Burdened only changes speed 12 → 9 (allmain.c:139-141). [STRONG]

### 2.4 Fumbling, attributes, encumbrance under R3
**Fumbling (VERIFIED, timeout.c:902-924, 1225-1330).** On each expiry of the HFumbling timeout: if the hero moved this
turn, `slip_or_trip()` then `nomul(-2)`, "make a lot of noise" + `wake_nearby` (no monsters); re-arm `rnd(20)` while
Fumbling (boots worn ⇒ forever; nature picks 1..20). `slip_or_trip`: object under the hero ⇒ "You trip over X" (only
the iron ball or dropped boots can be there; a cockatrice corpse is the only harmful case: absent); ice branch needs
`HFumbling & FROMOUTSIDE`, set only on ice (hack.c:2395-2415; no ice in W) — the only `hurtle`; else `rn2(4)` message.
**No `losehp`, no drop, no `exercise` in this code.** Other Fumbling reads: doors (hack.c:1098, 1114; none), untrap
×2 (trap.c:5320), kicks `clumsy` (dokick.c:250, 537), apply/dig/throw multishot/steed/zap boomerang (no such items),
`hold_another_object` drops gifts (invent.c:1245; no gifts), dbridge/mthrowu/music (absent), stairs (do.c:1780;
leaving = loss). Exercise: `Fumbling` abuses **Dex** every 5 turns (attrib.c:581): Dex may drift to 3; Dex enters
nothing on intended plays (no doors, kicks, throws, ice). Fumbling never reads Str/Con.

**Attributes (VERIFIED).** Start: Valkyrie base Str 10, Con 10 (role.c:519); `init_attr(75)` only adds (attrib.c:723-
737; nature can put all 27 points into Int/Wis/Dex/Cha, capacity 44); then `vary_init_attr` (u_init.c:1391;
attrib.c:764-776): per attribute with `!rn2(20)` an `adjattrib` by `rn2(7)−2 ∈ [−2, 4]`. So nature can start the
hero at Str = Con = 8 (human minimum 3, role.c:597). Change in play: only `exerchk` (attrib.c:598-672) via AEXE, or
direct `adjattrib`/`losestr`. AEXE(i) grows only through `exercise(i, TRUE)` by `rn2(19) > ACURR(i)` ∈ {0,1} and
falls only through `exercise(i, FALSE)` (attrib.c:489-519); decay `(|ax|/2)·sgn` keeps the sign; a decrease needs
AEXE < 0. Grep of every `exercise(A_STR|A_CON, FALSE)`, `adjattrib(A_STR|A_CON, −)`, `losestr`, `poisoned` (36 sites)
— reachable in W+C only: kicks (dokick.c:873, 888, 937), Overtaxed `exerper` (attrib.c:548-552), "not enough stamina"
Stressed + HP < 10 (hack.c:2616-2631), pass-out from overexertion (hack.c:3036-3047), Punished ball on stairs
(ball.c:1010-1027, needs stairs: loss). All need the hero to kick or to be Stressed+ first; Stressed+ needs
wc ≤ 346 (below) or the iron ball carried (hero's choice after an angering prayer). Positive exercise: push
(hack.c:197), NOT_HUNGRY Con every 10 turns (attrib.c:528-532; hunger fixed at start). **So on every play without
self-abuse Str and Con are non-decreasing** (nature can only refuse increases). [STRONG]

**Encumbrance numbers (VERIFIED formulas hack.c:4311-4344, 4372-4388).** wc = 25·(ACURRSTR + Con) + 50, capped 1000,
−100 per wounded leg; W = 520 (500 + 20); wt = W − wc; level = 0 if wt ≤ 0 else min(5, ⌊2wt/wc⌋ + 1).
| Str+Con | wc | level |
|---|---|---|
| ≥ 19 | ≥ 525 | Unencumbered |
| 16-18 (R3 worst start: 16) | 450-500 | Burdened |
| 12-15 | 350-425 | Burdened |
| ≤ 11 | ≤ 325 | Stressed (≤ 8: Strained; 6 = racial min 3+3: wc 200, wt 320, ⌊640/200⌋+1 = 4 = **Overtaxed**) |
So the min-attribute worst case **would** break the margin (Overtaxed: `overexert_hp` every 10 moving turns,
allmain.c:297-301, Con abuse, "not enough stamina" below 10 HP), but it is unreachable without hero self-abuse
(J10). Decision: **margin survives; no fix needed**; keep the loadstone (dropping it would let the hero empty his
inventory before wearing the boots: `!invent` ⇒ squeezable onto boulders, hack.c:136-137). Burdened effects checked:
speed only; no exercise case for SLT_ENCUMBER (attrib.c:540-552); no `overexert` (needs > MOD_ENCUMBER,
allmain.c:297); `carrying_too_much` needs ≥ Stressed+low HP or Overloaded (hack.c:2620-2622); `teleds` drag rule
(teleport.c:462) only matters when Punished. hu-off's "wc ≥ 550, unencumbered" (Lemma C) must read "wc ≥ 450, at most
Burdened" — Lemma C is unaffected (OVERLOADED needs wc ≤ 166 there).

### 2.5 Prayer under R3 (unchanged except as noted; model §3.2 VERIFIED)
Troubles now: minor TROUBLE_FUMBLING (worn cursed boots) + TROUBLE_CURSED_ITEMS (loadstone): neither fixable (action ≤ 2
at Luck ≤ 0). Majors reachable only by hero choice: TROUBLE_HIT (after self-damage), TROUBLE_COLLAPSING (Overtaxed and
Str drained > 3, pray.c:224). STUCK never (J8). So prayer still never moves the hero or a boulder; it can heal
(record ≥ 1) or punish/kill (model §3.2). Teleport being allowed adds nothing: no prayer outcome calls `tele()`.

### 2.6 Wrap of `moves` (N1, answers B's C-4)
`noteleport_level` (teleport.c:30-46): `svl.level.flags.stasis_until >= svm.moves` ⇒ TRUE; `stasis_until` is set to 0
by level reset (mklev.c:904) and only raised by a wand of stasis (zap.c:2565-2566, absent). Under SC3 (two's
complement), after 2^63−1 turns (LP64; 2^31−1 under LLP64) `moves` runs through [LONG_MIN, 0]: the coin is **dead**
for 2^63+1 turns, then alive again. Dead coin: "wrenching sensation" (teleport.c:1503-1506), hero stays on T.
- With Z2 a dead coin is a **bounce** (T's only exit is E): a nature-favourable null visit (B's "null visit" class).
  Without Z2 (e.g. A T B adjacent, the W9 board) the hero would wait into the dead phase and then *walk* T→A or T→B:
  a hero choice ⇒ NO direction fails. Hence Z2 is mandatory, and the boots-free variant (escape = hero choice when
  A, B are adjacent to T) is ruled out by the same argument.
- YES direction: the intended strategy waits (free: hunger off, no monsters, HP unchanged) whenever it would enter T
  with `moves ≤ 0` (Z4). Nothing else in a gadget reads `moves` (model §2.6 table; boulder pushes, Sokoban, pits,
  Fumbling timers are relative; exercise tests just pause).
- Other wrap effects: `stasis` also blocks `u_teleport_mon`/magic whistle (no monsters/whistle). [VERIFIED]

## 3. Hero-damage audit (R3: every damage roll maximal, no HP regeneration ever, model §3.1)
HP 16/16 at start. Sources reachable in L_OFF^{W+C}, with the rule that keeps them off intended plays:
| Source | Damage (max) | Reached only by | Rule |
|---|---|---|---|
| Kick wall/stone/boulder (`kick_ouch`) | rnd(5) (rnd(3) if Con > 15) + wounded leg + Str/Dex abuse | hero `^D` | never kick |
| Kick empty air (`kick_dumb`) | 0 HP; Str abuse + wounded leg (dokick.c:864-875) | hero `^D` | never kick |
| Sokoban pit (forced fall) | rnd(6), utrap 2-7 | stepping on an unfilled pit | Z3 |
| Hole / trapdoor | leaves level = loss | stepping on it | never |
| Throw an object up (`<` direction) | non-weapon (boots): weight-based, 1..6; iron ball: its `dmgval` (dothrow.c:1349-1360) | hero `t`/`f` | never throw |
| Angering prayer | `god_zaps_you` death; `losexp` non-fatal; Punishment | hero `#pray` | never pray |
| Overexertion | 1 HP per 30/10 moving turns, pass out at 1 HP (hack.c:3036-3047; not death) | Stressed+: only after self-abuse or carrying the ball | follows from the above |
| Fumbling / teleport / waiting / steps / pushes | none (§2.2, §2.4; `moverock` has no `losehp`) | — | — |
| Ice slip `hurtle`, falling down stairs, cockatrice trip | — | need ice / stairs / corpse: absent | — |
**Claim D.** On every intended play the hero takes 0 damage against every nature strategy, so nature cannot kill him
at any length of play; every lethal or damaging event requires a hero command outside the intended set. [STRONG; each
row's source line VERIFIED except the toss_up cap, read only at dothrow.c:1349-1360]

## 4. Membership: C1-C6 for L_OFF^{W+C} (every instance, not only Z-compliant ones)
- **C1 poly state.** New state: boots record (worn mask), HFumbling/EFumbling (O(1) words; FROMOUTSIDE never set),
  trap records (fixed count: no trap creator; TELEP_TRAP never deleted), `dndest/updest` (static after finalize),
  `stasis_until` (static 0), static `in_tele_trap` flag. No creators: teleport moves only the hero; `rloco` moves a
  boulder (count conserved; may fill a pit/plug a hole = deletion). Continuation: recursion guarded
  (teleport.c:1497-1500); `safe_teleds` frame holds `candy[ROWNO·(COLNO−1)]` = O(w·h) words: poly. [STRONG]
- **C2 poly segments.** `safe_teleds` ≤ 40 tries + one `collect_coords` pass (finite shuffle) + scan; `rloco` ≤ 4000
  tries (teleport.c:2106, 2117-2121); Fumbling expiry O(1) RNG; no uncapped loop added. [VERIFIED]
- **C3** ranges ≤ max(COLNO, ROWNO, 20, 100); poly. **C4** unchanged. **C5** TELEP_TRAP never changes level
  (`tele_trap` → `tele`/`teleds` only); LEVEL_TELEP not whitelisted. **C6** `stasis_until` reset by the harness;
  wrap is internal state (κ includes `moves`). [STRONG]
⇒ by Thm M, **L_OFF^{W+C} under R3 ∈ EXPTIME** (feasibility §6 confirmed, now with the full audit). Membership needs
none of Z1-Z4 (a boulder on T or a dead coin are just more configurations).

## 5. Answers to B (INTERFACE "B → C")
- **C-1 YES** (STRONG): on intended plays the RNG calls are: per-turn block (model §3.1: no π/HP effect; exercise can
  only raise Str/Con, Dex may fall), push `exercise(A_STR, TRUE)`, Boots_on/Fumbling `rnd(20)`, `slip_or_trip`
  `rn2(4)` (message), `safe_teleds` coordinates + shuffle at T (the coin). Only the last changes π.
- **C-2 YES with correction**: Str/Con never decrease without hero kicks/self-made Stressed+ (§2.4); but they may
  **start** at 8/8 ⇒ hero possibly Burdened (time only). Push and squeeze rules never change (J4: weight ≥ 500).
- **C-3 YES** under Z1/Z2 (J8): A, B, T each have a boulder-free floor neighbour (X_A, X_B, E).
- **C-4 NO as stated → repaired**: the coin itself is wrap-sensitive (N1, §2.6). Repair = Z2 (bounce) + Z4 (wait).
  B's YES strategy H_σ must insert waits before T in the dead phase; B's NO direction needs the bounce = null visit.
- Extra rules for A: no boulder within Z1's zone (R_B as defined in §1); gadgets with hero-crossable pits violate Z3
  unless every pit is filled before the hero can step on it in the intended play.

## 6. Weakest steps
1. R_B over-approximation must actually be computed for B's layout (A's gadget files + corridors); Z1 is easy to
   violate near E/X_A/X_B.
2. Lemma S^C rows U/X inherit hu-off's entry-point reading (~60 handlers); new rows were read in full except `#sit`
   (taken from monsters-traps §1.4) and object-flight details near T (T1 row relies on hu-off T1 + Z2).
3. N1 depends on SC3 (wrap) and on `stasis_until == 0` after the harness (read at mklev.c:904; not witnessed).
   An alternative spec choice (moves saturates, or W_moves = poly(n)) would remove the dead phase but changes SC3.
4. `vary_init_attr`/`init_attr` setup range is a direct reading; whether the spec instead fixes attributes (making
   the start unencumbered) is a spec decision; harmless either way.
