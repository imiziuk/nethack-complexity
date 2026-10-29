# Milestone 1: definition, transition model, ranked strategies (orchestrator synthesis)

Source: NetHack 5.0.0, tag `NetHack-5.0.0_Released`, commit `16ff59115315917b93185d026aeefea06db9b0f4`.
Line refs are `src/<file>:<line>` inside the checkout. Inputs: `problem-definition.md`, `upper-bound.md`,
`lower-bound-strategies.md`, `../mechanics/*.md`. Labels: [src] auto-extracted from source, [orch-read] orchestrator
read the code itself, [conj] LLM conjecture, [assump] human/modelling assumption, [ext] external theorem.
**No class is declared here.** Adversarial review: `review-1.md` (pending).

## 1. The finite literal game and why the generalization is the research question

- Literal executable: COLNO=80, ROWNO=21 (include/global.h:382-383), ≤16 dungeons × 32 levels, fixed-width ints,
  hard turn cap `moves >= 1000000000L` -> game ends (src/allmain.c:253) [orch-read]. Finite-state: every
  question about it is decidable in O(1). Not interesting.
- A scalable family must lift constants. We lift: map w×h, number of levels L, number of objects/monsters/traps
  (already list-based), and **we must choose an integer model W** and **a horizon model H**. These two choices
  turn out to decide the class (§4), because of two clocks found in source:
  - **Turn cap** 10^9 (allmain.c:253).
  - **Hunger clock**: `gethungry()` decrements `u.uhunger` every turn unless `u.uinvulnerable` (only during
    prayer) or the form doesn't eat (src/eat.c:3163-3180) [orch-read]; starvation kills (eat.c:3437) [src].
    Prayer refills hunger but the prayer timeout grows by (moves−100000)/100 per prayer once moves > 100000
    (src/pray.c:1363-1377) [orch-read], so prayer fails as a food source after about 2×10^5 turns [conj: arithmetic
    in §4]. Renewable nutrition exists only through RNG outcomes: fountain "cool draught" +rnd(10)
    (src/fountain.c:281), `newman()` resets hunger to rn1(500,500) (src/polyself.c:414) via polymorph [orch-read].

## 2. Formal problem (primary + variants)

Adopted from `problem-definition.md` §6 with one correction (the integer model W is a separate axis, §4).

**NH-REACH_{R,W,H}.** Input I = (D, H₀, g):
- D: generalized special level(s) in NetHack's own Lua `des.*` format (src/sp_lev.c, dat/*.lua), explicit
  coordinates, no RNG-dependent calls, any level flags (sp_lev.c:3772-3819), map w×h.
- H₀: full hero record (role, race, attributes, HP, Pw, nutrition, Luck, prayer timeout, god anger, intrinsics,
  inventory incl. curse status). **Required**: a Lua level alone cannot stop the hero from dropping everything and
  squeezing onto boulders (hack.c:139-163) [src], so hardness needs hero state in the input [conj, check nhlua.c].
- g: target cell on a level. Question: is there a legal play reaching "hero alive on g at a player turn"?
- Legal commands: all non-wizard commands **except** `#exploremode` (lets the hero undo death) [assump].
- Axes:
  - R (randomness): DET = instances where no RNG outcome can change (hero position, boulders, terrain) — the
    calls still happen; R2 = ∃ outcomes; R1 = seeded (non-native: RNG is never saved and is reseeded from OS
    entropy on every level creation/reload, do.c:1709, mklev.c:1579 [orch-read]); R3 = ∀ outcomes;
    R4 = probability threshold (full / partial observation).
  - W (integers): W_C = C widths (int/long constant bits, coordinates Θ(log n)); W_poly = all game integers
    p(n)-bit; W_∞ = arbitrary precision.
  - H (horizon): H_cap = 10^9 kept; H_T = unary T in input; H_∞ = turn cap scaled with W (2^{width}) or removed.
- External inputs to fix as constants [assump]: wall clock (`night()`, `midnight()` read localtime mid-game:
  allmain.c:328, mhitu.c:979), moon phase, Friday 13th, birthday, bones files off, default options.

## 3. State and transition model (initial)

S = (Map, Levels, Objs, Mons, Traps, Hero, Timers, Globals, ρ):
- Map_ℓ: w×h array of `struct rm` (typ, flags e.g. doormask, wall_info W_NONDIGGABLE/W_NONPASSWALL, lit, seen,
  roomno 6 bits rm.h:168) per level + level flags (sokoban, noteleport, hardfloor, rndmongen…).
- Objs: object chains (floor per cell, inventory, containers nested, monster inventories, buried, migrating),
  each record = (otyp, quan:long, spe:schar, cursed/blessed, o_id, timers…).
- Mons: chain, ≤1 per cell (goodpos) + uncapped off-map migrating queue (dog.c:601-621) [src].
- Hero `u`: position, HP/Pw (int), nutrition (int), Luck (schar, ±10), ublesscnt, ugangr, intrinsics/timeouts,
  polymorph form + timer, encumbrance.
- Timers/regions/light sources; Globals: moves (long), context.ident, mvitals (uchar born/died).
- ρ: two ISAAC64 streams (~4 KB each), **not part of saved state**; modelled per axis R, not as state.
Full component table with file:line: `../mechanics/state-architecture.md`.

Transition T(S, a, r): one call of the main loop body `moveloop_core` (src/allmain.c) with hero command a and
RNG outcome sequence r. Per-turn RNG consumers: random monster generation (allmain.c:164; gated by level flag,
makemon.c:1168 returns NULL iff `!rndmongen && !ptr` [orch-read]), hunger accessory slot rn2(20) (eat.c:3189),
movement amount, regen, exerchk, engraving wipe. **Lemma 2 (draft)**: one T step is poly-time in |S| [conj; to verify
no super-polynomial per-turn loops, e.g. vision is O(w·h)].

## 4. Analysis: the integer/horizon model decides the class (central synthesis)

Lemma H (hunger horizon, DET + W_C) [conj, STRONG pending review]. In a DET instance with no monster generation
and no RNG-chosen nutrition, total nutrition available is ≤ u.uhunger₀ + Σ_food quan·nutrition + O(1) prayers
(timeout grows past 10^5 turns, pray.c:1371). With W_C every summand is ≤ 2^{O(1)} and there are ≤ n records,
so any play lasts ≤ c·n turns (c galactic but constant). Hence:
- **NH-REACH-DET_{W_C} ∈ NP** (guess a play of ≤ c·n turns, simulate) [conj STRONG; needs Lemma 2 and a check
  that no DET mechanic creates nutrition, e.g. eating through rock when polymorphed, hack.c:730, is bounded by
  the finite rock supply].
- So PSPACE-hardness for that variant would imply NP = PSPACE. The tightest likely answer there is
  **NP-complete**, via a SAT reduction whose yes-instances have poly-length solutions (Push-1 / Framework 1),
  with food = solution length [conj].

With W_poly (nutrition and turn cap p(n) bits), plays can last 2^{p(n)} turns:
- **Upper**: DET instances create no objects/monsters → state poly → NPSPACE = PSPACE (Savitch) [conj STRONG].
- **Lower**: Push-1F is PSPACE-complete [ext: Ani et al., FUN 2022, *verify*]; simulation lemma
  (lower-bound-strategies.md §2.2): Sokoban-flagged level with floor/wall/boulders only + hero carrying a cursed
  loadstone (500 wt, can't drop, do.c:685-697; squeeze needs inventory ≤ cap−850, weight.h:24; cap ≤1000) +
  one sealed sentinel pit (keeps the Sokoban flag on, trap.c maybe_finish_sokoban ignores no other condition)
  [orch-read] + nutrition 2^{p(n)} + noteleport, nomongen, nondiggable, nonpasswall.
- Together: **NH-REACH-DET_{W_poly} PSPACE-complete** [CONJECTURE: needs the simulation lemma verified line by
  line, the DET lemma (no RNG outcome matters: exerchk attribute drift, speed rn2, hunger rn2(20) with no
  accessories and ≤Burdened), and the Push-1F citation checked].

R2 (∃ randomness) with W_C: renewable nutrition (fountains, newman) makes unbounded plays possible, but also
opens every RNG-gated exploit (fountain wishes need Luck — instance sets Luck low; water moccasins; polymorph
side effects). Upper bound: unbounded object/monster growth (acid-blob farming, pudding cloning without birth
count, makemon.c:837, uhitm.c:1605) breaks poly-size state → no PSPACE bound without a population cap [src via
upper-bound.md]. Status: **open; possibly not even known decidable** [conj].

W_∞ (arbitrary precision): gold/shop credit and `quan` act like counters (no overflow check, invent.c:836) →
Minsky-style undecidability plausible [conj, weak].

## 5. Ranked strategies

Upper bounds (best first):
1. U1 DET_{W_C}: nutrition-horizon lemma → NP. Cheap; main risk a missed nutrition source.
2. U2 DET_{W_poly}: no creation in DET instances → poly state → PSPACE. Cheap.
3. U3 R3 full info with population cap / W_poly → APSPACE = EXPTIME [ext: Chandra–Kozen–Stockmeyer 1981].
4. U4 R2/R1 unrestricted: needs a population cap or a quotient lemma (upper-bound.md §6); likely false as stated.
5. U5 W_∞: no bound expected; aim for undecidability instead.

Lower bounds (best first):
1. L1 Push-1F → NH-REACH-DET_{W_poly}: PSPACE-hard (makes U2 tight). Needs simulation lemma + witnesses.
2. L2 Push-1 / Framework 1 → NH-REACH-DET_{W_C}: NP-hard (makes U1 tight). Self-contained boulder/hole gadgets.
3. L3 Transfer: DET hardness lifts to R2/R3/R4 only if DET instances stay DET-equivalent under those semantics
   (they do by definition of DET, if the DET lemma holds) [conj].
4. L4 Counter machine via gold/quan in W_∞ → undecidable. Speculative.
5. L5 EXPTIME-hard for R3 with monsters as adversary. Long shot.

## 6. Open checks before any claim is promoted
- Simulation lemma, line-by-line (hack.c test_move 1153-1171, moverock 348-640, could_move_onto_boulder 145-163).
- DET lemma: list every rn2 call reachable in a DET instance per turn (tools/extract_facts.py gives call sites)
  and show each outcome is irrelevant.
- Can the hero record be part of the input natively (nhlua hero setters? save-file format)? Else justify [assump].
- Real witnesses: a 1-gadget Sokoban level run headless (only when Ivan is off the laptop).
- Verify citations F2 (Push-1F) and F3 (Push-1 NP-hard).

## 7. After review 1 + blind theorist (2026-10-28) — supersedes §4 where they differ

- Review (`review-1.md`): 3 fatal-as-stated flaws, all repaired. (X1) Lua `nh.debug_flags({hunger=false})`
  (src/nhlua.c:1463, no wizard gate, "debugging use only") or an impossible H₀ disables hunger, so the hunger
  clock, not W, is the decisive axis. (X2) Strict DET is near-empty (fainting, Con drift, prayer anger are random);
  DET is now defined at the answer level: "no RNG outcome can help or hurt reaching g". (X3) god anger ≥ 1
  escalates; use anger 0, Luck 0, no full moon / Friday 13th, mongen off. Prayer cap is LARGEST_INT=32767
  (include/global.h:135), so prayer never stops entirely: Lemma H needs a rate bound (≤ ~1250 nutrition per
  ~32.6k turns < consumption).
- Blind theorist (`independent-theorist.md`) re-derived the hunger horizon without seeing this file.
- New axis replaces W as primary: **Hu ∈ {ON (faithful), OFF (debug flag)}**.
  - Hu=ON, DET-answer: target NP-complete (U1 + L2).
  - Hu=OFF, DET-answer: target PSPACE-complete (U2 + L1).
  - R2 with Hu=ON: magic fountain (src/fountain.c:279-284) gives renewable food → PSPACE-hard target, open upper bound.
- Modelling rules added: instance Lua = straight-line `des.*`/`u.*` calls from a whitelist (the Lua sandbox caps
  1 MB / 1M steps, sp_lev.c:6457, are hidden constants and lifting them makes instances Turing-complete);
  role fixed to one without force bolt; `#exploremode` forbidden; wall clock/moon/Friday-13 fixed.

## 8. Proposed next phase (needs Ivan's OK before scaling)
1. Ivan picks the primary hunger semantics (or both).
2. Formal proofs: Lemma H (rate argument), Lemma 2 (poly-time step), simulation lemma line by line → `proofs/`.
3. Verify citations (Push-1F, Push-1 NP-hard, Mundhenk et al.) with web search.
4. Headless witnesses via `test/testmove.lua`-style Lua harness: push rules, corner rule, loadstone squeeze block,
   sentinel pit (only when Ivan is off the laptop).
5. Lean skeleton: abstract grid-push model + simulation lemma statement; source facts as axioms with provenance.
6. Second review round on the repaired lemmas. Estimated 4–6 agents.
