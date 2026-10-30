# Live claims table

Labels: VERIFIED (source read by orchestrator + reasoning checked) · STRONG (argument complete, survived one review
or independently re-derived) · CONJECTURE · FAILED. Membership and hardness listed separately.
Updated 2026-10-29 (reviews 3-4, Lean, variants, prior work); first written 2026-10-28 after phase 2 (reviews 1-2, blind theorist, proofs hu-off / hu-on-upper / hu-on-lower); L_ON* rows 2026-10-29 (global construction + generator + brute-force checker).

## Source facts

| # | Fact | Where | Status |
|---|---|---|---|
| F1 | Version 5.0.0 exists; commit 16ff591 | include/patchlevel.h:10-15 | VERIFIED |
| F2 | Game ends at moves ≥ 10^9 | src/allmain.c:253 | VERIFIED |
| F3 | RNG not saved; reseeded on level creation/reload | src/do.c:1709, src/mklev.c:1579 | VERIFIED |
| F4 | `rndmongen` level flag off blocks random spawns only; `debug_mongen` blocks all | src/makemon.c:1168 | VERIFIED |
| F5 | Sokoban flag clears when no non-hero PIT/HOLE left (sentinel pit keeps it) | src/trap.c maybe_finish_sokoban | VERIFIED |
| F6 | Hero can't diagonal-squeeze in Sokoban; light hero can step onto boulders | src/hack.c:139-163, 955-979 | VERIFIED |
| F7 | Hunger decrements each turn unless invulnerable / non-eating form / `debug_hunger` | src/eat.c:3163-3180 | VERIFIED |
| F8 | Prayer timeout grows by (moves−10^5)/100 per prayer, capped at LARGEST_INT=32767 | src/pray.c:1363-1377, include/global.h:135 | VERIFIED |
| F9 | Lua `nh.debug_flags({hunger=false, mongen=false})` works with no wizard-mode gate; source calls it "debugging use only" | src/nhlua.c:1459-1489, test/testmove.lua:143 | VERIFIED |
| F10 | Magic fountain "cool draught" (+rnd(10) food) returns before dryup | src/fountain.c:279-284 | VERIFIED |
| F11 | Lua can set hero inventory (`u.clear_inventory`, `u.giveobj`) | nhlua per review-1 | STRONG (not re-read) |
| F12 | Under R2 the hero can avoid starving forever: the starvation test runs only on some faint-roll outcomes (corrected 2026-10-29: it is also reached while fainted when the roll is < 19 and uhs > WEAK), and R2 picks the outcome that skips it | src/eat.c:3414-3437 | VERIFIED (corrected) |
| F13 | `des.object` quantity loops for non-mergeable objects | src/sp_lev.c:3732 | VERIFIED |
| F14 | newgame: mklev before hero kit; pet survives reset unless pettype:none | src/allmain.c:807-815, src/dog.c:225, src/nhlua.c:1473 | VERIFIED |
| F15 | Push-1F PSPACE-complete (Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch, FUN 2022, LIPIcs 226) | proofs/citations.md | VERIFIED (web) |
| W1-W8 | Real-game witnesses: orthogonal push, refused diagonal push, refused diagonal squeeze, heavy hero can't step on boulder, sentinel pit keeps Sokoban; L_ON gadgets closing site, one-way door, hole crossover — all behave as the proofs say | tools/witness/*.lua via tools/run_witnesses.sh (WSL headless build of 16ff591, #wizloadlua) | VERIFIED experimentally: 8/8 pass in 3 of 3 full runs (different RNG seeds), 2026-10-29. Evidence, not proof. |

| L1 | Lean 4 + Mathlib: `simulation` (Push1F.solvable B c₀ ↔ NH.solvable B c₀) for the movement model `nhMove`; no sorry, axioms only propext/Classical.choice/Quot.sound | proofs/lean/NetHackPush.lean, build-log.txt | VERIFIED (formal) for the model; nhMove vs C checked by hand (review 3: HOLDS) |

## Complexity claims (phase 2; languages in proofs/phase2-spec.md incl. Revisions 1-3)

| Language | Claim | Kind | Status | Evidence / remaining gap |
|---|---|---|---|---|
| Literal game, or 10^9 cap kept | decidable in O(1) / in P | upper | STRONG | constant horizon |
| **L_OFF^W** (hunger off, whitelist) | ∈ PSPACE | upper | STRONG (survived review 2) | proofs/hu-off.md Thm A, Savitch |
| **L_OFF^W** | PSPACE-hard, for R1–R4 | lower | STRONG (survived review 2 after pet repair) | Push-1F (F15) + simulation lemma (Lean L1), hu-off.md Thm B/C; review 3: stair-pocket hole found and repaired (Rev. 3 item 8, not re-reviewed); open: Lemma E (c) check of Ani et al. Figs 32-37 (enclosure) |
| L_OFF unrestricted (any des.object) | ∈ PSPACE | upper | CONJECTURE, likely FALSE | thrones give unbounded wishes under R2 (sit.c) |
| **L_ON\*** (faithful hunger, R2 + rule S, whitelist) | ∈ NP | upper | STRONG (survived review 2) | proofs/hu-on-upper.md, horizon margin 0.907 |
| **L_ON\*** | NP-hard (answer-level DET, so for R1–R4 too) | lower | STRONG (gadgets proved + witnessed W6-W8; global construction explicit, hu-on-lower §4-5, 2026-10-29) | proofs/hu-on-lower.md §4-5; tools/gen_on_instance.py; tools/check_small.py on all 513 PMR instances with n, m ≤ 3 [auto-experimentally verified, partial: 370/370 SAT levels won by replay, 20/20 SAT BFS find g, UNSAT exhaustive 19/23 levels unreachable (tools/fastbfs; [3][-3][1,2,3] = 48,002,512 states, 2026-10-29), 4 largest unfinished (capped at 90 M states, g not reached), 0 mismatches]; review 4: Lemmas 4.1/4.2, §5 HOLD, generator stair pocket repaired; open: DET for R1/R3/R4 if the hero starts Burdened (vary_init_attr can give Str+Con = 16, wc 450 < 500; §5 hunger budget assumes speed 12; R2 claim unaffected; found 2026-10-30), exact de Berg–Khosravi statement (citations R2-1 PARTIAL), Lemma 4.2 by hand only, no generated level run in the game (smallest 132×132) |
| ⇒ L_ON\* | **NP-complete** | both | STRONG (not machine-checked; gadget witnesses pass; global layout brute-force checked for n, m ≤ 3) | above two rows |
| ⇒ L_OFF^W | **PSPACE-complete** | both | STRONG (survived review 3; movement core formal in Lean; witnesses 8/8 ×3) | above |
| L_ON, R2 without rule S | hunger not a clock (faint forever, F12) | — | VERIFIED mechanism; PSPACE-complete STRONG (variants.md (b), survived review 3) | proofs/variants.md |
| L_ON, R3 (∀ outcomes) | NP-hard and ∈ PSPACE (poly horizon, AP); exact class open | both | STRONG (variants.md (c), survived review 3) | proofs/variants.md |
| R3 full info, poly state | ∈ EXPTIME | upper | STRONG | APSPACE = EXPTIME |
| W_∞ | undecidable | lower | CONJECTURE (weak) | — |
| **L_OFF^{W+C}** (hunger off, teleport-coin traps + cursed fumble boots, R3, non-wizard mode) | ∈ EXPTIME | upper | STRONG | proofs/exptime/B-reduction.md Thm M (APSPACE = EXPTIME) |
| **L_OFF^{W+C}** | EXPTIME-hard (from Stockmeyer–Chandra G6) | lower | CONJECTURE, strong partial evidence | coin real-game witnessed (W9–W11, 1,200 landings only A/B); SCD verified in model + real game (0 mismatches); check path 5.94 M-position end-to-end; crossover v2 map (453×432) passes X_verify + review5_abc/cd; review 5: T1 holds (700 random G6, 0 mismatches), joined-check-port bug found and repaired (2026-10-30, not re-reviewed); layout generator built (tools/exptime/L_gen.py, proofs/exptime/L-generator.md, 2026-10-30): main layer generated concretely, network = G6 on 340+ random instances (S1/S2 0 mismatches), check path routed for all 8 crossover variants and every tile type + independent replay, Z1/Z2 on the generated coin, S3 postselection end to end (abstract); machinery gadgets on the routed path not drawn in cells (STRONG), smallest level ≈ 40k×7k cells, so no real-game run. Open: SC79 original text (repair 6, citation PARTIAL), C-vs-model neighbourhood check, Lean, review 6 |

Nothing is VERIFIED at the theorem level: proofs are LLM-written drafts that survived adversarial reviews (1-4).
Formal: only the movement simulation lemma (L1). Witnesses W1-W8 pass. Prior work: none found for NetHack (proofs/prior-work.md).

## FAILED / withdrawn

| Claim | Why it failed |
|---|---|
| "NetHack 5.0.0 doesn't exist" | tag exists (F1) |
| "Lua level alone can't fix hero inventory" | partly reversed: Lua sets inventory (F11); role/spells still need fixing |
| Light hero Push-1F reduction | squeeze onto boulders (F6) |
| DET_{W_C} PSPACE-hard (no turn cap) | hunger clock (F7, F8) |
| DET_{W_C} ∈ NP as originally stated | instance can disable hunger via F9 or impossible H₀ (uinvulnerable); repaired by splitting the hunger axis |
| "DET = no RNG outcome changes the state" | almost empty (fainting, Con drift, prayer anger are random); redefined at answer level |
| Block prayer with god anger ≥ 1 | anger escalates (minions, wand of striking drops); use anger 0, Luck 0 |
| Fountains at depth ≥ 20 never dry up (theorist) | not in source: dryup is rn2(3) at any depth (fountain.c:201) |
| Hunger ON is a clock under R2 | faint-forever loophole (F12); needs rule S [assump] |
| Lua script can be run at game start as the level | kit + pet are created after mklev (F14); run after newgame + pettype:none |
| Pits as barriers (hu-on-lower draft) | hero falls in and climbs out (trap.c:1920, 4209); holes used instead |
| Setup always places the hero on s (L_OFF/L_ON) | DL1 branch stair can take s; stale hero position + prayer teleport (review 3); repaired by stair pocket (Rev. 3) |
| BFS pruning "W on Q dominates" | unsound once the door is open (layout agent); checker uses no pruning |
