# EXPTIME mechanisms audit: monsters and traps as nature's choice (R3)

Author: source-audit sub-agent, 2026-10-29. Source: NetHack 5.0.0 @ 16ff591, read-only; paths `src/<f>` mean
`src/src/<f>`. Nothing built or run. Labels: **[src f:l]** read this session; **[conj]** reasoning only.
Setting: hu-off.md (hunger off, Sokoban flag, cursed loadstone, Valkyrie, no pet) under **R3** (every RNG
outcome chosen by an adaptive, fully informed adversary = "nature").
Question: can a monster or a trap give nature a clean, local, repeatable binary choice without extra powers?

## 0. Verdict (ranked)

| Rank | Mechanism | Nature's choice | Stall-proof? | Verdict |
|---|---|---|---|---|
| 1 | **Teleport fork**: random TELEP_TRAP on a level WITHOUT `noteleport`, inside a teleport exclusion box holding exactly two landing cells | lands hero on L1 or L2 | yes, if L1, L2 are walk-adjacent to the trap (escape = hero's choice, nature never uses it) | **best candidate**; ≤ 3 forks per level (2 boxes); boulders must never reach the trap (§3.2) |
| 2 | **Monster boulder-gate**: peaceful floating eye that the hero can never stand next to; it blocks a boulder push lane | which lane is blocked, re-chosen 0/1 step per turn | yes ("stay" is nature's, hero never waits on it alone) | **promising, R3 only**; needs anger-proof geometry, confinement by water + taught squeaky boards (§2.6) |
| 3 | Monster hero-gate (eye stands on the hero's path) | which gate cell is occupied | yes (swap refused deterministically from a trap square) | **weak**: hero can always anger it (F-prefix); hostile eye only stays or steps toward hero, so gadget must survive "frozen" mode |
| 4 | Web / bear trap / pit | delay length in a bounded range | **yes, nature can NOT hold the hero forever** | no positional choice; in a monsterless level a delay is a no-op; with a nature monster = bounded tempo gift; pits and bear traps also damage (finite use, §1.3) |
| 5 | Squeaky board, rust trap | trigger or "escape" | n/a | pure no-op; useful only as a **monster barrier** after the monster learns the type (§2.6) |
| 6 | Magic trap | menu of 20 fates | n/a | NO: fate 20 uncurses inventory (frees the loadstone), flash blinds, explosion; not positional |
| 7 | Rolling boulder, land mine, fire, sleeping gas, anti-magic | damage / sleep / scatter | — | NO: damage is permanent under R3 (§1.3); land mine scatter is one-shot |
| 8 | Hole, trapdoor, level teleporter | — | — | loss gadgets only |
| ✗ | Doors (other agents) | open/close may fail forever | **no** | NO-GO, nature stalls |

Headline: traps alone give nature no positional choice EXCEPT the teleport trap; monsters give one, but the hero
can anger any monster it can reach, so the clean monster gadget keeps the monster out of the hero's reach.

## 1. Global facts

### 1.1 Placing a monster at all [src]
- `nh.debug_flags{mongen=false}` sets `iflags.debug_mongen` and `mongone()`s every live monster
  [src nhlua.c:1463-1482]; then `makemon` returns NULL for every call, specific or random:
  `if (iflags.debug_mongen || (!svl.level.flags.rndmongen && !ptr)) return 0;` [src makemon.c:1168].
  So **with debug_mongen, `des.monster` is impossible** (before the call it is killed, after it is refused).
- Replacement: level flag `nomongen` sets `rndmongen = 0` [src sp_lev.c:3812-3813]; this blocks only
  `makemon(NULL, ...)`. The per-turn random spawn is `makemon((struct permonst *) 0, ...)` [src allmain.c:160-167],
  so it stays blocked. `des.monster` passes an explicit `pm` → `makemon(pm, x, y, ...)` [src sp_lev.c:1988] works;
  `peaceful` and `asleep` are honoured [src sp_lev.c:2126-2132].
- Cost: explicit-pointer creators become live. Found: prayer anger → `summon_minion` → `makemon(&mons[mnum], ...)`
  [src pray.c:684-686, 771; minion.c:198-239]; shrieker → purple worm [src mon.c:4095-4102]. Prayer is a hero
  choice and its outcome is nature's, so the hero never prays (it can only be hurt) [conj]. hu-off A.1 item 2 and the
  harness assertion "no monsters" must be rewritten for `nomongen` (monster count still ≤ w·h: poly state).
- Death drops (other agents' concern): level flag `nodeathdrops` exists [src sp_lev.c:3814-3815]; use it, or make the
  monster unkillable (§2.3). Floating eye leaves corpses (no G_NOCORPSE) [src include/monsters.h:333-339].
- `des.monster` cannot set trap knowledge (`seentraps = 0`, "TODO") [src sp_lev.c:3311, 2133-2134].

### 1.2 Monster speed under R3 [src mon.c:1155-1166]
`mcalcmove` rounds speed s to a multiple of 12 at random: movement = 12·⌊s/12⌋ + (12 if rn2(12) < s mod 12).
So under R3: **0 < s < 12 → nature chooses 0 or 12 each turn (stay or one action)**; s = 12 → exactly one action
(forced); 12 < s < 24 → one or two. Hero (XL1, unencumbered, not Fast) gets exactly 12 per turn [src allmain.c:114-155].

### 1.3 No HP regeneration under R3 [src allmain.c:658-660]
Below XL10 without Regeneration: `heal = (u.ulevel + ACURR(A_CON)) > rn2(100)`; nature picks rn2 ≥ 19 forever.
So **every damage point is permanent** (prayer healing only fixes HP ≤ 5 or < max/7 and depends on prayer outcomes;
not re-checked). Any repeatedly crossed damaging trap or hostile attacker eventually kills: such gadgets are finite-use.

### 1.4 Seen traps: nature may always "escape" [src trap.c:3026-3044]
For a trap with `tseen`, not forced, not Fumbling, not undestroyable, not ANTI_MAGIC, not pit-adjacency cases:
`!rn2(5)` → "You escape a <trap>." and nothing happens. Sokoban pits/holes have no escape (air currents,
[src trap.c:3014-3025]). Sitting on a trap (`#sit`, VIASITTING) is not FORCETRAP and also allows escape
[src sit.c:503]. Fumbling would remove the option, but the Valkyrie resists cold, so ice gives none
[src hack.c:2396-2415]. **Consequence: every trap gadget must make "nothing happens" useless to nature.**

## 2. Monsters

### 2.1 Peaceful movement is nature's free choice [src]
- dochug sends every peaceful to `m_move` [src monmove.c:882-911]. In `m_move`, `appr = 0` for any peaceful
  non-shopkeeper [src monmove.c:1869]; candidates come from `mfndpos`, and with `appr == 0` the pick is reservoir
  sampling: the first candidate is taken, each later one replaces it with chance 1/chcnt [src monmove.c:1969-1977].
  So **nature can pick any legal neighbour**; with s < 12 it can also stay (1.2). If there is no candidate, it stays.
- Peacefuls never enter the hero's square (no ALLOW_U) [src mon.c:2080-2083]; never enter a boulder square unless
  ALLOW_ROCK (passes_walls, throws_rocks, rider/shk/priest/leader) [src mon.c:2091-2095, 2334-2338;
  monmove.c:133-139]; avoid a **known** non-harmless trap [src mon.c:2355-2369].
- Peacefuls look for items only on `!rn2(10)` [src monmove.c:1891]; a M1_NOTAKE monster takes nothing.
- Elbereth does not affect peacefuls (`onscary` returns FALSE for `mpeaceful`) [src monmove.c:294-302].

### 2.2 Hero meets a peaceful [src]
- `is_safemon` = option `safe_pet` on, peaceful, seen, hero not Conf/Hallu/Stun [src include/display.h:159-161];
  `safe_pet` and `confirm` can be toggled in game [src include/optlist.h:239, 633].
- Bump with safemon: `Punished || !rn2(7)` → "You stop. X is in the way!" (turn used) [src uhitm.c:462-500]; else the
  hero tries to swap [src hack.c:2920-2922 → 2098-2175]. Swap with a peaceful is **refused with no RNG** when the
  hero's square fails `goodpos` for it, **has a trap**, or the monster is undisplaceable [src hack.c:2153-2161].
  So: R3 → nature decides block/swap; from a trap square → always blocked (R1-R4).
- `m` prefix into a monster: "Pardon me", no move [src hack.c:1925-1946]. Boulder pushed at a monster: "There's X
  on the other side", push refused, no RNG [src hack.c:451-478].

### 2.3 The hero can always anger a reachable monster [src]
- `F<dir>` sets forcefight: safemon is skipped [src uhitm.c:462] and `attack_checks` returns before the "Really
  attack?" prompt [src uhitm.c:201-212]. A miss calls `missum` → `wakeup(mdef, TRUE)` → `setmangry`
  [src uhitm.c:5198-5214; mon.c:4333-4362]. So a miss still angers.
- Only blocker: `check_capacity` needs Overtaxed (EXT_ENCUMBER) [src hack.c:4399-4409], but Overtaxed moving costs
  HP [src allmain.c:298-301] that R3 never returns (1.3), then the hero cannot move at all
  [src hack.c:2616-2634]. Not viable. Kicks are blocked above Burdened [src dokick.c:1282-1283].
- To-hit [src uhitm.c:365-420, 780-781]: hit iff tmp > rnd(20), tmp = 1 + abon + AC + uhitinc + Luck term + ulevel
  (+2 flee, +2 asleep, +4 can't move) + bare-hand bonus. abon ≤ 8 [src weapon.c:950-990], bare-hand bonus +1 at
  Unskilled/Basic [src weapon.c:1601-1613], Luck ≤ 0, XL 1. **Floating eye (AC 9), peaceful, awake: tmp ≤ 20, so
  nature always makes the hero miss: the eye is unkillable** → no corpse, no death drop. Hostile + fleeing (+2) could
  reach 22; nature avoids that by picking low Dex/Str at `u_init` (abon ≤ 6) [conj: attribute rolls are RNG].
- Hostile, no active attacks, adjacent to the hero: never moves (`nearby` and not scared) [src monmove.c:882-887];
  not adjacent: steps toward the hero (`appr = 1`, greedy) or stays (s < 12); flees Elbereth only when the hero stands
  on it [src monmove.c:533-567, 294-302]. Hostiles still avoid known traps. So **anger shrinks nature's options to
  {stay, greedy step}**: gadgets must stay sound in that mode, or keep the monster out of the hero's reach.

### 2.4 Candidates (no active attack, speed > 0) [src include/monsters.h, scan of all entries]
| Monster | Speed / AC / size | Notes | Verdict |
|---|---|---|---|
| **floating eye** | 1 / 9 / small, flies, M1_NOTAKE | passive paralysis only if hit (never, 2.3); crosses water, avoids lava (`lavaok = FALSE`) [src mon.c mfndpos] | **best** |
| gas spore | 3 / 10 / flies | explodes 4d6 on death; AC 10 → tmp ≤ 21, killable at abon 8 | backup if nature fixes low abon |
| acid blob | 3 / 8 / tiny, amorphous | passes iron bars and closed doors; passive acid | possible, harder to confine |
| shrieker | 1 | shrieks next to hero → 1/10 makemon, 1/13 of those an explicit purple worm (passes `nomongen`) [src mon.c:4089-4125] | **NO** |
| molds, jellies, Oracle | 0 | never move | NO |
| lichen, grid bug, cockatrice | — | have attacks (stick, bite, stoning) | only if anger must be fatal; grid bug is NODIAG with speed 12 (forced moves) |

None of the eye's extra powers apply: no teleport, dig, multiply, summon, item use, boulder moving, stairs
(only the sealed branch pocket), no death by age or hunger [conj: no such mechanic seen].

### 2.5 Monster confinement tools [src]
- Water: eye floats over it, hero cannot enter. But a pushed boulder fills water, making land; keep boulders away.
- **Taught squeaky boards**: with the Sokoban flag on, floor traps are never "harmless" to flyers
  (`!Sokoban && ...` guard) and SQKY_BOARD is harmful by default [src trap.c:1106-1123]; a monster that knows the type
  will not step on it (peaceful or hostile) [src mon.c:2364-2367]. It learns when it sees the hero trigger an
  **unseen** board (no escape option on the first trigger) within dist² ≤ 49 on a lit square, if it is not an animal,
  not mindless, has eyes [src mondata.c:1641-1657; trap.c:3045-3046]. The eye qualifies. For the hero a board only
  wakes monsters [src trap.c:1403-1437; mon.c:4367-4399]: a no-op. The hero should teach at turn 1.
- Swaps never happen from a board square (2.2).

### 2.6 Gadget M-B: monster boulder-gate (rank 2)
Eye zone Z = water channel plus land cells r₁..r_k, each r_i the push destination of a boulder lane; Z sealed by
walls, water and taught boards; no hero-reachable cell within Chebyshev distance 1 of Z (so no bump, no F-attack, no
kick: no anger, no kill, no swap). While the eye sits on r_i, pushing lane i is refused (2.2); nature moves the eye
0/1 step per turn (1.2). Each lane push is a hero commitment and nature answers with the eye's position: the
adversary can block any one lane it can reach in time. **Open [conj]:** (a) the race/tempo geometry that makes this a
binary ∀ choice (channel length vs hero path length); (b) after a push the hero stands on the lane's old boulder
square, which must still be ≥ 2 from Z; (c) boulders must never be pushed into the channel water.
State: one `struct monst` per gadget, O(1) words.

### 2.7 Gadget M-H: monster hero-gate (rank 3)
Eye on gate cells A, B of the hero's routes; hero approaches only from board squares, so swaps are refused in every
semantics. Works under R3 until the hero F-attacks the eye; then nature keeps only "stay" or "step toward hero",
which can freeze the gate at its last value or let the eye follow the hero. Usable only if every gadget is proved
sound against the frozen mode too.

## 3. Traps

### 3.1 Table [src trap.c unless noted]
| Trap | Hero effect | Nature's choices | Stuck forever? | Verdict |
|---|---|---|---|---|
| SQKY_BOARD | `wake_nearby` [1403-1437] | trigger / escape | no | no-op; monster barrier (2.5) |
| BEAR_TRAP | `u.utrap = rn1(4,4)` (4-7), d(2,4) dmg, wounded legs 10-19 [1479-1561] | length, dmg | **no**: every diagonal move attempt decrements (orthogonal only on 1/5) [src hack.c:1567-1578] | finite use (damage) |
| PIT | utrap rn1(6,2) (2-7), rnd(6) dmg unless deliberate/conjoined [1920-1955] | length, dmg | **no**: `climb_pit` decrements each attempt [4183-4224]; exception: boulder in the pit → 1/2 "crevice" loop (unreachable if boulders fill pits) | finite use; Sokoban gives no escape |
| WEB | utrap 1-11 by Str; Str ≥ 18/51 tears and deletes the web [2106-2200] | length | **no**: `--u.utrap` per move attempt [src hack.c:1588-1606] | delay only |
| TELEP_TRAP, `noteleport` level | "You feel a wrenching sensation", nothing [src teleport.c:1502-1505] | none | — | inert |
| TELEP_TRAP, no `noteleport` | random teleport (3.2) | landing cell | — | **rank 1** |
| boulder pushed onto TELEP_TRAP | `rloco`: boulder to any goodpos cell, **ignores noteleport** [src hack.c:578-590; teleport.c:2102-2139] | global placement | — | **hazard**: nature drops a boulder anywhere |
| MAGIC_TRAP | 1/30 explosion rnd(10) + trap deleted, else `domagictrap` fate rnd(20) [2293-2321, 4317-4440] | fate | — | NO: fate 20 uncurses all (loadstone free), fate < 10 blinds + makemon(NULL) |
| ANTI_MAGIC | drains energy | — | — | no-op, not positional |
| ROLLING_BOULDER, LANDMINE, FIRE | damage; land mine scatters objects then becomes a pit | dmg, scatter | — | NO (1.3), one-shot |
| SLP_GAS | sleep ≤ 25 turns | length | no | delay only |
| HOLE, TRAPDOOR, LEVEL_TELEP | leave level | — | — | loss gadgets |

### 3.2 Gadget T-F: teleport fork (rank 1)
- Random tele trap → `tele()` → `scrolltele(NULL)` → `safe_teleds` [src teleport.c:1530-1531, 842-847, 849-?, 717-772]:
  40 tries at `(rnd(COLNO-1), rn2(ROWNO))`, take the first `teleok(x, y, FALSE)`; then a shuffled full scan; a trap
  cell only if nothing else fits. Under R3 nature names the coordinates, so **the landing cell is any teleok non-trap
  cell, nature's choice**; nature cannot make it fail while a candidate exists.
- `teleok` = no trap, `goodpos` (no monster, no boulder), `tele_jump_ok`, region ok [src teleport.c:420-446].
  `tele_jump_ok`: if the start is inside the dndest (or updest) **exclusion box** (`nlx > 0`), the target must be inside
  too, and vice versa [src teleport.c:386-418].
- Boxes come from `des.teleport_region{region=..., exclude={x1,y1,x2,y2}, dir=...}` [src sp_lev.c:5410-5459];
  `fixup_special` copies the exclude area into `updest`/`dndest` (`dir="both"` writes both) [src mkmaze.c:611-634].
  Only two slots → at most 3 fork classes (A only, B only, A ∩ B); the main play area must lie outside both. One of
  the regions can also serve as the hero's start region (inarea = s, exclude = box).
- Layout: box = one row [L1 T L2]; hero enters T from outside the box; L1, L2 exit outside the box. Landing set
  = {L1, L2}. If nature takes the seen-trap escape (1.4), the hero stands on T and picks L1 or L2 himself, so nature
  never escapes. From L1, stepping back on T re-triggers; nature can always return him to L1. Under R2 the hero picks:
  the fork is ∀ only in R3.
- Requirements: drop `noteleport` (hu-off used it only as belt-and-braces); no boulder may ever reach a tele trap
  (3.1 hazard); keep L1, L2 free of boulders. No `sokoban_guilt` in teleport code [grep: none in teleport.c].
  State: no growth. **Open [conj]:** whether ≤ 3 reusable ∀ hubs suffice for an ASPACE(poly) = EXPTIME simulation
  (route every ∀ step through one hub; I think yes, needs a design).

## 4. Answers to the brief
- A(1) harmless: floating eye peaceful never attacks; hero can always anger it (2.3) but cannot hit it (tmp ≤ 20).
- A(2) random position: yes, any neighbour, plus stay for speed < 12 (2.1, 1.2).
- A(3) blocks the hero: yes; R3 swap is nature's, from a trap square it is refused deterministically (2.2).
- A(4) boulders: eye cannot move them; boulders cannot be pushed onto it. `debug_mongen` blocks `des.monster`;
  use `nomongen` (1.1).
- B: no trap lets nature hold the hero forever (web, bear trap, pit all decrement per attempt). Only the teleport trap
  gives a positional choice; seen traps always offer nature a no-op escape (1.4); damage is permanent under R3 (1.3).

## 5. Spec changes the candidates need
1. Replace `mongen=false` by level flag `nomongen` (+ `nodeathdrops`), keep `pettype:none`; rewrite hu-off A.1 item 2.
2. Teleport fork: remove `noteleport`; whitelist TELEP_TRAP and `teleport_region` with `exclude`.
3. Monster gadgets: whitelist `des.monster{id="floating eye", peaceful=1, asleep=0}`, SQKY_BOARD, water.
Not checked: `rloc` box rules for monsters, prayer healing under R3, doors (other agents: NO-GO).
