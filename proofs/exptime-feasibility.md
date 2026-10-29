# EXPTIME feasibility study: generalized NetHack under adversarial randomness (R3)

Feasibility agent, 2026-10-29. Source: NetHack 5.0.0 @ 16ff591, read-only (`src/<f>` = `src/src/<f>`). Nothing built
or run, nothing committed. Labels: **VERIFIED** (source line read this session) · **STRONG** (argument complete, not
reviewed) · **CONJECTURE** · **FAILED**. Builds on hu-off.md, variants.md, phase2-spec.md (Rev. 1-3) and the parallel
audits `exptime-mech-doors.md` (+ `exptime-sources.md`, `exptime-mech-monsters-traps.md`, `exptime-model.md` if
present; see §7).

## 0. Verdict

**PARTIAL → conditional GO.**
- **Language:** L_OFF^{W+C} under R3 = L_OFF^W (hunger off, mongen off, Push-1F boulders, Sokoban rules, heavy hero)
  + teleport traps inside a `des.teleport_region{exclude=Z}` zone + one cursed pair of fumble boots; `noteleport` dropped.
- **Nature mechanism (new, not in the parallel audits): the restricted teleport coin C (§3).** A seen teleport trap in
  a teleport-restricted rectangle (the Wizard's-Tower `tele_jump_ok` rule) sends the hero to exactly one of two cells
  A, B, nature's choice; Fumbling removes the only veto (seen-trap escape). It meets all of exptime-sources.md's
  N1-N4 (forced, non-stallable, one-way-able, unboundedly reusable, single level, nothing consumed) and the model's
  H4/H6/H7 (positional, no new creators, zero damage) — VERIFIED line by line, STRONG as a lemma, witness W9 pending.
  It is the best candidate found: doors veto (FAILED), crawl-out has a null (FAILED), pool fill consumes boulders
  (FAILED: ≤ poly choices ⇒ PSPACE), boulder teleport is global (FAILED), monsters are a large audit and the hero can
  swap with peacefuls deterministically (hack.c:2154-2169).
- **Source:** Stockmeyer–Chandra **G6** (as recommended in exptime-sources.md; ALBA route §4.2 as backup), realized as
  a planar one-agent system of self-closing doors + diodes + crossovers + nature forks (§4-5).
- **What is not done (the GO condition):** Push-1F's SCD/diode/crossover are only *checkable, nonlocal* 1-player
  simulations (Ani et al. Def. 5.1-5.3). They must be re-proved **game-safe** (winning strategy never enters a broken
  state on any nature branch; coin kept off the check path). If that lifts, L_OFF^{W+C} (R3) is EXPTIME-complete;
  if not, own gadgets are needed (high risk). Effort §7: ~2-4 weeks of agent sessions, dominated by that step.

## 1. What EXPTIME-hardness needs (STRONG, standard)

1.1 **Unboundedly many nature choices.** If every play contains ≤ p(n) nature choices, the R3 game is in PSPACE:
W_k(c) = "∃ player path c → nature node a, ∀ outcomes c' of a: W_{k−1}(c')"; each level is an NPSPACE reachability
with a recursive oracle, depth k ≤ p(n), poly space per level [ext: Savitch 1970]. So one-shot mechanisms (e.g. boulder
into water, which consumes the boulder) can never give EXPTIME-hardness.

1.2 **No null outcome.** A reachability player loses infinite plays. If some roll has an outcome that leaves the game
where it was (veto, "nothing happens", "back where you came from"), nature repeats it forever and the gadget is a wall.
The parallel door audit reaches the same conclusion for every door roll (exptime-mech-doors.md §5).

1.3 **No extra nature power.** Under R3 nature takes the worst branch of *every* roll in the play. Any reachable
damage/teleport/curse roll elsewhere must be harmless or avoidable by the player.

1.4 **Player commitment.** After a nature choice the hero must be unable to undo it (one-way paths), and re-triggering
must only give nature another identical choice (harmless).

1.5 **R2 ≠ R3 is expected.** A nature choice is by definition a place where R2 (∃ outcomes) gives the player the
choice. So the new language is studied under R3 only; under R2 it stays in PSPACE (hu-off Thm A, if the whitelist
extension keeps Lemma 1). Bonus: same language, R2 PSPACE-complete vs R3 EXPTIME-complete would be a clean separation.

## 2. Mechanism survey (task 1)

| # | Mechanism | Source | Nature controls | Null outcome? | Repeatable? | Extra nature power | Status |
|---|---|---|---|---|---|---|---|
| M1 | Doors: open / close / kick / unlock / search | lock.c:904, 1039; dokick.c:930; detect.c:2043 (via door audit) | success or "resists" | **yes** (failure = no-op) | yes | trapped doors (excluded) | **FAILED** (veto only; exptime-mech-doors.md §5) |
| M2 | Boulder into pool: fill (90%) or sink | do.c:55-75 (`chance = rn2(10)`, `fills_up = chance != 0`) | pool → floor, or pool stays | no (boulder consumed either way) | **no**: each try consumes a boulder; no boulder creator in W | none found | **FAILED for EXPTIME** (≤ #boulders choices ⇒ PSPACE by 1.1). Useful only for PSPACE-level ∀ gadgets |
| M3 | Hero falls into water, crawls out to a random neighbour | trap.c:5059-5170 `drown`; trap.c:4947-4970 `rnd_nextto_goodpos` (shuffles all 8 dirs, checks all: no give-up); hack.c:4079-4101 `crawl_destination` | which goodpos neighbour | **yes**: entry square S is always a legal crawl target (crawl_destination's diagonal test = test_move's corner test, symmetric; goodpos(S) holds) | yes | drowning if no target (avoidable); `emergency_disrobe` only if encumbered (hero unencumbered) | **FAILED** (S = null; already noted in variants.md §C.4). Repairable only by non-adjacent entry (jump: Knight/jumping boots), which adds a long-range move to the whole Push-1F simulation: not recommended |
| M4 | Hero teleport trap, unrestricted level | teleport.c:1492-1530 `tele_trap` → teleport.c:849-930 `scrolltele` → teleport.c:717-770 `safe_teleds` | any `teleok` cell of the whole level | no (own square is a trap: `teleok(..,FALSE)` rejects it, teleport.c:420-440) | yes | **global**: nature puts the hero on the worst cell of the level | **FAILED** as is; see M5 |
| **M5** | **Hero teleport trap inside a teleport-restricted zone** (`des.teleport_region{..., exclude=Z}`) | `tele_jump_ok` teleport.c:386-418 (inside the `delarea` rectangle ⇒ destination must be inside, and vice versa); region parse sp_lev.c:5443-5460; `delarea` → `dndest/updest.nl*` mkmaze.c:613-635; `teleok` calls `tele_jump_ok` (teleport.c:420-440); fallback scan also uses `teleok` (teleport.c:745-768) | which non-trap goodpos cell of Z | **no**, given (a) Fumbling (seen-trap escape `!rn2(5)` is skipped when Fumbling, trap.c:3035-3043) and (b) no `noteleport` flag (teleport.c:30-39, 852) | **yes, unbounded** (trap persists; `once` unset; no `teledest`) | see §3.3: none found besides time | **CHOSEN** (STRONG, source-read; witness pending) |
| M6 | Boulder pushed onto a teleport trap | hack.c:578-590 → `rloco` teleport.c:2102-2135 | boulder lands on any goodpos cell; `tele_jump_ok` NOT applied to objects (only W-tower/fall restrictions) | no | yes | **global** (boulder dropped into any corridor); after 4000 tries uses last coords even if bad | **FAILED** (design invariant: no boulder may ever reach a teleport trap) |
| M7 | Hole/trapdoor fall: arrival cell on the next level | trap.c:602-690 `fall_through`; do.c:1804 `u_on_rndspot` (arrival inside the level's down-tele region, `place_lregion` has a deterministic fallback scan) | arrival cell in region | no | yes (climb back by stairs) | destination depth fixed **at creation** by `hole_destination` `rn2(4)` loop (trap.c:442-453, 520-522) ⇒ instance ill-defined unless the hole is on the dungeon's second-to-last level; arrival level must be scripted ⇒ needs a custom dungeon description (multi-level, not des-level-only) | **STRONG alternative, heavier spec**; keep as Plan B |
| M8 | Peaceful monster random walk (`appr = 0` for peacefuls, monmove.c:1859-1872; peacefuls always reach `m_move`, monmove.c:880-887) | monmove.c | the walker's next cell, every turn | must check whether a peaceful can stand still when it has moves (else veto); speed must be a multiple of 12 (random `mmove_adj` rounding otherwise lets nature freeze it) | yes | **hero can swap places with peacefuls deterministically** (hack.c:2154-2169: refused only if the hero's old square is not goodpos for it, has a trap, or it is `mundisplaceable`) ⇒ a blocker is not a blocker; monster AI audit is large; requires dropping `mongen=false` (which deletes all monsters, nhlua.c:1463-1482) and using level flag `nomongen` | **CONJECTURE, not recommended** (deferred to exptime-mech-monsters-traps.md) |
| M9 | R1/R2 with monsters as a deterministic 2nd player | — | — | — | — | — | **Not natural**: monster moves are functions of RNG outcomes; under R1 they are a fixed pseudo-random stream (player can't be "against" them), under R2 the player chooses them. A genuine 2nd player exists only under R3 |
| M10 | Squeaky board, pit/web/bear-trap durations, fainting, regen, exercise | trap.c, eat.c, allmain.c | time or noise only | n/a | — | bear trap / land mine / rolling boulder do HP damage (permanent under R3: regen refusable, door audit D5) | **FAILED** (time is free with hunger off; no positional choice) |
| M11 | Confusion/stun random direction, ice slip `hurtle` | hack.c `confdir`; timeout.c:1262-1290 | direction | yes (blocked direction = no move) | — | needs items/ice | **FAILED** |
| M12 | Fountains/sinks/thrones | fountain.c, sit.c | many outcomes | yes ("tepid water", nothing) | — | water moccasins/demons need makemon (dead with mongen=false) but wishes/teleports/curses exist; thrones break Lemma 1 under R2 (hu-off A.4) | **FAILED** |

## 3. The chosen mechanism: the restricted teleport coin (M5)

### 3.1 Gadget C (coin)
A rectangle Z = `exclude` area of one `des.teleport_region` call. Inside Z: trap cell T (`des.trap("teleport", T)`),
exactly two non-trap floor cells A, B that are goodpos for the hero, everything else wall. Z's cells are reachable on
foot from outside only via the entry corridor to T and the exit corridors from A and B (walking across Z's border is
unrestricted; only teleports are). No boulder can ever reach T, A, B (M6, and goodpos excludes boulder cells,
teleport.c:177-178). Hero wears cursed fumble boots (whitelist add: FUMBLE_BOOTS, objects.h:722-724, cursed).

### 3.2 Behaviour (STRONG; each step VERIFIED in source)
Hero steps onto T (any time, any number of times):
1. `dotrap`: not FORCETRAP; `floor_trigger && check_in_air` false (not levitating); seen-trap escape needs `!Fumbling`
   → skipped (trap.c:3026-3043). → `trapeffect_telep_trap` → `tele_trap` (trap.c:2070-2085).
2. `tele_trap`: not endgame, no Antimagic, not `noteleport_level` (flag absent, no demon court) ; `next_to_u()` true
   (no pets); `trap->once` false; `teledest` not ok (no launchplace in des) → `tele()` (teleport.c:1492-1530).
3. `scrolltele`: `(u.uhave.amulet || On_W_tower_level) && !rn2(3)` false (no amulet, not W tower) — this is the only
   "nothing happens" branch and it is closed; no Teleport_control → `safe_teleds` (teleport.c:849-930).
4. `safe_teleds`: 40 random tries with `teleok(..,FALSE)`, then a full ring scan with the same test, then a trap
   backup spot (teleport.c:717-770). `teleok` rejects trap cells (so not T), non-goodpos cells, and anything outside Z
   (`tele_jump_ok`, hero is inside the `delarea`). Hence the destination is **exactly A or B, nature's choice; never
   T, never outside Z, never "no teleport"**.
So C = a ∀-vertex with in-port T and out-ports A, B, reusable forever, state-free.

### 3.3 Extra powers given to nature (audit; STRONG unless marked)
- Fumbling (boots): `slip_or_trip` on the HFumbling timeout = `nomul(-2)` + messages (+ "trip over" objects under the
  hero: only possible object is none/ball) (timeout.c:912-924, 1225-1330). Off ice there is no `hurtle`
  (timeout.c:1262-1290 is the ice/FROMOUTSIDE branch only). Fumbling also blocks autoopen (hack.c:1098; no doors) and
  doubles #untrap chances (trap.c:5320; player-chosen). Effect: **time only**; time is free with hunger off. Weight
  500 + 20 = 520: still `inv_weight > −850` (hu-off I3), and unencumbered iff wc ≥ 520 — check the hu-off "wc ≥ 550"
  claim once [CONJECTURE until checked].
- Dropping `noteleport`: other teleport sources stay unreachable (no ^T intrinsic, no items, no monsters; prayer's
  STUCK fix excluded by hu-off I7). [STRONG, inherits hu-off §B.4 audit]
- Zones restrict *all* hero teleports level-wide; hero placement at start must use the same region record: put the
  start cell s in `region` and Z in `exclude` (u_on_rndspot uses `place_lregion(region, exclude)`); with `dir="down"`
  and `dir="up"` two independent rectangles exist ⇒ up to 3 bounded zones (D∩U, D\U, U\D). One coin suffices (§4.3).
- Phase2-spec Rev. 3 stair pocket must stay outside Z.
- R2 view: the same trap is a *player* choice under R2 — consistent with 1.5. R4 view: the coin can be re-triggered,
  so a probability-1 player could retry until lucky (fails exptime-sources N5): the result is for R3 only (model H8).
- Model checklist (exptime-model.md): C1 (no creator: teleport moves only the hero; boots are one declared record),
  C2 (`safe_teleds` ≤ 40 tries + one O(w·h) scan, teleport.c:717-770; no uncapped loop), C5 (no level change: TELEP_TRAP
  ≠ LEVEL_TELEP; the only `morehungry` in teleport.c is the `^T` path, teleport.c:1159-1160, not reached), H6 (no
  hero gain), H7 (zero HP cost per coin use) — all hold [STRONG].

### 3.4 Language L_OFF^{W+C}
L_OFF^W (hunger off, mongen off, harness, pettype:none, stair pocket) with: level flag `noteleport` removed (keep
`sokoban`, `noflip`, `hardfloor`, `solidify`); whitelist adds TELEP_TRAP (explicit coords, no destination),
`des.teleport_region` with `exclude`, and one cursed FUMBLE_BOOTS given via `u.giveobj` (the player may wear them; not
wearing only gives nature an extra veto). Semantics R3 (full information, adaptive, infinite play = loss).

## 4. Source problem (task 2)

4.0 **Chosen: G6** (Stockmeyer–Chandra 1979; verbatim in Hearn 2006 §6.2.1 / Demaine–Hearn CCC 2008): CNF F over
X ∪ Y, players flip ≤ 1 own variable or pass, Player I wins iff F ever becomes true; infinite play = no win for I
(= our REACH semantics). Construction (exptime-sources.md §5): hub → player selector (free fork) → forced set path
(open own literal SCDs, open-then-traverse the complementary ones = forced close) → **nature tree of ⌈log₂(2|Y|+1)⌉
coin uses** → forced set path for y_j → hub; checker = clauses in series, each clause = parallel literal-SCD traversals,
then t. With one physical coin, nature's tree uses context SCDs as in 4.3 (open K_u before the coin, demux on K_u
after it; the demux traversal closes K_u by itself — SCDs make this free). Checker passability is monotone in open
doors and the only opening routes are legitimate set paths, so cheating never helps [STRONG for the abstract system].

4.1 **Backup: ALBA.** Direct: acceptance of a fixed alternating linear-space TM M (ASPACE(n) = EXPTIME [ext: Chandra,
Kozen, Stockmeyer, JACM 28(1) 1981]). Reason: our "nature" moves only where the hero walks, so the clean target is a
one-token game graph with ∀-vertices, not a symmetric game where the opponent moves anywhere (2CL, G-games). 2CL
(Hearn–Demaine, unbounded 2-player constraint logic, EXPTIME-complete) and locking-2-toggle 2-player motion planning
(Demaine–Hendrickson–Lynch ITCS 2020, EXPTIME-complete via 2CL; arXiv 1812.03592) both give the opponent a free choice
of *where* to move and need a separate agent or a shared robot (SAND 2023 shared-robot game with ko rule, EXPTIME-complete
[secondary summary, not read]). They are fallbacks if §4.2 fails review; exptime-sources.md has the literature.

4.2 **Intermediate problem DOOR-GAME (STRONG, standard construction).** Directed graph with player vertices,
nature vertices (out-degree 2), door gadgets (tunnels: open, close, traverse-iff-open; each tunnel one-way), start, goal.
Reduction from M on input x, |x| = n: doors D[i,b], i ≤ n, b ∈ {0,1}, invariant "exactly one of D[i,0], D[i,1] open"
(cell i holds b). Vertex v[q,i]: player vertex → traverse D[i,0] or D[i,1] → r[q,i,b] (only the true one passes).
r[q,i,b]: player vertex if q ∃, binary tree of nature vertices if q ∀, one leaf per transition τ = (q,b → q',b',±1);
leaf → close D[i,b] → open D[i,b'] → v[q', i±1]. Accept states → goal; dead ends → sink (no exit). Infinite plays lose
for both M (least fixed point) and the game. Size O(|δ|·n). Correct if door tunnels are **forced** (traversal always
performs the action) and the only routes are the drawn ones.

4.3 **One coin is enough (STRONG).** Replace every nature vertex u by: open a context door K_u → walk to the single
coin C → from A (resp. B) a demux: parallel branches "traverse K_u → close K_u → u's left (right) successor", one per
u; only the open K_u passes. Invariant: all K closed outside the coin trip. Poly many K doors.

## 5. Reduction sketch and risks (task 3)

Gadgets needed in the boulder world (Sokoban rules, heavy hero, hunger off):
- G_door: reusable door with forced open/close tunnels and a read tunnel that does not change state.
- G_diode: reusable one-way corridor.
- G_cross: reusable crossover (4.2's graph is not planar; Lichtenstein-style planarization not available for game
  graphs without a crossover).
- C: §3 (done modulo witness).
The player choice vertex is free (a fork in a corridor). Alternation is enforced by graph structure: every route to the
goal passes the coin whenever M is in a ∀ state, and one-way gadgets stop the hero from backing out.

**Plan A (preferred, found 2026-10-29): use self-closing doors (SCD) instead of 3-tunnel doors.** Facts from the papers
(arXiv HTML read via WebFetch, secondary-level, re-read before citing): (i) Ani et al.'s Push-1F proof reduces from
*planar reachability with self-closing doors* (their Thm 2.5) and builds a **checkable** SCD in Push-1F from a
reusable diode, a 1-toggle and helpers; the simulation is *nonlocal*: a final checking path (with weak-closing and
single-use crossovers) rules out plays that left a gadget "broken" (Def. 5.2) [arXiv 2412.20079]. (ii) "Walking through
Doors is Hard, even without Staircases" (Ani, Bosboom, Demaine, Diomidov, Hendrickson, Lynch, FUN 2020; arXiv
2006.01256 v2 2026 "Universality and PSPACE-hardness of Planar Door Gadgets"): **every SCD planarly simulates every
gadget, incl. a directed crossover (their Lemma 2.6)**, so no separate crossover is needed [secondary summary].
SCD fits 4.2 even better: reading cell i *closes* D[i,b] (self-closing traversal), the transition then *opens* D[i,b'];
declining to open only strands the player. So the target becomes **SCD-GAME := planar SCD reachability + nature
vertices** (EXPTIME-hard by 4.2 with SCDs, planarized by the universality paper's crossover), realized by Ani et al.'s
checkable Push-1F SCD + the coin C. What must be re-proved for games: (a) the universality paper's *local* simulations
remain correct when nature vertices sit outside the gadgets (game simulation, not just 1-player trace equivalence:
partial traversals / backing out must give the player nothing new); (b) Ani et al.'s *postselection* argument holds
per play (a winning play ends through the check path, so no gadget was broken at the end) — needs "broken is
absorbing" or a final-state-only argument; (c) nature's coin never sits on the check path. [CONJECTURE, the crux]

**R1 (main risk) — reusable *forced* boulder doors (if Plan A fails).** Push-1F hardness (Ani et al. FUN 2022) uses checkable gadgets
whose transitions may be "weak" (the agent may decline a state change or break a gadget; correctness comes from a final
check). In 1-player PSPACE reductions declining never helps; in 4.2 a declined "close D[i,b]" would let the player read
both values = cheat in the player's favour. Need: either (a) Ani et al.'s gadgets give a context-independent simulation
of a gadget for which a 2-player/∀ theorem exists (then cite instead of 4.2), or (b) design forced doors ourselves and
brute-force-check them with tools/fastbfs (the hero must push the block to get through, so writes are naturally forced;
the hard part is a read that is non-destructive and a door that cannot be jammed half-open). [CONJECTURE]
**R2 — crossover.** hu-on-lower's G_X is one-shot for one direction. A reusable crossover in Push-1 with Sokoban corner
rules is not known to us; the Push-1F paper's network may avoid crossings by its own gadget choice. [CONJECTURE]
**R3 — hidden nature power.** Everything not in §3.3 that nature touches in an exponentially long play: exercise drift
(attributes only change weight cap: hu-off I3 robust), prayer (player's choice, never needed), Fumbling timeouts.
Also the weight margin with boots (§3.3). [STRONG for listed items]
**R4 — spec acceptability.** Fumbling boots + teleport zones are native (Wizard's Tower uses exactly this exclusion
mechanism), but each whitelist growth must be re-audited for hu-off Lemma 1/2 (no object/monster creators: boots and
traps create none).

## 6. Upper bound (task 4) — STRONG
R3 game on L_OFF^{W+C}: state = hu-off Lemma 1 state + worn-boots flag, HFumbling timeout (long, W_C), trap `tseen`
bits, the two region rectangles (static). No new creators: teleport moves the hero only; boots create nothing. Step
time poly: `safe_teleds` is ≤ 40 + O(w·h) `teleok` calls (teleport.c:717-770). A full-information reachability game on
2^{poly} states is solved by an attractor computation in exponential time (= APSPACE = EXPTIME [ext: CKS 1981]); infinite
plays are losses (least fixed point). **L_OFF^{W+C} under R3 ∈ EXPTIME.** Under R2 it stays in PSPACE (Savitch).

## 7. Plan, effort, witnesses (task 5)
Lemmas: (L1) coin lemma §3.2 (done in text; needs a second reader); (L2) Fumbling/no-noteleport audit added to hu-off
§B.3-B.5 (≈ 1 session); (L3) DOOR-GAME EXPTIME-hard (§4.2-4.3, 1 session, write-up only); (L4) Plan A: read Ani et al. §§5-7 (checkable SCD, check path) and the
door-universality paper's Lemma 2.6 in full; prove the game versions (a)-(c) of §5 Plan A; transcribe the Push-1F SCD,
diode, 1-toggle into Sokoban-rule boulder maps (Push-1F ≡ our movement, Lean L1) and exhaustively check each with
tools/fastbfs (3-6 sessions, highest risk); fallback: own G_door/G_cross designs; (L5) global layout + generator
(2 sessions, reuse tools/gen_on_instance.py patterns); (L6) review round.
Witness scripts to run in the real game (tools/witness, WSL headless build, #wizloadlua; not run here):
- W9 `exp_coin.lua`: zone {T,A,B}, cursed fumble boots worn, step on T 200× over 3 seeds: hero always lands on A or B,
  both seen, never stays on T. Control 1: no boots ⇒ "You escape a teleportation trap" occurs. Control 2: no `exclude`
  ⇒ hero lands outside Z.
- W10 `exp_coin_boulder.lua`: push a boulder onto T ⇒ boulder relocates outside Z (documents M6 as a hazard).
- W11 `exp_fumble_push.lua`: with fumble boots worn, W1-W4 behave identically (pushes, refusals, no squeeze).
Overall: **PARTIAL** now; GO if L4 succeeds (estimate 2-4 weeks of agent sessions, dominated by L4).
(L3 is now "G6 → planar SCD + coin system EXPTIME-hard", §4.0, replacing the ALBA lemma.)

Top 3 risks: (1) Push-1F's checkable/postselected SCD, diode and crossover simulations are 1-player Karp-level
results; lifting them to games (broken-state absorption on every nature branch, coin off the check path) is unproved.
(2) The door-universality crossover (Ani et al. FUN 2020, Lemma 2.6) and Push-1F's single-use/weak crossovers must
be reusable and leak-free against an adaptive hero in a game. (3) Hidden nature power from the whitelist growth:
Fumbling timeouts, dropped `noteleport`, encumbrance margin with boots (520 vs wc ≥ 550, attribute drift under R3),
and the invariant that no boulder ever reaches a teleport trap (M6 = global relocation).

Synthesis note: exptime-mech-monsters-traps.md was not yet written when this file was finalized; its monster-walker
candidate (M8) should be compared against C, but C already satisfies N1-N4 with a far smaller audit.

## 9. Witness results (2026-10-29)
Real game: NetHack 5.0.0 headless tty (WSL build of tools/run_witnesses.sh), `#wizloadlua`, one fresh game (system
seed) per run, 40 re-entries of T per run. Scripts `tools/witness/exp_coin*.lua` (generated variants of one template),
driver `tools/witness_driver_exp.py`, batch `tools/run_witnesses_exp.sh`; raw lines in `build/witness-exp-results.txt`.
Board: Z = {A=(7,1), T=(8,1), B=(9,1)} (one row), entry E=(8,2) below T, two open rooms with ~60 free cells outside Z
(incl. (6,1), (10,1), E right next to Z), Rev. 3 start (1-cell `teleport_region`, branch stair via `des.levregion`
into a sealed pocket). Every run asserted start cell = S0, trap `tseen`, boots worn + cursed (lua `obj:totable()`).

| Witness | Runs × entries | Landings | Verdict |
|---|---|---|---|
| W9 coin (cursed fumble boots + cursed loadstone, seen trap) | 30 × 40 = 1200 | A 608, B 592, T 0, outside Z 0, no-move 0; both in every run | **PASS** |
| W10 veto check (no boots) | 15 × 40 = 600 | A 225, B 227, **T 148** (= 148 "You escape a teleportation trap", ≈ 1/5 as `!rn2(5)`), in every run | **PASS** (escape exists ⇒ boots needed) |
| W11b positive control Z = {C=(6,1),A,T,B} | 10 × 40 = 400 | A 143, B 136, C 121, T 0, outside 0 | **PASS** (landing set = free non-trap cells of Z, exactly) |
| W11c negative control (no `exclude`) | 10 × 1 | 8 of 10 outside {A,B}: (4,3) (8,3) (2,1) (6,3)×3 (5,2) (3,1); A 1, C 1 | **PASS** (the zone is what restricts) |

Other effects (tty text scan; message counts are inflated by redraws, presence is reliable): with boots only
"You trip over your own feet" / "slip and nearly fall" / "flounder" / "stumble" + "You make a lot of noise!"
(timeout.c slip_or_trip + wake_nearby; no monsters) — they recur over ~100 turns per run, so the HFumbling timeout
re-arms as read (timeout.c:924). Never: "trip over <object>", dropping, hurtle/ice slide, Burdened/Stressed, HP loss
(16/16 at end of every run), "disoriented", "wrenching", "shudder", "mysterious force". Time only, as §3.3 says.

Surprises / harness notes:
1. **Wizard mode diverts trap teleports to a getpos prompt** (scrolltele: `|| wizard`). The driver answers `.` = the
   hero's own cell T; T is a trap ⇒ `teleok` false ⇒ "Sorry..." ⇒ `safe_teleds`, i.e. exactly the non-wizard path
   (observed "Sorry..." before every landing). A non-wizard game cannot load the level, so this is the closest
   faithful run. A queued key (not a tty key) at that prompt would abort the teleport (getpos.c:816-825).
2. Fumbling's `nomul(-2)` and its `unmul` clear the canned key queue (hack.c:4172 `cmdq_clear`), so scripted keys
   pushed while helpless are dropped; the scripts re-push until the hero moves (no double moves possible).
3. API form confirmed (sp_lev.c:5410-5459, mkmaze.c:611-634, teleport.c:386-418): `des.teleport_region({ region =
   {s}, region_islev = true, exclude = {Z}, exclude_islev = true, dir = "both" })` — one call is both the start
   region and the coin zone (start is placed in region \ exclude). Without `exclude_islev = true` the exclude
   coordinates are **map-relative** (levregion_add → get_location); `nlx > 0` is the "zone present" test, so Z must
   not start at absolute x = 0. `des.exclusion` is a different mechanism (arrival placement / monster generation,
   mkmaze.c:423, teleport.c:181), not usable for the coin.
4. Encumbrance: this Valkyrie with loadstone 500 + boots 20 was never Burdened; the wc ≥ 520 margin claim (§3.3)
   still needs the general check for the instance's fixed attributes.
Not run: §7 W10 boulder-onto-T (M6 hazard) and W11 fumble-push (W1-W4 with boots) from the original §7 list.
