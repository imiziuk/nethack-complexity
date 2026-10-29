# Upper bounds and state space: generalized NetHack reachability

Source: NetHack 5.0.0 (tag NetHack-5.0.0_Released, commit 16ff591), `src/` read-only. Paths below are relative to `src/`.
Labels: [auto-extracted file:line] = grepped in source this session; [LLM conjecture] = my reasoning, unverified;
[external theorem] = published result, cite carefully; [human assumption] = modelling choice to be fixed by the team.
Status of the whole file: DRAFT, session 1 (2026-10-28).

## 0. Setting (provisional)

- Instance: encoded state S (w x h maps, L levels, w,h,L <= poly(n), all monsters/objects/hero/RNG state) + goal G
  (e.g. hero on square g). Question: does some legal command sequence reach G?
- Generalization knobs that change the answer:
  - (K1) **Integer width.** "Same code": every integer keeps its C type (`long quan` [auto-extracted include/obj.h:47],
    `long moves` [include/decl.h:1165], `unsigned o_id` [include/obj.h:43], `coordxy` = `int16_t` [include/global.h:71],
    `long credit/debit` in shops [include/mextra.h:126-127]). Since coordinates must grow with n, the honest version is
    "word size = Theta(log n)" or "fixed 64-bit words, w,h <= 2^15". [human assumption] Alternative (K1'): unbounded
    integers in binary.
  - (K2) **Population bound.** Is the number of objects/monsters a hard cap, or can it grow during play? (Section 1: it can grow.)
  - (K3) **Horizon.** Unbounded turns vs. turns <= poly(n) given in unary.
  - (K4) **Randomness** R1 (seed in input), R2 (existential outcomes), R3 (adversarial), R4 (probability threshold).

## 1. Facts about population growth (verified)

Monsters:
- One monster per square per level: `level.monsters[COLNO][ROWNO]` is a single pointer per square
  [auto-extracted include/rm.h:476]; `place_monster` complains if occupied [include/rm.h:522]; `goodpos` rejects occupied
  squares [src/teleport.c ~ line 114-118, `MON_AT`]; random spawns go through `makemon_rnd_goodpos`
  [src/makemon.c:1076-1126]. Long worms: segments share the head pointer [src/teleport.c:121-124 comment].
  => **on-map monsters <= w*h per level** [auto-extracted].
- Random spawn each turn with prob 1/70 (1/50 below the castle, 1/25 after demigod) [src/allmain.c:160-167].
- Species extinction: `propagate` increments `mvitals[].born` and sets G_EXTINCT once born >= MAXMONNO = 120
  (Nazgul 9, erinyes 3) [src/makemon.c:958-981, 1549-1550; include/global.h:415]. Random selection skips G_GONE
  species (`uncommon`) [src/makemon.c:1593-1597, 1688, 1724]; when nothing qualifies `makemon` returns null
  ("no more monsters!") [src/makemon.c:1218-1221]. => **randomly generated monsters are bounded** by ~120 x #species.
- BUT a *specific* monster request is only refused if genocided, not if extinct [src/makemon.c:1203-1210]. Confused
  create monster asks for `PM_ACID_BLOB` specifically [src/read.c:1615-1618], and `SPE_CREATE_MONSTER` runs the same
  scroll effect [src/spell.c:1529-1530]; energy regenerates over time [src/allmain.c:600-615].
  Pudding cloning refuses only if extinct or mhp <= 1 [src/makemon.c:845-847].
  => [LLM conjecture, chain verified piecewise] **an unbounded stream of new monsters is possible** in a long game
  (one at a time, each needing a free square).
- Off-map monsters: a follower that cannot be placed on arrival goes to `failed_arrivals` then `m_into_limbo`, which
  re-queues it on `migrating_mons` for the same level [src/dog.c:601-621, 396-414; src/mon.c:3834-3840].
  [LLM conjecture] Limbo is a list with no size cap, so the off-map population is not bounded by w*h*L.

Objects:
- Floor objects are linked lists (`nexthere`) [include/obj.h:18,38]; containers nest (`cobj`) [include/obj.h:42].
  No per-square cap found. [auto-extracted; absence of a cap is LLM conjecture from not finding one]
- Merging: dropping calls `stackobj` [src/do.c:837] which merges into one record with `quan += quan` and **no overflow
  check** [src/invent.c:4366-4374, 836]. Mergeable requires same otyp, `oc_merge`, same BUC etc.
  [src/invent.c:4386-4400]. Weapons/armor/most tools are not `oc_merge` => stay as separate records.
- Monster death drops a random object with prob 1/6 (not for clones/kops) [src/mon.c:3587-3594].
  => with the unbounded monster stream above, **the number of separate object records is unbounded** [LLM conjecture].
- Hero inventory is weight-bounded: carrying capacity capped at MAX_CARR_CAP = 1000 [include/weight.h:25;
  src/hack.c:4316]; weight sums saturate at LARGEST_INT = 32767 [src/mkobj.c:1960; include/global.h:135].
  Hero inventory and its nesting are therefore bounded in the fixed-width model; the floor is not.

Other counters:
- Luck clamped to [-10, 10] (+3 from luckstone) [include/you.h:460-468]. XL <= 30 [include/global.h:413,
  include/you.h:378]. Exp saturates at LONG_MAX [src/exper.c:179-181]. These are the code's own "fixed width" stance.
- `o_id` behaviour is mostly identity plus a few `o_id % k` effects (helm of opposite alignment, T-shirt text,
  stacking of charged objects) [src/do_wear.c:470; src/invent.c:4487; src/read.c:185,279,430-482]; `next_ident` adds
  rnd(2) each time [src/mkobj.c:505-520]. So identifiers matter only modulo small numbers and as distinct names.
- RNG: ISAAC64 context, constant size [src/rnd.c:7-21, 43].

## 2. Lemma 1 (state representation bound)

**Lemma 1a (STRONG, under assumptions).** [LLM conjecture, built on the facts above]
Assume (K1) words of O(log n) bits (or fixed 64-bit) and (K2-cap) a cap P(n) = poly(n) on the total number of
monster and object records (plus their timers, light sources, regions, engravings, shop bills, which are bounded by a
constant per record or per square). Then every reachable state has an encoding of size
O((w*h*L + P(n)) * log n) = poly(n) bits, plus O(1) bits of RNG state (ISAAC64) and O(#species) birth counters.
Proof sketch: map layer O(w*h*L) records of O(1) words; each monster/object a constant-size struct
(obj/monst structs; extra structs `mextra`/`oextra` constant size except name strings, bounded by BUFSZ);
pointers replaced by indices of O(log P) bits.

**Lemma 1b (negative, CONJECTURE).** Without (K2-cap), the reachable state space of a single instance can be infinite even
with fixed-width integers: unbounded acid-blob creation (confused SPE/SCR create monster, extinction ignored for specific
monsters) + 1/6 random death drops of non-mergeable objects + limbo queue for off-map monsters. Each record is O(1) words,
so after T turns the state is O(T + poly(n)) words: the state is **linear in elapsed time**, not in n.
Caveats to verify: hunger (prayer fixes it periodically, so unbounded play is plausible), energy needed per cast,
whether acid blob passive damage stops this, whether non-mergeable death drops really accumulate on one square.

**Lemma 1c (quotient idea, CONJECTURE).** Objects of identical attributes on one square behave identically except for
`o_id` (identity, and `o_id % k` effects). If a bisimulation argument shows that only "count capped at some c(n)" matters
per (square, object-kind) class, the reachable quotient is poly(n)-size again. This is the main open route to PSPACE for
the unrestricted game; it fails if any mechanic counts objects exactly (weight sums on the floor? `#force`, kicking piles,
monsters picking up entire piles, scare monster pickups, shop price totals).

## 3. Lemma 2 (transition computability)

**Lemma 2 (STRONG for poly-size states).** [LLM conjecture, with source anchors] One command and the resulting turn are
computable in time poly(|S|) and space O(|S|):
- `movemon` iterates all monsters once (`iter_mons_safe`) [src/mon.c:1326-1330]; each monster's `dochug`/`m_move`
  [src/monmove.c:690, 1715] looks at O(1) neighbouring squares, but some routines scan the level or monster list
  (e.g. target selection, `set_apparxy` [src/monmove.c:2198]); worst case O(|monsters| * w*h) per turn.
- `vision_recalc` loops over all rows and per-row column ranges [src/vision.c:512, 570-620]: O(w*h) per call,
  possibly several calls per turn. Travel `findtravelpath` is a BFS over the level [src/hack.c:1266]: O(w*h).
- Hard-coded loops over ROWNO/COLNO appear in ~235 places [count via grep], all linear or quadratic in map size.
- No recursion found that is exponential in map size [LLM conjecture: not exhaustively checked; flood fills and
  explosion chains should be audited].
- A single command can expand into a multi-turn occupation or a count prefix (`n20s`); count is bounded by
  LARGEST_INT in some prompts [src/invent.c:1944]. Model each turn as one step, so a command = poly many steps.
Net: per-turn cost poly(n) when the population is poly(n). Under Lemma 1b it is poly(T + n).

## 4. Theorem-1 candidates per randomness variant

Assume Lemma 1a (poly state) and Lemma 2 throughout, unless stated.

| Variant | Candidate upper bound | Status | Argument |
|---|---|---|---|
| R1 seed in input, unbounded horizon | **PSPACE** | STRONG (given 1a) | Configuration graph with 2^poly(n) nodes; player choice = nondeterminism; NPSPACE = PSPACE [external theorem: Savitch 1970]. Also gives "reachable iff reachable within 2^poly steps". |
| R1, horizon poly(n) unary | **NP** | STRONG (given 1a) | Guess the command sequence, simulate (Lemma 2). |
| R2 existential outcomes | **PSPACE** (poly horizon: NP) | STRONG (given 1a) | Outcomes are just more guesses; transition relation still poly-time checkable. |
| R3 adversarial, full observation, unbounded horizon | **EXPTIME** | STRONG (given 1a) | Reachability game on 2^poly graph = attractor computation in exp time; equivalently APSPACE = EXPTIME [external theorem: Chandra-Kozen-Stockmeyer 1981]. |
| R3, poly horizon | **PSPACE** | STRONG (given 1a) | AP = PSPACE [external theorem: CKS 1981]. |
| R3, partial observation (player does not see RNG / hidden squares) | **EXPSPACE** for unbounded horizon via subset construction (2^2^poly belief states, reachability game on beliefs) ; poly horizon: NEXPTIME-ish / PSPACE depending on formulation | CONJECTURE | [external theorem] Reif 1984 (imperfect-information games: exponential blowup); Peterson-Reif-Azhar 2001 (team/hidden-info games up to undecidable for multiplayer). Two-player one-sided hidden info with poly-space positions: EXPTIME-hard and in 2-EXPTIME/EXPSPACE region; pin down before citing. Recommend: **define R3 with full observation** (RNG outcomes revealed after each step) for Theorem 1. |
| R4 probabilistic threshold, Pr[reach G] >= theta | **EXPTIME** (exact threshold via LP on exp-size MDP); PSPACE if horizon poly and we only need the optimal value | CONJECTURE (STRONG for EXPTIME given 1a) | Succinct MDP with 2^poly states: optimal reachability probability by LP in poly(size) = exp time [external theorem: standard MDP LP]. Succinct/compressed MDPs are EXPTIME-complete for many objectives [external theorem: Papadimitriou-Tsitsiklis 1987 for finite-horizon poly MDPs P-complete; succinct versions EXP-complete, Mundhenk-Goldsmith-Lusena-Allender 2000]. Poly horizon full observation: PSPACE (finite-horizon MDP evaluation by recursion with poly depth, rational numbers of poly bits). Note RNG is a pseudo-random ISAAC64, so "probabilistic" is an idealization [human assumption]. |
| Any variant, no population cap (Lemma 1b), fixed-width ints | **r.e. only** (semi-decidable for R1/R2) | CONJECTURE | Infinite configuration graph; reachability is Sigma_1. Decidability needs a quotient (Lemma 1c) or a WSTS argument. |
| Unbounded integers (K1') | possibly **undecidable** | CONJECTURE | See Section 5. |

## 5. Where decidability could break

Counter-machine ingredients (increment, decrement, zero test on two independent unbounded quantities) [LLM conjecture
for each, source anchors given]:
1. **Floor object counts per square** (non-mergeable records, or one mergeable stack under K1'): increment = drop,
   decrement = pick up one (`#pickup` with count), zero test = whether a pickup takes a turn / "nothing here" (time passes
   or not, which changes monster moves). Unbounded supply from death drops of an unbounded acid-blob stream
   [src/mon.c:3587; src/read.c:1615]. Two squares give two counters; the inventory weight cap (1000) only limits what the
   hero carries at once, not the floor counts. This survives **even with fixed-width ints** (counts = number of records),
   so it is the most dangerous one.
2. **Gold / shop credit** (`long credit`, `debit` [include/mextra.h:126-127]; `quan` of coins always merges
   [src/invent.c:4391-4393]): increment by selling, decrement by buying, zero test = "cannot afford". Needs K1'
   (otherwise wraps at 2^63; note no overflow check at src/invent.c:836).
3. **Object `quan`** under K1': split with `#adjust`/count-drop, merge on drop; zero test = stack exists or not.
4. **Turn counter** `moves` (long) [include/decl.h:1165]: only increments; `moves % k` tests (e.g. energy regen
   [src/allmain.c:604]) are bounded-modulus. Not a counter by itself, but under K1' it is unbounded state with no decrement.
5. Bounded, cannot serve as counters: luck [-10,10] [include/you.h:467-468], XL <= 30, exp saturates at LONG_MAX,
   weight sums saturate at 32767, `born` saturates at 255 [src/makemon.c:970].
Risk statement: with K1' (or with unbounded populations) the problem plausibly simulates a 2-counter Minsky machine
[external theorem: Minsky 1967], giving undecidability (Sigma_1-complete for R1/R2). Proving this needs a gadget whose
zero test is forced (player cannot cheat), which is the hard part; it is a lower-bound task for the hardness agent.

## 6. Ranked upper-bound strategies

1. **Cap the population in the problem definition (K2-cap: total records <= poly(n), creation fails beyond) + fixed
   O(log n)-bit words** -> PSPACE for R1/R2, EXPTIME for R3 full-obs, EXPTIME for R4. Obstacle: it is a modelling
   restriction; must argue it is "the same game" (the code already caps randomly generated monsters per species,
   so a global cap is in its spirit but not in its letter).
2. **Poly horizon (turns <= p(n) in unary)** -> NP (R1/R2), PSPACE (R3, R4 finite-horizon). No cap needed: population
   grows by O(1) per turn so states stay poly. Obstacle: per-turn creation must be O(poly) (check mass creation such
   as confused scroll = 13 monsters, explosions, polypiling) and it changes the question to bounded reachability.
3. **Quotient / bisimulation of identical objects (Lemma 1c)** -> PSPACE for the unrestricted game. Obstacle: must
   show no mechanic distinguishes counts above c(n); exact counts are visible via pickup menus, weights and
   `o_id % k`, so likely false in the letter of the code.
4. **Well-structured transition system argument** (monotone in object counts) -> decidability without a complexity
   bound. Obstacle: zero tests (pickup succeeds or not, boulder blocks movement) break monotonicity.
5. **Arbitrary-precision integers (K1')** -> no upper bound expected; best one can claim is r.e. for R1/R2.
   Obstacle: likely undecidable (Section 5).

**Single biggest obstacle:** reachable states are not poly-size in the unrestricted game: specific-monster creation
ignores extinction (src/makemon.c:1203-1210) and energy regenerates, so a long game can create unboundedly many
monsters, death-drop objects and limbo monsters. Every PSPACE/EXPTIME bound above therefore needs either a population
cap, a poly horizon, or a quotient lemma.

## 7. To verify next (open checks)
- Is acid-blob farming actually sustainable (Pw cost of create monster, hunger via prayer timeout `ublesscnt`
  [include/you.h:484], passive acid)? Any cleaner unbounded object source (e.g. tree fruit, fountain, sink)?
- Does anything on the floor auto-merge or auto-delete objects (e.g. object rot timers only for corpses/eggs)?
- Audit for per-turn work superlinear in w*h (explosion chains, flood fill, `vision` multiple calls).
- Fix R3 observation model with the setting agent before citing Reif.
