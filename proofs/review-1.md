# Adversarial review 1 of milestone-1 (NetHack 5.0.0, commit 16ff591)

Reviewer: adversarial sub-agent, 2026-10-28. Source read-only; nothing built or run.
Paths are `src/<dir>/<file>:<line>` relative to the checkout. Labels: [src file:line] = I read it;
[conj] = my reasoning, not machine-checked.

## 0. Fatal flaws first

**X1 (FATAL for "DET, W_C, H_∞ ∈ NP"). The instance language can switch hunger off.**
`nh.debug_flags({hunger=false})` sets `iflags.debug_hunger` [src src/nhlua.c:1485-1489], and `gethungry()` returns
immediately when it is set [src src/eat.c:3167-3168]. `nh.*` is registered in every Lua state, including the one
`load_special()` uses for special levels [src src/nhlua.c:2334-2336, src/sp_lev.c:6454-6460]. There is no wizard-mode
gate. The devs use it themselves in level tests [src test/testmove.lua:143, test/test_des.lua:619]. The same call with
`mongen=false` sets `iflags.debug_mongen`, which makes **every** `makemon` return NULL, explicit species included
[src src/makemon.c:1168], and it removes all current monsters, the starting pet too [src src/nhlua.c:1470-1482].
A des-level may also call `u.clear_inventory()` and `u.giveobj(obj.new("cursed loadstone"))`
[src src/nhlua.c:2045-2058, src/nhlobj.c:142-162, 350-363]. So with milestone-1 §2's instance format (a Lua level,
"no RNG-dependent calls"), the Push-1F construction needs **no large integers at all**. Zero hunger is deterministic,
so plays are unbounded with C-width ints. If the rest of L1 holds, DET_{W_C} is PSPACE-hard, and the NP claim would
imply NP = PSPACE. The "W decides the class" story in §4 is then wrong: H (via hunger) decides it, and the instance
language controls H.
Even if `nh.*` is banned, the "full hero record" H₀ can carry illegal states that also stop hunger:
`u.uinvulnerable=1`, which only prayer and `nomul()` clear [src src/eat.c:3167, src/hack.c:4166, src/pray.c:2269-2280];
or a non-eating form plus intrinsic `HUnchanging`, which no game code ever grants [grep: only src/end.c:742 clears it].
With Unchanging the timer just re-arms [src src/timeout.c:641-643], so the form lasts forever.

**X2 (FATAL as defined, repairable). DET as defined is (almost) empty, so no reduction can output DET instances.**
DET = "no RNG outcome can change (position, boulders, terrain, alive)" for every play. Two moves are always legal:
- *Wait into fainting.* Once `u.uhunger ≤ 0`, fainting is `rn2(20 - h/10) >= 19` [src src/eat.c:3409-3431]. The
  starvation threshold `-(100+10·ACURR(A_CON))` [src src/eat.c:3436] moves with Con, and Con exercise is random
  [src src/attrib.c:538-548]. So when the hero dies, and how many actions he gets before that, depends on the RNG.
  This applies to every instance with finite nutrition.
- *Pray repeatedly.* The "too soon" branch calls `gods_upset()`, which does **ugangr++** and `angrygods()`
  [src src/pray.c:2305-2309, 1436-1442]. `angrygods` rolls `rn2(maxanger)` with `maxanger = 3·ugangr ± Luck`
  [src src/pray.c:716-723]. The outcomes are: displeased, `losexp`, curses, `punish` (creates ball+chain),
  `summon_minion` (creates a monster), `god_zaps_you` (kills unless resistant) [src src/pray.c:725-777]. Two quick
  prayers are enough to reach these branches.
Repair: define DET at the answer level ("R2-answer = R3-answer", i.e. RNG can neither help nor hurt reachability), or
remove `#pray` and treat fainting as failure, as explicit [assump]s. Then prove that property for each reduction.

**X3 (FATAL for the L1 prayer neutralization as drafted; repairable).** lower-bound-strategies E2 plans to "set
`u.ugangr ≥ 1`". That turns every prayer into angrygods, and angrygods escalates (X2). Under R2 that **helps** the
player: a neutral god summons an elemental [src src/minion.c:207-208]. An air elemental engulfs the hero and carries him.
The Sokoban corner ban is hero-only (`cant_squeeze_thru` case 3 checks `mon == &youmonst`) [src src/hack.c:953-978],
so a monster can cut corners that the hero cannot [conj: engulf transport]. A killed minion also has a 1/6 random drop
[src src/mon.c:3585-3594]; a wand of striking from that drop destroys boulders [src src/zap.c:2275-2286].
`rndmongen=0` does not stop any of this: an explicit species bypasses the flag [src src/makemon.c:1168].
Working neutralization [conj, source-backed]: keep `ugangr=0` and **Luck = 0**, with **no full moon** (full moon gives
+1 Luck [src src/allmain.c:58-60]) and no Friday 13th, and set `mongen=false`. Why it works: the loadstone is always a
minor trouble [src src/pray.c:236-237]. Off an altar `action = rn2(Luck+2)+1` is capped at 3, and minor troubles are
only fixed at action ≥ 3 [src src/pray.c:1116-1146]. So the loadstone is uncursed **iff Luck ≥ 1**. With Luck 0 a
successful prayer fixes only major troubles. With hunger off and HP full, none apply, except STUCK_IN_WALL (see L-4).

## 1. Verdicts on claims.md

### Source facts
| # | Verdict | Evidence / correction |
|---|---|---|
| F1 | survives | — |
| F2 | survives | Note: it calls `done(ESCAPED)`, not death [src src/allmain.c:253-257]. |
| F3 | survives | [src src/do.c:1709-1710, src/mklev.c:1578-1579] |
| F4 | **damaged** | Only `ptr==NULL` calls are blocked. Prayer minions, create monster and clones are not. `iflags.debug_mongen` blocks all [src src/makemon.c:1168]. |
| F5 | survives | Hero-made traps (`madeby_u`) are ignored. SPIKED_PIT/TRAPDOOR don't count. Called only on deltrap or ttyp replace [src src/trap.c:7059-7095]. |
| F6 | survives | Squeeze needs total weight ≤ wc−850 ≤ 150 [src src/hack.c:139-140, 4311-4365; include/weight.h:24-25]. |
| F7 | **damaged** | Also skipped when `iflags.debug_hunger` is set (Lua-settable) and under Slow_digestion. Asleep: only 1/10. Plus random accessory/encumbrance hunger via `rn2(20)`. 5.0: SD armour burns on case 0 [src src/eat.c:3167-3270]. |
| F8 | **damaged** | The increment is **capped at LARGEST_INT=32767** [src src/pray.c:1371-1377; include/global.h:135]. So after a success, `ublesscnt ≤ 32767`, and a hunger prayer stays available every ~32.6k turns **forever**. "O(1) prayers" is false. |

### Complexity claims
| Variant / claim | Verdict | Reason and repair |
|---|---|---|
| Literal game O(1) | survives | Turn cap plus O(1) creation per turn gives a finite state space. |
| any R, W_C, H_cap ∈ NP | survives but **vacuous** | Within 10^9 turns the hero moves O(1) squares per turn (teleport choices are poly). The reachable region is constant-radius, or the branching is poly^const, so the problem is in P with a galactic constant [conj STRONG]. No H_cap variant can be NP-hard unless P=NP. Drop H_cap. |
| DET, W_C, H_∞ ∈ NP | **FATAL as stated** (X1) | Repair needs both of: (a) instance = straight-line `des.*` calls only, no `nh.*`/`u.*`, no loops (otherwise the Lua script is Turing-complete once the sandbox limits [src src/sp_lev.c:6457] are lifted); (b) H₀ restricted to consistent states (no `uinvulnerable`, no `HUnchanging`). Then rewrite Lemma H: prayers number ≤ C + T/32567 and give ≤ 900+100+10·Con ≤ 1250 each [src src/pray.c:404-411, eat.c:3436]. Strictly DET instances have deterministic hunger: base 1/turn, or 0 only in a non-eating form for ≤ `mtimedone` turns. Deficit ≥ 1 − 1250/32567 per turn, so T = O(total resources) [conj]. Caveat: under (a) the hero inventory is no longer settable (see FAILED row). |
| DET, W_C, H_∞ NP-hard | damaged | Blocked by X2 (definition). Under answer-level DET, Push-1 instances still need prayer neutralization (X3) and a fixed role (L-3). |
| DET, W_poly ∈ PSPACE | damaged-repairable | Under strict DET it is vacuous. Under answer-DET, prayer keeps creating monsters (`summon_minion`, explicit species; extinction not checked) → state is not poly. Repair: `mongen=false` or ban `#pray`. Then list the bounded creators: engravings (≤1 per square), stack splits (merge per square), ball+chain (once), `fracture_rock` rocks. Also add `moves`, `context.ident` and `ublesscnt` to the state (poly bits). |
| DET, W_poly PSPACE-hard | damaged-repairable | The simulation lemma survives (§2). Neutralization must change per X3. Hero role must be fixed (L-3). Moon/Fri-13 must be fixed. With `debug_flags` allowed, W_poly is unnecessary: the same reduction gives PSPACE-hardness for W_C (X1). |
| R2, W_C ∈ PSPACE likely false | survives | Agree. Prayer adds one more unbounded monster source (minions). |
| R3 full-info + cap ∈ EXPTIME | survives | Per-turn outcome vectors are poly length, so alternation stays in poly space. |
| W_∞ undecidable (weak) | survives as conj | Warning: if the Lua instance language is unrestricted, undecidability is trivial (the script itself computes). It must be excluded, or the result means nothing. |
| EXPTIME-hard | unknown | — |
| FAILED: "Lua level alone suffices" | **partly reversed** | `u.clear_inventory` + `u.giveobj(obj.new("cursed loadstone"))` set the inventory natively, and `debug_flags` removes hunger and the pet. Still out of reach from Lua: role/known spells, Luck, moon phase. Starting spells survive `clear_inventory` [src src/u_init.c:1297]. A Wizard's force bolt breaks boulders [src src/zap.c:2275-2286]. |

## 2. Push-1F simulation lemma (lower-bound-strategies §2.2): checked leaks
- L-1 Orthogonal and diagonal step/push logic matches the draft [src src/hack.c:939-946, 953-979, 1153-1171, 386-414, 432-448].
  A successful push consumes RNG only through `exercise(A_STR)` [src src/hack.c:194-197]. **Survives.**
- L-2 Thrown iron ball pulls the hero to the square before the landing point [src src/ball.c:931-941]. This path is
  guarded: each ball step calls `test_move(...TEST_MOVE)` (Sokoban corner rule included), and a boulder stops the ball
  [src src/zap.c:4095-4117]. Hurtling obeys the corner rule [src src/dothrow.c:885-891]. Kicking a boulder is a no-op
  [src src/dokick.c:517-519]. **Closed.**
- L-3 Role: Wizard (force bolt known), Priest/Monk/Healer (starting spells), Knight (`#jump`). The role must be fixed
  in the instance. A non-Wizard role without spells or jumping closes this. For knight jumps, each hurtle step is
  checked, so a jump = legal walk [conj].
- L-4 Prayer STUCK_IN_WALL teleport works on noteleport levels [src src/pray.c:461-477]. **Invariant [conj, short
  proof]:** after any move, the square the hero came from is floor without a boulder. Boulders only move away from the
  hero, so nothing can refill it while he stays put. Hence `stuck_in_wall()` [src src/pray.c:159-181] is false after
  the first move. The instance only has to avoid a boxed-in start.
- L-5 Cursed loadstone uncursing: only through prayer with Luck ≥ 1 (X3). The heavy-hero condition never flips:
  total 500 > 150 for every capacity ≤ 1000. Encumbrance: wc = 25(Str+Con)+50 [src src/hack.c:4314-4315]. The hero is
  unencumbered iff Str+Con ≥ 18. With hunger off, exercise only raises Str (pushing) and Con (Not Hungry); the only
  abuses are Weak/Fainting/Overtaxed [src src/attrib.c:533-564]. So once he starts unencumbered, he stays that way.
  With hunger on, Stressed+ gives random hunger [src src/eat.c:3196-3197] and HP drain [src src/allmain.c:298-302].
  Choose Str+Con ≥ 18 and keep hunger off.
- L-6 Sokoban flag sentinel pit: OK [src src/trap.c:7063-7082; include/rm.h:538]. Nothing else clears the flag except
  level init [src src/mklev.c:891]. Sokoban luck penalties (`sokoban_guilt`) only fire on squeeze/step-over, which are
  impossible here.
- L-7 Per-turn RNG consumers in a bare instance: `rn2(70)` monster gen (no effect when gen is off) [src src/allmain.c:160-167];
  speed rn2(3) only if Fast/Very_fast (choose a role without intrinsic Fast) [src src/allmain.c:120-131]; hunger rn2(20);
  exerchk; Teleportation/Polymorph/lycanthropy rolls (absent) [src src/allmain.c:306-334]. With hunger off, none of
  them touches the projection [conj].

## 3. Methodology
- M1 DET is a semantic promise, and checking it is probably as hard as the problem. State the results as promise
  problems, and prove the promise for each reduction's outputs.
- M2 Lua instance language: the sandbox caps of 1 MB memory and 1M steps [src src/sp_lev.c:6457] are hidden constants.
  Lifting them makes instances Turing-complete. Use straight-line des.* code, plus an explicit whitelist
  (`u.giveobj`, `nh.debug_flags`) if the native construction is wanted.
- M3 The wall clock (moon phase, Friday 13th, night) changes Luck and therefore prayer behaviour. It belongs in the instance.
- M4 Citation F2: the author list looks merged with the *pulling-blocks* paper (Asif, Scheffler, Suhl). The Push-1F /
  Block Dude paper (FUN 2022) is, from memory, Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch [conj; verify].
- M5 The hero-record model can express states the game can never reach (X1). Either restrict H₀ to reachable or
  consistent states, or prefer the native Lua construction, which needs no H₀ beyond role and attributes.

## 4. Repairs list (priority order)
1. Fix the instance language: straight-line `des.*`, plus either (A) `u.giveobj` + `nh.debug_flags` whitelisted,
   giving the clean native result "DET_{W_C} PSPACE-hard" and dropping Lemma H; or (B) no `nh.*`/`u.*`, H₀ restricted
   to consistent states, and Lemma H rewritten with the 32767-cap rate argument.
2. Replace strict DET with answer-level DET, or [assump] no `#pray` and fainting = failure.
3. Prayer neutralization: ugangr=0, Luck=0, not full moon, not Fri-13, `mongen=false`. Prove: loadstone never uncursed
   (action ≤ 2), STUCK invariant (L-4), success outcomes harmless. Remove the "ugangr ≥ 1" plan.
4. Fix the hero: non-spellcaster, non-Knight, no intrinsic Fast, Str+Con ≥ 18, inventory = {cursed loadstone}, not boxed in at start.
5. Correct F4, F7 and F8 in claims.md. Drop the H_cap row (it is in P).
6. U2: an explicit list of object/monster/engraving creators reachable in the repaired DET model.
7. Verify the F2 citation. Witness: adapt `test/testmove.lua` (`nh.pushkey` + `nh.doturn`) [src src/nhlua.c:1424-1456]
   for a headless 1-gadget check, when Ivan is off the laptop.
