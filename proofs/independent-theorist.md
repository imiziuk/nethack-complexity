# Independent theorist's view: classifying generalized NetHack

Written 2026-10-28 by an outside consultant agent. Inputs read: `proofs/problem-definition.md`, `mechanics/*.md`, plus
greps of `src/` (NetHack 5.0.0, 16ff591). I did NOT read milestone-1, upper-bound, lower-bound-strategies, claims, log.
Labels: **[src file:line]** checked in source (paths relative to `src/src/` unless shown) · **[ext]** external theorem
(**[ext?]** = citation from memory, verify) · **[conj]** my conjecture / unverified reasoning.

---

## 0. Bottom line first

The decisive mechanic is **hunger plus the prayer throttle** (section 3). Once these are modelled faithfully, a
hero who must eat can only survive for a number of turns that is **linear in the food written into the instance**,
unless the instance contains a *renewable* nutrition source. So:

* On the randomness-free sublanguage of problem-definition §5.1 (no fountains, no monsters, `nomongen`, an
  ordinary eating hero, C-width integers), every play is short. The problem is **in NP**, and I expect it to be
  **NP-complete**. PSPACE-hardness there is impossible unless NP = PSPACE.
* PSPACE-hardness needs an explicit renewable-food argument. Which argument works depends on the semantics:
  under existential randomness (R2), fountains on every floor cell give unlimited food. Under poly-width integers,
  one huge ration stack does. Under a liberal hero record, a non-eating form with intrinsic Unchanging does.
  Under seeded play (R1) it hangs on how ISAAC64 behaves, which cannot be proved.
* "NetHack contains Sokoban, Sokoban is PSPACE-complete, so NetHack is PSPACE-hard" is **wrong as stated** for any
  hunger-faithful deterministic formulation.

---

## (a) Which generalization, and how each choice moves the answer

### a.1 What scales
* **Map width/height** (COLNO/ROWNO) on a **single level**, with instances given as explicit des-levels (problem-definition
  §3(c)) plus a hero record. I agree with the team here. The level count adds nothing for hardness, and room ids stay
  O(1) (`roomno` is 6 bits [src include/rm.h:168]).
* **Objects and monsters scale with the input** (they are lists). One caveat the team's §2 regime 1 misses: "state =
  O(n) bits" is **not automatic**. Objects can be *created* during play: monster death drops and corpses, spells such
  as create monster with Pw that regenerates, `#name` making objects distinct so they do not merge, splitting a
  quan-Q stack into Q objects. The state bound holds only for an instance class whose object count stays
  poly-bounded. Sufficient condition [conj]: no object/monster creation sources, and stacks merge on drop
  (`stackobj`). Then each cell or container holds at most K distinct-kind stacks (K = a constant number of object
  kinds), so the state is O(n·K) bits.

### a.2 Integer model
| Choice | Effect |
|---|---|
| **C widths for per-object integers** (recommended) | State is O(n) bits (given a.1). **But the per-object nutrition is a constant (≤ 2^63 rations × 800), so total food is O(n): hunger then forces horizon O(n) (§3).** |
| poly-width binary | A single stack of 2^{p(n)} food rations [quan is `long`, src include/obj.h:47] buys an exponential horizon. Hunger is neutralised, so deterministic PSPACE-hardness becomes available. NP membership is lost. |
| unbounded | Matters only if growth sources exist; see (b) R-UNB. |

### a.3 Turn counter / horizon
* Remove the 10^9 cap [src allmain.c:253-256]. Literature convention: timers are dropped, e.g. Mario PSPACE-completeness
  ignores the level timer [ext?: Demaine, Viglietta, Williams, "Super Mario Bros. is harder/easier than we thought",
  FUN 2016].
* **But `moves` cannot simply stay a C `long`.** Kept at 64 bits it is just a 2^63 cap (constant horizon again).
  Made unbounded, it puts an unbounded integer into the state. The fix is an **abstraction lemma** [conj, needs
  an audit of 212 `svm.moves` uses in 47 files, grep]. `moves` affects play only through:
  (i) differences with absolute timers (relative deltas are C-width);
  (ii) residues `moves % {2,3,5,7,10,20,30,600,...}`, e.g. [src allmain.c:299,551,604,640,643; monmove.c:309; timeout.c:607];
  (iii) monotone thresholds that saturate: the prayer throttle saturates at LARGEST_INT [src pray.c:1365-1378];
  `ALIGNLIM = 10 + moves/200` [include/align.h:17] matters only through `u.ualign.record`, an `int`
  [src attrib.c:1313-1314], so it saturates once moves ≳ 4·10^11.
  So (min(moves, M0), moves mod P) for constants M0, P is a sound finite abstraction. This lemma is **required for
  every PSPACE/EXPTIME upper bound**. It is not in problem-definition.md.
* **With the 10^9 cap kept the situation is worse than problem-definition §2 says.** For the deterministic sublanguage
  the problem is in **P** (galactic degree), not just NP. A play has ≤ 10^9 turns. Each turn has poly(n) distinct
  choices: O(1) commands × O(wh) targets (travel, controlled teleport) × 52 letters. So there are poly(n)^(10^9)
  candidate plays [conj: zero-time commands can be normalised away].
  Under R2 the per-turn RNG choices are 2^{poly}, so the problem is in NP. Either way it is an artifact.

### a.4 Hunger: keep it
Hunger is a core rule, not a constant. Disabling it needs `u.uinvulnerable` or the wizard-only `debug_hunger`
[src eat.c:3166-3167], so removing it is a **new game**. Keep it, and say exactly which instance features make
nutrition renewable (§3). Moving hunger in or out changes the class (NP vs PSPACE), so this choice must be in the
problem statement.

### a.5 Randomness semantics
R2 (∃ outcomes) as the primary semantics is fine for upper bounds, but **R2 is a different game**: luck turns
fountains into infinite food and, at shallow depth, into wishes
(`rnd(100) > 80 + level_difficulty()` [src fountain.c:76-80], `level_difficulty = depth(&u.uz)` [src dungeon.c:2036]).
A wish grants e.g. a scroll of earth (new boulders) or a wand of striking, which wrecks boulder gadgets
(mechanics/terrain-movement §Gadget killers). R2 reductions must place the level at depth ≥ 20, so that no wish
is possible. I'd keep R2 and R3 as the two primary semantics, and drop R1 (non-native: the RNG is never saved and
is reseeded per level).

### a.6 Hero record
Must be restricted. At minimum: an ordinary eating form, no lifesaving, no explore mode [src cmd.c:952], and
intrinsics limited to those obtainable in play. A record that allows "polymorphed into a non-eater + intrinsic
`HUnchanging`" switches hunger off: base hunger skips non-eaters [src eat.c:3174-3179], and the source comment notes
that staying polymorphed normally needs an *amulet*, which still burns nutrition [src eat.c:3170-3173]. This one
switch moves the deterministic problem from NP to (likely) PSPACE.

---

## (b) Bounds per formulation

Common premise P0 [conj, team must certify]: one turn is computable in poly(n) time, including a poly bound on RNG
calls per turn and on zero-time commands between turns.

### F1 (my preferred): NH-REACH-DET-H: deterministic sublanguage, C widths, hunger ON, ordinary eating hero, no cap
Instances: problem-definition §5.1 sublanguage (no fountains/sinks/monsters, `nomongen`, no spells/wands that create
monsters, no polymorph).

* **Upper bound: NP** [conj, near-provable]. Key lemma (horizon bound): every play has length
  ≤ c1 + c2·N(I), where N(I) = Σ nutrition × quan over food in I.
  * Base hunger is −1/turn for eaters [src eat.c:3174-3179]. Starvation comes once hunger drops below −(100+10·CON)
    [mechanics/objects §5, eat.c:3437-3444]. Slow digestion is a ring/armor: excluded, or it at most scales
    c2 by 20.
  * Prayer is the only free refill: it sets hunger to 900 and fixes TROUBLE_STARVING when `u.uhs >= WEAK`
    [src pray.c:216-217]. It only works when `ublesscnt ≤ 200` [src pray.c:2151], and `ublesscnt` drops by 1 per turn
    [src allmain.c:276-277].
  * After each prayer, `ublesscnt = rnz(350) + (moves−100000)/100`, capped at 32767 [src pray.c:1356-1378]; the
    source comment says outright that "eventually hunger prayers will fail".
  * Once moves ≳ 2.5·10^5, the post-prayer wait exceeds the ≤ 1250-turn hunger budget, so prayer contributes
    only O(1) turns plus food-funded waiting. Hence the play length is O(n) (constant ~2^73 because quan is
    C-width), and the witness is poly.
* **Lower bound: NP-hard** [conj]. Boulders are Push-1F: pushing a boulder onto another boulder is refused
  [src hack.c:432-435, per mechanics], so exactly one block moves per push, and walls are fixed blocks.
  * Diagonal movement is harmless when the level has the Sokoban flag: diagonal pushes are refused
    [hack.c:442], and a diagonal squeeze past two boulders/walls is refused (`bad_rock`, hack.c:939-975). So hero
    reachability equals 4-connected reachability [conj].
  * Use **no pits at all**, so `maybe_finish_sokoban` never fires [trap.c:7059-7097, per mechanics].
  * Give the hero > capacity−850 carried weight, so they cannot squeeze onto boulders
    [hack.c:145-163, weight.h:24, per mechanics].
  * Reduce from Push-1 NP-hardness [ext?: E. Demaine, M. Demaine, J. O'Rourke, "PushPush and Push-1 are NP-hard in 2D",
    CCCG 2000], or from Push-1F.
  * Hunger: put a C-width ration stack on cells along the route. The reduction's solution length must be
    O(area), which holds if each gadget is traversed O(1) times [conj].
* **Verdict: NP-complete** [conj]. This is the only formulation where I think a full proof is within reach.

### F2: NH-REACH (R2, ∃ randomness), C widths, hunger ON, fountains allowed
* **Upper: PSPACE** [ext: Savitch 1970, NPSPACE = PSPACE], given P0, the `moves` abstraction (a.3) and a bounded
  object count (a.1). Without the object-count restriction I can't justify any recursive bound under R2 with
  `rndmongen` on, because luck yields unboundedly many distinct objects [conj: open].
* **Lower: PSPACE-hard** [conj, my best candidate]:
  * Make **every non-wall floor cell a FOUNTAIN** at depth ≥ 20. Quaffing: fate `rnd(30)` < 10 gives
    `u.uhunger += rnd(10)` [src fountain.c:247,276-279]. `dryup` removes the fountain only on `!rn2(3)`
    [src fountain.c:200-201], so ∃-luck keeps every fountain forever. Net gain is up to +9 per quaff turn.
  * Boulders may stand on furniture (furniture doesn't block pushes, per mechanics 1.1.4).
  * Then reduce from Push-1F PSPACE-completeness [ext?: Ani, Asif, Demaine, Diomidov, Hendrickson, Lynch, Scheffler,
    Suhl, "PSPACE-completeness of pushing blocks via checkable gadgets: Push-1F and Block/Box Dude", FUN 2021].
    Fallback: Sokoban PSPACE-complete [ext: Culberson 1999; Hearn & Demaine, TCS 343 (2005), via NCL], but its goal is
    boxes-on-targets, which needs translation to REACH.
  * Risks: the hero must stand on a fountain whenever it needs food; a boulder parked on a fountain blocks that cell
    only. Also check that no fountain fate is *forced* (all are rnd-chosen).
* **Verdict: PSPACE-complete** [conj, plausible].

### F3: NH-REACH-ADV (R3, ∀ randomness, sure-win), hunger ON
* Fountains are useless (nature dries them up). `nomongen` is mandatory, otherwise nature spawns a killer and almost
  every instance is "no". With F1's horizon lemma the game has poly length.
* **Upper: PSPACE** [ext: Chandra, Kozen, Stockmeyer 1981, AP = PSPACE].
* **Lower: PSPACE-hard** [conj]. Nature becomes the ∀ player through a placed **wandering monster as a mobile
  blocker**: a monster blocks boulder pushes [hack.c:456-483], and its move choice uses rn2 in `m_move`
  (mechanics/objects §4). Reduce from QBF / stochastic-free games.
* **With hunger neutralised** (non-eater hero or poly-width food): upper EXPTIME [ext: CKS 1981, APSPACE = EXPTIME],
  lower EXPTIME-hard [conj, via two-player constraint logic: ext?: Hearn & Demaine, *Games, Puzzles, and
  Computation*, 2009].

### F4: NH-REACH-PROB (R4, threshold θ), full information
* Fountains dry w.p. 1/3 per quaff, so food is finite a.s. With F1's lemma the horizon is poly.
* **Upper: PSPACE** (expectimax by DFS to poly depth; probabilities have poly bits after idealising
  `% x` to uniform [src rnd.c:61-64]) [conj, standard; cf. ext?: Mundhenk, Goldsmith, Lusena, Allender, JACM 47 (2000)
  on succinct finite-horizon MDPs].
* **Lower: PSPACE-hard** [conj] via Stochastic SAT [ext: Papadimitriou, "Games against nature", JCSS 31 (1985)], with
  random monster moves as the R-quantifier. Unbounded horizon: EXPTIME upper (LP on 2^{poly} states) [conj].
* Partial observability: with premapped, monster-free levels nothing relevant is hidden. The POMDP undecidability
  [ext: Madani, Hanks, Condon, AIJ 147 (2003)] needs an infinite horizon, which hunger takes away. So I don't expect
  undecidability for hunger-faithful instances [conj].

### F5: R1 seeded, and unbounded integers
* **R1**: deterministic, with a 4 KiB ISAAC64 state in the configuration. Upper bound **PSPACE**; lower bound **NP-hard**
  (F1 instances).
  * Whether fountains are renewable depends on whether the stream offers "fate<10 ∧ no dryup" turns often enough.
    The player can steer this, because ≥ 3 RNG calls are consumed every turn even under `nomongen` [src allmain.c:164-167,
    eat.c:3191].
  * That is a pseudo-randomness property of ISAAC64: **unprovable in practice**. The classification under R1 is
    stuck at NP-hard ∩ PSPACE.
* **Unbounded integers**: in a closed instance (no creation sources), split and merge preserve the total quan, so the
  values stay ≤ input values: still **PSPACE** (binary-encoded). Undecidability via Minsky machines [ext: Minsky
  1967] would need unbounded growth (RNG luck or spells) **and** game-enforced zero tests.
  * The only exact tests I see are hero-side: `!invent` and the weight thresholds in `could_move_onto_boulder` and
    the diagonal squeeze ≤ 600 rule [per mechanics 1.1/1.4]. The controller can dodge them by dropping items.
  * So I would **not** claim undecidability [conj: open].

---

## (c) The mechanic most likely to break naive arguments

**Hunger with the prayer anti-bot throttle** [src eat.c:3174-3179; pray.c:1356-1378]. It is an unremovable clock.
Under any semantics without renewable food it bounds the horizon linearly in the instance's food, which caps hardness
at NP. Consequences:
1. The team's §5.1 "randomness-free sublanguage" (it excludes fountains and monsters) **cannot host a PSPACE-hardness
   proof** unless NP = PSPACE. Hardness proved there does transfer to all semantics, but only as NP-hardness.
2. PSPACE-hardness is semantics-specific: fountains under R2, huge stacks under poly-width, non-eater + intrinsic
   Unchanging under a liberal hero record. So "a hardness result that holds under all semantics" is likely only
   NP-hardness.
3. The same clock trap reappears with `moves` as a C `long` (a 2^63 cap) and with the 10^9 cap (P/NP collapse). Every
   upper bound needs the `moves` abstraction lemma (a.3).

Runner-up issues: R2 luck granting wishes at depth < 20 [fountain.c:76-80]; object-count blow-up under R2 with
monster generation on, which breaks the "O(n)-bit state" premise behind every PSPACE upper bound; and the hero's
squeeze-onto-boulder rule even in Sokoban mode (it costs only Luck, so it must be blocked by carried weight).
