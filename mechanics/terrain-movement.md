# NetHack 5.0.0 — terrain and movement mechanics as gadget material

Source: `NetHack-5.0.0_Released` (16ff591), read-only tree at `src/`. All paths below are relative to
`src/` (so `src/hack.c` means `src/src/hack.c`; `dat/` and `include/` as shown). Every fact tagged
**[auto-extracted from source]** was read directly from the code at the cited line; line numbers are for this
checkout. Items tagged **[inferred]** are my reading of consequences and need a second look before a proof relies on them.
Nothing here uses the wiki or 3.6 memory. Note: 5.0 code is the 3.7 lineage (`svl.level.flags`, Lua level files in `dat/*.lua`).

Conventions: `rn2(n)` = uniform 0..n-1; `rnl` = Luck-adjusted rn2 (Luck is changed by Sokoban "guilt"); "det." = deterministic
given the move sequence (no RNG call on that path); "RNG" lists the calls.

---------------------------------------------------------------------------------------------------------------------

## 0. Terrain type order (everything below keys off this) [auto-extracted from source]

`include/rm.h:55-100` — `STONE VWALL HWALL TLCORNER ... DBWALL TREE SDOOR SCORR | POOL MOAT WATER DRAWBRIDGE_UP LAVAPOOL LAVAWALL IRONBARS | DOOR CORR ROOM STAIRS LADDER FOUNTAIN THRONE SINK GRAVE ALTAR ICE DRAWBRIDGE_DOWN AIR CLOUD`.

* `IS_OBSTRUCTED(t) = t < POOL` (rm.h:119): stone, all walls, DBWALL, **TREE, SDOOR, SCORR** are "rock" (a boulder can never be pushed into them; secret doors/corridors count).
* `IS_STWALL(t) = t <= DBWALL` (rm.h:118). `ACCESSIBLE(t) = t >= DOOR` (rm.h:125). `IS_FURNITURE = STAIRS..ALTAR` (rm.h:138).
* `DRAWBRIDGE_UP` (the span square of a raised bridge) and all water/lava/bars are `>= POOL`, so they are NOT obstructed for the boulder-destination test; IRONBARS is excluded separately (hack.c:433).
* Per-square flag bits: `W_NONDIGGABLE 0x08`, `W_NONPASSWALL 0x10` (rm.h:301-302); `D_NODOOR 0, D_BROKEN 1, D_ISOPEN 2, D_CLOSED 4, D_LOCKED 8, D_TRAPPED 0x10` (rm.h:233-239). D_LOCKED aliases W_NONDIGGABLE and D_TRAPPED aliases W_NONPASSWALL (rm.h:207-209) — they never coexist because one is for doors and the other for walls.
* Level-wide flags: `Sokoban = svl.level.flags.sokoban_rules` (rm.h:538), `noteleport`, `hardfloor` (set by `des.level_flags`, sp_lev.c:3774-3797).

---------------------------------------------------------------------------------------------------------------------

## 1. Boulders

### 1.1 Exact push rule (hero, ordinary levels) — `moverock_core`, src/hack.c:348-640 [auto-extracted from source]

Called from `test_move(..., DO_MOVE)` when `sobj_at(BOULDER, x, y) && (Sokoban || !Passes_walls)` (hack.c:1216-1224). Hero is at `(ux,uy)`, boulder at `s=(ux+dx,uy+dy)`, destination `r=(ux+2dx,uy+2dy)`. Loops over *every* boulder on `s` (`while sobj_at`, hack.c:353).

Order of checks (first failing check decides):
1. `m<dir>` (`context.nopick`) never pushes: giants step over, light/small squeeze, everyone else "boulder in your way" (hack.c:380-410).
2. `Levitation || Is_airlevel` → "not enough leverage", **cannot push** (hack.c:415-422). Flying (non-levitating) is not excluded here.
3. `verysmall(youmonst.data) && !u.usteed` → "too small to push" → `cannot_push()` (hack.c:426-430).
4. Destination must satisfy all of (hack.c:432-435):
   * `isok(r)`; `!IS_OBSTRUCTED(levl[r].typ)` (no wall/stone/tree/SDOOR/SCORR); `typ != IRONBARS`;
   * `!IS_DOOR(r) || !(dx && dy) || doorless_door(r)` — **diagonal push into any door square is forbidden unless the doorway has no door or a broken door** (open doors block diagonal pushes; `doorless_door` = `doormask` ⊆ {D_NODOOR, D_BROKEN}, hack.c:4063-4074);
   * `!sobj_at(BOULDER, r)` — **boulder cannot be pushed onto another boulder** (and so a stack of n≥2 boulders on s can move at most the top one; the next iteration finds r occupied).
   * objects, statues, furniture (stairs, altar, fountain, throne, ...) at r do **not** block; traps are handled below.
5. If Sokoban and diagonal: refuse (hack.c:442-448, "won't roll diagonally").
6. `revive_nasty(r)` (a Rider/cockatrice-type corpse revives) → blocked (hack.c:450).
7. A monster at r blocks unless `noncorporeal(mtmp->data)` or the monster is **trapped in a pit at r** (hack.c:456-483). Invisible/hidden monsters block too. [pets and peacefuls block]
8. `closed_door(r)` (D_CLOSED or D_LOCKED) blocks (hack.c:485); an **open** door square (orthogonal push) does not block.
9. Trap at r (`switch (ttmp->ttyp)`, hack.c:500-617): see 1.2.
10. `boulder_hits_pool(otmp, r, TRUE)` (do.c:50) if r is pool/moat/lava/water: see 1.3.
11. Otherwise `dopush()` moves the boulder (`movobj`, hack.c:166-244). No RNG on a plain push. Push message throttle uses `moves` only.

If any check fails: `cannot_push()` (hack.c:262): giants step over (Sokoban: `sokoban_guilt()`), else `could_move_onto_boulder()` lets you squeeze onto the boulder's square, else the move fails (-1). Squeezing condition (hack.c:145-163): `Passes_walls`, or giant (not into a diagonal squeeze), or `verysmall`, or `!invent || inv_weight() <= -WT_SQUEEZABLE_INV(=850)` (include/weight.h:24), i.e. carrying essentially nothing. Cannot squeeze while riding.

Reversible? The push is reversible only if the player can get to the opposite side and push back (no direct "pull"). Blocking squares = rock, bars, closed doors, another boulder, monsters. Deterministic: yes except where noted in 1.2/1.3. Resource: none. Repeatable: unlimited.

### 1.2 Boulder meets a trap at the destination (hack.c:500-617) [auto-extracted from source]

| trap at r | effect on boulder | trap after | RNG | notes |
|---|---|---|---|---|
| PIT / SPIKED_PIT | `flooreffects(..., "fall")` → boulder is consumed (`useupf`), `bury_objs` (do.c:188-266) | trap deleted (`delfloortrap`) | none | if a monster is trapped there it takes `hmon`/`dmgval` damage and is freed; boulder is consumed regardless (do.c:190-262). If the *hero* is in that pit `rnd(15)` squish damage (do.c:233). |
| HOLE / TRAPDOOR | boulder "plugs" it; `deltrap`, `useupf`, `bury_objs`, **`levl.candig=1`, W_NONDIGGABLE cleared** (hack.c:544-566) | trap deleted | none | works for trap doors too; `deltrap` → `maybe_finish_sokoban` only fires for PIT/HOLE (trap.c:6546). |
| LANDMINE | `rn2(10)` (90%): boulder lands on r, `blow_up_landmine` (mine becomes a PIT), `fill_pit(u.ux,u.uy)`; 10%: boulder passes over (hack.c:505-529) | 90%: mine → pit | rn2(10) hack.c:506 | non-deterministic |
| LEVEL_TELEP | `random_teleport_level()`; if result == current depth boulder moves normally, else boulder migrates to another level (hack.c:567-594) | trap persists (boulder, not hero) | rn2(5) + rn2(...) in teleport.c:2191-2233 | |
| TELEP_TRAP | `rloco()` random relocation on the level (hack.c:578-590; teleport.c:2102) | persists | rn1/rn2 loop up to 4000 tries | may land in a pit/pool and be consumed (flooreffects) |
| ROLLING_BOULDER_TRAP | boulder is *launched* along the push direction to the trap's launch point/edge (hack.c:595-616) | persists | none in the push itself | |
| any other (web, bear trap, squeaky board, magic portal, vibrating square, ...) | boulder just moves onto it; trap unaffected (`default: break`) | persists | none | |

### 1.3 Boulder into water / lava (do.c:50-151) [auto-extracted from source]

`chance = rn2(10)` (do.c:61). `fills_up = Is_waterlevel ? FALSE : IS_WATERWALL ? chance<5 : lava ? chance==0 : chance!=0` (do.c:66-68).
So pool/moat (and the moat under a raised drawbridge) fills with probability 90%, lava 10%, wall-of-water 50%, Plane of Water never. Fill: `typ = ROOM` (or `DB_FLOOR` for a DRAWBRIDGE_UP span), any monster there is killed unless it flies, trap deleted, objects buried, boulder consumed. Failure: boulder is consumed anyway ("sinks without a trace"), pool stays. **So each push into water costs one boulder with prob. 1; water is converted with prob. 0.9.**

### 1.4 Squeezing, diagonals, and Sokoban movement restrictions [auto-extracted from source]

* Diagonal tight-squeeze test (`test_move`, hack.c:1153-1176): if moving diagonally and **both** orthogonal neighbours are `bad_rock`, call `cant_squeeze_thru` (hack.c:953-978): returns 1 if `bigmonst` (unless amorphous/whirly/noncorporeal/slithy/can_fog), 2 if `inv_weight()+weight_cap() > WT_TOOMUCH_DIAGONAL(=600)` (include/weight.h:22), 3 if Sokoban (hero only). `Passes_walls` always squeezes.
* `bad_rock(mdat,x,y)` (hack.c:939-945): `(Sokoban && boulder at x,y)` **or** an obstructed square the monster cannot tunnel/dig/phase. So **boulders only count as squeeze-blockers when the Sokoban flag is set** — outside Sokoban a hero (or monster) can slide diagonally between two boulders.
* Diagonal into a door square forbidden unless `doorless_door` and no shopkeeper block (hack.c:1141-1150); diagonal *out of* a door square likewise (hack.c:1209-1214). Applies to hero and boulders (boulder via 1.1.4). Monsters: same rule in `mfndpos` (mon.c, ~2290-2345; `bad_rock` squeeze test at mon.c:2345).
* Sokoban flag effects: no diagonal boulder push (hack.c:442); diagonal squeeze past 2 boulders/walls forbidden (hack.c:973-975, case 3); `could_move_onto_boulder` still allowed but each squeeze/step-over calls `sokoban_guilt()` = `u.uconduct.sokocheat++; change_luck(-1)` (trap.c:7039-7052; hack.c:299,307,398,403); travel never routes through boulders (hack.c:1234-1236); pits/holes are inescapable even when levitating/flying and for monsters (trap.c:1970,2031,3015, dothrow.c:955); hero cannot pick up boulders (pickup.c:1713); jump/hurtle stops at a pit/hole (dothrow.c:955-962); rolling-boulder traps are not generated there (trap.c:3610, 2820).
* **Sokoban flag is cleared permanently the moment the last non-hero-made PIT or HOLE on the level is deleted** (`maybe_finish_sokoban`, trap.c:7059-7097, called from `deltrap` trap.c:6546 and from `maketrap` overwrite trap.c:584). After that all restrictions above (including diagonal push) vanish. SPIKED_PIT, TRAPDOOR are *not* counted.
* Level files: all 8 `dat/soko*.lua` use `level_flags("mazelevel","noteleport","premapped","sokoban","solidify")` and `des.non_diggable(whole map)`, `des.non_passwall(whole map)` (e.g. dat/soko1-1.lua:7,36-37); only `soko4-*` (entry level) also have `hardfloor` (dat/soko4-1.lua:~30).

### 1.5 Breaking / creating / moving boulders (not pushing) [auto-extracted from source]

| action | effect | source | Sokoban penalty |
|---|---|---|---|
| force bolt / wand of striking | boulder → `ROCK` stack of `rn1(60,7)` rocks (`fracture_rock`) | zap.c:2275-2290, 5537-5565 | `sokoban_guilt()` (zap.c:5555) |
| pick-axe/mattock applied toward boulder (`DIGTYP_BOULDER`) | after effort>100 the boulder fractures | dig.c:180-186, 455-462 | via `fracture_rock` (guilt) |
| digging a hole under a boulder | "KADOOM": boulder and hole both vanish (dig.c:942-958) (50%: if pit already there, boulder settles & becomes PIT w/ rn2(2)) | dig.c:942-958 | none |
| wand of digging zapped sideways | does NOT touch boulders (zap_dig has no boulder case, dig.c:1548-1754) | | none |
| stone-to-flesh / polymorph on boulder | boulder → meatball / other; "if left in liquid it fractures" | zap.c:1710, 1953-1960, 2014 | `sokoban_guilt()` (zap.c:1711) |
| scroll of earth | up to 8 new boulders around hero + 1 on hero (uncursed), `rn1(5,2)` rocks if confused | read.c:1919-1968, 2294-2360 | `sokoban_guilt()` (read.c:1951) |
| wand of teleportation / teleport trap | `rloco` random relocation | zap.c:2321-2326; teleport.c:2102 | none (permitted per dat/soko4-1.lua header) |
| giant (polymorphed hero) | picks up boulder (not in Sokoban) or steps over it | pickup.c:1713-1722; hack.c:262-300 | step-over → guilt |
| giant monsters | pick up (`!Sokoban`), throw boulders; `ALLOW_ROCK` | monmove.c:1023; mon.c:2093-2095 | |
| shopkeeper/priest/quest leader/Rider | break boulders in their way (`m_can_break_boulder`) | monmove.c:133-170 | |
| rolling boulder trap | launched boulder rolls, breaks closed doors (door becomes D_BROKEN), fills pits/holes/pools, hits other boulders and chains them, stops at walls/bars | trap.c:3260-3578 | |
| melting ice under a boulder | boulder falls in → `boulder_hits_pool` | zap.c:5064-5072 | |

Giant/jump interplay: jump path rejects squares with boulders unless `throws_rocks` (apply.c `check_jump` ~1870).

### 1.6 Summary row: boulder

| field | value |
|---|---|
| name | movable block (boulder) |
| trigger | hero moves orthogonally toward it (diagonal allowed outside Sokoban if destination not a door-with-door) |
| state change | boulder position moves 1; or boulder consumed (pit/hole/trapdoor/pool/lava/teleport) |
| reversible? | push: only by walking around; consumption: no |
| deterministic? | yes for floor/pit/hole/trapdoor/ordinary traps; RNG for water 90% (do.c:61), lava 10%, landmine rn2(10) (hack.c:506), level-tele/tele traps |
| resources | boulder (consumed when it fills something); no player resource |
| repeatable? | pushes unlimited; each fill consumes a boulder |
| scalable to arbitrary maps? | yes, board is just `levl[][]`; no hardcoded size besides COLNO=80/ROWNO=21 |
| source | hack.c:moverock_core:348-640, do.c:boulder_hits_pool:50, do.c:flooreffects:162 |
| breakers | see "Gadget killers" |

---------------------------------------------------------------------------------------------------------------------

## 2. Doors [auto-extracted from source]

States: `NODOOR(0) BROKEN(1) ISOPEN(2) CLOSED(4) LOCKED(8)` (+TRAPPED 0x10 flag) (rm.h:233-239); SDOOR is a secret door shown as wall (rm.h:14 enum; `IS_OBSTRUCTED`).

| action | transition | RNG | resource | reversible? | source |
|---|---|---|---|---|---|
| `#open` / walk into closed door (autoopen) | CLOSED → ISOPEN (TRAPPED: → NODOOR + explosion) | `rnl(20) < (STR+DEX+CON)/3` (fails w/ "door resists", may retry) | none | yes (close) | lock.c:904 |
| LOCKED door `#open` | no change ("This door is locked") | det. | | | lock.c:~851 |
| `#close` | ISOPEN → CLOSED | `rn2(25) < (STR+DEX+CON)/3` (always for steed rider) | none | yes | lock.c:1039; fails if a monster **or any object** is on the square (`obstructed`, lock.c:926-955) → a boulder on an open door prevents closing |
| key/pick/card (apply) | LOCKED ↔ CLOSED | per-turn `rn2(100) >= chance` (lock.c:98), `usedtime++ >= 50` gives up; chance e.g. key `70+DEX`, pick `3*DEX`, card `2*DEX` (+Rogue bonus) (lock.c:628-640) | none (tools not consumed) | yes (relock with key/pick; card cannot lock) | lock.c:68-160, 358-640 |
| kick | CLOSED/LOCKED → BROKEN (or NODOOR if STR>18 && !rn2(5)); TRAPPED → NODOOR+explosion | `rnl(35) < avrg_attrib (+DEX for martial)` (dokick.c:930); `!rn2(5)` (dokick.c:940); Levitation cannot kick door open (dokick.c:919) | HP risk via kick_ouch | **irreversible** except wand of locking/wizard lock (re-locks a BROKEN door, lock.c:1161-1163) | dokick.c:909-960 |
| wand of opening / spell of knock | LOCKED → CLOSED (never opens); SDOOR → CLOSED door | det. | wand charge/Pw | yes | lock.c:1103-1135, 1195-1200 |
| wand of locking / wizard lock | CLOSED/ISOPEN/BROKEN/NODOOR → LOCKED (adds a door to an empty doorway!) | det.; fails if object/monster on square or **any trap** at the doorway (lock.c:1141-1156) | charge/Pw | yes (unlock) | lock.c:1135-1190 |
| wand of striking / force bolt | CLOSED/LOCKED → BROKEN (TRAPPED → NODOOR + explosion, loudness 40); SDOOR revealed first | det. | charge/Pw | irreversible except relock | lock.c:1201-1250 |
| wand of digging (horizontal zap) | closed door or SDOOR → NODOOR ("razed") | `digdepth=rn1(18,8)` range only | charge | irreversible except wizard-lock/wand of locking | dig.c:1669-1683 |
| pick-axe/axe applied | CLOSED door → BROKEN (SDOOR → BROKEN door) after effort>100 | `10+rn2(5)+...` per turn | time | irreversible | dig.c:436-482 (axe dig_typ DIGTYP_DOOR dig.c:174) |
| `#force` | **only boxes/chests; NOT doors** (lock.c:676-757, "TODO: allow force on doors" comment lock.c:684) | | | | |
| hero passes door diag | forbidden unless NODOOR/BROKEN (`doorless_door`) | | | | hack.c:1141, 1209 |
| closed door passage | `Passes_walls` or `can_ooze` (amorphous) pass; tunnelers eat it | | | | hack.c:1075-1092 |
| rolling boulder | closed door → BROKEN | | | | trap.c:~3548 |
| search | SDOOR → door if `!rnl(7 - fund)` per adjacent square per search | rnl | time | one-way (reveal) | detect.c:2016-2060 |

Reversibility summary: OPEN↔CLOSED↔LOCKED is a 3-state switch fully reversible by hero with keys/spells; BROKEN/NODOOR are absorbing states unless the hero owns a wand of locking/wizard lock (lock.c:1161-1190), which can rebuild *any* doorway into LOCKED. Boulders on a door square keep it open.

---------------------------------------------------------------------------------------------------------------------

## 3. Traps relevant to topology [auto-extracted from source]

General rules
* **Known-trap escape**: hero walks onto a `tseen` trap and escapes with `!rn2(5)` (20%) unless Fumbling/forcetrap/plunged/conjoined pit; **not** for Sokoban pits and holes, and not for `fixed_tele_trap` (trap.c:3009-3041). So hero-trap interaction is *non-deterministic by default*; hero can also `#sit`/plunge deliberately (`>` on pit/trapdoor → TOOKPLUNGE, do.c:1238-1245).
* `immune_to_trap` (trap.c:2783-2935): levitation/flying hero evades ground traps (pit, hole, trapdoor, bear trap, squeaky board, landmine (partly), rolling boulder) **except pits/holes in Sokoban** (trap.c:2818). Level/teleport traps are never evadable except by Antimagic (tele) or endgame.
* Traps cannot be created on stairs/ladders (maketrap, trap.c:464-468: `!CAN_OVERWRITE_TERRAIN`), on pool/lava, or on furniture except PIT/HOLE; level teleporter not allowed in single-level branch.
* `maketrap()` (trap.c:456-590). Hole/trapdoor destination fixed at creation by `hole_destination` (trap.c:442-453): starts at current level+1, each extra level with `rn2(4)` nonzero stops → **25% chance per level to fall deeper** (RNG at creation, not at fall).

| trap | trigger | state change | reversible? | deterministic? | resources | repeatable? | scalable | source | exploits / interactions |
|---|---|---|---|---|---|---|---|---|---|
| Pit / spiked pit | step on (known: 80% fall; unknown: 100%); monsters fall unless flying; Sokoban: all fall | hero `set_utrap(rn1(6,2))` (2..7 escape turns) | pit stays; boulder fills it (consumable) | fall det. except 20% known-trap escape; escape counter `rn1(6,2)` at trap.c:1920; `--u.utrap` per move (hack.c:1580, trap.c:4183-4230) | boulder consumed to fill | until filled | yes | trap.c:1825-1960 | dig-down by hero makes pit (madeby_u so doesn't count for Sokoban completion, trap.c:7066); pit can be climbed out (passes adjacent pits "conjoined") |
| Hole | step on; always visible (`unhideable_trap(HOLE)`, trap.h:115) | hero → level+1 .. (fixed dst) random arrival spot (`u_on_rndspot`, do.c:1804, dungeon.c:1605); trap persists | **one-way** (arrive at random location; must find stairs back) | fall det. (Sokoban/holes inescapable), landing random | none | unlimited until plugged | yes | trap.c:2013-2060; fall_through trap.c:602-724 | plug with boulder (hack.c:544); levitation/flying avoid it outside Sokoban; `Can_fall_thru` (dungeon.c:1662) must hold |
| Trap door | same as hole but may be hidden | same | one-way | same | | | yes | trap.c:2013 (same fn) | `>` while on a seen trapdoor jumps in deliberately (do.c:1238) |
| Level teleporter | step on | **trap deleted** (hero) then `level_tele()` (random level unless Teleport_control; none in Sokoban/with Amulet/endgame) | no (trap used up for hero; boulders/monsters leave it) | RNG: `rn2(5)` same-level 20%, `rn2(cur_depth+3-min)`... (teleport.c:2191-2233) | trap | single-use for hero | | teleport.c:1538-1575; trap.c:2088-2104 | Antimagic blocks (non-intentional); noteleport levels: `level_tele` aborts in Sokoban (teleport.c:1185) |
| Teleport trap | step on | hero moved to random legal spot (`safe_teleds`, 40 random tries then ring scan), or **fixed destination** if `teledest` set (des-file trap), or `once` flag → vault | no | random unless `fixed_tele_trap` (trap.h:125) where it is fully deterministic and cannot be resisted (trap.c:3009) | | unlimited | yes | teleport.c:1492-1535; safe_teleds teleport.c:717-770 | Antimagic or `noteleport_level` ("wrenching sensation"); `tele_jump_ok` forbids crossing special-level restricted regions |
| Magic portal | step on (needs adjacent pets `next_to_u`, not just arrived via portal) | hero → `trap->dst` (fixed) with 3-turn stun | reversible (portal back exists on target) | det. | | unlimited | no — only created by special levels or `mktrap` using `u.ucamefrom` (mklev.c:~2080); `undestroyable_trap` (trap.h:116) | teleport.c:1444-1482 | cannot be dug/destroyed; cannot be created on DRAWBRIDGE_UP |
| Web | step on; stuck `tim` from STR (rnd/…) | `u.utrap` | web persists; destroyed by fire, STR≥69 etc., mu_maybe_destroy_web (trap.c:972) | RNG | | | yes | trap.c:2106-2278 | Sokoban webs restricted (monmove.c:1250-1308) |
| Bear trap | step on | `set_utrap(rn1(4,4))` | can be disarmed (#untrap) | RNG | | | | trap.c:1479-1560 | `(dx&&dy) || !rn2(5)` decrements escape (hack.c:1565) |
| Landmine | step on / boulder push | explodes → becomes PIT | no | RNG `rnd(16)` damage; boulder push rn2(10) | | single-use | | trap.c:2528-2660 | ok |
| Rolling boulder trap | step on | launches the boulder stored at `launch` along line to `launch2` | boulder ends elsewhere | placement random at creation (`find_random_launch_coord` uses rn1(5,4) and rn2(N_DIRS), trap.c:3599-3656) | boulder | until boulder is not at launch point | | trap.c:2661-2708, 3260-3578 | immune/non-generated in Sokoban (trap.c:2820, 3610) |
| Squeaky board | step on | wakes nearby monsters only | persists | det. effect (note chosen at creation) | | | | trap.c:1403-1478 | irrelevant for topology |
| Magic trap | step on | `rnd(20)` table: monsters, light, deafness, `!rn2(30)` self-destruct | | RNG | | | | trap.c:2293-2320, 4317-4450 | |
| Vibrating square | step on in Gehennom bottom | triggers invocation | | | | | | trap.c:2725 | undestroyable |

Trap generation is RNG (level-creation `rn2`s inside `mktrap`, mklev.c:2036-2150: `traptype_rnd`, `somexyspace`, `rnd(4)` victim). In hand-written Lua level files traps are placed explicitly (`des.trap("pit",x,y)`), hence deterministic for a constructed instance. **Whether a trap exists is determined by the level, not the hero's turn counter.**

---------------------------------------------------------------------------------------------------------------------

## 4. Stairs, ladders, portals, teleport and levelport restrictions [auto-extracted from source]

* Stairs/ladders: `stairway_at` (`dodown`, do.c:1131-1297; `doup`, do.c:1298-). Reversible (stairs lead to the matching stairs on the other level); `u_stuck_cannot_go`, `next_to_u` (adjacent pets can be held back, do.c:1204), steed, Levitation (do.c:1160-1197), Amulet restrictions (up). No traps can be created on stairs. `dig_check` forbids digging on stairs/ladders (dig.c:211-218).
* Arrival after trapdoor/hole/levelport = `u_on_rndspot` random location (do.c:1804); after stairs = at the connecting stairs.
* `noteleport_level()` (teleport.c:30-47): `svl.level.flags.noteleport` (not for covetous monsters), Gehennom demon-lord court, wand-of-stasis timer. Files with `noteleport` (grep dat/): all Sokoban levels, Wizard's Tower and its 3 levels, Medusa 1-4, Castle, Valley, Knox, Sanctum, elemental planes/Astral, many quest start/goal levels, Vlad's tower floors.
* Level teleport: `level_tele()` refuses if `u.uhave.amulet || In_endgame || In_sokoban` (teleport.c:1185). `random_teleport_level` RNG: `!rn2(5)` same level; target `rn2(cur_depth+3-min_depth)+min_depth` skipping current (teleport.c:2191-2233).
* Controlled teleport (Teleport_control or blessed scroll, not Stunned): `teleok()` conditions — non-trap (or levitating/flying onto pit/hole), `goodpos` (so **not a boulder square**, teleport.c:178, and not water/lava unless allowed), `tele_jump_ok`, `in_out_region` (teleport.c:420-445, 842-916). Gets `!rn2(3)` "disoriented" failure if carrying Amulet or on Wizard-tower level (teleport.c:865).
* Uncontrolled hero teleport: `safe_teleds` tries 40 random squares then expanding ring (teleport.c:717-770).

---------------------------------------------------------------------------------------------------------------------

## 5. Digging [auto-extracted from source]

* Tool → what is dug (`dig_typ`, dig.c:169-193): pick/mattock: statue, boulder, closed door, rock/wall (not trees); axe: closed door, tree. Anything else `DIGTYP_UNDIGGABLE`. `autodig` option lets a wielded pick auto-dig when walking into rock (hack.c:1032-1040).
* `may_dig(x,y)` = not `((IS_STWALL||IS_TREE) && W_NONDIGGABLE)` (hack.c:923-929). Used by `dig()` (dig.c:316-330) and `zap_dig` (dig.c:1711-1713, maze branch dig.c:1684-1710 prints "wall glows then fades"). IRONBARS and DBWALL: bars `W_NONDIGGABLE` honored; drawbridge wall `lev2->wall_info = W_NONDIGGABLE` (dbridge.c:~797).
* Horizontal pick dig timing: `effort += 10 + rn2(5) + abon + spe - erosion + udaminc` per turn (dwarves ×2); wall/rock/door done at `effort > 100`, boulder also > 100 (dig.c:366, 440). Results: stone → CORR; wall → ROOM (maze level) / CORR (cavernous) / DOOR(no door); SDOOR → BROKEN door; tree → ROOM; closed door → BROKEN (dig.c:436-540).
* Dig down: `effort > 250` → `dighole` (dig.c:372-376). `dig_check` (dig.c:207-253): fails on stairs, ladder, throne, altar (except by object), air/water level, `W_NONDIGGABLE` obstructed squares, undestroyable traps; `!Can_dig_down && !candig` ⇒ pit only (or destroys non-pit/hole trap); **boulder on square ⇒ cannot dig** (DIGCHECK_FAIL_BOULDER).
* `Can_dig_down(lev) = !hardfloor && !Is_botlevel && !Invocation_lev` (dungeon.c:1649-1654); `Can_fall_thru = Can_dig_down || Is_stronghold`.
* `dighole()` (dig.c:885-1025): hole in pool/lava → "sloshes"; drawbridge square: destroy bridge; boulder: KADOOM; grave: pit + zombie; `fillholetyp` (dig.c:606-637) makes the hole fill with adjacent moat/pool/lava with probability `rn2(cnt+1)` stuff (pool count /3 unless `fill_if_any`) → terrain can flip to POOL/MOAT/LAVAPOOL; otherwise `digactualhole` makes PIT or HOLE. Holes made by hero (`madeby_u`) do not count for Sokoban solution and are escapable.
* Wand of digging (`zap_dig`, dig.c:1548-1754): down → `dighole(FALSE,TRUE)` (hole; also disarms/explodes magical traps); sideways → range `digdepth = rn1(18,8)` (8..25), costs 2 per wall/door; stone→CORR; passes boulders without affecting them (no boulder code); in maze levels (is_maze_lev) walls → ROOM; nondiggable walls stop the beam.
* Digging for monsters: `mdig_tunnel` (dig.c:1414-1502).
* Levels where digging is prohibited (data): all Sokoban levels `non_diggable` entire map (dat/soko*.lua); `hardfloor` set in dat/soko4-*.lua, wizard1-3, tower1-3, valley, sanctum, air/water/fire/earth/astral, quest start/locate levels, etc. (grep `hardfloor` dat/*.lua).
* Reversible? No: dug stone/walls are never restored by the game (no "refill" except `mkcavearea` on earth plane and boulder/fill of holes). Walls can be re-created only by ice→wall for lavawall (zap.c:5249) or `Is_earthlevel` caves.

---------------------------------------------------------------------------------------------------------------------

## 6. Water, lava, ice, drawbridge, bars, trees, furniture [auto-extracted from source]

| mechanic | trigger | state change | reversible | RNG | source |
|---|---|---|---|---|---|
| pool/moat filled by boulder | push (1.3) | POOL/MOAT → ROOM (drawbridge span: `DB_FLOOR`) | no (new pool only via dig hole filling `fillholetyp` or ... digging next to water) | 90%/10% | do.c:50-151 |
| wand/spell of cold at pool/moat/lava | zap | POOL→ICE (`ICED_POOL`), MOAT→ICE, LAVAPOOL→ROOM, LAVAWALL→wall, WATER stays; ice gets **melt timer** | ice melts again (see below) | `start_melt_ice_timeout`: `rn2` loop with window 50..2000 turns; if no roll succeeds before 2000 turns ice is permanent (zap.c:5081-5111); lavawall freezes with prob `1-1/chance` (zap.c:5240) | zap.c:5238-5305, 5088-5112 |
| ice melts | timer or fire zap | ICE → POOL/MOAT; items on it fall; boulder on it falls in via `boulder_hits_pool` (90% fill!) | yes | timer | zap.c:5040-5075 |
| fire zap at pool | POOL → ROOM + PIT (steam) (only plain POOL; MOAT/water level only evaporate message) | no | none | zap.c:5190-5215 |
| fire zap at fountain | `dryup` | | no | `!rn2(3)` (fountain.c:201-205) |
| fountain | quaff/dip/kick/zap | `dryup` → ROOM | no | `!rn2(3)` per use (fountain.c:201-234) | |
| drawbridge | open: wand of opening/knock/force bolt/passtune; close: wand of locking/wizard lock; destroy: wand of striking/force bolt, dig with `destroy_drawbridge` | UP↔DOWN; DBWALL becomes door NODOOR when open; **closing/opening deletes all objects on span/portcullis squares (incl. boulders)** (dbridge.c:775-884) | open/close reversible; destroy not | `rn2(6)` iron chains on destroy | dbridge.c:775-1010; zap.c:3260-3310, 3633-3715; music.c:811-846 |
| drawbridge destroyed | | span → MOAT/LAVAPOOL/ICE/ROOM (depends on `DB_UNDER`), wall → NODOOR | no | | dbridge.c:888-1010 |
| iron bars | passable by passes_bars monsters (small, amorphous, rust/corrode, metallivore), polymorphed hero | removal by acid/lightning zap (`rn2(10)` skip for lightning), rust monster/rock mole eat, rolling boulder `hits_bars` (`!rn2(20)`) | no (never rebuilt) | hack.c:784 `dissolve_bars` via monmove.c:2170; zap.c:5352-5365; bars `W_NONDIGGABLE` → "somewhat but remain intact" | |
| tree | axe `DIGTYP_TREE` → ROOM (+`!rn2(5)` fruit) | no | | dig.c:480-495 |
| altar/throne | cannot be dug by hero (`dig_check`); altar dig by object only | | | dig.c:219-229 |
| secret door / corridor | search, wand of opening/striking/probing/zap | SDOOR/SCORR → DOOR/CORR | one-way | `rnl(7-fund)` (detect.c:2042,2054) | |

Water walking, levitation, flying: hero in/over pool needs `Levitation||Flying||Wwalking` else `drown()` (dothrow.c:~986 pattern; hack.c `swim_move_danger` hack.c:1885).

---------------------------------------------------------------------------------------------------------------------

## 7. Movement modes that bypass the above [auto-extracted from source]

| mode | what it bypasses | what it does NOT bypass | source |
|---|---|---|---|
| `Passes_walls` (xorn polymorph, prayer boon `HPasses_walls` d(4,4)+4 turns) | walls, closed doors, bars, **boulders (outside Sokoban)**; may squeeze diagonals | `W_NONPASSWALL` squares ("Sokoban walls resist your ability", hack.c:1053-1056) and boulders **in Sokoban** (hack.c:1216: `Sokoban || !Passes_walls`) | hack.c:1026-1060, 1216; pray.c:473 |
| Levitation | pits, holes, trap doors, bear traps, water, lava, ice slip (hack.c:2398) | **cannot push boulders** (hack.c:415); cannot go down stairs; **in Sokoban cannot escape pit/hole** (trap.c:1850,2818) | youprop.h:240 |
| Flying | same as levitation for traps/water; can still push boulders; not on Plane of Water | Sokoban pits/holes (trap.c:1850) | youprop.h:253 |
| Water walking | pools/moats (not lava) | | hack.c:1696-1702 |
| Jumping (boots/spell/knight) | hops over squares incl. pits/water/traps outside Sokoban ("pass right over" dothrow.c:~950) | cannot jump over a boulder square except giants (apply.c `check_jump`); stops at pit/hole in Sokoban (dothrow.c:955); closed doors, walls block; diagonal through doors forbidden | apply.c:1893-1990; dothrow.c:742-980 |
| Small/tiny polymorph | squeezes onto boulder squares (`verysmall`) but then cannot push ("too small"); passes bars | | hack.c:145-163, 426 |
| Giant polymorph | steps over / picks up boulders (not in Sokoban) | Sokoban: cannot pick up; step-over gives guilt | hack.c:262-310; pickup.c:1713 |
| Amorphous / ooze | under closed doors (`can_ooze`) | | hack.c:1075 |
| Tunneling polymorph (umber hulk etc.) | eats rock (non-Sokoban), eats boulders | `!Sokoban` in test_move boulder branch (hack.c:1226) | hack.c:1037, 1226 |
| teleportation / level teleport | everything except noteleport/Sokoban/restricted regions | | teleport.c |
| trapdoor/hole | one-way | | |

---------------------------------------------------------------------------------------------------------------------

## Gadget-relevant primitives

Ranked by usefulness for NP/PSPACE-hardness style reductions (as for Sokoban-like puzzles). Each lists the exact source facts a proof would cite.

1. **Boulder = movable block, push-only (no pull).** *Facts:* push is orthogonal-only in Sokoban (hack.c:442) and any direction outside; destination must be non-rock, non-bars, no other boulder, no blocking monster, not a closed door, not a diagonal into a door with a door (hack.c:432-435, 485, 456-483); moves exactly one square per push, objects/furniture/traps other than those in table 1.2 do not stop it; deterministic (`dopush` has no rn2). Hero cannot squeeze past unless carrying ≤ ~0 (`inv_weight() <= -850`, hack.c:138-143, weight.h:24) — a reduction can fix inventory weight above this by starting inventory. Sokoban rules (diagonal squeeze ban hack.c:973) make this exactly the Sokoban pushing model; the original-game theorem (Sokoban is PSPACE-complete) then applies if all levels flags are set as in `dat/soko*.lua`. Caveat: NetHack boulders are also blocked by monsters, so monster-free initial state is needed.

2. **Push-only ⇒ irreversible corner traps / dead squares.** Because no pull exists and a boulder against a rock/bars/second boulder cannot move away on its own, any boulder pushed into a dead end is permanently immobile (barring breakage). *Facts:* hack.c:432-436 block pushing into rock; there is no code path where a boulder moves other than via `dopush`, launch (rolling trap) or teleport/rloco; therefore reachability is monotone.

3. **Pit/hole filled by boulder = consumable sink, 1 boulder : 1 trap, deterministic.** *Facts:* hack.c:530-566 PIT/SPIKED_PIT go through `flooreffects` (do.c:188-266, no RNG, boulder `useupf`); HOLE/TRAPDOOR through the code at hack.c:544-566 (no RNG). Pit/hole trap is deleted (`deltrap`/`delfloortrap`) so the square becomes plain floor. Sokoban completion criterion: last PIT/HOLE deleted clears `Sokoban` (trap.c:7059-7097). This gives a counting resource (boulders vs holes) and a "gate opens" event (the hero can now walk across the square, and the diagonal-push/squeeze restrictions drop globally — usable as a one-time global switch **or a hazard**).

4. **One-way passage: hole/trap door (and level teleporter).** *Facts:* fall is deterministic in Sokoban or when the hero is not levitating/flying and doesn't hit the 20% known-trap escape (trap.c:3038 + Sokoban override trap.c:3015); destination level fixed at trap creation (trap.c:442-453, `dst`), but arrival square is random (`u_on_rndspot`, do.c:1804) so the landing spot cannot encode information; trap persists after hero falls (trap.c:2013-2060 does not delete) until plugged. Good for "fail" sinks / exits; the random landing makes it unsuitable for transmitting state except via the level number.

5. **Door as a 2-3 state switch.** *Facts:* OPEN/CLOSED/LOCKED transitions with tools (key `70+DEX`%/turn, lock.c:640) and wand/spell of locking/opening are deterministic in outcome (RNG only in time: lock.c:98, 904); BROKEN/NODOOR are absorbing (only wand of locking or wizard lock can undo, lock.c:1161-1190). Diagonal restriction (hack.c:1141,1209) and boulder-diagonal restriction (hack.c:434) give crossing gadgets. Closing needs the square free of objects/monsters (lock.c:926-955), so a boulder on an open door is a "door cannot close" lock.

6. **Raised/lowered drawbridge as a connected switch.** *Facts:* open/close are controlled by wand/spell/passtune (dbridge.c:775-884; zap.c:3260-3310) and are fully reversible; they **delete all objects on both squares** (`delallobj`, dbridge.c:822-824), including boulders, and kill/crush entities (`do_entity`). Moat under span fills with boulder like any moat (DB_FLOOR). Switch state = `levl[x][y].typ` DRAWBRIDGE_UP/DOWN; DBWALL is `W_NONDIGGABLE` (dbridge.c:~797).

7. **Water squares with 90% boulder fill (probabilistic consumable) and ice with melt timer.** *Facts:* do.c:61-68. Use only if the reduction allows probabilistic gadgets (for NP-hardness of reachability with randomness you need a "random-but-unlimited-retry" argument; fill failure **consumes the boulder**, so retry costs resources). Cold zap freezes with explicit melt timer (50-2000 turns unless it rolls permanent, zap.c:5081-5111) → time-dependent, avoid.

8. **Level-teleport/teleport traps with fixed destination** (`teledest`, trap.h:125, trap.c:3009): deterministic, unresistable teleport within a level → "wire"/warp gadget for planarity-breaking in crossing gadgets. Needs the level generator (Lua `des.teleport_region`/trap with coords) — constructible in a custom level. Landing square occupied by a monster is displaced (teleport.c:1517-1530).

9. **Secret doors/corridors as hidden one-way reveals:** `rnl(7-fund)` per search (detect.c:2042) — probabilistic; avoid for deterministic proofs.

10. **Squeeze rule as a weight-threshold gate.** Diagonal squeeze requires `inv_weight()+weight_cap() ≤ 600` (hack.c:970, weight.h:22) and non-big form; inventory is a resource the hero controls → can build gates that need dropped inventory, but they depend on hero state not just map; most useful for Sokoban-mode where squeeze is just banned (case 3).

---------------------------------------------------------------------------------------------------------------------

## Gadget killers (what a reduction must disable)

All items [auto-extracted from source] with citations; "disable by" suggests the initial-state / level-flag choice.

| killer | what it breaks | source | disable by |
|---|---|---|---|
| **Digging** (pick-axe, mattock, wand of digging, dwarves/umber hulks, digging monsters) | removes walls/doors/boulders, makes holes/pits anywhere diggable, floods | dig.c:300-570, 885-1025, 1548-1754; mdig_tunnel dig.c:1414 | `W_NONDIGGABLE` over the whole map (des.non_diggable, sp_lev; dat/soko1-1.lua:36); `hardfloor` (dungeon.c:1651); no digging tool in inventory and none generated; note boulders+bars: `W_NONDIGGABLE` on bars honoured (hack.c:660, zap.c:5352) |
| **Breaking boulders** (force bolt, striking, pick on boulder, stone-to-flesh, polymorph) | destroys the block (Sokoban gives only −1 Luck) | zap.c:2275-2290, 5537-5565; dig.c:455-462 | start with no wands/spells/pick; in Sokoban the penalty `change_luck(-1)` (trap.c:7041-7046) is mere flavour, **not** a prohibition — a reduction must exclude these items |
| **Scroll of earth / new boulders** | creates arbitrary boulders (also cures lost boulders) | read.c:1919-1968 | no scrolls; no confused/random items |
| **Giants / polymorph into giant, tiny forms** | step over/pick up boulders, squeeze under | hack.c:262-310, 145-163; pickup.c:1713 | no polymorph source (traps: `POLY_TRAP`; wand; potion), disable generation of giants; Sokoban only blocks pickup, not stepping (with luck penalty) |
| **Passes_walls** | ignores walls, boulders outside Sokoban | hack.c:1026,1216 | `W_NONPASSWALL` all map (`des.non_passwall`, soko1-1.lua:37); no xorn polymorph; prayer boon (pray.c:473) |
| **Levitation / flying** | cross pits, holes, water, lava; **cannot push boulders while levitating** (helps) | hack.c:415; trap.c:1850,2818 | Sokoban flag makes pits/holes inescapable (trap.c:3015, 1850); water/lava needs removal of levitation items, or use rock only |
| **Jumping** | jumps over pits/holes/water outside Sokoban | apply.c:1893-1990; dothrow.c:955 | start without jumping boots/spell; Sokoban stops jump at pit/hole (dothrow.c:955) but doesn't penalize |
| **Teleportation** (traps, scrolls, wands, teleport control) | bypasses all walls within level | teleport.c:842-916, 1492-1535 | `noteleport` level flag (teleport.c:38; set in dat/soko*.lua `level_flags`); no teleport traps/items |
| **Level teleport / trapdoor fall** | leaves level | teleport.c:1165-1190, trap.c:602-724 | `noteleport`+Sokoban (teleport.c:1185); a reduction using a single fixed-size level should treat falling as "lose" |
| **Monsters** (blocking pushes, picking items, doors, breaking boulders, shopkeepers/priests) | monster at r blocks push (hack.c:456-483); `m_can_break_boulder` (monmove.c:133); peacefuls and pets block too; revives `revive_nasty` (hack.c:450) | `des.exclusion monster-generation` (as dat/soko4-1.lua:~60), start with no monsters, no pets; `Sokoban` also affects monster AI (monmove.c:1310) |
| **Random monster/trap generation, ice melting timers, doors RNG** | introduces nondeterminism | mklev.c, timeout | use explicit Lua level (`des.map`, `des.trap(type,x,y)`), no random generation; avoid ice |
| **Kicking / forcing** | kicks break doors (dokick.c:930-950); kicking boulders does nothing special (dokick.c:517 `BOULDER` excluded from being kicked) | | restrict to doors that are never closed or use bars; or accept door breaking as an allowed move (monotone) |
| **Wand of opening/knock/locking/wizard lock** | switches arbitrary doors and drawbridges | lock.c:1103-1290; zap.c:3260-3310 | no wands; |
| **Cold/fire zaps** | freeze/unfreeze/evaporate water, burn webs, dry fountains | zap.c:5141-5300 | no wands/spells; no fire/cold monsters |
| **Rolling boulder / launched boulders** | creates non-hero-driven boulder motion; breaks doors | trap.c:3260-3578 | not generated in Sokoban (trap.c:3610); don't place `ROLLING_BOULDER_TRAP` |
| **Magic portal / vibrating square** | undestroyable special traps, cannot be removed by deltrap | trap.h:116 | don't place; irrelevant |
| **Sokoban flag turning itself off** | solving the last pit/hole drops *all* restrictions (diagonal squeezing and diagonal pushes become legal) | trap.c:7059-7097 | in a reduction ensure that the last PIT/HOLE is the victory condition, or keep an unfillable PIT (e.g. a pit under a spot no boulder can reach), or use a level that doesn't depend on the flag |
| **Hero-dug pits** (still possible under `hardfloor` as pits: `DIGCHECK_PASSED_PITONLY`, dig.c:237-246) | hero can create pits (`madeby_u` pits don't count for Sokoban completion and aren't inescapable) | dig.c:735-740, trap.c:7066 | no digging tool |
| **#untrap / force-fight / #force / #loot / #pray** | none directly relevant to topology; `#force` does not open doors (lock.c:684). Prayer can grant 8-20 turns of Passes_walls (pray.c:473) | | exclude prayer or accept (`W_NONPASSWALL` still blocks) |
| **Polymorph trap in path** | grants polymorph forms (giant, xorn, tiny) | trap.c:2453 | don't place `POLY_TRAP`; [inferred] hand-written Sokoban levels place no POLY_TRAP |

### Minimal "sandbox" choice list for a reduction (consistent with dat/soko4-1.lua)

1. `des.level_flags("mazelevel","noteleport","hardfloor","premapped","sokoban","solidify")`; `des.non_diggable(whole)`; `des.non_passwall(whole)`; `des.exclusion monster-generation`.
2. Hero starts with a fixed starting inventory containing no digging tools, no wands, no scrolls, no spells, no jumping/levitation/flying, weight > squeeze threshold (so `could_move_onto_boulder` fails: `inv_weight() > -850`).
3. Only features used: floor, walls, boulders, pits/holes (placed by `des.trap`), maybe doors (initial state set in the des file).
4. Account for the "flag clears when last PIT/HOLE disappears" semantics (trap.c:7059): after that the level behaves as a non-Sokoban level (diagonal pushes legal), which is irrelevant if reaching that state *is* the goal.

Open items for follow-up (not yet verified in code): `m<dir>` push semantics for monsters (monsters can never push boulders — only giants carry them, mon.c:2093); shopkeeper `block_door` (shk.c:5791) interactions; `u.usteed` riding effect on pushing (hack.c:426 uses `!u.usteed`); travel `_` command not modelled. Level difficulty / luck penalty effects through `rnl` only change timing of door-opening (not outcome).
