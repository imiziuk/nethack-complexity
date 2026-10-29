# NetHack 5.0.0 (16ff591): objects, monsters, player-status mechanics (complexity-relevant)

Source root: `src/` (paths relative to it: `src/hack.c` means `src/src/hack.c`; headers are `include/`).
Label key: **[A]** = [auto-extracted from source] with file:line. **[I]** = inference from code I read (no single line proves it). **[N]** = not verified in code / only skimmed.
Nothing here comes from the wiki. `long` is 32-bit on Windows (LLP64) and 64-bit on LP64 Unix (`include/integer.h:78-83` [A]); long-based bounds below are platform dependent. `LARGEST_INT` = 32767 (`global.h:135`) is only a conservative clamp constant.

---------------------------------------------------------------------------------------------------
## 0. RNG / determinism

- One CORE RNG (ISAAC64; `rnd.c:25-55`, `rn2` at `rnd.c:95`) plus a separate DISPLAY RNG used only for hallucination display. All game-state randomness uses CORE. [A]
- Given (seed, full command sequence) the game is deterministic EXCEPT wall-clock inputs [A]:
  - moon phase / Friday 13th: `allmain.c:57-65`, `timeout.c:595-598` (baseluck +1 / -1).
  - `night()` / `midnight()`: lycanthrope change `allmain.c:328`, shapeshifter `mhitu.c:979`, undead `mhitu.c:1188`, pet loyalty `dog.c:1176`, `hack.c:3686`.
  - `getnow()` only feeds realtime stats/score (`cmd.c:5667`, `end.c:1164`).
  A reduction should fix seed and date. [I]
- Levels are generated lazily on first arrival from the CORE stream at that moment, so unvisited levels are not a fixed function of the seed; they depend on all prior RNG consumption. [I]
- `rnl(x)` (`rnd.c:112`) is Luck-adjusted (locks, traps, trees, etc.). [A]

---------------------------------------------------------------------------------------------------
## 1. Inventory, weight, containers, stacking

| Mechanic | Rule (code) | Reversible / deterministic / resources | Gadget relevance / exploit risk |
|---|---|---|---|
| Inventory slot cap | `invlet_basic = 52` (`hack.h:584`); gold takes an extra `$` slot (`hack.h:585-587`, `invent.c:702`). Pickup refused when `inv_cnt(FALSE) >= 52` and nothing mergeable ("knapsack cannot accommodate", `pickup.c:1738-1747`); undo-merge guard `invent.c:1274`. Loadstone / giant-held boulder bypass weight and (if you have a free slot or already carry one) the slot limit (`pickup.c:1721-1728`). [A] | Hard cap: 52 distinct stacks + gold. Quantity inside a stack not capped by this. | Bounds inventory-resident state to 52 stacks; container contents are NOT counted. |
| Carrying capacity | `weight_cap()` `hack.c:4295`: `25*(STR+CON)+50` clamped to `MAX_CARR_CAP=1000` (`weight.h:23`); Levitation / strong steed / air level => exactly 1000; wounded legs -100 per side; polymorph scales it. `inv_weight()` `hack.c:4351`; `calc_capacity()` capped at OVERLOADED `hack.c:4374-4382`. Gold weighs `(quan+50)/100` (`hack.c:4357`, `mkobj.c:1969`). [A] | Fixed constant max for an unpolymorphed hero. | Carried weight is bounded (`carry_count` `pickup.c:1570`); floor piles and container-on-floor contents are not. |
| Encumbrance | Move rate cuts `allmain.c:140-149`; heavy encumbrance moves only 2/3 of turns `hack.c:3057`; +1 hunger when > SLT_ENCUMBER `eat.c:3197`; no HP regen while moving encumbered `allmain.c:629`. [A] | n/a | Changes the clock rate (movement per turn). |
| Gold | One COIN stack, `quan` is `long`, always merges (`invent.c:4391`); merge adds with no overflow check (`invent.c:836`). `mkgold` `mkobj.c:2003`. `nowrap_add` is used only for score (`botl.c:435`, `end.c`), not for gold. [A] | Reversible (drop). | Storage up to LONG_MAX (2^31-1 Windows, 2^63-1 LP64). |
| Stack merging | `mergable()` `invent.c:4379`: same otyp, BUC, `spe`, `oeaten`, known-bits, name, erosion, etc.; needs `oc_merge`. `merged()` does `otmp->quan += obj->quan` (`invent.c:836`) with no cap. `quan` is `long` (`obj.h:47`), `owt` is `unsigned` (`obj.h:46`). [A] | Split via `splitobj` is reversible. [N lines] | A stack is a `long` counter. |
| Object ids | `next_ident()` `mkobj.c:509`: `unsigned`, +rnd(2) per new object/monster; wrap only skips 0 (`mkobj.c:527`). [A] | Monotone. | ~2^32/1.5 creations to wrap: unreachable in practice. |
| Container types | `Is_container(o)` = LARGE_BOX..BAG_OF_TRICKS (`obj.h:337`); `Is_mbag` = BAG_OF_HOLDING or BAG_OF_TRICKS (`obj.h:339`). [A] | | |
| Nesting rule | Boxes, ice boxes, boulders, big statues cannot go into any container (`pickup.c:2613-2620`). Sacks / oilskin / BoH / bag of tricks can nest; **no depth counter found**. [A]+[I] | Fully reversible (take out). | Depth bounded only by the number of non-box containers that exist. Contents never count toward the 52 slots. |
| Weight of nested stuff | `weight()` recurses over `cobj` (`mkobj.c:1911-1955`). BoH: contents x2 cursed, `(x+3)/4` blessed, `(x+1)/2` uncursed (`mkobj.c:1949-1953`). [A] | Recomputed. | Weight is `int`; BoH halves each BoH subtree. |
| Magic-bag explosion | `mbag_explodes(obj,depth)` `pickup.c:2488-2507`: a BoH, bag of tricks, or non-empty wand of cancellation put in a BoH explodes if `rn2(1<<min(depth,7)) <= depth` (certain at depth 0-1, 3/4 at 2, 4/8 at 3, ... 8/128 at 7+), checked recursively through all nested contents. On explosion each content item vanishes w.p. 1/13 (`is_boh_item_gone` `pickup.c:2510`), bag destroyed, `d(6,6)` damage (`pickup.c:2680`). Cursed BoH loot: 1/13 per item (`pickup.c:2537-2546`). [A] | Irreversible. | **Disables BoH-in-BoH gadgets.** |
| Locks | `picklock()` `lock.c:68`: key/lock pick/credit card do not break or get consumed on unlock/lock; attempt aborts after 50 turns (`lock.c:90`); success per turn `rn2(100) < chance` (`lock.c:98`), `chance` from DEX/Rogue (`lock.c:522-531,634-643`). Blade #force can break the blade (`lock.c:98-110`, ~0.8%/turn). [A] | Reversible 1-bit toggle; deterministic given RNG. | Keys/picks/cards are effectively **unlimited-use**; locks/doors are cheap reversible switches costing only turns. |

---------------------------------------------------------------------------------------------------
## 2. Wands, charges, recharging, wresting, creators and duplicators

| Mechanic | Rule | Reversible / deterministic | Gadget relevance |
|---|---|---|---|
| Wand charges | `schar spe`, `SPE_LIM=99` (`obj.h:49,51`). Initial: directional `rn1(5,4)`=4..8, nodir `rn1(5,11)`=11..15, wishing exactly 1, stasis `rn1(4,3)` (`mkobj.c:1115-1124`). [A] | Monotone decreasing except recharge. | Finite per wand. |
| Zap / wrest | `zappable()` `zap.c:2514`: needs `spe>0`; at `spe==0` succeeds w.p. 1/121 (`WAND_WREST_CHANCE`, `hack.h:1411`) then `spe--` to -1 and the wand turns to dust (`zap.c:2677`). [A] | Irreversible only on the successful wrest. | **Retrying a wrest has no resource cost** except game time/hunger: an unlimited-retry loop. Applies to a depleted wand of wishing. |
| Recharge | `recharge()` `read.c:728-800`: wand limit 1 (wishing) / 8 (dir) / 15 (nodir). `recharged` is a **3-bit** field (`obj.h:102`). Explodes if `n>0 && (wishing || n^3 > rn2(343))` (`read.c:761-762`). New charge `rn1(5,lim-4)`, blessed full else `rnd(n)`; if already `spe>=n` then `spe++` (`read.c:771-778`). Rings: explode if `spe > rn2(7)` or `<=-5`. [A] | Irreversible counter. | Each wand yields bounded total; certain explosion at the 8th recharge. |
| Magic marker | `write.c:256-283`: ink `spe` consumed by `rn1(basecost/2, basecost/2)`. [A] | Finite ink. | Scroll/book creation bounded by ink and blank paper. |
| Horn of plenty / bag of tricks | `spe = rn1(18,3)`=3..20 (`mkobj.c:1036-1038`). `bagotricks()` `makemon.c:2554-2601`: 1 charge => 1 monster, plus `rnd(7)` more w.p. 1/23 (`makemon.c:2577-2578`). [A] | Finite (rechargeable <=7x). | Bounded creators. |
| Object polymorph ("polypiling") | `poly_obj()` `zap.c:1702-1850`: replaces each object by random same-class object (`mkobj(oclass)`, 3 tries to keep magic status, `zap.c:1713-1726`), **preserves quantity** (`zap.c:1740`), deletes box contents, never yields WAN_WISHING/WAN_POLYMORPH (`zap.c:1848`) or POT_POLYMORPH (`zap.c:1857`), wand `recharged` may increment. `obj_resists` (`zap.c:1458`) protects some. [A] | Irreversible; deterministic given RNG. | No duplication of object count but converts stacks and can create new containers/wands. |
| Altar sacrifice | `dosacrifice` `pray.c:1854`; corpse must be <=50 turns old (`sacrifice_value` `pray.c:1839-1850`); Luck gain capped at corpse value and 10 (`pray.c:2085-2100`); reduces `ublesscnt` by `value*300` (chaotic 500) (`pray.c:2065-2070`); artifact gift w.p. `1/(6+2*ugifts*nartifacts)` (`pray.c:1792`). [A] | Irreversible. | Finite artifacts; prayer timeout can be driven to 0 with corpses -> repeated prayers. |
| Fountains | `drinkfountain` `fountain.c:243-390`: `rnd(30)`. Every quaff ends in `dryup()` (`fountain.c:389`), which removes the fountain w.p. 1/3 (`fountain.c:204`; certain if warned). Water demon (fate 23, `fountain.c:~69-90`) grants a wish w.p. `rnd(100) > 80+level_difficulty`; snakes `rn1(5,2)` moccasins (`fountain.c:40`); gems once per fountain (looted flag, `fountain.c:355-358`). [A] | Geometric lifetime, **no hard cap**. | Finite almost surely, expected ~3 uses; monster creation (demon/snakes/nymph). |
| Thrones | `sit.c:45-115`: effect `rnd(13)`; case 6 is a wish unless `u.uluck+rn2(5)<0` (`sit.c:105-110`); throne vanishes w.p. 1/3 after effect (`sit.c:223-236`). Vlad's throne: 4 of 13 effects are wishes then it vanishes (`sit.c:242-256`). [A] | Geometric lifetime. | Finite a.s. |
| Sinks / trees | Sink kick gives ring/pudding/dishwasher once each (`dokick.c:1209-1232`); tree fruit once (`TREE_LOOTED`, `dokick.c:1145,1166`). [A] | One-shot. | Finite. |
| Egg laying | `lay_an_egg()` `sit.c:356-387`: female polymorphed hero; needs `u.uhunger >= EGG nutrition`; costs `morehungry(egg nutrition)`. [A] | Costs hunger. | Bounded by nutrition (itself replenishable). |
| Cloning | `clone_mon()` `makemon.c:837-910`: needs `mhp>1`, species not G_EXTINCT; `m2->mhp = mhp/2; mon->mhp -= m2->mhp` (HP conserved, `makemon.c:885-887`); no `propagate()` (not counted toward 120). Triggers: pudding hit with iron/metal weapon (`uhitm.c:1605-1631`, `mhitm.c:455-468`) which splits `mhp` **but not `mhpmax`**; clones regain HP at 1 per 20 turns (`monmove.c:309-310`) or per turn if regenerating; gremlin in water/fountain via `split_mon` (`mon.c:988`, `potion.c:2873-2910`) which halves `mhpmax` too (bounded); long worm (`worm.c:430`); hero-gremlin `cmd.c:920`. XP shrinks for mrevived/mcloned (`exper.c:143`). [A] | Irreversible. | **Pudding farming grows monster count without a counted cap** (limited by free squares, `enexto`, HP regen rate, attacks). |
| Corpse revival | `start_corpse_timeout()` `mkobj.c:1389-1432`: troll corpses get `REVIVE_MON` w.p. ~75% (1/37 per turn for turns 2..50, `hack.h:1405`); Riders always; zombies via `ZOMBIFY_MON` `rn1(15,5)`. `revive` creates with `MM_NOCOUNTBIRTH` (`zap.c:1008`); `norevive` only if killed with a bane (`mhitm.c:1082`, `uhitm.c:1907`). [A] | | **Unbounded kill/revive cycle** (troll loop); XP shrinks (`exper.c:143`). |
| Wizard of Yendor | Re-created after death by `resurrect()` (`wizard.c:715`, called `wizard.c:807`, `do.c:1889`), `clonewiz` (`wizard.c:517`); `mrevived=1`; sets `udemigod` (`wizard.c:818`) which raises random generation to 1/25 per turn (`allmain.c:164`). [A] | | Unbounded harassment source in the endgame. |

---------------------------------------------------------------------------------------------------
## 3. Monster generation, caps, species counters

| Mechanic | Rule | Cap? | Notes |
|---|---|---|---|
| Per-turn random generation | `maybe_generate_rnd_mon()` `allmain.c:162-168`, called once per game turn after movement allotment (`allmain.c:239`): `makemon(NULL,0,0,NO_MM_FLAGS)` w.p. **1/70** (1/50 below the Castle, **1/25** if `udemigod`). [A] | No limit on monsters alive; independent of current population. | |
| Can it be disabled? | `makemon.c:1168`: `if (iflags.debug_mongen || (!level.flags.rndmongen && !ptr)) return 0`. `rndmongen` set to 1 at level creation (`mklev.c:899`, `sp_lev.c:6370`), cleared only by level flag `"nomongen"` (`sp_lev.c:3812`), which appears **only in `dat/tut-1.lua` and `dat/tut-2.lua`** (grep over `dat/*.lua`). `debug_mongen` is a wizard/explore option (`optlist.h:278`, `nhlua.c:1472`). [A] | | Ordinary play (incl. Sokoban) always generates monsters. |
| Hunger can be disabled? | `iflags.debug_hunger` (`eat.c:3167`, `optlist.h:275`): wizard only. [A] | | |
| Species birth cap | `propagate()` `makemon.c:958-983`: random births per species < `MAXMONNO=120` (`global.h:415`; Nazgul 9, Erinys 3: `makemon.c:1550`); at the limit set `G_EXTINCT`; uniques get G_EXTINCT immediately; `born` is `uchar` saturating at 255 (`hack.h:681`, `makemon.c:970`). Called only from `makemon()` (`makemon.c:1233`), `restore.c:412`, `sp_lev.c:2371`. `uncommon()` excludes G_GONE from random choice (`makemon.c:1597`). Explicit `makemon(ptr,..)` ignores G_EXTINCT (only G_GENOD blocks, `makemon.c:1205-1208`); `clone_mon` blocks G_EXTINCT (`makemon.c:846`). [A] | Random births <= 120/species. Clones, revivals, explicit summons escape the cap. | |
| Geometry | One monster per square; `COLNO=80, ROWNO=21` (`global.h:382-383`); `makemon` returns NULL if no free square (`makemon.c:1174-1176,1195-1197`). [A] | <= ~1,600 on a level; migrating/limbo lists unbounded. [I] | |
| Objects per level | No cap constant found (grep for MAXOBJ-style limits in `include/`: none). [N, negative grep] | Unbounded. | |
| Traps per level | One per square; player-creatable by digging. [I] | Bounded by map size. | |
| Dungeon size | `MAXDUNGEON=16`, `MAXLEVEL=32` (`global.h:408-409`). [A] | Finite number of levels. | |

---------------------------------------------------------------------------------------------------
## 4. Monster AI, pets, peacefuls, shopkeepers, priests, guards

- Movement loop: `movemon()` `mon.c:1326` -> `dochug()` `monmove.c:690` -> `m_move()` `monmove.c:1715`. Speed allotment `mcalcmove()` `mon.c:~1130-1167` randomizes via `rn2(2)` / `rn2(NORMAL_SPEED)` (`mon.c:1152,1164`). Count of RNG calls (grep rn2/rnd/rn1/d/rnl/rne/rnz): monmove.c 71, dogmove.c 35, mon.c 158, mhitu.c 121, mhitm.c 39, shk.c 80, priest.c 29, vault.c 44, muse.c 94, dog.c 32. [A]
  => AI is **deterministic given the RNG state**, but heavily randomized; a construction cannot assume monsters are predictable unless RNG consumption is controlled. [I]
- Monster regeneration: `mon_regen()` `monmove.c:307-320`: +1 HP when `moves % 20 == 0`, every turn if `regenerates`. [A]
- Level-away catch-up: `mon_catchup_elapsed_time()` `dog.c:627-` advances blind/frozen/flee timers by elapsed turns (clamped `LARGEST_INT-1`, `dog.c:643-646`) with random thaws (`rn2(imv+1)`, `dog.c:670-674`). Time away changes the level. [A]
- Pets: `tamedog` `dog.c:1143`, `dog_move` `dogmove.c:977`, `keepdogs` `dog.c:789` (adjacent pets follow on level change); pets eat, can starve, fight, and are subject to cloning/revival. [A]/[N details]
- Shopkeepers: standing in the door blocks entry while hero carries a pick-axe/mattock (or Fast with one on the door square) and is not invisible/steed (`shk.c:859-871`, AI `shk.c:4962-4975`). `shopdig` `shk.c:5019`. Robbery -> `call_kops` `shk.c:510`, `makekops` `shk.c:5113`. Money finite. [A door rule; N Kop counts]
- Priests: `priest.c` donation tiers use `rn2` (`priest.c:~504-520`). [N]
- Vault guard: `invault()` called every turn (`allmain.c:357`); guard arrives when `u.uinvault` hits `VAULT_GUARD_TIME=30` (`hack.h:69`, `vault.c:240,326-337`); after guards die, `vgdeathcount<50 && !rn2(vgdeathcount^2)` (`vault.c:334`). [A]
- Carrying the Amulet of Yendor: `amulet()` each turn (`allmain.c:359`, `wizard.c:61`), `intervene()` (`wizard.c:785`), Luck timeout halved (`timeout.c:607`), +1 hunger/20 turns (`eat.c:3266`). [A]

---------------------------------------------------------------------------------------------------
## 5. Player status counters and clocks

| Counter | Type / bound | Dynamics (code) | Monotone? Death? |
|---|---|---|---|
| `moves` | `long` (`decl.h:1165`); **hard stop at 10^9** ("The dungeon capitulates", `done(ESCAPED)`, `allmain.c:253-256`) | +1 per turn (`allmain.c:244`) | Monotone global clock. |
| Hunger `u.uhunger` | `int`; HUNGRY<=150, WEAK<=50, FAINTING<=0 (`eat.c:3369-3372`); starvation death when `< -(100+10*CON)` (`eat.c:3437-3444`); choke at >=2000 (`eat.c:3138,3296`); start 900. | `gethungry()` `eat.c:3163` (called `allmain.c:354`): -1 **every turn** for eaters unless Slow_digestion (`eat.c:3174-3179`; only 1/10 turns while asleep); random extra costs from `rn2(20)` (`eat.c:3191`): regeneration, encumbrance, Hunger, Conflict, rings (slots 4,12), amulet (8), carrying Amulet (16); Slow_digestion leaves 1/20 (`eat.c:3232-3236`). Intake: food, fountain water `rnd(10)` (`fountain.c:281`), potions, prayer sets 900 (`eat.c:129`). | **Hard clock**: starvation within ~1000-2000 turns of a ration; slowed to ~1/20 by slow digestion; stopped only by non-eating polymorph + Unchanging or wizard `debug_hunger`. |
| HP | `int uhp, uhpmax`; `regen_hp` `allmain.c:625-682`: heal 1 w.p. `(ulevel+CON)/100` per turn (encumbrance permitting); Regeneration +1. `uhpmax` raised by level, potions (`potion.c:1438`), prayer +5 (`pray.c:1255`), throne +4 (`sit.c:91`). No explicit cap other than `int`. | | Death at HP<1 -> `done()`. |
| Pw | `u.uen/uenmax`; `regen_pw` `allmain.c:600-622` every `(30+8-ulevel... )*(4 or 3)/6` turns by `rn1(upper,1)`. | | Bounded by `uenmax`. |
| Level / XP | `ulevel <= MAXULEV=30` (`global.h:413`); `u.uexp` clamps at LONG_MAX (`exper.c:179-181`). | | |
| Luck | `u.uluck` in [-10,10] (`you.h:467-468`, `attrib.c:411-418`); drifts to baseluck every **600** turns (300 with Amulet/god anger) (`timeout.c:606-620`); luckstone blocks. | Reversible. | |
| Prayer timeout `u.ublesscnt` | `int`; start 300 (`u_init.c:1005`); **-1/turn** (`allmain.c:276-277`); after good prayer `rnz(350)` (`pray.c:1356`) + `rnz(1000)` per kick (demigod / hand of Elbereth, `pray.c:1357-1362`); **anti-bot throttle**: if `moves>100000`, `ublesscnt += (moves-100000)/100`, capped at 32767 (`pray.c:1365-1378`). `rnz` `rnd.c:214-229`. Prayer works when `ublesscnt<=200` in major trouble, `<=100` minor, `0` none (`pray.c:2151-2153`) and Luck>=0, alignment>=0, god not angry (`pray.c:2154`). Low-HP trouble: `curhp<=5 || curhp*divisor<=maxhp`, divisor 5..9 by level (`pray.c:116-155`). | | Free full heal / hunger reset; period grows after turn 100000. |
| Alignment | `int record`; `adjalign` `attrib.c:1298`; upper limit `ALIGNLIM = 10 + moves/200` (`align.h:17`) -> grows with clock. | | |
| Intrinsic timeouts | `TIMEOUT=0x00ffffff` (`prop.h:135`), decremented in `nh_timeout()` `timeout.c:588`. | | |
| Polymorph / random events | `u.mtimedone` decremented per turn; at 0 `rehumanize()` or, if Unchanging, re-rolled `rnd(100*mlevel+1)` (`timeout.c:641-648`). Random self-polymorph `Polymorph && !rn2(100)` (`allmain.c:325`), lycanthropy `!rn2(80-20*night())` (`allmain.c:328`), teleportitis `!rn2(85)` (`allmain.c:308`). | | |
| Misc per-turn | Searching `dosearch0(1)` (`allmain.c:344`), `age_spells()` (`allmain.c:355`), engraving wipe `!rn2(40+3*DEX)` (`allmain.c:360`), `seer_turn` `rn1(31,15)` (`allmain.c:415`). | | Spell memory decays: another clock. |

---------------------------------------------------------------------------------------------------
## 6. Death / quit / save / escape

- `done(how)` `end.c:1020`; `u.umortality++` (`end.c:1070`). **Lifesaving** (worn amulet) intercepts once for `how <= GENOCIDED`: amulet destroyed, -1 CON, `savelife()` (`end.c:1081-1095`). [A]
- `#quit` -> `done2()` `end.c:90` after "Really quit without saving?". `S`/`#save` saves and exits (RNG state saved). `done(ESCAPED)` for leaving the dungeon and for the 10^9-turn stop. [A]
- `#pray` `dopray` `pray.c:2200-2262`: `nomul(-3)` helpless with `u.uinvulnerable`; `can_pray()` `pray.c:2124-2174` sets p_type; success p_type 3 fixes worst trouble (HP -> max, hunger 900) and resets timeout (`pray.c:1356`). [A]
- `#exploremode` (`cmd.c:952`) is available in ordinary play and allows undoing death (disqualifies scoring). A reduction must forbid it. [A]

---------------------------------------------------------------------------------------------------
## 7. Command set (`src/cmd.c:1667 extcmdlist[]`; 213 brace-entry lines in cmd.c)

Source: `struct ext_func_tab extcmdlist[]` (key, name, function, flags). WIZMODECMD entries are unavailable in normal play. Y = changes game state, n = display/info only, c = conditional.

Y (normal play): apply(a), adjust(M-a; no time), cast(Z), chat(M-c), close(c), dip(M-d), down(>)/up(<), drop(d)/droptype(D), eat(e), engrave(E), enhance(M-e), fire(f), force(M-f), invoke(M-i), jump(M-j), kick(^d), loot(M-l), monster(M-m; polymorph abilities such as breathe, spit, summon, egg, mindblast, gremlin split), offer(M-o), open(o), pay(p), pickup(,), pray(M-p), puton(P)/remove(R), quaff(q), quiver(Q), read(r), ride(M-R), rub(M-r), search(s), sit(M-s), swap(x), takeoff(T)/takeoffall(A), teleport(^t), throw(t), tip(M-T), turn(M-t), twoweapon(X), untrap(M-u), wait(.), wear(W), wield(w), wipe(M-w), zap(z); movement move*/rush*/run*/travel(_)/retravel; prefixes F, m, G, g; repeat(^a); `#exploremode`; `save`(S), `quit` (exit).
c: autopickup(@), options(O)/optionsfull/toggle/saveoptions (behavioral options), call/name (stores text), showspells (reorder).
n: attributes, bugreport, chronicle, conduct, genocided, glance, help, herecmdmenu, history, inventory, inventtype, known, knownclass, look, lookaround, overview, perminv, prevmsg, redraw, reqmenu, seeall, seeamulet, seearmor, seerings, seetools, seeweapon, showgold, showtrap, terrain, therecmdmenu, vanquished, version, versionshort, whatdoes, whatis, annotate, shell, suspend.
WIZMODECMD (unavailable in normal play): debugfuzzer, levelchange, lightsources, migratemons, panic, polyself, stats, timeout, vision, wizborn, wizbury, wizcast, wizcustom, wizdetect, wizdispmacros, wizfliplevel, wizgenesis, wizidentify, wizintrinsic, wizkill, wizlevelport, wizloaddes, wizloadlua, wizobjprobs, wizmakemap, wizmap, wizmondiff, wizrumorcheck, wizseenv, wizshownhuuid, wizsmell, wiztelekinesis, wizwhere, wizwish, wmode.
INTERNALCMD: clicklook, mouseaction, altadjust, altdip, alttakeoff, altunwield.
Count prefixes accepted up to `LARGEST_INT` (`cmd.c:5118`, `dothrow.c:299`, `invent.c:1944`). [A]

---------------------------------------------------------------------------------------------------
## 8. Unbounded-state sources

**Can the reachable state of a single game be unbounded?** Every C integer is finite and the game ends at 10^9 turns, so the state space is finite; but nothing in the game rules bounds object count, container depth, stack size, or population of cloned/revived monsters by a polynomial in a small parameter. Specifically:

1. **Time**: `long moves`, hard stop 10^9 (`allmain.c:253`). Random spawns accrue at 1/70 per turn, so entities grow Theta(T/70) (subject to 120 per species). [A]
2. **Objects**: no per-level or per-square cap. Sources without an explicit finite budget: monster death drops and corpses (every spawn yields objects, `mon.c:3181 corpse_chance`), troll/Rider/Wizard revival loops (`mkobj.c:1418-1424`, `zap.c:1008`), pudding division (`uhitm.c:1605`), egg laying (nutrition-bounded, `sit.c:356`), fountain geometric lifetime (`fountain.c:204`), wand wresting at 1/121/turn with no cost (`zap.c:2516`).
3. **Stack quantity**: `long quan` (`obj.h:47`), `merged()` adds without overflow check (`invent.c:836`); weight of corpses clamped to `LARGEST_INT` (`mkobj.c:1960`); gold similarly `long`. Bound: 2^31-1 (LLP64) or 2^63-1 (LP64).
4. **Container depth**: unbounded in principle (recursive `weight()` `mkobj.c:1934`); only the number of existing non-box containers limits it; boxes cannot nest (`pickup.c:2613`).
5. **Monsters**: <= one per square (~1,600 per level) alive on a level, but clones/revivals escape tallying (`makemon.c:837`, `zap.c:1008`), and migrating/limbo lists are unbounded.
6. **Species tallies**: `mvitals.born/died` are `uchar`, saturating at 255 (`makemon.c:970`, `mon.c:3135`); random births capped at 120/species (`global.h:415`).
7. **Player scalars**: `uhpmax`/`uenmax` `int` (no cap besides overflow); `ulevel<=30`; `u.uexp` saturates at LONG_MAX (`exper.c:179`); Luck in [-10,10]; `ublesscnt` capped at 32767 only by the post-100000-turn increment (`pray.c:1373-1376`); alignment limit grows ~moves/200 (`align.h:17`).
8. **Terrain**: ROWNO x COLNO fixed grid, but terrain is player-mutable (digging, boulders, holes, pits, engravings) and trap/engraving state is per-square (bounded by map size). Finite number of levels (<= 16 x 32 slots).
9. **RNG state**: ISAAC64 context is part of the game state (fixed size). [I]

Hard caps that do exist: 52 inventory stacks (+gold); 1000 carried weight; 120 random births/species (Nazgul 9, Erinys 3); ~1,600 monsters/level (geometry); `recharged` 3-bit (<=7 recharges); `spe` <= 99; Luck +/-10; level <= 30; turns <= 10^9; post-100000-turn prayer throttle.

---------------------------------------------------------------------------------------------------
## 9. Must-disable list for reductions

1. **Random monster generation** (1/70 per turn, `allmain.c:162-168`; 1/25 after `udemigod`). Cannot be switched off in real levels (only `nomongen` in tutorial levels or wizard `debug_mongen`). Either keep play to poly(n) turns and treat spawns as bounded adversarial noise, or choose a level where they are harmless.
2. **RNG-driven monster moves** (`monmove.c`, `mon.c:1152,1164`): the construction must hold for all RNG outcomes, or the problem is about the randomized game.
3. **Hunger clock** (`eat.c:3163-3180`, starvation `eat.c:3437`): needs a bounded budget or a controlled unbounded food source (fountain/corpses).
4. **Prayer** (`pray.c:2200-2262`, `1356-1378`): a repeatable free heal/hunger reset; period `rnz(350)` and growing after turn 100000. Treat as a bounded recovery resource or keep HP/hunger out of trouble.
5. **Lifesaving and explore/wizard mode** (`end.c:1081`, `cmd.c:952`): forbid.
6. **Pudding division** (`uhitm.c:1605`, `mhitm.c:455`, `makemon.c:837`): iron/metal hits on black/brown puddings replicate monsters with no counted cap. Forbid or exclude puddings.
7. **Troll/Rider/Wizard revival** (`mkobj.c:1418-1424`, `zap.c:1008`, `wizard.c:715,807`): unbounded respawn. Exclude trolls (or use banes), exclude endgame.
8. **Wishes** (`zap.c:6314 makewish`; callers `allmain.c:201,450`, `fountain.c`, `sit.c:105-110,251`, `potion.c:2809`, `zap.c:2583`): arbitrary object creation. Exclude wands of wishing (and their 1/121 wresting retry), magic lamps, fountain quaffing/dipping, thrones, Vlad's tower.
9. **Wand wresting and recharging** (`zap.c:2516`, `read.c:728`): free retries and counter resets; restrict to wands with finite budgets.
10. **Polymorph** (traps, wands, potions, rings, `polyself`, object polymorph `zap.c:1702`): changes entity types, capacity and move rate (`hack.c:4295`, `allmain.c:114`); exclude.
11. **Digging and terrain mutation** (pick-axe, wand of digging, scroll of earth): lets the player restructure the maze. Use undiggable levels or ban tools. Sokoban's first level has `noteleport`, `premapped`, `sokoban`, `solidify` (`dat/soko1-1.lua:7`); whether walls are undiggable depends on the `solidify` handling [N].
12. **Teleportation / level change** (`allmain.c:308`, `^t`, trapdoors): breaks locality; Sokoban is `noteleport`.
13. **Autonomous agents**: shopkeepers (`shk.c:4962`), vault guards (`vault.c:326-337`), priests (`priest.c`), pets (`dogmove.c:977`): keep out of the construction or park them.
14. **Wall-clock inputs** (`allmain.c:57-65`, `night()`): fix the date; Luck drift (`timeout.c:606-620`) moves `rnl()` outcomes.
15. **`moves`-dependent thresholds**: prayer throttle (>100000, `pray.c:1365`), alignment limit (`align.h:17`), hard stop (1e9, `allmain.c:253`), corpse ages (50/250 turns, `hack.h:1404-1406`), sacrifice freshness (50, `pray.c:1844`). Any time-unbounded construction crosses these.
16. **Magic-bag explosions** (`pickup.c:2488-2507`, `2537`): avoid BoH-in-BoH and cancellation wands in bags.
17. **Inventory limit 52** (`hack.h:584`): usable as a structural bound, but unbounded memory must live in containers or floor stacks.
