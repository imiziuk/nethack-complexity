# L_OFF is PSPACE-complete (proof draft, phase 2)

Author: proof sub-agent, 2026-10-28. Source: NetHack 5.0.0 @ 16ff591, read-only at `src/`. Paths `src/<f>` below mean
`src/src/<f>`; `include/`, `dat/`, `test/` are under `src/` too. Nothing was built or run.
Labels: **[src f:l]** = I read that code this session; **[conj]** = my reasoning, not machine-checked;
**[ext]** = published theorem; **[assump]** = modelling choice that the team must accept.
Binding language: `proofs/phase2-spec.md` (L_OFF). Inputs used: review-1 (L-1..L-7, X1-X3), lower-bound-strategies §2,
upper-bound.md, mechanics/terrain-movement.md.

## 0. Result and what it needs

| Claim | Status |
|---|---|
| **Thm B** L_OFF is PSPACE-hard (all four randomness semantics R1-R4) via Push-1F | proof below; rests on [ext] Push-1F + 3 spec clarifications (SC1-SC3) |
| **Thm A** L_OFF^W ∈ PSPACE, where W = the object/terrain/trap whitelist of §A.0 | proof below; L_OFF without W: **open**, and likely false-as-stated (§A.4) |
| Corollary: L_OFF^W is PSPACE-complete; f's outputs lie in L_OFF^W | yes |
| **Thm C** answer-level DET holds for every output of f | proof below |

Spec changes needed (proposed; the spec is binding, so these go to Ivan / the spec owner):
- **SC1 (realization of "fresh game, then S run as the level").** In a real `newgame()` the level is made by `mklev()`
  BEFORE the starting kit: `mklev(); u_on_upstairs(); ... makedog(); u_init_inventory_attrs();`
  [src allmain.c:806-816], and `u_init_inventory_attrs()` starts with `while (gi.invent) useupall(gi.invent);` and then
  hands out the role kit [src u_init.c:1373-1393]. So if S runs at mklev time, `u.clear_inventory()` and
  `u.giveobj(...)` are **overwritten** and the Valkyrie gets spear, dagger, shield, food [src u_init.c:160-166];
  she can drop all of it, becomes squeeze-light, and the reduction collapses (lower-bound-strategies P8).
  Fix: define the instance run as the test-harness sequence used by `test/testmove.lua:11-20`: after `newgame()`
  completes, execute `des.reset_level(); S; des.finalize_level()`, then play starts. Add those two wrapper calls
  to the spec (fixed, not part of S).
- **SC2 (whitelist for the upper bound).** The spec lets S place any otyp, any trap and any terrain. With a throne,
  `#sit` gives a wish with outcome `rnd(13)==6` and `u.uluck + rn2(5) >= 0` [src sit.c:45-46, 105-110], and the
  throne only vanishes on `!rn2(3)` [src sit.c:225]; under R2 the player picks "no vanish" forever, so wishes,
  hence object records, are unbounded (§A.4). Theorem A is therefore stated for L_OFF^W (§A.0). The reduction
  only uses W, so the completeness result is "L_OFF^W is PSPACE-complete, and L_OFF is PSPACE-hard".
- **SC3 (fixed-width counters).** With the 10^9 cap deleted [src allmain.c:253-257 is the cap], `svm.moves` (long)
  eventually overflows. Declare W_C integers to wrap (two's complement). Nothing in f's outputs reads `moves` in a
  way that matters (§B.4 per-turn table). Same for `u.ugangr` (int, only grows; §B.3 I6).
- Also make `nh.debug_flags{mongen=false, hunger=false}` **mandatory** in L_OFF (as written it is only whitelisted,
  so L_OFF would contain hunger-on instances).

## 1. Common definitions

- **Hero template** [assump, satisfies spec]: human female lawful Valkyrie. Non-spellcaster (kit has no spellbook
  [src u_init.c:160-166]), not a Knight (no `#jump`, no `#turn` [src apply.c:2002-2004, pray.c:2414-2423]), intrinsics
  cold res @1, stealth @3, speed @7 [src attrib.c:81-83] and XL stays 1 (§B.3 I8), so never Fast; base Str 10,
  Con 10 [src role.c:519], `init_attr` only adds points (np = 75-48 > 0) [src attrib.c:699-733], so Str+Con ≥ 20.
- **Harness H** (SC1): `newgame()`, then `des.reset_level()` (clears level incl. `sokoban_rules=0` and all stairways,
  resets xstart=1, ystart=0 [src sp_lev.c:5993-6009; mklev.c:850-922 (891, 918, 922)]), then S, then
  `des.finalize_level()` [src sp_lev.c:6014-6064]: wallification, `flip_level_rnd` unless `noflip` (6041),
  `solidify_map`, `fixup_special` (places only declared lregions), `level_finalize_topology` (mineralize, sets
  `in_mklev=FALSE`, xstart=ystart=0 [src mklev.c:1544-1555]), `makemap_prepost(FALSE)` → `u_on_rndspot(0)` puts the
  hero in the declared teleport region [src cmd.c:986-1060; dungeon.c:1605-1638; mkmaze.c:356-470].
- **Projection** π(X) of a game state X: (hero square, set of boulder squares, alive?). "Board" = the Push-1F cells.

## A. Upper bound: L_OFF^W ∈ PSPACE

### A.0 The whitelist W (proposed spec text)
S may use only: `des.level_init{style="solidfill"}`; `des.level_flags` with flags from {noflip, sokoban, noteleport,
hardfloor, solidify, premapped, mazelevel, nomongen, noautosearch} [names: src sp_lev.c:3772-3821]; `des.map` /
`des.terrain` with map chars {' ' stone, '-' '|' walls, '.' room, '#' corridor}; `des.object` with otyp ∈ {boulder,
loadstone} (any BUC, quantity 1); `des.trap` with type pit; `des.teleport_region`; `u.clear_inventory()`;
`u.giveobj(obj.new("<buc> loadstone"))`; mandatory `nh.debug_flags{mongen=false, hunger=false}`. (No des.region:
room records are not needed; no "inaccessibles": `ensure_way_out` can create features [src sp_lev.c:5217-5260].)
Note: there are **no** level flags named "nondiggable"/"nonpasswall"; those are the separate functions
`des.non_diggable`/`des.non_passwall` [src sp_lev.c:5934-5937]. f does not need them (nobody can dig or phase, §B.3).

### A.1 Lemma 1 (poly-size reachable states) [conj, each creator pinned to source]
Let n = |I|. Every state reachable from an L_OFF^W instance has an encoding of poly(n) bits, after quotienting the
write-only logs (message history, `gamelog` [src pline.c:495-531]) [assump Q: never read by game logic].

Proof. Components and bounds:
1. **Map**: w·h `struct rm` of O(1) words; w, h ≤ |I| (they are written in S). Terrain never changes (no digging tool,
   no wand, no force bolt; boulder-into-pit deletes the trap, not the terrain [src do.c:186-266]).
2. **Monsters: always 0** after `debug_flags`. `mongen=false` sets `iflags.debug_mongen` and `mongone()`s every
   monster incl. the pet [src nhlua.c:1463-1482]; `makemon` returns NULL whenever `iflags.debug_mongen`
   [src makemon.c:1168]. The other allocators of map monsters are `clone_mon` [src makemon.c:866] (needs an existing
   monster) and restore [src restore.c:391]; mkobj.c:120/2210 only build OMONST records inside corpses/statues (none
   in W). Callers that ask for a monster (summon_minion [src minion.c:198-245], bag of tricks, eggs, figurines,
   create-monster) all go through `makemon` and handle NULL (minion: `if (mon)` [src minion.c:237]).
3. **Objects**: initial k ≤ n, plus `mineralize` at finalize (≤ w·h, buried in stone, unreachable without digging)
   [src mklev.c:1550]. Creators reachable in W: only `punish()` from `angrygods` case 6 [src pray.c:757-761]: one
   ball + one chain, and only while `!Punished`. Punishment is absorbing: every `unpunish()` caller needs an item,
   monster, terrain or Luck ≥ 1 that W lacks (blessed bell [src apply.c:1276-1280], drawbridge [src invent.c:1415-1419],
   eating the ball [src eat.c:2478-2481], polymorph [src polyself.c:994, 1492], prayer minor-trouble fix
   [src pray.c:524] which needs action ≥ 3 ⇒ Luck ≥ 1 (I5), theft [src steal.c:281], digging [src dig.c:1993],
   explosion [src explode.c:756], bones [src bones.c:440], scroll [src read.c:1599], mon.c:1403-1406 (monster eats
   ball)). Hence ≤ k + w·h + 2 records. Records only split by `#adjust`/count-drop, which conserves Σquan; with
   quantity 1 per record this cannot exceed k + w·h + 2. Boulders filling pits are destroyed (count decreases).
4. **Traps** ≤ initial: hero cannot make traps (no tools); pits only get deleted.
5. **Engravings**: ≤ 1 per square (`make_engr_at` [src engrave.c:408]), text ≤ BUFSZ.
6. **Timers / light sources / regions**: none attach to boulder, loadstone, ball, chain; hero timeouts live in
   `struct you` (O(1) words). Regions: none created (no gas sources).
7. **Levels**: only dlvl 1. H frees all stairways [src mklev.c:918] and `fixup_special` places only declared
   lregions [src mkmaze.c:570-640] (W has no stair/portal); W has no hole/trapdoor/level teleporter, no digging, no
   level-teleport item. So no other level is ever generated.
8. **Counters** (`svm.moves`, `svc.context.ident`, `u.ublesscnt`, `u.ugangr`, `u.uluck`, conduct counters, AEXE
   exercise, `mvitals`): O(1) words each under W_C (SC3). RNG state: ISAAC64, constant size [src rnd.c:7-21].
   `u.uluck` ∈ [-10, 10] [src attrib.c:411-418; include/you.h:467-468].
Total: O((w·h + k)·1) words = poly(n). ∎

What about "any des.object" (the brief's question)? Partial answer [conj]: with mongen=false every *monster* creator
is dead (item 2), including wand/scroll of create monster, bag of tricks, egg hatching, figurines, cloning, minions.
The *object* creators are the problem: thrones (unbounded wishes, §A.4), and finite-but-chainable ones
(wands of wishing + scrolls of charging + magic marker, horn of plenty, polypiling). A per-item proof for all ~450
otyps is not done; hence W.

### A.2 Lemma 2 (poly-time step) [conj, spot-checked]
Given a state X (poly size), a command c and a vector ρ of RNG outcomes, the successor state (one iteration of
`moveloop_core`, i.e. the hero's action plus the once-per-turn block [src allmain.c:236-365]) is computable in
time poly(|X|), and ρ has poly length. Spot checks: vision recalc is O(w·h) per call; travel is a BFS
(`findtravelpath` [src hack.c:1266]); `place_lregion` tries 200 random spots then scans [src mkmaze.c:393-410];
`safe_teleds` is bounded likewise; `movemon` has no monsters; `rnz`/`rne` loops are bounded. A turn therefore makes
poly many RNG calls, so an R2 certificate is poly bits per turn [conj: no unbounded RNG retry loop is reachable in W
– all loops checked above have explicit caps].

### A.3 Theorem A
L_OFF^W ∈ PSPACE under R1, R2 (and R3 ∈ EXPTIME, not needed). Proof: a nondeterministic machine keeps only the
current state (Lemma 1), guesses the next command and (R2) its RNG outcome vector, simulates the turn (Lemma 2), and
accepts when the hero is alive on g at the start of a player turn. Space poly(n), so L_OFF^W ∈ NPSPACE = PSPACE
[ext: W. J. Savitch, "Relationships between nondeterministic and deterministic tape complexities", JCSS 4 (1970)
177-192]. Under R1 the guess is only the command. ∎

### A.4 Why not all of L_OFF [conj, source-backed obstruction]
A throne ('\\' is a legal des.map char) gives under R2 an unbounded stream of `makewish()` calls
[src sit.c:45-46, 105-110, 225]; wished-for armour/weapons do not merge, so the number of object records grows
without bound and Lemma 1 fails. Whether L_OFF (unrestricted) is still decidable/in PSPACE needs a quotient argument
(upper-bound.md Lemma 1c); not attempted. Thrones also need no monsters, so mongen=false does not help.

## B. Lower bound: Push-1F ≤_p L_OFF

### B.1 Push-1F [ext]
Instance I = (a, b, T, s, g): a board of a×b cells, T: cells → {empty, movable, fixed}, robot start s (empty),
target g. Outside the board counts as fixed [assump: bounded-board form; Push-1F hardness constructions are finite
and walled, so this loses nothing – check against the paper]. A move in direction d ∈ {N,E,S,W}: if s+d is empty, the
robot steps there; if s+d is movable and s+2d is empty, the block moves to s+2d and the robot to s+d; otherwise
nothing. Question: can the robot reach g?
**Theorem** [ext, title to be verified by the citation agent]: Push-1F is PSPACE-complete. J. Ani, L. Chung,
E. D. Demaine, Y. Diomidov, D. Hendrickson, J. Lynch, "Pushing Blocks via Checkable Gadgets: PSPACE-Completeness of
Push-1F and Block/Box Dude", FUN 2022, LIPIcs 226, paper 3 (author list per review-1 M4; the draft's list with Asif,
Scheffler, Suhl mixes in the *pulling-blocks* paper).

### B.2 The map f(I)
Pre-processing (poly time): if T(g) = fixed, output NO0; if s = g, output YES0; if the robot has no legal first move,
output NO0. YES0 = the construction below for the 1×1 board with s = g. NO0 = the construction for the 1×4 board
`s . F g` (robot walks between two cells, never stuck, g unreachable). Otherwise:

Map-relative coordinates (mx, my); the map is placed at absolute (1,0), so absolute = (mx+1, my). Map size
(a+4) × (b+2); generalized `COLNO = a+5`, `ROWNO = b+2` (column 0 unused: `isok` needs x ≥ 1 [src cmd.c:4326-4330]).
- board cell (i, j) ↦ (mx, my) = (i+1, j+1): '.' if T ∈ {empty, movable}, '-' if fixed;
- every other map cell is '-', except the **sentinel** (a+2, 1) which is '.'.
So the board is enclosed by a wall ring (mx ∈ {0, a+1} or my ∈ {0, b+1}); the sentinel's 8 neighbours are all walls
and it is at Chebyshev distance ≥ 2 from every board cell. Wallification may retype a wall cell (or make it STONE);
every such type is `IS_OBSTRUCTED` (typ < POOL) [src include/rm.h:119], which is all the proof uses.

S_I (straight-line, inside the W whitelist; H wraps it with reset/finalize):
```lua
des.level_init({ style = "solidfill", fg = " ", lit = true });
des.level_flags("noflip", "sokoban", "noteleport", "hardfloor", "solidify");
des.map({ x = 1, y = 0, map = [[ <the (b+2) rows above> ]] });
des.trap("pit", a+2, 1);                       -- sentinel, map-relative
des.object("boulder", i+1, j+1);               -- one line per movable cell (i,j)
des.teleport_region({ region = { s_i+2, s_j+1, s_i+2, s_j+1 }, region_islev = true, dir = "both" });
u.clear_inventory();
u.giveobj(obj.new("cursed loadstone"));
nh.debug_flags({ mongen = false, hunger = false });
```
Target in the instance: g_abs = (g_i+2, g_j+1). Size O(a·b) lines, so f is poly-time (log-space even).
Why each piece: `sokoban` → corner rule + no diagonal push [src sp_lev.c:3796-3797; hack.c:441-448, 953-978];
`noflip` → `flip_level_rnd` would mirror the map randomly while g stays fixed [src sp_lev.c:3804-3805, 6041];
`noteleport`, `hardfloor`, `solidify` are belt-and-braces (nothing in f can teleport, dig or phase).
Hero start: the region is one cell, so `place_lregion` is "oneshot" and returns that cell (`rn1(1,x)=x`)
[src mkmaze.c:393-397]; it must be ROOM and unoccupied (`bad_location` [src mkmaze.c:341-351], `occupied`
[src mklev.c:1806-1811]): s is '.', has no trap and no boulder. ✓.

### B.3 Invariants of every reachable state X of f(I) (any commands, any RNG outcomes)
Proved together by induction over turns; the step cases are the command table of §B.4.
- **I1 no monsters** ever: §A.1 item 2.
- **I2 loadstone**: the inventory always contains the cursed loadstone (weight 500 [src include/objects.h:1600]).
  Drop/throw/fire/put refused by `canletgo` [src do.c:685-697; dothrow.c:118]; not splittable [src invent.c:1666];
  uncursing needs prayer action ≥ 3 (I5) or pat_on_head case 4 (needs Luck ≥ 4) [src pray.c:1112-1146, 1283-1305];
  no other item or monster can remove it (I1, inventory ⊆ {loadstone, ball}).
- **I3 never squeezable**: `could_move_onto_boulder` is false: not Passes_walls (only source would be the STUCK
  fallback [src pray.c:461-477], excluded by I7), not riding (no steed), not a giant or very small (never
  polymorphed: no source), and `inv_weight() = Σwt − weight_cap() ≥ 500 − 1000 > −850` because
  `weight_cap() ≤ MAX_CARR_CAP = 1000` when not levitating [src hack.c:139-163, 4311-4337, 4351-4365;
  include/weight.h:24-25]. Diagonal squeeze: `cant_squeeze_thru(&youmonst)` ≠ 0 whenever Sokoban (case 3) and
  not Passes_walls [src hack.c:953-978].
- **I4 Sokoban stays on**: only `maybe_finish_sokoban` clears it [src trap.c:7059-7097], called from `deltrap` of a
  PIT/HOLE [src trap.c:6546-6547] or a trap retype [src trap.c:584-585]; the only trap is the sentinel; nothing
  reaches it (boulders cannot enter walls; no digging; `#untrap` needs adjacency; thrown ball stops at walls,
  `!ZAP_POS` [src zap.c:4076-4079]). With zero pits the flag could not clear either; the sentinel is redundant for
  f but required for gadget libraries with pits (witness W5).
- **I5 Luck ≤ 0**: starts 0 [src u_init.c:963] (no full moon / Friday 13: spec); `change_luck(+)` callers are
  full moon [src allmain.c:58-60], restore undo [src save.c:143-146], fedora [src do_wear.c:437-439], unicorn gems
  [src dothrow.c:2331-2364], altars [src pray.c:1667, 1741, 2043, 2078, 2106], throne [src sit.c:108]: none reachable;
  `u.uluck=0` resets only raise negative luck to 0 [src pray.c:1276, 2050, 2085, 2108, 2252]; timeout moves luck
  toward baseluck = 0 [src timeout.c:595-620]; `u.moreluck` needs a luckstone [src attrib.c:441-450; artifact.c:526-533].
- **I6 terrain fixed, traps = {sentinel}**: as A.1 items 1, 4.
- **I7 not stuck after any displacement**: after the hero moves (step, push, ball pull) the square he left is floor
  without a boulder; boulders move only when pushed, away from the hero (r = s+d ≠ s−d), so the square stays free
  while he stands still; hence `stuck_in_wall()` (needs all 8 neighbours obstructed or `blocked_boulder`)
  [src pray.c:161-181, 2677-2719] is false. At the start: pre-processing guarantees a legal first move, i.e. an
  orthogonal neighbour that is empty (not counted) or a single boulder with free floor beyond
  (`blocked_boulder` returns FALSE: count 1, orthogonal, isok, not obstructed, no boulder [src pray.c:2690-2716]).
  Also a "too soon" prayer never fixes anything and STUCK needs `ublesscnt ≤ 200` [src pray.c:2151-2154].
- **I8 hero stays XL1 human, unpolymorphed, not Levitating/Flying/Blind/Stunned/Confused**: no source of exp, poly,
  levitation, blindness or confusion is reachable (no items but loadstone/ball, no monsters, no traps reachable);
  `losexp` at XL1 from divine anger only resets exp, non-fatal [src exper.c:219-245].
- **I9 hunger inert**: `gethungry` returns at once [src eat.c:3167]; no reachable `morehungry` caller
  (callers: apply/fountain/spell/teleport/vomit/martial arts [grep, all need absent items/terrain]).

### B.4 Simulation lemma
**Lemma S (soundness).** For every reachable X, π(X) restricted to the board is reachable in Push-1F from (s, B₀),
or the hero is dead. Equivalently: every command changes (hero square, boulder set) by a sequence of Push-1F moves
(possibly empty).

Per-command proof (groups cover the whole table `extcmdlist` [src cmd.c:1667-2067]; wizard-mode commands
(WIZMODECMD) and `#exploremode` are excluded by the spec).

| Group | Commands | Effect on π | Evidence |
|---|---|---|---|
| M1 step to free square | move h/j/k/l/y/u/b/n, count prefix, `F` with no monster | orthogonal: same as Push-1F step. Diagonal a→b is refused iff both corners are `bad_rock` (wall/stone, or boulder under Sokoban) [src hack.c:939-945, 1153-1171]; if allowed, a free corner c exists, c is ROOM without boulder (only terrain in the ring is ROOM/obstructed, I6), so = Push-1F path a→c→b. `F` toward a boulder or wall: `domove_fight_empty` digs only with a pick (`dig_typ(uwep)`) [src hack.c:2266-2274] → no-op | [src hack.c:2712-2880 domove_core, 991-1255 test_move] |
| M2 step into a boulder, orthogonal | same keys | push iff r = s+d is isok, not obstructed, not bars, no boulder, no monster (I1), no closed door, no trap at r (I6: board has none), not pool [src hack.c:432-500, 615-631]; then `dopush` moves it, hero enters s (`return 0`). RNG only in `exercise(A_STR)` [src hack.c:194-197]. Else `cannot_push` → I3 → −1, no move [src hack.c:262-312]. Exactly Push-1F | lower-bound-strategies P1, P7 |
| M3 step into a boulder, diagonal | y/u/b/n | if both corners bad_rock: refused before reaching the boulder (M1). Else `moverock`: "won't roll diagonally" → `cannot_push` → I3 → no-op [src hack.c:441-448] | W2 |
| M4 m-prefix | `m<dir>` | toward boulder: "boulder in your way", no move (I3) [src hack.c:380-410]; else as M1 | W4 |
| M5 run / rush / travel / retravel / mouse | G, g, shift/ctrl dirs, `_`, `^_` | sequences of `domove` single steps; with `context.run ≥ 2` (incl. travel = 8) a boulder square is refused [src hack.c:1216-1222]; travel never routes through boulders in Sokoban [src hack.c:1232-1235]; run = 1 pushes like M2 | [conj: each step = M1/M2] |
| M6 Punished movement | any step while Punished | `drag_ball` runs **after** `test_move` [src hack.c:2846-2863]: may refuse the move ("cannot drag", [src ball.c:775-780]) after a push already happened → state (a, B') = Push-1F push then step back to a (a is empty). "Jerked back" needs a pool/pit under the chain [src ball.c:782-820]: none reachable | [conj] |
| T1 throw/fire | t, f | loadstone refused (I2). Iron ball (only if Punished and carried): each flight step checks boulder (stop) then `test_move(x−d, d, TEST_MOVE)` incl. corner rule [src zap.c:4096-4117]; walls stop it via `!ZAP_POS` [src zap.c:4076-4079]; hero lands at the square before the ball [src ball.c:931-941], having passed only boulder-free squares each reached by a legal step ⇒ = sequence of M1 steps. Throw up/down: no displacement. Recoil `hurtle` needs Levitation (I8) | review L-2 re-verified |
| K kick | `^D` | boulder, ball, chain never move [src dokick.c:517-519]; walls/boulders/empty air → `kick_ouch` / `kick_dumb`: HP loss, right-leg wound, Str/Dex abuse; every `hurtle` there needs Levitation or air level [src dokick.c:864-905, 1430-1462]. Wounded legs block further kicks [src dokick.c:1279-1281]. No π change (death possible = loss) | |
| P pray | M-p | see §B.5 | |
| I inventory | d, D, `,`, w, x, X, Q, W, T, A, P, R, M-a (adjust), C/M-n (name), i, I, `*`, seeX | only the ball/chain move between inventory and the hero's square; loadstone stays (I2). No π change | [src do.c:685-697] |
| U item use, nothing usable | a (apply: loadstone/ball → `use_stone` rubbing, messages only [src apply.c:2680-2730, 4396-4398]), M-r rub, M-d dip, e eat, q quaff, r read, z zap, Z cast (no spells), M-i invoke, E engrave (dust engraving on own square only), M-f force (needs a box [src lock.c:676-757]), M-l loot, M-T tip, o open, c close, M-u untrap (sentinel never adjacent), M-o offer (needs altar [src pray.c:1860-1862]), p pay, M-c chat, M-R ride (no monster [src steed.c:183-190]), M-j jump ("can't jump very far" [src apply.c:2001-2003]), M-m monster (not polymorphed), M-t turn [src pray.c:2418-2423], `^T` teleport (no Teleportation, no spell [src teleport.c:932-933, 1074-1086]), M-s sit (floor/object messages [src sit.c:436-465, 560-563]), `<` `>` (no stairs: "can't go up/down here" [src do.c:1298-1316, 1131-1240]), M-w wipe, M-e enhance | no π change | [conj for the ones cited only by entry point] |
| W time | `.` wait, `s` search (nothing hidden: no SDOOR/SCORR; sentinel not adjacent) | per-turn block only | below |
| X meta | help, options/toggle, look, glance, terrain, overview, chronicle, conduct, known, vanquished, version(s), redraw, prevmsg, perminv, annotate, autopickup, whatis/whatdoes, herecmdmenu/therecmdmenu (dispatch to listed commands), repeat (^A), save (game stops; restore re-applies moon/Fri-13 luck, = identity under fixed external inputs [src save.c:143-146]), quit (game over), shell, suspend, bugreport | no game-state change except UI/option bits; options that change physics need items (autodig needs a wielded pick [src hack.c:1049-1053]) | [conj] |

**Per-turn block** [src allmain.c:160-167, 236-365]: random monster gen → `makemon` NULL (I1); Fast roll needs Fast
(I8) [src allmain.c:120-131]; `nh_timeout` (luck toward 0, leg wound heals); `ublesscnt--`; HP/Pw regen;
`overexert_hp` (only Stressed+ and moving); Teleportation/Polymorph/lycanthropy absent; `dosearch0` needs Searching;
`gethungry` inert (I9); `exerchk` (attributes ±1: only changes `weight_cap`, irrelevant by I3); `u_wipe_engr`;
`invault` (no vault). None changes π.

### B.5 Prayer (all outcomes)
`can_pray` [src pray.c:2124-2175]: p_type 0 "too soon" if `ublesscnt` > 200/100/0 for major/minor/no trouble; else
p_type 1 if Luck < 0, `ugangr` ≠ 0 or alignment < 0; else p_type 3 (no altar ⇒ no p_type 2, not undead ⇒ no −1).
Start: `ublesscnt = 300` [src u_init.c:1005], and the cursed loadstone is always a minor trouble (last loop of
`worst_cursed_item` [src pray.c:288-347]), so early prayers are "too soon".
- p_type 0/1 → `gods_upset`/`angrygods` [src pray.c:2316-2324, 1436-1442, 704-786]: outcomes "displeased" (none);
  −1 Wis + `losexp` (XL1: exp reset only); `rndcurse`/`attrcurse` (curses inventory, removes an intrinsic);
  `punish` (ball + chain, once; see M6, T1); `summon_minion` → NULL (I1); `god_zaps_you` → death or no effect.
  Plus `ublesscnt += rnz`, `change_luck(-3)`. None moves the hero or a boulder.
- p_type 3 → `pleased` [src pray.c:1071-1385]: `trouble ≠ 0` always (loadstone), so `pat_on_head` is set only by
  action 5, impossible: off-altar `action = rn1(Luck+2, 1) ≤ 2` at Luck 0, then `min(action,3)`, or ∈ {0,1} if
  record < STRIDENT [src pray.c:1125-1130]. Cases 1/2 fix **major** troubles only. Reachable majors: TROUBLE_HIT
  (heal, from kicks), TROUBLE_COLLAPSING (restore Str), TROUBLE_STUCK_IN_WALL (excluded by I7). Hunger, lava,
  levitation, hands etc. unreachable (I8, I9). So: no uncurse, no teleport, no levitation, no wish.
  (Even with no trouble and a DEVOUT record, pat_on_head at Luck 0 is `rn2(3)` ∈ {nothing, weapon fix, golden glow}
  [src pray.c:1166-1253]: heals and restores Str only.)
Prayer never changes π. ∎ (Lemma S)

**Lemma C (completeness).** If Push-1F moves m₁..m_t lead from (s, B₀) to (p, B), then the play "press the
direction key of mᵢ, i = 1..t" (no other command) reaches, for **every** RNG outcome sequence, a state with
π = (p, B), hero alive, at the start of a player turn.
Proof. Induction. In this play: no damage source exists (no monsters, traps, kicks, prayers), so HP stays max; not
Punished; `carrying_too_much` needs OVERLOADED or (Stressed+ and HP < 10) [src hack.c:2616-2631]; OVERLOADED needs
`2·(500 − wc)/wc + 1 ≥ 5`, i.e. wc ≤ 166, but wc ≥ 25·(3+3)+50 = 200 for any attribute values
[src hack.c:4311-4312, 4372-4381] (in fact wc ≥ 550 and the hero is unencumbered, since no abuse occurs). Then
`domove_core` reaches `test_move(DO_MOVE)` (no travel, swallow, turbulence, ice, impairment I8, out-of-bounds,
monster, web, bars, rooted, trap) [src hack.c:2724-2838]; M1/M2 give exactly mᵢ; the only RNG on the path is
`exercise` (attribute counters). Movement points only change *when* the next command is read. ∎

**Theorem B.** I ∈ Push-1F ⇔ f(I) ∈ L_OFF (and ∈ L_OFF^W). (⇒) Lemma C. (⇐) Lemma S: if some play (R2: with some
outcomes) puts the hero alive on g_abs, then g is reachable in Push-1F. Pre-processed cases are correct by
construction (NO0: robot confined to {s, s+1}; YES0: hero starts on g). With [ext] Push-1F PSPACE-hardness and
Theorem A, **L_OFF^W is PSPACE-complete and L_OFF is PSPACE-hard.** ∎

## C. Answer-level DET for f's outputs
Claim: for every I, R2-answer(f(I)) = R3-answer(f(I)) = R1-answer for every seed = [Pr = 1] (R4, any θ ∈ (0,1]).
Proof. R2-yes ⇒ (Lemma S, which quantifies over all outcomes) Push-1F-yes ⇒ (Lemma C, which works for all outcomes)
a fixed command sequence wins against every outcome sequence (R3-yes, R1-yes for every seed, probability 1).
R2-no ⇒ no outcome sequence wins ⇒ all others no. RNG can neither help (Lemma S covers every outcome of prayer,
kicks, throws, exercise) nor hurt (Lemma C's play contains no RNG-dependent projection step). ∎
Note the game is not *strictly* deterministic (prayer, kicks are random) – only the answer is.

## D. Witness scripts (written, NOT run)
All in `tools/witness/`, harness pattern of `test/testmove.lua` (`des.reset_level` … `des.finalize_level`,
`nh.pushkey` + `nh.doturn(true)`), each with a **control** run that must behave differently, so a pass is informative.
| File | Checks | Control |
|---|---|---|
| `off_push_orth.lua` (W1) | orthogonal push moves boulder s→r, hero → s; push into wall is a no-op | – |
| `off_diag_push.lua` (W2) | diagonal push refused under Sokoban (hero and boulder stay) | no flag ⇒ diagonal push succeeds |
| `off_diag_squeeze.lua` (W3) | step between two corner boulders refused; with one free corner allowed | no flag ⇒ squeeze succeeds |
| `off_heavy_no_squeeze.lua` (W4) | heavy hero: blocked push, `m`-move, run never enter the boulder square | empty inventory ⇒ squeezes |
| `off_sentinel_pit.lua` (W5) | fill the only reachable pit; corner squeeze still refused (flag kept) | no sentinel ⇒ flag clears, squeeze succeeds |
Harness assumptions the scripts assert (error if false): hero lands on the start square; no stairways exist.

## E. Weakest steps (in order)
1. **[ext] Push-1F** citation, its exact model (reachability goal, bounded board) – external, not checked here.
2. **Groups U and X of §B.4** rest on entry-point reading of ~60 command handlers (cited lines show the gate that
   makes each a no-op); a second reader should open each handler once. The highest-risk ones are throw-with-ball
   (T1) and Punished movement (M6), both reachable only after divine anger.
3. **SC1**: the instance must be run via the harness order; otherwise the reduction is false (kit overwrite).
4. Lemma 2's "no unbounded RNG retry loop" [conj]; Lemma 1's [assump Q] log quotient.
5. Theorem A only for L_OFF^W; unrestricted L_OFF upper bound is open (thrones).
