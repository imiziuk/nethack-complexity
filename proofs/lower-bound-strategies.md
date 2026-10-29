# Lower-bound strategies: hardness gadgets for generalized NetHack reachability

Source: NetHack 5.0.0 (tag `NetHack-5.0.0_Released`, commit 16ff591), read-only at `src/`.
Paths below are relative to `src/` (e.g. `src/hack.c:432` = `src/src/hack.c` line 432).
Labels: **[src file:line]** = auto-extracted from source (read this session); **[external theorem]** = published
result (citation given; statements marked *verify* are from memory and must be checked against the paper before
use); **[LLM conjecture]** = my unproved claim.

Date: 2026-10-28. Author: hardness/gadget sub-agent (session 1).

---

## 0. Headline

1. **Crux answer (8-directional movement).** In a level with the `sokoban` flag, the hero may step diagonally
   only if at least one of the two orthogonal "corner" squares is not *bad rock* (wall/stone, or a boulder while
   Sokoban rules are on); diagonal pushes are refused. [src hack.c:1153-1171, 939-946, 953-979, 441-448]
   On a board whose only terrain is floor + wall + boulders, every legal diagonal step a->b can be replaced by
   two orthogonal steps through the free corner square, so **hero reachability equals 4-connected reachability and
   NetHack-Sokoban is step-for-step the Push-1F model** [LLM conjecture, proof sketch in §2.2]. The 8-directional
   movement does *not* break Push-1F-style reductions; it *does* leak around holes, pits, water and doorways
   (corner squares that are hazards but not bad rock).
2. **Second crux (found in source): the hero must be heavy and unable to drop weight.** A hero whose inventory
   is empty or weighs <= capacity-850 can *squeeze onto any boulder square* instead of pushing it (with the
   `m` prefix always, otherwise whenever the push fails). [src hack.c:139-140, 145-163, 304-308, 386-404;
   include/weight.h:24] Capacity is capped at 1000 [include/weight.h:25, hack.c:4329-4330], so carrying >150
   weight units that cannot be dropped (a **cursed loadstone**, weight 500 [include/objects.h:1600], cannot be
   dropped/thrown [src do.c:685-697]) permanently disables squeezing. Without such an item, any hero can drop
   everything and boulders stop being obstacles: the Push-1F reduction then fails outright.
3. **Ranked strategies** (details in §4):
   S1 PSPACE-hard via Push-1F (Ani et al. 2022) + simulation lemma: highest value, mostly cheap.
   S2 NP-hard via Push-1 / PushPush family (Demaine-Demaine-O'Rourke 2000) + same lemma: fallback.
   S3 Self-contained NP-hard via the Aloupis-Demaine-Guo-Viglietta Framework 1 with boulder/hole gadgets.
   S4 Sokoban "all holes filled" (Culberson-style) via the global `sokoban_rules` switch-off: speculative.
   S5 Light-hero model ("tokens and holes"): open, likely NP-hard.
   S6 EXPTIME (adversarial randomness, monsters): long shot.

---

## 1. Frameworks (external theorems)

Each entry: statement, hypotheses, citation. *verify* = recalled, check the exact wording before citing.

| # | Result | Model / hypotheses | Citation |
|---|---|---|---|
| F1 | **Sokoban is PSPACE-complete** | Robot on a grid, 4-directional moves, pushes one block at a time into an empty square, no pulling, fixed walls; goal = every block on a storage square. | [external theorem] J. Culberson, "Sokoban is PSPACE-complete", Proc. FUN 1998, Carleton Scientific, pp. 65-76 (U. Alberta TR 97-02, 1997). Alternative NCL proof: R. A. Hearn, E. D. Demaine, *Games, Puzzles, and Computation*, A K Peters 2009 (Sokoban section); NCL itself: Hearn-Demaine, TCS 343 (2005) 72-96. |
| F2 | **Push-1F is PSPACE-complete** | Push-k family: robot moves 4-dir in a square grid, may push a row of <= k movable blocks one square (here k=1), cannot pull; "F" = fixed (immovable) blocks allowed; question: can the robot reach a given target square. | [external theorem, *verify title/venue*] J. Ani, S. Asif, E. D. Demaine, Y. Diomidov, D. Hendrickson, J. Lynch, S. Scheffler, A. Suhl, "Pushing Blocks via Checkable Gadgets: PSPACE-Completeness of Push-1F and Block/Box Dude", FUN 2022, LIPIcs 226 (same group also has a separate paper on *pulling* blocks; do not confuse them). Uses "checkable gadgets" (a framework for reductions where gadgets may be left in bad states as long as a final check traversal detects it). |
| F3 | Push-1 and PushPush are NP-hard in 2D | Push-1 without fixed blocks; reachability goal. | [external theorem] E. D. Demaine, M. L. Demaine, J. O'Rourke, "PushPush and Push-1 are NP-hard in 2D", CCCG 2000, pp. 211-219. Also M. Hoffmann, "Push-* is NP-hard", CCCG 2000, pp. 205-210. |
| F4 | Push-2F is PSPACE-complete | Push up to 2 blocks, fixed blocks. | [external theorem] E. D. Demaine, R. A. Hearn, M. Hoffmann, "Push-2-F is PSPACE-complete", CCCG 2002, pp. 31-35. Not directly usable: NetHack never pushes two boulders in a row (src hack.c:435). |
| F5 | Sokoban/pushing variants | Several push/pull variants NP-hard or PSPACE-complete. | [external theorem, *verify which variants*] D. Dor, U. Zwick, "SOKOBAN and other motion planning problems", Computational Geometry 13(4) (1999) 215-228. |
| F6 | **Framework 1 (NP)** | Reduction from 3-SAT; game must provide: Start, Finish, Variable gadget (enter, irrevocably choose one of two exits, cannot later take the other), Clause gadget (can be "unlocked" by visiting from a literal path; later traversed along a check path only if unlocked), Crossover gadget (two paths cross without leaking), and paths connecting them. Avatar only needs to reach Finish. | [external theorem] G. Aloupis, E. D. Demaine, A. Guo, G. Viglietta, "Classic Nintendo games are (computationally) hard", TCS 586 (2015) 135-160 (FUN 2014). Generalizes G. Forisek, "Computational complexity of two-dimensional platform games", FUN 2010, LNCS 6099, 214-227 (metatheorems in terms of start/exit, long fall (one-way), crossover, and switch/door elements; *verify exact list*). |
| F7 | **Framework 2 (PSPACE)** | Reduction from TQBF; door gadget with three disjoint paths Open, Close, Traverse (Traverse passable iff open; Open path opens; Close path closes), plus crossover (or planarity tricks), start, finish. Doors must be *reusable* (open/close many times). | [external theorem] Aloupis-Demaine-Guo-Viglietta 2015 (as F6). |
| F8 | Viglietta metatheorems | MT1: location traversal (avatar must visit a set of locations) + single-use paths => NP-hard. Further metatheorems: tokens/toll roads => NP-hard; doors + pressure plates: P-/NP-/PSPACE-hard depending on how many plates operate each door and whether plates can close doors (*verify the exact case split*). | [external theorem] G. Viglietta, "Gaming is a hard job, but someone has to do it!", FUN 2012, LNCS 7288, 357-367; Theory Comput. Syst. 54(4) (2014) 595-621. |
| F9 | **Motion planning through gadgets** | 1-player: robot walks a network of k-tunnel gadgets with states. Locking 2-toggle, 2-toggle, door gadgets (open/close/traverse tunnels) => PSPACE-complete (also planar for many). Gadgets whose state graph is a DAG (each transition irreversible, bounded # of state changes) => reachability in NP; nontrivial ones NP-complete. Reversible deterministic k-tunnel gadgets: PSPACE-complete iff "interacting", else in NL. | [external theorem, *verify exact statements*] E. D. Demaine, I. Grosof, J. Lynch, M. Rudoy, "Computational complexity of motion planning of a robot through simple gadgets", FUN 2018, LIPIcs 100, 18:1-18:21; E. D. Demaine, D. Hendrickson, J. Lynch, "Toward a general complexity theory of motion planning: characterizing which gadgets make games hard", ITCS 2020, LIPIcs 151, 62:1-62:42. |
| F10 | Generalized geography | PSPACE-complete (planar too); basis for 2-player / adversarial variants. EXPTIME-completeness of certain unbounded 2-player games. | [external theorem] T. J. Schaefer, JCSS 16 (1978) 185-225; D. Lichtenstein, M. Sipser, JACM 27 (1980) 393-401; L. Stockmeyer, A. Chandra, SIAM J. Comput. 8 (1979) 151-174. |

Relevance: NetHack boulders cannot be pulled (no pull code path in `moverock_core`), so any single boulder's
movement is irreversible in direction. That makes "DAG gadgets" (F9, NP) the natural home, and PSPACE requires
either Push-1F's checkable-gadget machinery (F2) or reusable doors (F7), which plain pushing does not obviously give.

---

## 2. NetHack mechanics checked in source

### 2.1 Facts (all [src])

Pushing (`moverock_core`, src hack.c:348-638):
- P1. A push moves the boulder from s = hero+d to r = hero+2d, then the hero steps into s (`return 0` path).
  Push succeeds only if `isok(r)`, r not obstructed (wall/stone/tree), not iron bars, not a closed door, not a
  doorway entered diagonally, and **no boulder at r** [hack.c:432-435, 485-488]. So at most one boulder per
  push (Push-1); a boulder against a boulder does not move.
- P2. **Sokoban: no diagonal pushes** ("won't roll diagonally") [hack.c:441-448].
- P3. Monster on r blocks the push ("Perhaps that's why you cannot move it") [hack.c:455-483].
- P4. Levitation / air level: cannot push [hack.c:415-425]. Very small form: cannot push [hack.c:426-431].
- P5. Boulder onto traps: landmine (random, rn2(10)) [hack.c:505-529]; pit/spiked pit -> `flooreffects` fills it
  deterministically [hack.c:530-543, do.c:187-269]; **hole/trapdoor: boulder plugs it, trap deleted, boulder
  used up** [hack.c:544-566]; level/teleport traps move it away [hack.c:567-594]; rolling boulder trap launches
  it [hack.c:595-614].
- P6. Boulder into pool: fills with prob. 9/10 (water), 1/10 (lava), else sinks and vanishes
  [do.c:61-68]. **Random** -> avoid water/lava in deterministic gadgets.
- P7. When a push fails, `cannot_push`: a giant-form hero steps over; else if `could_move_onto_boulder` the hero
  **squeezes onto the boulder square** (Sokoban luck penalty only); else no move [hack.c:262-312].
- P8. `could_move_onto_boulder`: true if Passes_walls, giant (with a diagonal restriction), very small, or
  `squeezeablylightinvent()` = empty inventory or `inv_weight() <= -850` [hack.c:139-163; weight.h:24].
  `inv_weight() = total weight - weight_cap()` [hack.c:4351-4365]; `weight_cap() <= 1000` unless levitating /
  air level / strong steed (then exactly 1000) [hack.c:4311-4337; weight.h:25]. Hence carrying > 150 units
  never allows squeezing.
- P9. With the `m` prefix (`context.nopick`) toward a boulder the hero never pushes: squeezes if P8 holds, else
  "There is a boulder in your way" [hack.c:386-414].

Movement (`test_move`, src hack.c:991-1255):
- M1. Walls/stone/iron bars block [hack.c:1011-1073]. Doors: no diagonal moves into or out of an intact doorway
  [hack.c:1139-1150, 1207-1214].
- M2. **Diagonal step (dx,dy) is refused iff both (ux, uy+dy) and (ux+dx, uy) are `bad_rock` and the hero
  can't squeeze** [hack.c:1153-1171]. `bad_rock` = (Sokoban && boulder there) || (obstructed terrain the hero
  can't tunnel/phase) [hack.c:939-946]. `cant_squeeze_thru` for the hero: 0 if Passes_walls; 1 if big; 2 if
  total inventory > 600; **3 if Sokoban** [hack.c:953-979]. So under Sokoban rules a non-phasing hero can never
  cut a corner between two walls/boulders, regardless of weight.
- M3. Outside Sokoban, boulders are *not* bad_rock, so the hero always cuts diagonally between two boulders
  (and between a boulder and a wall); diagonal pushes are allowed. **The `sokoban` flag is essential.**
- M4. Moving into a boulder square runs `moverock()` [hack.c:1216-1230]; travel `_` never routes through
  boulders in Sokoban [hack.c:1234-1236]. Running and travel are macros over single steps.

Sokoban flag and holes:
- S1. A Lua level sets it with `des.level_flags("sokoban")` -> `svl.level.flags.sokoban_rules = 1`
  [sp_lev.c:3796-3797; rm.h:451, 538]. Other useful flags: `noteleport`, `hardfloor`, `nomongen`
  (`rndmongen = 0`), `solidify`, `premapped`, `nodeathdrops` [sp_lev.c:3772-3821].
- S2. **The flag is cleared when the last non-hero-made PIT or HOLE is removed** (`maybe_finish_sokoban`,
  called from `deltrap` only for PIT/HOLE, and when a trap is overwritten) [trap.c:7059-7095, 6546-6547,
  584-585]. After that, diagonal pushes and corner squeezes become legal (M3). With **zero pits/holes from the
  start, the flag is never cleared**. A sealed, unreachable PIT is a cheap "keep Sokoban rules forever" sentinel.
  TRAPDOOR and SPIKED_PIT do not count.
- S3. Hero onto a hole in Sokoban: no escape by levitation/flying; falls if `Can_fall_thru` [trap.c:613-634];
  `Can_fall_thru` = !hardfloor && !bottom level (or stronghold) [dungeon.c:1649-1665]. On a hardfloor or bottom
  level with non-diggable floor the hero **does not fall** ("don't fall in") [trap.c:635-655] -> a hole would
  then be harmless to the hero. Holes must be on a non-hardfloor, non-bottom level.
- S4. Hole destination: random depth `rn2(4)` loop [trap.c:442-453]; deterministic if the next level is the
  dungeon bottom. Landing spot after a fall is a random spot unless constrained by a level region
  [LLM conjecture: check `goto_level` / `u_on_rndspot` in do.c].
- S5. Boulders cannot be picked up in Sokoban [pickup.c:1713-1717]. Kicking a boulder does nothing
  [dokick.c:517-519]. Vanilla Sokoban's rule list (what is allowed / penalized / forbidden) is in the comment of
  every `dat/soko*.lua`, e.g. [dat/soko4-1.lua:10-32]; real Sokoban levels use
  `mazelevel, noteleport, (hardfloor), premapped, sokoban, solidify` [dat/soko4-1.lua:38; dat/soko1-1.lua:7].

Escape routes for a hero with only a cursed loadstone, no spells, no monsters:
- E1. Drop/throw/put the loadstone: refused while cursed [do.c:685-697; invent.c:1666].
- E2. Prayer: `stuck_in_wall()` (all 8 neighbours wall or unpushable boulder) is a major trouble fixed by a
  teleport [pray.c:161-181, 226-227]; cursed items are a (minor) trouble too. Prayer is "too soon" while
  `u.ublesscnt` > 200/100/0 and "too naughty" if Luck < 0, `u.ugangr` > 0 or alignment < 0 [pray.c:2152-2156].
  Initial `ublesscnt` = 300 [u_init.c:1005]. **The instance must neutralize prayer** (set `u.ugangr` >= 1, which
  nothing on a bare level can lower [LLM conjecture: check sacrifice-only reduction]) or the model must exclude
  `#pray`.
- E3. Hunger: `u.uhunger` starts at 900 [eat.c:129], decreases ~1/turn [eat.c:3174-3179]; death below
  -(100+10*Con) [eat.c:3437-3444]. With a fixed int this caps solution length at ~1100 turns, which would make
  the generalized problem trivially "no" for long solutions. **Generalized model: nutrition is an unbounded
  integer given in binary** (a 2^poly value is enough for PSPACE reductions), or hunger is switched off.
- E4. No other actions affect boulders without items/spells/polymorph: no #force target, kicking fails (S5),
  no digging tool, no jumping unless Knight/jumping boots (exclude roles with intrinsic Jumping), no
  teleport (`noteleport`), no random monsters (`nomongen`) [sp_lev.c:3812-3813; makemon.c:1168].
- E5. Exercise changes Str/Con over time (pushing exercises Str [hack.c:196-197]) -> capacity changes, but by P8
  a 500-weight stone keeps the hero non-squeezable for every capacity <= 1000.

### 2.2 Simulation lemma [LLM conjecture, proof sketch]

**Model NH-Soko(n).** w x h board (w,h poly in n; NetHack's fixed 80x21 map, `COLNO`/`ROWNO`, is lifted), terrain
in {floor (ROOM/CORR), wall/stone}, a set of boulders (at most one per square), hero position, target t.
Level flags `sokoban, noteleport, nomongen, solidify` (non-diggable, non-passwall). No traps, objects, monsters,
doors, water. Hero: a non-jumping role, unpolymorphed, not riding/levitating, inventory = one cursed loadstone,
no spells, prayer neutralized, unbounded nutrition. Question: can the hero stand on t?

**Lemma.** For every configuration (hero p, boulder set B), the NetHack successor configurations of NH-Soko are
exactly the Push-1F successors, up to replacing a diagonal step by two orthogonal steps.

Sketch.
1. Orthogonal step into a free floor square: same in both. Orthogonal step into a boulder: NetHack pushes iff
   the square beyond is floor without a boulder (P1; no monsters/traps/doors/pools so P3/P5/P6 are vacuous);
   otherwise the hero stays (P7 with P8 false). Same as Push-1F.
2. Diagonal step into a boulder square: never a push (P2) and never a squeeze (P8 false) -> no-op.
3. Diagonal step to a free square b from a: allowed iff some corner c in {(ax,by),(bx,ay)} is not bad rock
   (M2, case 3 because Sokoban). With the restricted terrain, "not bad rock" = floor without boulder, so
   a -> c -> b is a legal Push-1F path with no pushes and the same final configuration. Conversely Push-1F has
   no diagonal moves. Hence the reachable hero cells (between pushes) coincide with the 4-connected component.
4. `m`-prefix, travel, running add nothing (P9, M4). No other command changes (p, B) (E1-E5).
5. The Sokoban flag never turns off (S2: no pits/holes).
So Push-1F instance I (with its board surrounded by fixed blocks) maps in poly time to NH-Soko with the same
board, walls for fixed blocks, boulders for movable blocks, and t unchanged; answers coincide.

Consequence: Push-1F PSPACE-hard (F2) => NH-Soko PSPACE-hard [conditional on F2 and the model choices above].
Upper bound PSPACE is immediate for NH-Soko (poly-size configuration, nondeterministic search, Savitch).

Model warning (instance = Lua level only): a Lua special level cannot set hero inventory, luck, god anger or
nutrition [LLM conjecture: check `nhlua.c` / `sp_lev.c` for any hero-state setters]. A standard starting hero can
drop everything, becomes squeezable (P8), and then walks onto any boulder square: NH-Soko collapses (boulders
are no obstacles; only the Sokoban corner rule M2 remains). A cursed loadstone lying on the floor does not help
(picking it up is optional). So S1/S2 need **instance = full game state** (at least: inventory, `ugangr`,
nutrition), not just a level file. This should be fixed as a modeling decision with the PI.

---

## 3. Gadget candidates

All rows: status **CONJECTURE** (not machine-checked). "Heavy hero" = P8 false; Sokoban flag on.
Notation: `@` hero, `0` boulder, `^` hole, `#` wall, `.` floor.

| Gadget | NetHack realization | Intended behavior | Allowed states | Required / forbidden traversals | Known leaks | Status |
|---|---|---|---|---|---|---|
| G0 Push-1F board (whole reduction) | Push-1F instance verbatim: fixed blocks -> walls, blocks -> boulders | Exactly the Push-1F behaviour (Lemma 2.2) | all Push-1F states | as in the source reduction | light hero squeeze (P8); prayer teleport when boxed in (E2); hunger cap (E3); Sokoban flag cleared if any PIT/HOLE exists and gets filled (S2); doorways / water / traps break the corner argument | CONJECTURE (hinges on F2 + lemma) |
| G1 Plugged-hole bridge (one-shot enable) | corridor `# . 0 ^ . #` (hero enters from W) on a non-hardfloor level | W->E crossing possible once the boulder plugs the hole; then the corridor is permanently open both ways; from E the boulder cannot be pushed into the hole (no pulling) | {closed, open} DAG | open only by a W-side push; nothing re-closes it | hero cuts a corner around `^` diagonally if the corridor is not 1-wide with walls on both sides (holes are not bad rock, M2); falling = leaving level (S3/S4: random landing unless constrained); boulder can be pushed elsewhere first if side room exists | CONJECTURE |
| G2 Variable (irreversible choice) | junction where the entry push sends one boulder into one of two exit corridors and jams it there (dead-end pocket) | choose x or not-x once; the other exit is sealed by a jammed boulder | {unset, T, F} | after choosing T, F-exit must be impassable forever | the hero might go back and approach the jammed boulder from another side (needs all sides walled); diagonal corner-cut into the pocket (M2 forbids only if both corners blocked) | CONJECTURE, needs design + BFS check |
| G3 Clause (literal-unlocked gate) | three G1-style holes in a check corridor? or one hole on the check path with boulders deliverable from 3 literal paths | visiting from any true-literal path delivers a boulder into the clause hole; check path later crosses | {locked, unlocked} | literal paths must not leak into the check path or to each other | boulder delivered by one literal path could be re-routed to another clause; literal path entering clause area might reach check path directly | CONJECTURE |
| G4 Crossover | standard Push-1F / Sokoban crossover from F2 paper; or avoid via planar 3-SAT | two paths cross with no leak | n/a | no turning | corner-cutting at the crossing cell if built from boulders with free corners | CONJECTURE |
| G5 One-way (diode) | Sokoban-style diode from the push literature (DDO 2000 has Push-1 one-way gadgets) | W->E repeatedly, never E->W | stateless or 2-state | forbidden E->W | needs re-verification under 8-dir (use Lemma: OK if built only from floor/wall/boulders) | CONJECTURE |
| G6 Trapdoor / hole descent | hole or trapdoor on level k into level k+1 with no up stairs; arrival region constrained | true one-way edge between levels | stateless | none back | random destination depth (S4) unless next level is bottom; random arrival spot unless region constrained; TRAPDOOR does not count for S2 | CONJECTURE |
| G7 Global unlock (puzzle solved) | sealed area whose entrance is a diagonal gap between two boulders/walls; all PIT/HOLE squares of the level elsewhere | gap opens exactly when the last PIT/HOLE is filled (S2, M3) | {Sokoban on, off} | can't pass gap while any pit/hole remains | after flag off, diagonal pushes and corner-cutting appear everywhere (changes global dynamics); pits are crossable by the hero (only delay), holes are not | CONJECTURE |
| G8 Door (Framework 2) | no reusable door from boulders known to me; doors (#open/#close, locks) are reversible by the hero from both sides, not controlled remotely | open/close/traverse | {open, closed} | open/close only via their own paths | real NetHack doors can be opened/closed from any adjacent square -> not a door gadget | CONJECTURE (negative: probably unrealizable directly) |

---

## 4. Ranked lower-bound strategies

**S1 (ambitious, likely cheapest real result): PSPACE-hard, deterministic.**
- Target: NH-Soko reachability PSPACE-complete (upper bound trivial).
- Framework: F2 (Push-1F PSPACE-complete) + Lemma 2.2.
- Primitives: floor, walls, boulders, `sokoban` flag, heavy undroppable inventory.
- Source facts: P1, P2, P7, P8, M2, M3, S1, S2, E1-E5.
- Risks: (a) verify F2's exact model (robot reachability goal; 4-dir; boundary conventions; whether the robot
  may start adjacent to blocks); (b) the instance must be full game state (loadstone, prayer, nutrition);
  (c) map size generalization (COLNO x ROWNO fixed in the real game). (d) Any extra terrain in the Push-1F
  gadgets (there is none: Push-1F boards are floor/fixed/movable only).
- Randomness: none involved (no monsters, no traps); valid for every randomness variant.

**S2 (cheap sure thing A): NP-hard via Push-1 / Push-* (F3) + Lemma 2.2.**
- Same mapping; only needs the older, widely cited NP-hardness (CCCG 2000). Risk: those boards may assume an
  unbounded plane; enclose by walls far enough away [LLM conjecture: harmless since their gadgets are finite].
- Randomness: none.

**S3 (cheap sure thing B, self-contained): NP-hard via Framework 1 (F6) with irreversible boulder gadgets.**
- Variable = G2, Clause = G3, Crossover = G4 (or planar 3-SAT to avoid it), paths = 1-wide walled corridors,
  one-way = G5. All gadgets are DAG gadgets (F9) because boulders cannot be pulled -> natural NP fit.
- Primitives: boulders, holes (on a non-hardfloor level) or pits, walls.
- Source facts: P1, P2, P5 (holes/pits plug), S2 (keep a sentinel pit so the flag never clears), S3, M2.
- Risks: every corridor around a hole must be 1-wide between walls (else diagonal corner-cut around the hole);
  falling through a hole must be a loss (design the level below without a way back, or count leaving the level as
  failure); pits are not barriers for the hero (only delay). Needs a small BFS checker over gadget
  configurations (Push-1F rules + Sokoban corner rule + holes) to certify each gadget; suggest
  `tools/pushcheck.py` (pure simulation of the rules in §2.1, not the game).
- Randomness: none, if holes' destinations/landing are irrelevant (falling = loss).

**S4 (speculative): PSPACE via Sokoban-with-holes and the global unlock G7.**
- Idea: "reach t" iff "fill every hole/pit" (Culberson's storage goal, F1) using G7 as the final check.
- Problem: holes consume boulders and are uncrossable by the hero, storage squares are neither; Culberson's
  construction would need re-verification with sinks. Not recommended unless S1 fails.

**S5 (open): light-hero model (instance = Lua level only, standard starting character).**
- Hero can drop everything, then squeezes onto boulders at will (P8/P9); boulders are pushable tokens that never
  block the hero, holes block the hero until plugged, Sokoban corner rule still holds. Question: is
  "transport boulders into holes to open a path" NP-hard? Likely yes (tokens/toll-road flavour, F8) since a boulder
  can block another boulder's route and pushes are irreversible [LLM conjecture]. Worth one session if the PI fixes
  the Lua-only model.

**S6 (long shot): EXPTIME-hard, adversarial randomness.**
- Model random events (monster generation, monster moves, hole destinations, pool fills) as an adversary and ask
  whether the hero can force reaching t. Gadgets would need monsters as autonomous blockers (P3: a monster beyond a
  boulder blocks the push). Framework: F10 (Stockmeyer-Chandra style 2-player games). No source work done yet;
  monster AI is huge and hard to pin down. Only after S1/S3.

---

## 5. Crux questions for the source

1. (Answered) Does Sokoban forbid diagonal *movement*? Only corner-cutting between two bad-rock squares
   (hack.c:1153-1171, case 3 at 974-975); diagonal steps with a free corner are allowed. Diagonal *pushes* are
   forbidden (441-448).
2. (Answered) Can a hero squeeze past boulders? Yes, onto the boulder square, iff inventory empty or
   `inv_weight() <= -850` (hack.c:139-163, 304-308, 386-404). Cursed loadstone (500) blocks this for good.
3. Can a Lua special level set hero state (inventory, curse status, luck, god anger, nutrition)? Check
   `src/nhlua.c`, `src/sp_lev.c`, `dat/nhlib.lua`. Decides S1/S2 vs S5.
4. Prayer: confirm `u.ugangr > 0` makes every prayer fail without fixing troubles and that nothing on a bare level
   lowers `ugangr` (pray.c `prayer_done`, `angrygods`, `gods_upset`). Confirm `angrygods` cannot teleport/free
   the hero or remove the loadstone curse.
5. After a hero falls through a hole: where does he land (`goto_level`, `u_on_rndspot`, level regions in do.c)
   and can a Lua level fix the landing square? Can he return (stairs)? Decides G1/G6.
6. Are monsters ever created on a `nomongen` level without explicit `des.monster` (e.g. at level creation,
   `fill_ordinary_room`, special-level fixups, or the hero's starting pet)? The **starting pet** exists in a normal
   game: it can stand beyond a boulder (P3) and randomly block pushes. Model must remove it.
7. Does anything else clear `sokoban_rules` (save/restore, level change) besides `maybe_finish_sokoban`?
   (grep found only trap.c:7082 and sp_lev.c:3797.)
8. Do any role intrinsics or `#` commands available to a no-item hero move boulders or the hero through walls
   (e.g. Monk martial-arts kick of a boulder, `#turn`, `#sit`, `#monster` for racial forms)? dokick.c:517-519 says
   kicking a boulder never moves it; check the rest.
9. `blocked_boulder()` in pray.c:2677-2719 treats 2+ boulders on one square specially: confirm Push-1F instances
   never create stacked boulders (they cannot: P1 forbids pushing onto a boulder).
10. Rolling-boulder traps, landmines and pools are random or launch boulders: exclude them, or check whether a
    deterministic subset exists (e.g. rolling boulder trap with fixed launch points, hack.c:595-614).
