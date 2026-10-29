# Problem definition and randomness semantics for generalized NetHack

Source: NetHack 5.0.0 (tag `NetHack-5.0.0_Released`, commit 16ff591), `src/` read-only. Paths below are relative to that tree.
Status: definitions only. **No complexity class is claimed here.** Section 6 says how each definitional choice moves the plausible bounds.

Claim labels: **[src file:line]** = auto-extracted from source; **[conj]** = LLM conjecture (not verified);
**[assume]** = human/modelling assumption we choose; **[thm: cite]** = external theorem.

---

## 1. Finiteness of the literal game and the generalized family NH_n

### 1.1 The literal executable is finite-state

| Constant / type | Value | Where |
|---|---|---|
| `COLNO` (map width) | 80 | [src include/global.h:382] |
| `ROWNO` (map height) | 21 | [src include/global.h:383] |
| `MAXNROFROOMS` | 40 | [src include/global.h:385] |
| `MAX_SUBROOMS` | 24 | [src include/global.h:386] |
| `MAXDUNGEON` (branches) | 16 | [src include/global.h:408] |
| `MAXLEVEL` (levels per branch) | 32 | [src include/global.h:409] |
| `MAXLINFO` = MAXDUNGEON*MAXLEVEL | 512 | [src include/hack.h:425] |
| `MAXULEV` | 30 | [src include/global.h:413] |
| `coordxy` | `int16_t` | [src include/global.h:71] |
| `xint8`, `xint16` | `int8_t`, `int16_t` | [src include/global.h:64,76] |
| map arrays | `locations/objects/monsters[COLNO][ROWNO]` | [src include/rm.h:474-476] |
| turn counter `moves` | `long`, **hard cap 10^9 turns, then game ends** | [src include/decl.h:1165], [src src/allmain.c:253-256] |
| HP, gold/quantity, timers | `int uhp`; `long quan`; `long timeout` | [src include/you.h:476], [src include/obj.h:47], [src include/timeout.h:64] |
| RNG state | ISAAC64 ctx: 2x256 `uint64_t` + 3 `uint64_t` + `unsigned` (~4 KiB) | [src include/isaac64.h:11-12,28-35] |

Every variable has fixed width and every level has a fixed number of cells. Object and monster lists are heap
linked lists [src include/rm.h:477-479], so the literal state space is bounded only by memory (a fixed limit of the
machine) [conj]. With any fixed memory bound the configuration graph is finite, so any reachability question about
the literal game is decidable in O(1) time. The constant is astronomically large, which says nothing useful [conj, standard
argument]. Even without a memory bound, the 10^9 turn cap [src src/allmain.c:253] bounds every play. Any interesting
statement needs a **family** indexed by a growing size parameter.

### 1.2 The generalized family NH_n

**Principle [assume]:** the generalized transition function δ_n must be *the same C code with some compile-time
constants turned into parameters*, plus widening any integer type whose range those parameters would overflow.
No new mechanics. Formally, NH_{w,h,L} = the program semantics of `src/` compiled with `COLNO=w`, `ROWNO=h`,
`MAXLEVEL*MAXDUNGEON >= L`, and type widths changed as listed below. Expressions written in terms of the constants
(e.g. `isok`, [src src/cmd.c:4329]; storm strike placement `rnd(COLNO - 1)`, [src src/timeout.c:1862]) then scale
on their own.

Parameters that scale, and how they interact with the code:

| Parameter | Liftable? | Code interactions to handle |
|---|---|---|
| Map width w, height h (COLNO/ROWNO) | Yes, the main parameter | 451 uses in 55 `src/*.c` files [src grep count]. `coordxy` is `int16_t` [src global.h:71], so the code is correct only for w,h ≤ 32767. Generalization: `coordxy` gets Θ(log(wh)) bits (word-RAM convention) [assume]. Static arrays `[COLNO][ROWNO]` [src rm.h:474-476] simply grow. Lua map bounds checks use COLNO [src sp_lev.c:561,1427-1441] and scale. The tty display assumes ~80 columns, but the decision problem is defined on the game core, not the window port [assume]. |
| Number of levels L | Yes | `d_level.dlevel` is `xint16` [src include/dungeon.h:11]. The save format reads the level number as `xint8` [src src/restore.c:1086] (so ≤127 levels per saved game, which is a save-format limit). `level_info[MAXLINFO]`, `dungeons[MAXDUNGEON]` [src include/decl.h:1124,1158] grow with the parameter. A **single-level** family is enough for most gadget work, and multi-level is a variant [assume]. |
| Number of rooms | Partly | `struct rm` packs `roomno` in a **6-bit** bitfield [src include/rm.h:168] with `ROOMOFFSET 3` [src include/mkroom.h:91], so ≤ ~60 room ids. `rooms[(MAXNROFROOMS+1)*2]` [src include/decl.h:1203]. Recommendation: **do not scale rooms**; build gadgets from terrain (walls/corridors/doors) placed via `des.map`/`des.terrain`, which need no room ids [assume]. Special rooms (shops, temples) then stay O(1) per instance. |
| Objects, monsters | Already unbounded | Linked lists [src rm.h:477-479]. At most one monster per cell (`monsters[x][y]`). Object/monster id counters (`unsigned`) may wrap [conj]; widen to Θ(log n) bits [assume]. |
| Per-cell bitfields (`flags:5`, `lit`, `candig`, ...) [src rm.h:163-170] | Not scaled | Cell semantics stay O(1) bits per cell: good, the state is O(wh) bits plus objects/monsters [conj]. |
| Gameplay integers (HP, quan, timers, attributes, uhunger, Luck) | Choice, see Section 2 | Default: keep C widths [assume]. |
| `nfountains`, `nsinks` (`uchar`) [src rm.h:432-433] | Wraps at 255 | Only used for ambient sounds/hints [conj]. Harmless, or widen. |

Instance size n := length of the encoded instance (Section 2); w, h, L, #objects, #monsters ≤ n.

**Per-turn cost [conj]:** a turn of δ_n runs in time polynomial in n (monster loop over `fmon`, vision over the
w×h map, bounded retry loops such as `count < 100` in [src timeout.c:1864]). This must be checked by the mechanics
team. It underlies every "∈ NP/PSPACE" upper bound below.

---

## 2. Input encoding

**Instance** = (S, G, R): a game state S (one or more levels + hero record + global context), a goal predicate G,
and a randomness specification R (Section 5). S is described either as a save-file-like record (field values of
`struct you`, `dlevel_t`, object/monster chains, timers) or as a generalized special level (Section 3, recommended).

**Numbers.** Three regimes:

1. **Fixed C widths (recommended) [assume].** HP, gold, `quan`, timers keep 32/64-bit ranges; only
   coordinates and ids widen to Θ(log n). Every number has O(1) bits, so unary vs binary does not matter. The state is
   O(n) bits ⇒ ≤ 2^{O(n)} configurations ⇒ an unbounded-horizon ∃-reachability problem is in NPSPACE = PSPACE, given
   poly-time turns [thm: Savitch 1970] [conj for the NetHack premise]. Caveat: a 32-bit HP or a 63-bit timer is
   "constant" but its value can be ~2^31 to 2^63, so gadgets that count down a timer could force very long plays. That
   matters only for bounded-horizon variants.
2. **Poly-width binary integers [variant].** Integers have p(n) bits, encoded in binary. The state is still poly(n)
   bits, so PSPACE/EXPTIME-style upper bounds are unchanged [conj]. But witnesses can become **exponentially long**:
   e.g. a "survive while HP > 0" or "wait for timer = 2^n" gadget needs 2^n turns. That kills NP membership even for
   deterministic/existential semantics [conj].
3. **Unbounded integers [variant NH-REACH-UNBOUNDED-INT].** Arbitrary-precision values that can grow during play
   (gold piles merging, `quan` from stacking, turn counter without the 10^9 cap). The state is no longer bounded by
   the input, so PSPACE/EXPTIME upper bounds fail. If the game can increment, decrement and zero-test two unbounded
   counters under player control, the problem becomes undecidable [thm: Minsky 1967, 2-counter machines] [conj
   that NetHack offers such gadgets, e.g. two gold stacks + a zero test].

**Unary vs binary of goal parameters.** A "survive k turns" goal with k in binary allows k = 2^n. In unary it keeps
the horizon polynomial. Recommendation: integers inside S at C widths; any horizon parameter in G or R **in unary**
when the variant is bounded-horizon [assume].

**The 10^9-turn cap** [src allmain.c:253-256] is itself a fixed integer constant. Keeping it literally means every
play has ≤ 10^9 = O(1) turns. The hero gets a bounded number of actions per turn (speed bounded by
`mmove` plus at most one extra `NORMAL_SPEED` action [src allmain.c:123-133]) [conj that free actions can be dropped].
So with the cap kept, every ∃-witness has constant length, and NH-REACH-EXISTS / -SEEDED would sit in **NP**. That is
an artifact of a constant [conj]. Recommendation: **lift the cap to a parameter T, default T = ∞ (removed)**, and
study the bounded-horizon version (T in unary) separately [assume].

---

## 3. Legality of initial states

**(a) Arbitrary well-formed save-file states.** `restore.c` validates very little. On a level load it checks only
the PID and level number, then calls `trickery()` on a mismatch [src src/restore.c:1084-1099]. Some local guards exist
(e.g. preventing `rn2(0)` [src restore.c:357], "bad monster weapon restore" [src restore.c:442]). The deep invariant
checker `sanity_check()` [src src/wizcmds.c:1460] runs only under `iflags.sanity_check || iflags.debug_fuzzer`
[src allmain.c:197-198]. So "passes restore" admits states that violate engine invariants (monster inside rock,
inconsistent `levl[][].typ` vs flags, object chains with bad `where`), and then δ_n can hit `impossible()`/UB
[conj]. Too permissive: the problem becomes about undefined behaviour, not NetHack. Also note the RNG state is
**not saved** (no rng/isaac references in `save.c`/`restore.c` [src grep]). On restore the RNG is freshly seeded
[src options.c:7161-7162, rnd.c:282-285].

**(b) States reachable from a new game.** This is the "natural" set, but it is a fixed finite set per seed, it has no
size parameter, and reductions cannot place gadgets. Useless for hardness [conj]. Mention it only as motivation.

**(c) Generalized special levels (recommended).** NetHack has its own mechanism for hand-designed levels: Lua
"des-files". The `des.*` API registered at [src sp_lev.c:6381-6410] includes `map`, `terrain`, `object`, `monster`,
`trap`, `door`, `stair`, `feature`, `engraving`, `region`, `levregion`, `teleport_region`, `level_init`,
`level_flags`. `des.level_flags` [src sp_lev.c:3759-3826] accepts: `noteleport`, `hardfloor`, `nommap`,
`shortsighted`, `arboreal`, `mazelevel`, `shroud`, `graveyard`, `icedpools`, `corrmaze`, `premapped`, `solidify`,
`sokoban`, `inaccessibles`, `noflip*`, `temperate|hot|cold`, **`nomongen`** (clears `rndmongen` [src sp_lev.c:3813]),
`nodeathdrops`, **`noautosearch`**, `fumaroles`, `stormy`. The flags exist in `struct levelflags` [src rm.h:431-471].
The shipped game uses them, e.g. Sokoban `des.level_flags("mazelevel","noteleport","premapped","sokoban","solidify")`
[src dat/soko1-1.lua:7], Fort Ludios [src dat/knox.lua:9], Vlad's tower [src dat/tower1.lua:9]. Wizard mode can load
any such file at runtime: `#wizloaddes`, `#wizloadlua` [src src/cmd.c:1972-1974]. 131 `dat/*.lua` files exist.

*Justification [assume]:* a level produced by the engine's own level loader is "legal" in a NetHack-native
sense, so we invent no states. Its post-load invariants are established by the engine's finalization code, not by us.
The format is succinct and parametric (w×h map strings), and it matches how prior game-complexity work defines
instances (generalized levels of a fixed engine) [thm-ish: Aloupis, Demaine, Guo, Viglietta 2015, "Classic Nintendo
games are (computationally) hard", which uses generalized level layouts].

*Required restrictions for (c) [assume]:*
- All placements use explicit coordinates and explicit object/monster types. Use no `des.*` call whose result depends
  on `rn2` (random placement, random object class, random `level_init` fill). Otherwise the loaded level depends on
  the RNG and the instance is ill-defined. Alternative: define S as *the state after loading*, quantified under the
  same R.
- Level loading runs finalization (`level_finalize_topology` [src mklev.c:1588]) and reseeds the RNG around
  creation when a strong seed is available [src mklev.c:1579-1592, rnd.c:289-294] [conj: finalization is deterministic
  for fully explicit levels; to verify].
- The des-file API does not set the hero (role, stats, intrinsics, inventory, HP, Luck, hunger). An instance therefore =
  **des-level script(s) + a hero record** (a restricted subset of `struct you` fields + inventory as `des.object`-style
  specs) [assume]. Recommend fixing role/race and listing intrinsics explicitly. The hero record is the one place
  where we borrow save-file style.

---

## 4. Goal predicates

| Goal | Definition | Relation |
|---|---|---|
| **REACH(x,y,ℓ)** (primary) | Hero alive, standing on cell (x,y) of level ℓ at the start of some player turn | Base case |
| REACH-LEVEL(ℓ) | Hero arrives on level ℓ | ≤ REACH: put the target-level arrival square as the goal cell. Conversely REACH ≤ REACH-LEVEL by making (x,y) the only down-stair/hole to ℓ [conj: needs digging/trapdoor control] |
| OBTAIN(o) | Object o in hero inventory | REACH ≤ OBTAIN by placing a unique object at (x,y) [conj: pickup must be always possible (not cursed-loadstone issues, burden)]. OBTAIN ≤ REACH-ish by gating (needs a "you have o" gadget) [conj] |
| SURVIVE(k) | Hero alive after turn k | Different flavour (safety vs reachability). Under ∀-randomness it is a co-reachability game. k encoding matters (Section 2) |
| ASCEND | `#offer` the Amulet at the right Astral altar | REACH (Astral altar cell) + one action. A special case of REACH on a richer instance; no independent interest for complexity [conj] |

Recommendation: **REACH(x,y,ℓ)** with "hero alive" (death ends the game: absorbing losing state) [assume].
For single-level instances ℓ is implicit.

---

## 5. Randomness semantics (central)

### 5.1 Where randomness enters a turn

The RNG is ISAAC64. `rn2(x)` = `isaac64_next_uint64() % x` [src rnd.c:60-64, 95-108] (slight modulo bias: not exactly
uniform). A separate display RNG `rn2_on_display_rng` [src rnd.c:70-73] exists for cosmetic choices and should not
affect game state [conj]. The source has ~2,557 `rn2/rnd/rn1/rnl/rne/rnz` call sites in `src/*.c` [src grep count].

Per-turn calls in `moveloop_core` and helpers (unconditional = the RNG is consumed every turn):

| Call | Where | Unconditional? | Can affect state when... | Neutralize by |
|---|---|---|---|---|
| Random monster generation `rn2(70/50/25)` | [src allmain.c:164-167] called at [src allmain.c:239] | **Yes, every turn** | `makemon(NULL,...)` returns immediately if `!rndmongen` [src makemon.c:1168] | level flag `nomongen` [src sp_lev.c:3813] ⇒ RNG consumed, **no effect** |
| Hunger `accessorytime = rn2(20)` | [src eat.c:3191] | **Yes, every turn** | ring/amulet worn (accessory nutrition) | wear no ring/amulet [conj] |
| Base hunger `!Unaware \|\| !rn2(10)` | [src eat.c:3174] | No (short-circuit when awake) | hero asleep/fainted | keep hero awake |
| Engraving wipe `rn2(40+3·Dex)`, `rnd(3)` | [src allmain.c:360-361] | **Yes, every turn** | an engraving under the hero | no engravings |
| Ambient sounds | [src sounds.c:213,220,226...] | Only if fountains/sinks/court etc. | messages only [conj] | none present |
| Storms / fumaroles | [src timeout.c:1855] | Only if `stormy` | lightning | flags off |
| Speed `rn2(3)` | [src allmain.c:127,131] | Only if `Fast`/`Very_fast` | extra hero actions | hero not Fast (or accept ∃ extra moves) |
| Monster speed rounding `rn2(NORMAL_SPEED)` | [src mon.c:1126ff (~1152,1164)] | Per monster per turn | any monster present | speeds that are multiples of 12 avoid the `mmove_adj` branch [conj] |
| HP / Pw regen | [src allmain.c:600-612, 625-660] | Only when below max | HP/Pw values | hero at full HP / no damage taken |
| Intrinsic teleport / polymorph | [src allmain.c:308,325] | Only with `Teleportation`/`Polymorph` | position/form | lack the intrinsic |
| Exercise / attribute drift | `exerchk` [src attrib.c:598], `rn2(19)`/`rn2(AVAL)` [src attrib.c:509,655] | periodic | Str/Con change ⇒ carrying capacity ⇒ encumbrance ⇒ speed | **risk**: needs a check that a short or inert play triggers no change [conj] |
| `u_calc_moveamt`, `settrack`, `mcalcdistress` | [src allmain.c:114-158, 228] | every turn | covered above | — |

**Key observation [conj, supported by the rows above]:** RNG *consumption* is unavoidable (≥3 calls per turn), but
RNG *outcome dependence* can be eliminated for a **randomness-free sublanguage**: `nomongen` + no monsters (or only
monsters whose behaviour is checked to be deterministic) + no traps with random effects + no engravings,
fountains, sinks or special rooms + no ring/amulet + hero awake, not Fast, at full HP, no teleport/polymorph intrinsics
+ no `stormy`/`fumaroles` + `noautosearch` (`dosearch0` [src allmain.c:341-343] uses chance rolls [conj]). Plus
action-level determinism of whatever the gadgets use (boulder pushing, doors (`#force`/kick are random), digging), which
the mechanics team must certify per action. On that sublanguage all of R1–R4 coincide with the deterministic
problem. **Hardness proved there transfers to every semantics** [conj, standard: a deterministic instance is a special
case of each]. Note also that `exerchk` may still need handling.

### 5.2 The four semantics

**(R1) Seeded RNG as part of the input (NH-REACH-SEEDED).** The input includes the full ISAAC64 state (≈4 KiB,
[src isaac64.h:28-35]) or the 64-bit seed (`init_isaac64(unsigned long seed)` [src rnd.c:43-57]). Then δ_n is
deterministic.
- The RNG state is O(1)-size (fixed 4 KiB), so it adds nothing to the state count asymptotically. Upper bounds
  equal the deterministic ones [conj].
- The player *manipulates* the RNG: every action that consumes a different number of calls shifts the stream (e.g.
  waiting vs searching). Under R1 the problem is "∃ action sequence such that this fixed PRNG stream produces G". For
  lower bounds you cannot exploit randomness without inverting ISAAC64 (cycle ≥ 2^72, mean 2^16583 [src
  isaac64.h:26-27]). In practice reductions must live in the randomness-free sublanguage anyway [conj].
- **Not NetHack-native:** the RNG is never saved [src save.c/restore.c, grep]. It is seeded from system entropy
  [src rnd.c:282-285, sys/unix/unixmain.c:824, sys/windows/windsys.c:762] and **reseeded on every level change** when the
  seed source is strong [src do.c:1709-1710, mklev.c:1579-1580, rnd.c:289-294]. So "seeded" is an artificial
  semantics (it models tool-assisted play) [assume].

**(R2) Existential randomness (NH-REACH-EXISTS): "can a lucky run reach G?"** Each `rn2(x)` result in [0,x) is
chosen by the player. Equivalent to Pr[reach G] > 0 under some strategy, given full support of every call [conj:
ISAAC64 mod x hits every residue].
- One-player reachability over a 2^{poly} graph ⇒ ⊆ NPSPACE = PSPACE (unbounded horizon) [thm: Savitch 1970] or NP
  (poly horizon / the 10^9 cap kept), given poly-time turns [conj].
- **Danger:** luck trivializes things. E.g. quaffing from a fountain can grant a wish (chance roll), a "lucky" trapdoor/level
  teleporter goes anywhere, and combat always hits. Instances must either avoid random sources that grant power, or the
  reduction must be robust to them [conj]. The randomness-free sublanguage avoids the issue entirely.

**(R3) Adversarial randomness (NH-REACH-ADV): "∀ outcomes, can the player force G?"** The player alternates with a
∀-nature. Sure-win (every outcome sequence) differs from almost-sure (probability 1). Define sure-win [assume].
- Unbounded horizon on 2^{poly} states: alternating PSPACE = EXPTIME [thm: Chandra, Kozen, Stockmeyer 1981] ⇒
  ⊆ EXPTIME. With a poly horizon (T unary): AP = PSPACE [thm: CKS 1981] ⇒ ⊆ PSPACE [conj for the NetHack premise].
- Lower bounds could exploit ∀-choices as a second player (e.g. monster movement as the adversary), which opens
  EXPTIME-hardness routes (succinct reachability games) [conj]. But this needs the adversary's choices to be
  "rn2-only" and fully adversarial, which overstates NetHack (real AI is mostly deterministic given RNG) [conj].

**(R4) Probabilistic threshold (NH-REACH-PROB): Pr[reach G] ≥ θ under optimal play.** An MDP whose
transition probabilities come from the `rn2` calls, idealized as exactly uniform (ignoring the `%` bias, [src rnd.c:63])
[assume].
- **Full information (recommended for R4) [assume]:** the player sees the true state S (not just `glyph` memory,
  [src rm.h:160]). An explicit MDP is solvable in time poly in its size. A succinct (2^{poly}-state) MDP ⇒ ⊆ EXPTIME for
  threshold reachability [thm: Papadimitriou & Tsitsiklis 1987, MDPs P-complete for explicit/finite horizon; the
  exponential blow-up from succinctness is standard] [conj for exact-threshold arithmetic on 2^{poly}-bit probabilities].
- **Partial observability (true NetHack: the hero sees `glyph`, not `typ`):** POMDP. Finite-horizon POMDP plans are
  PSPACE-complete for explicit models [thm: Papadimitriou & Tsitsiklis 1987]. Infinite-horizon threshold questions for
  finite POMDPs are **undecidable in general** [thm: Madani, Hanks, Condon 2003]. Our family is a restricted subclass,
  so this is a warning, not a result [conj].
- In the deterministic sublanguage, R4 with θ = 1 collapses to the deterministic problem.

Information matters only for R3/R4. Under R1/R2 with S in the input the player can simulate, so full vs partial
information makes no difference to existence of a plan [conj].

### 5.3 Recommendation

- **Primary: R2 (existential)** restricted to instances in the randomness-free sublanguage, where it coincides with R1,
  R3 and R4 [assume]. Lower bounds proved there are semantics-independent. Upper bounds are stated for R2 on all
  instances (one-player reachability: cleanest).
- Classify separately: **R3** (adversarial, the natural home of EXPTIME-type questions), **R4 full-info** (MDP
  threshold), **R4 partial-info** (POMDP, flag possible undecidability), **R1** (tool-assisted; note it is
  non-native).

---

## 6. Recommended primary formulation and variants

### NH-REACH (primary)

**Input:** an instance I = (D, H, g) where
- D = a generalized special level: one or more Lua des-scripts over the NetHack 5.0.0 `des.*` API with explicit
  coordinates and no RNG-dependent calls, for map size w×h (COLNO=w, ROWNO=h lifted as in §1.2), any level flags of
  [src sp_lev.c:3772-3819];
- H = a hero record (role, race, alignment, level, attributes, HP/maxHP, Pw, hunger, Luck, intrinsics, inventory,
  start cell);
- g = a target cell (x,y) on level ℓ.

Integers in H and D have their C widths (constant bits). Coordinates/ids have Θ(log n) bits. The 10^9 turn cap
is removed. Size n = |I| in binary.

**Semantics:** δ_n = NetHack 5.0.0 C code with the constants lifted. Every `rn2` outcome is chosen existentially (R2).
The hero's actions are any command of the game core (excluding wizard-mode/debug commands).

**Question:** does there exist a finite sequence of player commands and RNG outcomes such that the hero is alive and on
g at the start of some player turn?

### Variants

| Name | Change vs NH-REACH |
|---|---|
| NH-REACH-DET | Instances restricted to the randomness-free sublanguage (§5.1); all semantics coincide. Hardness target. |
| NH-REACH-SEEDED | R1: input includes a 64-bit seed/ISAAC64 state; deterministic; reseeding on level change disabled. |
| NH-REACH-ADV | R3: ∀ over RNG outcomes, sure-win. |
| NH-REACH-PROB(θ) | R4: Pr ≥ θ under optimal play; sub-variants -FULL (true state visible) / -PO (glyph only). |
| NH-REACH-T | Horizon T (unary) added; with T = 10^9 constant this is the literal cap. |
| NH-REACH-UNBOUNDED-INT | Integers arbitrary-precision and the turn cap removed. State can grow beyond n. |
| NH-REACH-1LVL | Single level (L = 1); default gadget setting. |

### Definitional choice → effect on plausible class range (no claims)

| Choice | Option | Effect on upper bound | Effect on lower bound | Why |
|---|---|---|---|---|
| Randomness | R1 / R2 | ⊆ PSPACE (unbounded), NP (poly horizon) [conj] | Same as deterministic in practice | One-player reachability on 2^{poly} states [thm: Savitch] |
| | R3 adversarial | rises to ⊆ EXPTIME (unbounded) / PSPACE (poly horizon) | May rise (adversary gadgets) | alternation [thm: CKS 1981] |
| | R4 full info | ⊆ EXPTIME-ish | ≥ deterministic | succinct MDP [thm: P&T 1987] |
| | R4 partial info | possibly no recursive bound | ≥ deterministic | POMDP undecidability [thm: Madani et al. 2003] |
| Turn cap | 10^9 kept | collapses to NP for R1/R2 (bounded witness) [conj] | PSPACE-hardness impossible unless NP = PSPACE | constant horizon |
| | parameter T unary | NP (R1/R2), PSPACE (R3) | — | poly horizon |
| | removed | PSPACE (R1/R2), EXPTIME (R3) | allows PSPACE-hardness | exponential-length plays possible |
| Integer width | C widths (const) | state O(n) bits | no counter-based gadgets beyond constant range | — |
| | poly-width binary | same space bounds; NP membership lost (exp. witnesses) | could allow binary-counter gadgets | — |
| | unbounded | PSPACE/EXPTIME bounds fail; possibly undecidable | counter-machine reductions [thm: Minsky 1967] | state grows during play |
| Initial states | (a) save-file | ill-defined (UB on bad invariants) | trivially strong (arbitrary states) | weak restore checks [src restore.c:1084-1099] |
| | (b) new-game reachable | no family / finite | none | no parameter |
| | (c) des-levels (rec.) | as above | all gadget freedom NetHack itself offers | engine-native loader |
| Levels | 1 vs L | unchanged asymptotically [conj] | multi-level adds stair/level-teleport gadgets | — |
| Goal | REACH vs SURVIVE(k binary) | SURVIVE with binary k may force exp. witnesses | — | §2 |
| Information | full vs partial | matters only for R3/R4 | — | §5.2 |

**The three choices that most move the answer [conj]:** (1) randomness semantics (∃ vs ∀ vs threshold, plus
observability), (2) horizon / turn cap (constant 10^9 vs parameter vs removed), (3) integer model (C widths vs
poly-width vs unbounded).
