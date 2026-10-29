# NetHack 5.0.0 state architecture (source-derived)

Source: `Research/nethack-complexity/src` (NetHack 5.0.0 release, commit 16ff591). Read-only; nothing built or run.
All facts are [auto-extracted from source] as `file:function:line` unless marked [inferred] or [not verified].
Paths are relative to `src/`. `svX`/`gX` are the 5.0 global-struct prefixes: `sv*` = "saved" globals (decl.h:1108-1236), `g*` = unsaved globals (decl.h:141-1105).

Oracle used: `dosave()` (src/save.c:43) -> `savelev(current)` (save.c:429/451) -> `savegamestate()` (save.c:265) -> every other level via `getlev`+`savelev` (save.c:195-215).
Whatever those write is the game's persistent "complete state". Anything they omit is either derived, transient (only valid mid-command), or external.

## 1. State components

"Scales?": FIXED = bounded by a compile-time constant; DYN = linked list / malloc with no explicit cap in the code read.

### 1a. Global (per-game) state, written by `savegamestate()` (save.c:265-330)

| Component | C type / struct | Stored in | Saved in | Size / bound | Scales? |
|---|---|---|---|---|---|
| Turn counter `moves` | `long` | `svm.moves` (decl.h:1163) | save.c:274 `Sfo_long`; per-level timestamp save.c:516 | hard stop at 1,000,000,000: "The dungeon capitulates." -> `done(ESCAPED)` (allmain.c:253-257) | FIXED cap 1e9 |
| Hero struct `u` | `struct you` (you.h:365-507) | `u` global | save.c:287 `Sfo_you` | see 1c | FIXED fields |
| Game context | `struct context_info` (context.h ~140-186) | `svc.context` (decl.h:1117) | save.c:277 | includes `ident` (o_id/m_id counter, `unsigned`), `seer_turn`, `rndencode`, dig/eat/engrave/tin/spellbook/takeoff/polearm progress, `next_attrib_check`, lifelist, tips | FIXED fields |
| Option/flag block | `struct flag` (flag.h:20-~200) | `flags` | save.c:281 `Sfo_flag`; overwrites live options on restore (restore.c:570-571) | ~50 booleans + ints and char arrays (`pickup_types[MAXOCLASSES]`, `inv_order[MAXOCLASSES]`) | FIXED |
| Inventory | `struct obj *` chain | `gi.invent` | save.c:306 `saveobjchn` | 52 letters `a-zA-Z` + `$` + `#` overflow (hack.h:580-587, `invlet_basic=52`); "knapsack cannot accommodate" (pickup.c:1749, invent.c:5246-5248). Gold is a COIN_CLASS object in inventory (`quan` = amount, `long`) (mkobj.c ~1970 weight of COIN_CLASS) | FIXED 52 stacks (+gold) |
| Loose ball & chain | obj chain | `gl.looseball/loosechain` | save.c:309 `save_bc` (695) | 2 objects | FIXED |
| Migrating objects / monsters | obj chain / monst chain | `gm.migrating_objs`, `gm.migrating_mons` | save.c:311-313 | none found | DYN |
| Global timers | `timer_element` list (timeout.h:62-70) | `gt.timer_base` (decl.h:961) | save.c:299 `save_timers(RANGE_GLOBAL)` (timeout.c:2668) | `timeout` is `long` absolute move number; `tid` `unsigned long`; `svt.timer_id` counter saved (decl.h:1214) | DYN |
| Global light sources | `light_source` list | `gl.light_base` (decl.h:539) | save.c:300 `save_light_sources` (light.c:421) | none found | DYN |
| Monster-vitals table | `struct mvitals[NUMMONS]` (hack.h:680; `uchar born`, died counts) | `svm.mvitals` (decl.h:1166) | save.c:310-312 | NUMMONS ~ 394 `MON(` entries in monsters.h [grep count; enum not compiled] | FIXED by data tables |
| Dungeon structure | `dungeon dungeons[MAXDUNGEON]`, `dgn_topology`, `branch` list, `n_dgns`, `level_info[MAXLINFO]`, `mapseen` chain, `inv_pos`, `tune[6]` | `svd.dungeons`, `svb.branches`, `svl.level_info`, `svm.mapseenchn` (decl.h:1108-1173) | save.c:313 -> `save_dungeon` (dungeon.c:149-205) | MAXDUNGEON 16, MAXLEVEL 32 per dungeon, MAXLINFO 512 (hack.h:425). Actual: 8 dungeons, ~72-80 levels (sec. 3) | FIXED by constants + dungeon.lua |
| Special level chain | `s_level` list | `svs.sp_levchn` | save.c:314 `savelevchn` (973) | one per special level | data-driven |
| Quest status | `struct q_score` | `svq.quest_status` | save.c:315-316 | | FIXED |
| Known spells | `struct spell spl_book[MAXSPELL+1]` | `svs.spl_book` (decl.h:1208) | save.c:317-319 | MAXSPELL = LAST_SPELL-FIRST_SPELL+1 (objclass.h:184); +1 terminator slot | FIXED by object table |
| Artifact state | `arti_info` array | artifact.c | `save_artifacts` (artifact.c:119) | by artilist | FIXED |
| Oracle table | `oracle_loc[]` | `svo.oracle_loc` | `save_oracles` (rumors.c:598) | data-file-sized | external data |
| Object discoveries / randomized appearances | `svd.disco[NUM_OBJECTS]` (`short`), `svb.bases[MAXOCLASSES+2]`, `objects[NUM_OBJECTS]` (`struct objclass`, incl. `oc_descr_idx` shuffle, `oc_name_known`, `oc_uname`) | `objects[]`, decl.h:1112,1131 | `savenames` (o_init.c:375-402) | NUM_OBJECTS ~ 505 entries in objects.h [grep count, approximate] | FIXED by table |
| Named fruits | `struct fruit` chain; `pl_fruit[32]`, `pl_character[32]` | `ffruit`, `svp.*` | save.c:320-324 `savefruitchn` (951) | names 32 chars; count guarded by `made_fruit` | DYN |
| Killer info | `struct kinfo` | `svk.killer` | `save_killers` (end.c:1760) | | FIXED |
| Msg history, gamelog | list | | `save_msghistory` (save.c:1029), `save_gamelog` (237) | MAX_MSG_HISTORY 128 (global.h:419) | display only, not game state |
| Lua variable table | string (serialized `nh_lua_variables`) | Lua state | `save_luadata` (nhlua.c:1328) | unbounded string | DYN (script-visible persistent vars) |
| UUID, uid, birth/real time | `nhuuid[37]`, `unsigned long uid`, `ubirthday` (time_t), realtime | | save.c:272-290 | | metadata (but see sec. 4 item 4) |
| Reserved | `wreserve`, `wtreserved` | `svw` | save.c:285-286 | unused | |

### 1b. Per-level state, written by `savelev_core()` (save.c:451-568); one copy per visited level

| Component | C type / struct | Stored in | Saved in | Size / bound | Scales? |
|---|---|---|---|---|---|
| Terrain grid | `struct rm locations[COLNO][ROWNO]` (rm.h:159-171; dlevel_t rm.h:473-483): `int glyph` (hero's remembered glyph), `schar typ`, `uchar seenv`, 5-bit `flags`, `horizontal`, `lit`, `waslit`, 6-bit `roomno`, `edge`, `candig` | `levl` = `svl.level.locations` | `savelevl` (save.c:577), `Sfo_rm` per cell | 80*21 = 1680 cells (valid x 1..79) | FIXED by COLNO/ROWNO |
| Last-seen terrain | `schar lastseentyp[COLNO][ROWNO]` | `svl.lastseentyp` (decl.h:1157) | save.c:510-514 | 1680 | FIXED |
| Level flags | `struct levelflags` (rm.h ~430-471): bitfields, `schar temperature`, `long stasis_until` | `svl.level.flags` | save.c:521 | | FIXED |
| Stairs / ladders | `stairway` list | `gs.stairs` | `save_stairs` (save.c:665) | DYN (MAXSTAIRS=1 applies only to special stairways in dungeon topology) | DYN |
| up/down dest areas | `dest_area` | `svu.updest`, `svd.dndest` | save.c:518-519 | | FIXED |
| Doors array | `coord *doors`, `doors_alloc` | `svd.doors` | save.c:524-532 | grown in steps of DOORINC=20 (global.h:387) | DYN |
| Rooms | `struct mkroom rooms[(MAXNROFROOMS+1)*2]` (mkroom.h:12-25), `nroom` | `svr.rooms` (decl.h:1203) | `save_rooms` (mkroom.c:863) | MAXNROFROOMS 40, MAX_SUBROOMS 24 per room; mklev.c:310 refuses past 40; roomno field is 6 bits | FIXED 40 |
| Monsters | `struct monst` chain | `fmon` | `savemonchn` (save.c:884) / `savemon` (826) | no per-level cap found; per-species birth limit `mbirth_limit`: MAXMONNO 120 (Nazgul 9, Erinys 3) (makemon.c:1549-1550, global.h:415); worms: 31 per level (monst.h:160-161) | DYN |
| Monster extras | `struct mextra` (mextra.h:205): name, egd (guard), epri (priest), eshk (shopkeeper), emin, edog (pet), ebones, mcorpsenm | `mtmp->mextra` | save.c:833-880 | | FIXED per mon |
| Worm segments | `wtails[]`, `wgrowtime[MAX_NUM_WORMS]` | worm.c | `save_worm` (worm.c:528) | segments | DYN |
| Traps | `struct trap` chain (trap.h; `ttyp` 5-bit) | `gf.ftrap` | `savetrapchn` (save.c:920) | <= 1 per cell [inferred] | <= 1680 |
| Floor / buried / shop-bill objects | `struct obj` chain + `level.objects[x][y]` index | `fobj` (rm.h:489), `svl.level.buriedobjlist`, `gb.billobjs` | save.c:559-561 `saveobjchn` | none found; containers nest via `cobj` | DYN |
| Engravings | `struct engr` (engrave.h:18-38): text, type, `long engr_time` | `head_engr` | `save_engravings` (engrave.c:1551) | text length `unsigned` | DYN |
| Pending shop repairs | `struct damage` list | `svl.level.damagelist` | `savedamage` (save.c:640) | | DYN |
| Level timers / light sources | as global, `RANGE_LEVEL` | `gt.timer_base`, `gl.light_base` | save.c:545-546 | | DYN |
| Regions (gas clouds etc.) | `NhRegion` (region.h ~30-70): rect list, `long ttl`, callbacks as `short` indices | region.c array, `svn.n_regions` | `save_regions` (region.c:741) | | DYN |
| Air/water bubbles | `struct bubble` list | `svb.bbubbles` | `save_bubbles` (save.c:591), `save_waterlevel` (mkmaze.c:1723) | Plane levels only | FIXED |
| Exclusion zones | `exclusion_zone` list | `sve.exclusion_zones` | `save_exclusions` (dungeon.c:2596) | | DYN |
| Hero movement track | `coord utrack[UTSZ=100]`, `utcnt`, `utpnt` | track.c:9-12 | `save_track` (track.c:76) | UTSZ 100 | FIXED 100 |
| Bones info | `struct cemetery` chain | `svl.level.bonesinfo` | `savecemetery` (save.c:617) | | DYN |
| Level timestamp | `long omoves` | `svo.omoves` | save.c:516 | monsters are caught up on return via `mon_catchup_elapsed_time` (dog.c:627; restore.c:1213) | |

### 1c. Key scalar types (hero, objects, monsters)

| Quantity | Type | Where | Bound / overflow behavior |
|---|---|---|---|
| HP `u.uhp`, `u.uhpmax`, `u.uhppeak` | `int` | you.h:476-477 | no cap found in source; status line clamps display to 9999 for Pw (botl.c:145, 1080). Per-level gains `uhpinc[MAXULEV]` are `xint16` (you.h:480). |
| Pw `u.uen`, `u.uenmax`, `u.uenpeak` | `int` | you.h:478-479 | no cap found; display clamps 9999 |
| Experience level `u.ulevel` | `int`, 1..MAXULEV=30 | you.h:378, global.h:413 | hard cap 30 |
| Exp points `u.uexp`, score `u.urexp` | `long` | you.h:487 | explicit saturate to `LONG_MAX` on wraparound (exper.c:177-181 `more_experienced`). Thresholds `newuexp()` exper.c:14-23 (lev<10: 10*2^lev; <20: 10000*2^(lev-10); else 10,000,000*(lev-19)) |
| Hunger `u.uhunger` | `int` | you.h:392 | |
| Attributes (6) cur/exe/bon/max/temp/time | `struct attribs { schar a[A_MAX]; }` | attrib.h:39-41 | `schar`; race caps via `ATTRMAX` (attrib.h:43) |
| Luck `u.uluck`, `u.moreluck` | `schar`; LUCKMIN -10, LUCKMAX 10, LUCKADD 3 | you.h:460-470 | clamped |
| AC `u.uac` | `schar`, `AC_MAX 99` | you.h:471-472 | |
| Alignment record `u.ualign.record` | `int` in `align`; ALIGNLIM = 10 + moves/200 (align.h:17) | align.h:10-17 | limit grows with turn counter |
| Properties | `struct prop uprops[LAST_PROP+1]`, each `{long extrinsic, long blocked, long intrinsic}` (prop.h:97-144); LAST_PROP = LIFESAVED = 68 -> 69 entries | you.h:395 | timeouts stored in low bits of `intrinsic` (`long`) |
| Skills | `weapon_skills[P_NUM_SKILLS=38]`, `skill_record[P_SKILL_LIMIT]` | you.h ~500-505, skills.h:66 | FIXED |
| Achievements | `schar uachieved[N_ACH=32]` | you.h:105,506 | 31 + terminator |
| Conduct / events counters | `struct u_conduct` (~14 `long`), `u_event`, `u_have` | you.h ~20-60 | FIXED |
| Gold | object `quan`, `long` | obj.h:47 | no explicit gold cap found; some paths saturate at LARGEST_INT (steal.c:16, mhitu.c:2275) |
| Object quantity `quan` | `long` | obj.h:47 | zap.c:1532/1658 and mon.c:2004 special-case > LARGEST_INT |
| Enchantment/charges `spe` | `schar` (-128..127) | obj.h:51 | item-specific rules cap well below |
| Object weight `owt` | `unsigned`; `weight()` returns `int`; corpse weight saturates at LARGEST_INT=32767 (mkobj.c:1958-1960) | obj.h:46 | |
| `timed` (timers on obj) | `xint16` | obj.h:88 | |
| `corpsenm` | `int` | obj.h:160 | |
| Object id `o_id`, monster id `m_id` | `unsigned` (32-bit) | obj.h:43, monst.h:99 | `next_ident()` (mkobj.c:509-531) advances by rnd(2) per new obj/mon; if it wraps to 0 it is forced to rnd(2)+1; code says it "lives with" collisions on 16-bit int |
| Monster HP `mhp, mhpmax` | `int` (MHPMAX 500, global.h:416) | monst.h:112 | |
| Monster level `m_lev` | `uchar` | monst.h:104 | |
| Monster movement | `short` | monst.h:102 | |
| Monster tameness `mtame` | `schar` | monst.h:116 | |
| Monster track | `coord mtrack[MTSZ=4]` | monst.h:109-111 | |
| Monster timers (flee, blind, frozen) | 7-bit bitfields `mfleetim`, `mblinded`, `mfrozen` | monst.h:141,144,147 | max 127 |
| Coordinates | `coordxy` = `int16_t` | global.h:71 | |
| Level ids `d_level` | `xint16 dnum, dlevel` | dungeon.h:9-12 | |
| Ledger / depth | `ledger_no()`, `maxledgerno()` are `xint16` (dungeon.c:1375,1391), BUT `savelev(NHFILE*, xint8 lev)`, loop var `xint8 ltmp` (save.c:212) and `xint8 bbubbly` | | effective ceiling 127 ledger entries; `depth()` returns `schar` (dungeon.c:1430) -> max depth 127. `xint8` = `int8_t` (global.h:64) |
| Command repeat count `multi` | `cmdcount_nht` = `long` (hack.h:199) | decl.h gm | transient, not saved |

## 2. RNG

- **Algorithm:** ISAAC-64 (bundled, `include/isaac64.h`, `src/isaac64.c`), enabled by `#define USE_ISAAC64` (config.h:671). Without it, falls back to OS `random()`/`srand48` (rnd.c:92+).
- **State size per stream:** `struct isaac64_ctx` = `unsigned n; uint64_t r[256]; uint64_t m[256]; uint64_t a,b,c;` (isaac64.h:28-35; `ISAAC64_SZ = 1<<8`, :12) = ~4.1 KB.
- **Streams:** exactly two (rnd.c:26-29 `rnglist[]`): `CORE` (`rn2` family: rn2/rnl/rnd/d/rne/rnz, plus Lua `nh.rn2`/`nh.random`) and `DISP` (`rn2_on_display_rng`, rnd.c:70) for display-only effects, kept separate "so users cannot control the main sequence" (rnd.c:66-68 comment).
- **Extraction:** `RND(x) = isaac64_next_uint64(CORE) % x` (rnd.c:61-64); modulo bias present. `rnd(x)=RND(x)+1`, `d(n,x)=n+sum RND(x)`, `rne` (cap max(ulevel/3,5), rnd.c:192), `rnz` (long arithmetic, rnd.c:214), `rnl(x)` luck-adjusted (reads `Luck`).
- **Lua `math.random` is overridden** to call `nh.rn2`/`nh.random` (dat/nhlib.lua:5-16), so level-generation scripts share the CORE stream. Caveat: nhlua.c:2946 comment says raw `math.random` would use Lua's own xoshiro256** if the shim were not loaded; `submodules/lua` is empty in this checkout so Lua's source was not read. 24 dat/*.lua files use `math.random` (86 occurrences) and rely on the shim.
- **Seeding:** `init_random(fn)` -> `set_random(sys_random_seed(), fn)` -> `init_isaac64(seed, fn)` (rnd.c:282, 43-58). The seed is one `unsigned long` (8 bytes on LP64 Unix; 4 on LLP64 Windows) fed as the ISAAC key bytes, so at most 64 bits of seed enter either stream [inferred from `sizeof seed`, rnd.c:46-52]. Called once per stream at startup (options.c:7161-7162).
  - Unix: `sys_random_seed()` reads `sizeof(long)` bytes from `/dev/urandom` or `/dev/random` (unixmain.c:813-840; DEV_RANDOM unixconf.h:425-428) and sets `has_strong_rngseed = TRUE`; fallback is `time()*pid` (weak). Windows and libnh also set the strong flag (windsys.c:762, libnhmain.c:752); the generic pcmain.c version is `time*pid` only (pcmain.c:792-812).
- **Saved? NO.** `grep isaac|rng` in save.c and restore.c returns nothing; RNG state is never written. After restore the RNG continues from the fresh process seed.
- **Reseeded during play:** `reseed_random()` (rnd.c:289-295) re-runs `init_random` for BOTH streams, but only if `has_strong_rngseed`. It is called twice in every new-level `mklev()` (mklev.c:1579-1580 at start, 1591-1592 at end) and whenever a previously visited level is reloaded (do.c:1709-1710). On normal installs the RNG is therefore re-keyed from OS entropy at each level change; there is no single long deterministic sequence. Consequence: modeling r_t as an external random input is faithful; a "seed" model holds only if `has_strong_rngseed` is false.
- **Hidden RNG-adjacent counter:** `svc.context.ident` advances by `rnd(2)` per object/monster (mkobj.c:521), consuming CORE output; ids (`o_id`, `m_id`) feed behavior (e.g. `o_id % 2` for helm of opposite alignment do_wear.c:470; message selection read.c:185,279,430,475-483; do_name.c:1532).

## 3. Hard constants

| Constant | Value | File:line |
|---|---|---|
| COLNO | 80 (valid x 1..79; col 0 unused) | include/global.h:382 |
| ROWNO | 21 | global.h:383 |
| MAXNROFROOMS | 40 | global.h:385 |
| MAX_SUBROOMS | 24 | global.h:386 |
| DOORINC | 20 | global.h:387 |
| MAXDUNGEON | 16 (actual in dat/dungeon.lua: 8 = Doom, Gehennom, Mines, Quest, Sokoban, Ludios, Vlad's Tower, Elemental Planes) | global.h:408 |
| MAXLEVEL | 32 per dungeon; `num_dunlevs > MAXLEVEL -> MAXLEVEL` | global.h:409; dungeon.c:1103-1104 |
| MAXLINFO | MAXDUNGEON*MAXLEVEL = 512 | hack.h:425 |
| MAXSTAIRS | 1 (special stairways per dungeon) | global.h:410 |
| MAXULEV | 30 | global.h:413 |
| MAXMONNO | 120 (per-species birth limit before "extinct") | global.h:415; makemon.c:1549-1550 |
| MHPMAX | 500 (monster HP cap) | global.h:416 |
| LARGEST_INT | 32767 ("int-ish" saturation point) | global.h:135 |
| BUFSZ / QBUFSZ | 256 / 128 | global.h:389-390 |
| PL_NSIZ / PL_CSIZ / PL_FSIZ / PL_PSIZ | 32 / 32 / 32 / 63 | global.h:401-404 |
| MAX_MSG_HISTORY | 128 | global.h:419 |
| MAX_NUM_WORMS | 32 (31 usable, 5-bit `wormno`) | monst.h:160-161 |
| MTSZ | 4 | monst.h:109 |
| UTSZ | 100 | track.c:9 |
| invlet_basic | 52 | hack.h:584 |
| LUCKMAX / LUCKMIN / LUCKADD | 10 / -10 / 3 | you.h:467-468, 463 |
| AC_MAX | 99 | you.h:472 |
| N_ACH | 32 | you.h:105 |
| MAX_CARR_CAP | 1000 | weight.h:25 |
| MAX_ERODE | 3 | obj.h:129 |
| `moves` limit | 1,000,000,000 -> game ends | allmain.c:253-257 |
| Dungeon level counts (`num_dunlevs = rn1(range, base)` = base..base+range-1, dungeon.c:1074) | Doom 25..29, Gehennom 20..24, Mines 8..9, Quest 5..6, Sokoban 4, Ludios 1, Vlad's Tower 3, Planes 6 | dat/dungeon.lua:10-11, 91-92, 172-173, 198-199, 219-220, 260-263, 285-287 |
| Total ledger entries | roughly 72-80, below the xint8 ceiling of 127 | [inferred sum] |
| Depth type | `schar` (max 127) | dungeon.c:1430 |
| rm.roomno bits | 6 | rm.h:168 |

## 4. NOT in the save file but affects behavior

1. **Wall clock (live, not stored):** `night()` (hour < 6 or > 21) and `midnight()` (hour == 0) call `localtime()` each time (calendar.c, functions `night`, `midnight`, `getlt`). Re-evaluated mid-game in: lycanthrope change (allmain.c:328, were.c:16-17), lycanthropy bite (mhitu.c:979), undead at midnight (mhitu.c:1188), gremlins (uhitm.c:3024,3040,3061), sounds (sounds.c:747-838), morgue entry (hack.c:3686), pets at full moon+night (dog.c:1176).
2. **Moon phase and Friday 13th:** `phase_of_the_moon()` and `friday_13th()` (calendar.c) are called from `moveloop_preamble` (allmain.c:57-67) on every start AND restore, and stored in `flags.moonphase`/`flags.friday13`. The save contains them but they are overwritten on resume. Effects: +1 luck at full moon, -1 on Fri 13th, luck-timeout baseline (timeout.c:595-597), were/dog/sounds, `NEW_MOON` (uhitm.c:4245). The startup `change_luck` is undone before saving (save.c:142-145).
3. **Real time as seed:** weak-seed fallback `time()*pid` (unixmain.c:834-840, pcmain.c:792-812); see sec. 2.
4. **`ubirthday`** (game-start time_t; saved as a 14-char string, save.c:288): `ubirthday % 3` picks the ant-hole monster family (mkroom.c:507); `o_id ^ ubirthday` picks T-shirt/apron text (read.c:95,217,245); bones pool (files.c:792). Stable per game but hidden state.
5. **Bones files on disk:** `getbones()` (bones.c ~630-680): when `flags.bones` and not wizard, `rn2(3)` gates loading of a ghost level from other games' bones files in the save directory. External filesystem state.
6. **Data files / Lua scripts:** `dat/*.lua` (dungeon.lua, themerms.lua, special levels, quest text), `data`, `rumors`, `oracles` are read at runtime via dlb and define level generation and dungeon shape. They are not in the save (version-locked); only `nh_lua_variables` is saved.
7. **Options and environment:** `struct flag` is saved and restored over the live config (restore.c:570-571), but `iflags` is NOT saved and `sysopt` (SYSCF file: MAXPLAYERS, bones pools, `check_save_uid`, etc.) is external. Behavior-affecting items in saved `flags`: `pickup`/`pickup_types`, `autodig`, `autoopen`, `autoquiver`, `safe_dog`, `safe_wait`, `confirm`, `pushweapon`, `nopick_dropped`, `pickup_thrown`, `pile_limit`, `pickup_burden`. Wizard-mode env overrides: `SHOPTYPE` (mkroom.c:103, mklev.c:1347), `SPLEVTYPE` (mkmaze.c:1161), `THEMERM`/`THEMERMFILL` (nhlua.c:1001).
8. **Play mode:** wizard/explore/normal (`flags.debug`, `flags.explore`) is saved but re-authorized on restore (restore.c:587-600).
9. **Transient mid-command state (unsaved globals):** `gm.multi` (long; counts/helplessness), `go.occupation`/`occtxt`, `gm.nomovemsg`, `gc.command_count`, `gm.bhitpos`, `gy.youmonst` (hero's `struct monst`, rebuilt from `u` via `set_uasmon`, restore.c ~620), vision arrays (recomputed), `gh.hero_seq`. Saving normally happens at the command prompt, where these are idle; `dosave` refuses while `gm.multi > 0` (save.c:48).
10. **Process identity:** `hackpid`, `getuid()` (saved only for file matching).

## 5. Natural scaling parameters and hard-coded obstacles

Natural parameters for a generalized family:
- **Map size:** COLNO x ROWNO (1680 cells). `levl`, `lastseentyp`, `objects[][]`, `monsters[][]` index arrays are static `[COLNO][ROWNO]` (rm.h:473-476, decl.h:1157). Generalizing means changing two constants; `coordxy` is int16 so fine to 32767, but `rm.roomno` is 6 bits and special-level Lua scripts hard-code fixed-size maps (Sokoban, Medusa, Castle, etc.).
- **Level count / depth:** per-dungeon MAXLEVEL (32), MAXDUNGEON (16), MAXLINFO; ledger/depth types `xint8`/`schar` cap at 127. The real dungeon shape is set by dat/dungeon.lua.
- **Rooms:** MAXNROFROOMS 40 (+24 subrooms each; rooms array 2*(40+1)).
- **Object count:** no cap on floor/monster/buried chains; hero inventory capped at 52 stacks; `quan` is `long`; container nesting unbounded.
- **Monster count:** no per-level cap found (one monster per cell, except worm tails, bounds it by about 1680); per-species births MAXMONNO=120. Generation rates live in code (`maybe_generate_rnd_mon`) [not verified here].
- **Integer widths:** HP/Pw `int`; exp `long` (saturates at LONG_MAX); `moves` `long` capped at 1e9; `quan` `long`; `spe` `schar`; attributes `schar`; AC `schar` (|AC| <= 99); luck `schar` (|10|); monster HP int capped at MHPMAX=500 by gameplay code; timeouts `long`; `o_id/m_id` `unsigned` 32-bit (collisions tolerated); several monster timers are 7-bit bitfields. Quantities unbounded in principle but bounded by source: `moves` (1e9), exp (LONG_MAX), level (30).
- **Hard-coded in ways that would need generalizing:**
  - RNG: two fixed ISAAC64 streams, 64-bit seed, reseed-on-level-change.
  - Object/monster/role tables (NUM_OBJECTS ~505, NUMMONS ~394) are compile-time enums; `objects[]` is mutable state (appearance shuffle, discoveries).
  - Wall-clock inputs (moon, night, Friday 13th).
  - Level shapes and some constants live in `dat/*.lua`, outside C types.
  - 52-letter inventory, 100-entry hero track, 4-entry monster track, 31 worms.
  - `xint8` ledger indexing in save/restore.
