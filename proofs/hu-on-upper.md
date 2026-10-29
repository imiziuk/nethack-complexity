# L_ON ∈ NP: upper-bound proof draft (R2 semantics)

Proof agent, 2026-10-28. Source: NetHack 5.0.0 @ 16ff591, read-only, nothing built or run.
Paths are `src/<file>` = `src/src/<file>` and `include/<file>` relative to the checkout.
Labels: [src f:l] = I read it · [conj] = my reasoning, not machine-checked · [ext] = external theorem ·
[assump] = a definition/spec choice.

## 0. Verdict first

**As written, L_ON (R2) does NOT satisfy Lemma H, and the NP proof fails (FATAL gap G1).** Under R2 the certificate
chooses every RNG outcome. Starvation is only checked in the `else` branch of the faint roll:
`if (u.uhs <= WEAK || rn2(20 - h/10) >= 19) { faint } else if (u.uhunger < -(100+10*Con)) { die }`
[src eat.c:3410-3447]. For h ≤ -5 the outcome 19 is legal, so an R2 play never starves. Combined with prayer
(sets `u.uhunger = 900` from any value [src pray.c:404-411, eat.c:126-129], available again ≤ 32,567 turns after a
success [src pray.c:1356-1377, allmain.c:276-277]), the hero survives forever with ~900 aware actions per prayer
cycle. So alive plays are unbounded, and hunger acts like L_OFF. Two more loopholes (G2 rotten food, G3 sleeping-gas
trap + `#sit`) independently give infinite plays with zero forced hunger.

**With the repairs in §5 (language L_ON\*), the theorem holds:** L_ON\* ∈ NP, with horizon
T ≤ 3.4·10^6 + 0.8·10^6 + 616·N, where N = total food nutrition = 40·(number of fortune cookies). The repairs are
spec choices. The main one is rule S: the play loses as soon as `u.uhunger < -(100+10·ACURR(A_CON))`.

## 1. The repaired language L_ON\* (assumptions used by every lemma)

[assump] Everything in proofs/phase2-spec.md (common part + L_ON), plus:
- **S (starvation rule).** A play is losing from the first moment `u.uhunger < -(100 + 10·ACURR(A_CON))`.
  This is the R3-faithful reading: below the threshold, every tick kills with probability ≥ 19/(20+|h/10|). Since
  ACURR(A_CON) ≤ 25 [src attrib.c:1200ff, 309], alive plays keep **h ≥ -350**.
- **Level change = loss.** L=1: stairs, holes, trapdoors and level teleport end the play (losing). The verifier stops
  there, so no new level is ever generated.
- **Mandatory script prefix:** `nh.debug_flags{mongen=false}` and `u.clear_inventory()`. The second removes the
  template FOOD_RATION (G2).
- **Object whitelist (des.object and obj.new/u.giveobj):** BOULDER (quantity 1), LOADSTONE (quantity 1, any BUC),
  FORTUNE_COOKIE (any BUC, explicit quantity q ≥ 1). No `contents`, explicit `spe`/BUC.
- **Trap whitelist:** PIT, HOLE, TRAPDOOR (the last two only lead off-level, which is a loss).
- **Terrain:** STONE, walls, ROOM, CORR, DOOR, POOL/MOAT/LAVA allowed (they only kill or block). No TREE, FOUNTAIN,
  SINK, ALTAR, THRONE, IRONBARS-for-H-is-fine-but-unaudited (ban to be safe). `des.level_init` only `solidfill`.
  `des.level_flags` only noteleport, hardfloor, premapped, sokoban, solidify, noflip/noflipx/noflipy, nommap,
  shortsighted, inaccessibles. No fumaroles, stormy or graveyard: regions and storms are not audited.
- **Size:** w, h ≤ n (unary). "Coordinates Θ(log n) bits" already implies this. If w, h were binary,
  `level_init` alone fills an exponential grid.
- **Integer semantics (W_C):** C widths; a play that would overflow a signed int is not considered (never needed below
  once S holds).
- Hero template as in the spec: human Valkyrie. No intrinsic Fast at XL1 [src u_init.c:767-773 role init; Fast comes
  at XL7, conj]. XP never increases in L_ON\* (no kills, no potions/wraiths) [conj], so the hero stays at XL1 with
  speed 12.

Time units. A **tick** is one execution of the once-per-turn block in `moveloop_core` (`svm.moves++`
[src allmain.c:244] through the `++gm.multi` handling [src allmain.c:382]). `gethungry()` runs exactly once per tick
[src allmain.c:354]. A **timed action** is a hero command that sets `context.move`. A **free action** does not
(options, look, inventory, #name, #adjust, …). The hero gains ≤ NORMAL_SPEED movement per tick (no Fast/Very_fast
[src allmain.c:113-153]), so #timed actions ≤ T + 1.

## 2. Lemma 1 (state size): every reachable state of an L_ON\* instance has poly(n, T) bits

Creators reachable in L_ON\*, each with its bound:

| Record kind | Creator in L_ON\* | Bound | Evidence |
|---|---|---|---|
| Monsters | none. `makemon` returns NULL for **all** calls, explicit species included, when `iflags.debug_mongen` | 0 | [src makemon.c:1168]; existing ones removed by the flag call [src nhlua.c:1470-1482]; prayer minions use `makemon` [src minion.c:222,232,239]; pet via makedog→makemon. Other `newmonst()` sites: clone (needs a monster) [src makemon.c:866], restore [src restore.c:391], corpse/statue OMONST attachments [src mkobj.c:120,2210] (not live) |
| Objects, initial | des.object lines | ≤ \|S\| (one record per line given rule "non-mergeable ⇒ quantity 1") | quantity loop [src sp_lev.c:3723-3738] (see G4) |
| Stack splits | pickup/drop/throw/kick with counts, `#adjust` | inventory ≤ 52 letters + `$` [include hack.h:584-587]; floor records grow ≤ 52 per timed action | splitobj creates 1 record per split; dropped parts merge via `stackobj` [src do.c:807-837] [conj: ≤1 split per touched stack per action] |
| Eating part of a stack | splits one off, which is then consumed | net 0; cookies have oc_delay 1, so no partly-eaten records | [src include/objects.h:1103] |
| Rotten / partly eaten food | none: cookies are exempt from the rot check | 0 | `otmp->otyp != FORTUNE_COOKIE && …` [src eat.c:3026-3037] |
| Rocks from boulders (`fracture_rock`) | callers are dig, explode/scatter, land mine + rolling boulder, monster, vault guard, zap force bolt/striking, invocation | 0 (none reachable: no tools, wands, spells, land mines, monsters) | [src dig.c:457, explode.c:783, trap.c:3449, monmove.c:171, vault.c:435, zap.c:1959,2286,5603, mklev.c:2537] |
| Boulders | no creator (scroll of earth absent; rolling-boulder trap absent) | non-increasing (filling a pit/pool deletes one) | [conj] |
| Ball & chain | `punish` via prayer anger case 6 only if `!Punished`; repeat → "heavier", no new object | ≤ 2 | [src pray.c:744-750, read.c:3019-3035] |
| Artifact/spellbook gifts | `pleased` pat_on_head cases need action ≥ 5 | ≤ 1 per successful prayer (Luck 0 gives action ≤ 2, so 0 [conj]) | [src pray.c:1340-1350] |
| Corpses, vomit, statues, eggs | none (no monsters; vomit creates no object) | 0 | [conj] |
| Traps | no creator (no digging, no tools); boulder fills pit → deltrap | ≤ \|S\| | [conj] |
| Engravings | engrave in dust/with weapon | ≤ 1 per square, text ≤ BUFSZ | [src engrave.c:1163, 1459-1461] |
| Timers / light sources | none (template lamp removed by clear_inventory; cookies have no rot timer) | 0 | [conj] |
| Regions | none (no gas sources; fumaroles banned) | 0 | [conj] |
| Fruit chain | `fruit` option (free action) | removed by normalization (Lemma N) | state-architecture.md 1a |

Scalars: under W_C every scalar is ≤ 64 bits by definition, including `moves`, `context.ident`, `ublesscnt`,
`ugangr`, `uhunger`, conduct counters and alignment. The ISAAC state is replaced by the certificate under R2 (R2 needs
no seed). Grid: O(w·h) cells × O(1) fields (`rm`, `lastseentyp`, vision arrays).

**Lemma 1.** After a normalized play with T ticks, the state has
O((w·h + |S| + 52·(T+1) + 4)·(BUFSZ + 64)) bits. [conj, built from the table above]

**Lemma N (free-action normalization).** For any winning play there is a winning play with the same timed actions
and RNG outcomes, and at most c·(1 + records) free actions between consecutive timed actions. Reason: the only state
that free actions change is the flag/option block (constant size), inventory letters (≤ 52), object/type names
(one string per record/type) and the fruit chain. The fruit chain only matters for slime molds, which never exist
in L_ON\*. So any block of free actions can be replaced by a direct sequence that sets these components to their
final values. [conj]

## 3. Lemma 2 (poly-time step, poly RNG vector)

The main loop is `moveloop_core` [src allmain.c:177]. Per tick: `movemon` [src mon.c:1326] (empty `fmon`),
`mcalcdistress`, `maybe_generate_rnd_mon` [src allmain.c:239] (one `rn2`, then `makemon`, which returns at
makemon.c:1168), `nh_timeout` [src timeout.c:588] (fixed 69 props + timer list), `run_regions` [src region.c:414],
`regen_hp`/`regen_pw`, `dosearch0` [src detect.c:2016] (3×3), `gethungry` [src eat.c:3163] (≤ 2 RNG calls),
`exerchk`, `u_wipe_engr`. Per hero action: `rhack` [src cmd.c:3627] → e.g. `domove` [src hack.c:2695] (boulder
push loops over the objects on one square), `findtravelpath` [src hack.c:1266] (BFS over the grid; O((w·h)^2)
worst case), pickup/drop menus (O(#objects)), `vision_recalc` [src vision.c:512] (COLNO×ROWNO arrays, lifted to
w×h: O(w·h·(w+h)) worst case).

Each subsystem makes O(1) RNG calls per entity it scans. So RNG calls per tick or action are O(s), where s is the
state size, and each outcome has ≤ 64 bits. Level creation: the straight-line script makes |S| calls. Each call is
poly(w·h + |S|) **given G4** (otherwise `quantity` = 2^60 boulders loops 2^60 times [src sp_lev.c:3734-3738]).

**Lemma 2.** One tick or action on a state of size s runs in poly(s) time with O(s) RNG outcomes. The script phase
runs in poly(n). [conj; the loop bodies are the cited functions]

## 4. Lemma H (horizon): every alive play of an L_ON\* instance has T ≤ 4.2·10^6 + 616·N ticks

N := 40·(total fortune cookies placed) is all the food nutrition (cookie oc_nutrition = 40 [src include/objects.h:1103]).

### 4.1 Tick classification
At its `gethungry()` call [src allmain.c:354] each tick is exactly one of:
- **V (invulnerable):** `u.uinvulnerable`, so `gethungry` returns at once [src eat.c:3167-3168]. The only setter is
  `dopray` when `p_type == 3` [src pray.c:2266-2270]. It is cleared by `prayer_done` [src pray.c:2280] when
  `nomul(-3)` expires, so each successful prayer gives exactly 3 V ticks. Failed prayers (p_type 0/1) are helpless
  but not invulnerable and not Unaware, so their ticks are F.
- **U (Unaware, not V):** `Unaware = multi<0 && (unconscious() || is_fainted())` [include youprop.h:399,
  src trap.c:6776-6786]. Then the decrement happens only if `!rn2(10)`, so under R2 it can be skipped.
- **F (forced):** the rest. Here `u.uhunger--` is unconditional [src eat.c:3174-3179]. This uses three invariants:
  `iflags.debug_hunger` is false (L_ON); the form is human (an eater) because no polymorph source exists (POLY_TRAP
  banned, no wands/potions/rings/corpses, no lycanthropy without monsters, `mvl_change` needs Polymorph/ulycn
  [src allmain.c:315-332]); and there is no Slow_digestion (only RIN_SLOW_DIGESTION and white dragon armour
  [src include/objects.h:805, do_wear.c:876], both absent). **This is why rings of slow digestion break the lemma:**
  the base decrement disappears and the remaining ring hunger is `rn2(20)`-gated [src eat.c:3190, 3212-3221], so R2
  avoids all of it.

### 4.2 Which Unaware episodes exist in L_ON\*
`u.usleep` is set only by `fall_asleep` [src timeout.c:951]. Its callers: cursed apple [src eat.c:2595] (absent),
overexertion [src hack.c:3045], monsters [src mhitu.c:1862, uhitm.c:3502], potion [src potion.c:909], spellbook
[src spell.c:491], Sleepy intrinsic [src timeout.c:790], sleeping-gas trap [src trap.c:1575] (banned), wands
[src zap.c:2864,4461]. The `nomovemsg` sources are "You are conscious again" (rotten food [src eat.c:1841-1849];
cookies exempt), "You awake…" (potion [src potion.c:790]) and "You regain consciousness" (faint [src eat.c:3427]).
Two episode kinds remain:

- **Faint episodes.** They start only in `newuhs` with h ≤ 0, `!is_fainted()`, `multi ≥ 0`
  [src eat.c:3410-3432], and last `duration = 10 - sgn(h)·((|h|+5)/10)` ≤ 10 + 35 = **45** ticks (h ≥ -350 by S).
  Charging: a start inside `gethungry` comes right after an F decrement that landed at h ≤ 0 (V returns before
  `newuhs`; on a U tick the hero is already fainted or asleep, so no new start). A start inside `morehungry` comes
  after a decrement landing ≤ 0. A start inside `lesshungry`/end of a meal is charged to the cookie eaten.
  So E_faint ≤ Z + K, where K = cookies eaten ≤ N/40 and Z = unit decrements landing in [-350, 0].
  Down-crossings of the 351 unit edges in [-351, 0] are ≤ 351 + up-crossings. Up-crossings come from eating (≤ N)
  and from prayers (≤ 351 each). So **Z ≤ 351 + N + 351·P**, where P = #successful prayers.
- **Overexertion episodes** (`fall_asleep(-10)` when `*hp ≤ 1` at a tick with wtcap > MOD_ENCUMBER, `u.umoved` and
  `moves % 30 (or % 10) == 0` [src allmain.c:297-302, hack.c:3035-3046]): ≤ 10 U ticks each. Claim: between two
  episodes there is ≥ 1 F tick. Proof sketch [conj, source-backed]:
  `u.umoved` is reset every hero turn [src allmain.c:513], so the second episode needs a successful move after the
  first one. At the first episode HP ≤ 1. To move again while encumbered beyond Burdened, the hero needs
  `uhp ≥ 10 || uhp == uhpmax` [src hack.c:2620-2623].
  (a) `uhpmax ≥ 10` always: reducers are fire trap [src trap.c:4286-4295], poison→`losestr` [src attrib.c:224-256]
  (spiked pit, dart), and `losexp` (prayer anger), which floors at `minuhpmax(10)` [src exper.c:247-255]. The first
  two are banned. So `uhp == uhpmax` forces uhp ≥ 10.
  (b) A move with uhp ≥ 10 cannot end at hp ≤ 1 by the next tick: the only move damage in L_ON\* is a plain pit,
  rnd(6) [src trap.c:1950], and `regen_hp` runs before `overexert_hp` in the tick.
  (c) So the hero must first drop to ≤ Burdened through a timed non-move action (drop, throw, eat). The tick after a
  timed non-move, non-prayer action of an aware hero is F: no sleep source exists, and a faint can only start after
  that tick's decrement.
  Hence **E_over ≤ |F| + 1.**

### 4.3 Nutrition ledger
Writers of `u.uhunger` [grep, src]: `init_uhunger` = 900 (start [src u_init.c:1002]; prayer TROUBLE_STARVING/HUNGRY
[src pray.c:404-411]; golden glow only if < 900 [src pray.c:1270]; lifesave [src end.c:720], no amulet;
tutorial [src nhlua.c:1768], not reachable). Also `lesshungry` (eating), `morehungry(±)`, and direct `+=` in
fountain/potion/chewing/poly-attack [src fountain.c:281, potion.c:721,784,857, hack.c:730,779, uhitm.c:5073,
eat.c:678], all absent in L_ON\*. Choking at ≥ 2000 [src eat.c:3296] either kills or vomits (−1000), so h ≤ 2040.
Each prayer raises h by ≤ 900 − (−350) = 1250.

Forced decrements: |F| ≤ h_start − h_end + intake ≤ (h_start + 350) + N + 1250·P.

### 4.4 Prayer rate
A successful prayer sets `ublesscnt = rnz(350)` (+ kicks, zero here), then adds
`min((moves−100000)/100, 32767 − ublesscnt)` [src pray.c:1356-1377]. For moves ≥ M\* := 3,376,800 this makes
ublesscnt = 32767 exactly. Another success needs ublesscnt ≤ 200 [src pray.c:2151-2153]. ublesscnt drops by exactly
1 per tick [src allmain.c:276-277]. The other decreases are sacrifice (needs an altar [src pray.c:2067-2070]) and
wizard mode [src pray.c:2250]. So after M\*, successes are ≥ 32,567 ticks apart: **P' ≤ 1 + T'/32567** for a
segment of T' ticks after M\*. (u.ugangr only grows without altars [src pray.c:1436-1442], so anger only removes
prayers.)

### 4.5 Putting it together
Split the play at moves = M\*. The prefix has ≤ M\* ticks. For the suffix (h_start ≤ 2040):
T' = |F| + |U| + |V| ≤ |F| + 10(|F|+1) + 45(Z + K) + 3P'
   ≤ 11(2390 + N + 1250P') + 10 + 45(351 + N + 351P' + N/40) + 3P'
   ≤ 42,095 + 57.2·N + 29,548·P'.
With P' ≤ 1 + T'/32567, and 29,548/32,567 = 0.907 < 1:
T' ≤ (42,095 + 29,548 + 57.2N)/0.0927 ≤ 7.8·10^5 + 617·N.
**T ≤ 3.38·10^6 + 7.8·10^5 + 617·N ≤ 4.2·10^6 + 617·N.** ∎ [conj; the arithmetic is mine, the facts are cited]

The margin (0.907) is thin. Any extra free-sleep source (one more unaware tick per F tick) or any extra nutrition
per prayer breaks it. That is why the bans below are needed and not just tidy.

Under W_C, N ≤ 40·LONG_MAX·|S|, so T is linear in n with a galactic constant. To get a meaningful polynomial,
the spec should encode cookie quantities in unary (or require q ≤ n); then T = O(n).

## 5. Theorem: L_ON\* ∈ NP

Certificate: the R2 outcomes for the script phase; then a normalized (Lemma N) sequence of commands (with count
prefixes/menu answers/text) interleaved with the outcome of every RNG call in order, up to the first player-turn
start (`multi == 0`, hero's `rhack(0)` [src allmain.c:536]) where the hero is alive at g.

By Lemma H the play has ≤ p(n) ticks, so ≤ p(n)+1 timed actions and ≤ c·p(n)·records free actions (Lemma N).
By Lemma 1 every state has poly(n) bits. By Lemma 2 each step takes poly time and consumes O(s) outcomes. So the
certificate has poly(n) length. The verifier replays the C semantics deterministically, substituting the outcomes.
It checks each outcome is in range and rejects on death, rule S, or a level change. It accepts iff the hero stands
on g at a player-turn start.

Completeness: any winning play is ≤ p(n) long and normalizes. Soundness: the verifier only follows legal
transitions. ∎ [conj: depends on Lemmas 1, 2, N being complete]

## 6. Spec gaps found (each with the exact repair)

| # | Gap | Breaks | Repair |
|---|---|---|---|
| **G1 (FATAL as written)** | R2 never starves: faint roll `rn2(20-h/10) >= 19` skips the starvation `else` [src eat.c:3416, 3437]. With prayer (h ← 900 every ≤ 32,567 ticks) the alive play is infinite with ~900+ useful actions per cycle. Without prayer, h runs to INT_MIN (UB/wrap → infinite again) | Lemma H, NP membership. Also the lower-bound DET-answer argument: R2-answer ≠ R3-answer | Rule S (§1). Alternatives: ban `#pray` **and** declare no-overflow, which gives a 2^31-galactic bound; S is cleaner |
| **G2** | Rotten-food sleep loop: food older than 30 turns (or any cursed food) → `rottenfood` → "world spins" `nomul(-rnd(10))`, Unaware, `dont_start`, `oeaten` floors at 1, so the item never runs out [src eat.c:3026-3037, 1832-1849, 3866-3871]. Under R2: free sleep forever, which burns time to refresh prayer. **The Valkyrie starts with a FOOD_RATION** [src u_init.c:164] | Lemma H | Mandatory `u.clear_inventory()`. Food whitelist = FORTUNE_COOKIE only (exempt even when cursed). Lembas/cram are nonrotting [src eat.c:65-66] but rot when cursed, and curses are reachable (prayer anger `rndcurse` [src pray.c:751-759]), so allow them only if `#pray` is banned. **Food rations (the lower-bound team's plan) must go** |
| **G3** | Sleeping-gas trap + `#sit` re-triggers it without moving [src trap.c:1575, sit.c:503]: asleep at every tick, zero forced hunger | Lemma H | Ban SLP_GAS_TRAP |
| **G4** | `des.object` with `quantity=q` on a non-mergeable otyp (boulder, loadstone) loops q times [src sp_lev.c:3723-3738]: exponential records and time from a short script | Lemmas 1, 2 | Quantity 1 for non-mergeables; unary (or ≤ n) quantity for cookies |
| G5 | POLY_TRAP: non-eater form → F fails for the form's duration; new form abilities | Lemma H | Ban |
| G6 | FIRE_TRAP, MAGIC_TRAP (fire branch, uncurse), DART_TRAP, SPIKED_PIT (poison → `losestr`): uhpmax → 1, which allows overexertion sleep loops [src trap.c:4286-4295, 1939, attrib.c:224-256] | the §4.2(a) step | Ban. ROCKTRAP/ARROW_TRAP (damage ≥ 9 in one move, object creation), LANDMINE (rocks, pit), ROLLING_BOULDER, STATUE_TRAP (random statue with a possible spellbook), TELEP/LEVEL_TELEP/MAGIC_PORTAL: ban, unaudited or off-level |
| G7 | Arbitrary `des.object` otyp | Lemma H/1 | Whitelist {BOULDER, LOADSTONE, FORTUNE_COOKIE}. What breaks otherwise: ring of slow digestion / white dragon scales or mail (R2 removes all hunger, §4.1); amulet of unchanging + polymorph; amulet of life saving (extra 900 + one survived death [src end.c:715-720]); wands (wishing → anything; digging; striking/force bolt → rocks); horn of plenty (creates rotting food + potions; charges spe ≤ 20, finite but feeds G2); potions (juice/booze nutrition, sleeping); scrolls (earth → boulders; charging → horn refills; genocide); spellbooks (spells); magic marker (writes scrolls); containers/statues (random contents); corpses/eggs/tins/apples/food rations (rot, effects, cursed-apple sleep [src eat.c:2595]); bag of tricks is harmless with mongen off but unneeded |
| G8 | `mongen=false` must be **mandatory** and the hero template's possible lamp/food removed | Lemma 1/H | Fixed script prefix (§1) |
| G9 | Level change (stairs from `teleport_region`/stair placement, holes, trapdoors) generates a new level with random objects | Lemma 1 | "Leaving the level = loss" |
| G10 | `w, h` encoding unspecified | Lemmas 1, 2 | Unary / ≤ n |
| G11 | Free actions are unbounded (options, `fruit` chain growth, `#adjust`) | certificate length | Lemma N normalization, or count only timed actions plus a bounded free-action budget |
| G12 | TREE (kick → fruit, possibly a cursed apple), fumaroles/stormy flags (regions, storms), random `level_init` styles (random fill objects) | Lemma 1/H | Ban (§1) |

## 7. What the lower-bound team can use
Hero = human Valkyrie, `u.clear_inventory()`, then `u.giveobj(obj.new("cursed loadstone"))`. Map from walls, floor,
corridors and doors; boulders (quantity 1); pits (and holes/trapdoors only as losing exits); food = fortune cookies
(40 nutrition each, delay 1); rule S. Under S, prayer is a bounded resource of ≤ 1250 nutrition per ≥ 32,567 ticks
after moves ≥ 3,376,800, and anger never creates monsters (mongen off). Their DET-answer proof must now handle S and
the faint/prayer outcomes. Note: punishment (ball & chain from anger case 6 [src pray.c:744-750]) gives a heavy-ball
throw/drag mechanic that review-1 L-2 says obeys the corner rule.

## 8. Open items
- Lemma N and the per-action split bound (≤ 52 new records) are [conj]: a full audit of every count/menu path is needed.
- §4.2(c): check that no timed non-move action by an aware hero can itself put the hero to sleep in L_ON\*
  (only `fall_asleep` and `nomul` with the Unaware strings matter; the grep above found none).
- XL stays 1, so there is no Fast: grep every `more_experienced`/`pluslvl` caller [conj].
- Con ≤ 25: the exact clamp line in `acurr` [src attrib.c:1200-1230], read only partly.
