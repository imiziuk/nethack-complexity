# EXPTIME mechanics audit: doors as a "nature choice" gadget (R3)

Author: door-audit sub-agent, 2026-10-29. Source: NetHack 5.0.0 @ 16ff591, read-only; paths `src/<f>` = `src/src/<f>`,
`include/` = `src/include/`. Nothing built or run. Labels: **[src f:l]** read this session; **[conj]** my reasoning.
Setting: phase2-spec Rev. 1-3 (female human Valkyrie, only a cursed loadstone, Sokoban flag, hunger off, mongen off,
no monsters), semantics R3: every RNG outcome chosen by an adaptive, fully informed adversary ("nature").

## 0. Verdict (short)

**Doors do not give a usable nature choice.** Every door roll is a *veto* that nature can repeat forever at no cost,
and the "open" outcome never hurts the player. So under R3 nature's optimal play is fixed and trivial: never open,
never break, never unlock (and never let an open door close, which the player never wants anyway). Consequences:

- Under R3: closed / locked / secret doors = walls; open doors = floor that forbids diagonal steps; doorless/broken
  doorways = floor. No alternation is created; doors add nothing toward EXPTIME-hardness.
- Under R2 (∃): closed doors = floor (player opens them at will). So **any construction that needs a closed door opened
  breaks answer-level DET** (R2 ≠ R3). Current reductions are unaffected: L_OFF uses no doors; hu-on-lower's "G_D one-way
  door" is a boulder gadget, and §7 item 5 states no NetHack doors are used [checked: proofs/hu-on-lower.md:665].
- Doors created with an explicit state are trap-free and deterministic as terrain; they are DET-safe only as "open"
  (diagonal-blocking floor), "nodoor"/"broken" (floor) or "locked"/"closed" (wall under R3, floor under R2: avoid).

## 1. Thresholds: both outcomes are always available to nature

All door rolls compare a die to T = (ACURRSTR + Dex + Con)/3 (integer division).
- Human attribute caps: Str 18/100, Dex 18, Con 18; min 3 [src role.c:596-597]. `acurrstr()` maps Str ≤ 18/100 to
  ≤ 21 [src attrib.c:1245-1262]. No item gives bonuses (inventory = loadstone [+ ball/chain]). So **3 ≤ T ≤ 19** for
  every attribute vector, including the (nature-chosen, under R3) starting attributes and later exercise drift.
- `rnl(x)` [src rnd.c:112-151]: Luck 0 → no adjustment, i = RND(x) ∈ [0, x−1]. For any Luck ∈ [−10, 10] the
  adjustment is skipped when `rn2(37+|adj|) == 0`, so i = 0 and i = x−1 both stay reachable. Luck cannot be raised
  anyway (hu-off I5); doors never change Luck (no `change_luck` in lock.c/dokick.c door paths).
- Hence: open `rnl(20) < T` (0 succeeds, 19 fails); close `rn2(25) < T` (0 / 24); kick `rnl(35) < T` (Valkyrie is not
  `martial()`; 0 / 34); key/pick `rn2(100) < ch` with ch ≤ 70+18 = 88 (0 / 99). **Nature always has both outcomes.**

## 2. Door states and terrain rules (verified)

| Fact | Source |
|---|---|
| doormask: NODOOR 0, BROKEN 1, ISOPEN 2, CLOSED 4, LOCKED 8, TRAPPED 0x10 flag | [src include/rm.h:233-239] (per mechanics/terrain-movement.md; consistent with all code read) |
| `doorless_door` = DOOR typ with mask ⊆ {NODOOR, BROKEN} (rogue level excepted) | [src hack.c:4061-4074] |
| Hero: closed door blocks entry (autoopen → open attempt, see §3); no diagonal **into** a door square unless doorless | [src hack.c:1074-1150] |
| Hero: no diagonal **out of** a door square unless doorless | [src hack.c:1208-1214] |
| Boulder push: destination door + diagonal push forbidden unless doorless | [src hack.c:432-435] |
| Boulder push: Sokoban forbids every diagonal push anyway | [src hack.c:441-448] |
| Boulder push into a CLOSED/LOCKED door: refused (`cannot_push`, no move) | [src hack.c:485-488] |
| Boulder push orthogonally onto an open / broken / nodoor door: allowed (normal push) | [src hack.c:432-500] |
| Closing needs the square free of objects and monsters (`obstructed`), so a boulder on an open door keeps it open forever | [src lock.c:925-955, 1023] |
| `#force` does not work on doors at all (box-only, "TODO" comment; also needs a wielded weapon, none exists) | [src lock.c:676-700] |
| No Sokoban-specific door code (no `Sokoban` in lock.c / dokick.c) | [grep, this session] |
| `noteleport`, `hardfloor` don't touch door code [conj: no references in lock.c/dokick.c door paths] | |

## 3. Event table

"Repeatable" = the player can retry the same event with nothing changed except exercise counters / turn count.
"Nature's real power" assumes Rev.1-3 hero, no monsters, explicit door states (§4).

| # | Event (player action) | Source | Outcomes (nature picks) | State change | Side effects available to nature | Repeatable? | Nature's real power |
|---|---|---|---|---|---|---|---|
| D1 | `#open` / walk into CLOSED door with `autoopen` (default on; skipped if Confused/Stunned/Fumbling or running) | lock.c:780-922 (roll :904); hack.c:1095-1110 | (a) "The door opens." → ISOPEN; (b) "The door resists!" | (a) only | (a) none if untrapped; trapped: KABOOM (D5). (b) `exercise(A_STR, TRUE)` only (:918): gain-only, harmless | yes, unlimited, no cost (hunger off) | veto: "not now", forever if it likes |
| D2 | `#open` / walk into LOCKED, BROKEN, NODOOR, ISOPEN door | lock.c:852-892 | deterministic message "This door is locked / is broken / way has no door / is already open" | none | none. `autounlock` with "kick" asks y/n then queues a kick (D4): player's choice | — | none |
| D3 | walk into closed door, `autoopen` off | hack.c:1111-1133 | Dex<10 (or Blind/Stunned/Fumbling): "Ouch! You bump into a door." + `exercise(A_DEX, FALSE)`, a turn passes; else "That door is closed." | none | Dex abuse only; **no HP damage** | yes | none (player toggles the option) |
| D4 | `#close` an ISOPEN door | lock.c:957-1050 (roll :1039) | (a) "The door closes." → CLOSED; (b) "The door resists!" (+Str exercise) | (a) only | none | yes | veto on closing; useless (closing never helps the player, §5) |
| D5 | open / unlock / kick / untrap a **TRAPPED** door | `b_trapped` trap.c:6694-6707; callers lock.c:141, :908; dokick.c (break branch); trap.c:6070-6080 | explosion dmg = rnd(5 + lvl), lvl = depth 1 → 1..6; door → NODOOR; Stun +dmg turns; Str/Con abuse | door → NODOOR | **HP damage, stun, attribute abuse**. Under R3, damage is permanent: XL1 regen `heal = (ulevel+Con) > rn2(100)` [src allmain.c:659] (nature refuses forever) and prayer at record 0 gives `action = !rnl(2) ? 1 : 0` [src pray.c:1129-1130] (nature picks 0). Start HP = 14+2 = 16 fixed [src role.c:522, 600; attrib.c:1086-1090] | once (door becomes doorless) | toll / hazard only. **Excluded**: D_TRAPPED is never set by explicit-state `des.door` (§4) |
| D6 | kick (`^D`) CLOSED or LOCKED door | dokick.c:910-971 (roll :930) | (a) break: Str > 18 and `!rn2(5)` → "shatters" NODOOR, else "crashes open" BROKEN (both doorless, same for movement); (b) "Thwack!!"/"Whammm!!" | (a) only, **irreversible** (no wand of locking) | (a) +Str exercise; (b) +Str exercise. +Dex exercise always (:927). No HP damage (Levitation → `kick_ouch` impossible by hu-off I8) | yes, unlimited (no wound on a door hit) | veto on breaking |
| D7 | kick ISOPEN / BROKEN / NODOOR door, or empty space | `kick_dumb` dokick.c:864-878, called :914-917 | Dex ≥ 16: nothing; else nature may pick "Dumb move! You strain a muscle": wounded right leg 5+rnd(5) turns, Str abuse | none (terrain) | wounded legs: blocks kicking [src dokick.c:1279], carry cap −100 [src hack.c:4332-4335] (Burdened at worst with Str+Con ≥ 20: wc ≥ 450, 500 < 2·wc), heals by timeout. No HP loss | yes | player-inflicted nuisance only |
| D8 | kick wall / boulder / SDOOR (fail) | `kick_ouch` dokick.c:881-906; SDOOR `rn2(30) < T` :977 | "Ouch! That hurts!" rnd(3) (Con > 15) or rnd(5) HP, 1/3 wounded leg, Str/Dex abuse | SDOOR success → door (state kept) | **HP damage** (permanent under R3, see D5) | yes | only hurts a player who chooses it; never needed |
| D9 | key / lock pick / credit card (if whitelisted) on CLOSED/LOCKED door | `pick_lock` lock.c:358-650 (door chances :634-645); `picklock` occupation lock.c:68-160 | per turn `rn2(100) < ch` (key 70+Dex, pick 3·Dex, card 2·Dex unlock only); success toggles LOCKED↔CLOSED; after 50 turns "You give up" (:90) | success only | +Dex/+Wis exercise; trapped door → KABOOM (:139-145, excluded) | yes: re-apply restarts the 50-turn counter | veto on lock *and* unlock |
| D10 | `#untrap` toward a door | trap.c:6045-6095 | untrapped door, not Confused: deterministic "You find no traps on the door." | none | none. (Trapped door: find via `rn2(MAXULEV−ulevel+11) < 10`, disarm success gives exp `more_experienced(8,0)` → XL can rise: would break hu-off I8; excluded with D5) | yes | none |
| D11 | `s` search next to SDOOR | detect.c:2043, 2053 (`rnl(7 − fund)`) | reveal or not | SDOOR → DOOR | none | yes | veto (SDOOR ≡ wall under R3) |
| D12 | open a door diagonally / from a doorway | lock.c:780-922 has no direction test | same as D1 | — | — | — | opening is legal diagonally, passing is not (hack.c:1141) |

Messages asked about in the brief: "This door is stuck" and "The door won't close" **do not exist** in 5.0.0 (grep
lock.c); the failure text for both open and close is "The door resists!". "This door is locked" is the deterministic
LOCKED message (D2), not a random roll.

Not reachable in the setting (no source): wands of opening/locking/striking/digging, force bolt, knock, wizard lock,
pick-axe/axe digging, rolling boulder traps (break doors, trap.c:3185, 3538), monsters (shopkeepers, watchmen,
vault guards, door mimics: `stumble_on_door_mimic` needs a monster, lock.c:758-768), giants (`doorbuster`), amorphous
/ tunnelling / Passes_walls forms. Shop and town branches need room records of shop type / Minetown: none (no
`des.region`).

## 4. Creating doors in the instance (sp_lev.c)

- `des.door(state, x, y)` or `des.door{x=,y=,state=}` with explicit coordinates → `sel_set_door` sets typ DOOR and
  `doormask = state` **exactly**, with no trap bit and no RNG [src sp_lev.c:4647-4661, 4671-4732]. States: open, closed,
  locked, nodoor, broken, secret (secret → SDOOR, mask raised to ≥ CLOSED). "random" → `rnddoor()` (RNG, still no trap)
  [src sp_lev.c:1148-1153, 4702]. Whitelist rule: **explicit state only, never "random"**.
- The wall/room form (x = y = −1) goes to `create_door`, which with state "random" can add D_TRAPPED (1/25 or 1/20)
  [src sp_lev.c:1714-1747]. Excluded (needs a room anyway; no `des.region` in W).
- `des.map` '+' without a `des.door` keeps whatever `flags` the cell had; after `solidfill` init that is 0 =
  D_NODOOR [src sp_lev.c:383; set_levltyp mkmaze.c:77-115 does not touch flags] [conj: lspo_map not traced line by
  line]. Rule: every '+' gets an explicit `des.door`.
- `des.finalize_level` only re-links doors to rooms (`link_doors_rooms`, orientation) [src sp_lev.c:1121-1140, 6022];
  no state change.
- Under R2 vs R3 a door's *creation* is deterministic with explicit states; only the in-play rolls of §3 are random.

## 5. Why the veto is useless (monotonicity) [conj, source-backed]

Claim M. Let X, X' be states equal except that some door is CLOSED (or LOCKED) in X and ISOPEN/BROKEN/NODOOR in X'.
If the player wins from X under R3, the player wins from X'.
Sketch: copy the X-strategy, replacing each attempt on that door (D1/D4/D6/D9, autoopen bump) by a wait `s`.
Every legal X-move stays legal in X': an open door square only *adds* hero moves (orthogonal entry) and boulder
pushes (orthogonal onto the door, hack.c:432-500), and forbids diagonals exactly as the closed door forbade all entry
(hack.c:1141, 1208); a doorless doorway allows strictly more. Closed doors never serve as a needed stopper: pushes move
a block one cell, no sliding (hu-off B.4 M2). The only divergence is exercise counters (failed attempts give Str/Dex
*gains* only, §3), which affect T and weight cap, neither of which changes Push-1F moves (hu-off I3: inv_weight ≥
500 − 1000 > −850 for any attributes). Hence nature never benefits from opening; its R3-optimal strategy is "refuse
every roll", which makes the door game equal to a deterministic one with closed doors as walls. No alternation.

Why there is no fix inside doors:
1. **No commitment point.** A failed roll is a no-op (D1/D4/D6/D9 failure branches only call `exercise`), so nature
   can always say "not yet" and keep the option to open later. A nature-choice gadget needs a one-shot roll that
   moves the game on regardless of the outcome (e.g. "left or right, chosen now"). No door event forces anything.
2. **No non-dominated pair.** Opening helps the player or is irrelevant; the only "bad for the player" outcomes are
   damage/stun/abuse from trapped doors and kicks of non-doors (D5, D8), which the player can always avoid.
3. Limited retries do not exist: no counter on doors; the 50-turn give-up in D9 resets on re-apply; kicking a closed
   door never wounds legs; hunger is off, so time costs nothing (with hunger on, refusals would only drain the
   player's clock: more nature power, still a veto).

## 6. Answers to the specific questions

| Question | Answer |
|---|---|
| Can boulders be pushed through doorways? | Orthogonally yes for open / broken / nodoor (hack.c:432-500); never into closed/locked (hack.c:485); never diagonally into a door with a door (hack.c:434); never diagonally at all in Sokoban (hack.c:441-448) |
| Diagonal rule effect on Push-1F gadgets | Hero diagonals only shortcut via a free corner (hu-off M1), so forbidding them at door squares changes no Push-1F reachability. Open doors are safe "floor without diagonals" under R2 and R3 (closing is the player's choice and never helps, §5) [conj] |
| Can nature hurt the player through doors? | Only via trapped doors (excluded by explicit `des.door`) or kicks the player chooses (walls/boulders/SDOOR: rnd(3)/rnd(5) HP, permanent under R3; open doors: wounded legs, no HP). Normal open/close/kick-closed-door: no damage, no paralysis, no level change, no item loss, no curse |
| Exercise / attributes | Door failures give only *positive* Str/Dex exercise; T stays in [3,19]; no effect on Push moves |
| Luck | Not changed by any door event; any Luck in [−10,10] keeps both outcomes of every door roll available |
| Hero HP/regen under R3 | HP 16 fixed at start; regen and prayer healing can be refused by nature (allmain.c:659, pray.c:1129-1130), so any damage taken is permanent: avoid every damaging action |
| Add a key / lock pick to the whitelist? | Gains nothing: lock and unlock are both vetoable (rn2(100) ≥ ch always possible, ch ≤ 88); same monotone veto. Also adds an item to the hu-off Lemma 1 / B.4 audits. Not recommended |
| Shopkeepers / vault guards / watch | Need monsters or shop/town rooms; none under mongen=false and no `des.region` |
| autoopen | Default on; it only turns a bump into D1; player can toggle it (meta command) |

## 7. Recommendation for the EXPTIME attempt

- Do not use doors as nature-choice gadgets. Treat them as terrain: open = no-diagonal floor, nodoor/broken = floor;
  avoid closed/locked/secret doors entirely (they make R2 ≠ R3).
- A usable nature choice needs an RNG event that (i) the player cannot retry for free or that changes state on
  *both* outcomes, and (ii) has two outcomes neither of which dominates for nature. Candidates to audit next (not
  checked here): rolls whose *failure* branch also changes state (e.g. falling/landing position, boulder fate in water
  `do.c` flooreffects, known-trap escape `!rn2(5)` which moves the hero either way, stun/confusion direction), but
  each must be checked for extra nature powers.
