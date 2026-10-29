# Live claims table

Labels: VERIFIED (source read by orchestrator + reasoning checked) · STRONG (argument complete, survived one review
or independently re-derived) · CONJECTURE · FAILED. Membership and hardness listed separately.
Updated 2026-10-28 after phase 2 (reviews 1-2, blind theorist, proofs hu-off / hu-on-upper / hu-on-lower).

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
| F12 | Starvation is checked only when the faint roll fails; never while fainted | src/eat.c:3416-3437 | VERIFIED |
| F13 | `des.object` quantity loops for non-mergeable objects | src/sp_lev.c:3732 | VERIFIED |
| F14 | newgame: mklev before hero kit; pet survives reset unless pettype:none | src/allmain.c:807-815, src/dog.c:225, src/nhlua.c:1473 | VERIFIED |
| F15 | Push-1F PSPACE-complete (Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch, FUN 2022, LIPIcs 226) | proofs/citations.md | VERIFIED (web) |
| W1-W8 | Real-game witnesses: orthogonal push, refused diagonal push, refused diagonal squeeze, heavy hero can't step on boulder, sentinel pit keeps Sokoban; L_ON gadgets closing site, one-way door, hole crossover — all behave as the proofs say | tools/witness/*.lua via tools/run_witnesses.sh (WSL headless build of 16ff591, #wizloadlua) | VERIFIED experimentally: 8/8 pass in 3 of 3 full runs (different RNG seeds), 2026-10-29. Evidence, not proof. |

## Complexity claims (phase 2; languages in proofs/phase2-spec.md incl. Revisions 1-2)

| Language | Claim | Kind | Status | Evidence / remaining gap |
|---|---|---|---|---|
| Literal game, or 10^9 cap kept | decidable in O(1) / in P | upper | STRONG | constant horizon |
| **L_OFF^W** (hunger off, whitelist) | ∈ PSPACE | upper | STRONG (survived review 2) | proofs/hu-off.md Thm A, Savitch |
| **L_OFF^W** | PSPACE-hard, for R1–R4 | lower | STRONG (survived review 2 after pet repair) | Push-1F (F15) + simulation lemma, hu-off.md Thm B/C; open: Push-1F board-border convention |
| L_OFF unrestricted (any des.object) | ∈ PSPACE | upper | CONJECTURE, likely FALSE | thrones give unbounded wishes under R2 (sit.c) |
| **L_ON\*** (faithful hunger, R2 + rule S, whitelist) | ∈ NP | upper | STRONG (survived review 2) | proofs/hu-on-upper.md, horizon margin 0.907 |
| **L_ON\*** | NP-hard (answer-level DET, so for R1–R4 too) | lower | STRONG (gadgets proved, survived review 2) | proofs/hu-on-lower.md; open: global routing (§4 sketch), exact de Berg–Khosravi statement |
| ⇒ L_ON\* | **NP-complete** | both | STRONG (not machine-checked, witnesses not run) | above two rows |
| ⇒ L_OFF^W | **PSPACE-complete** | both | STRONG (not machine-checked, witnesses not run) | above |
| L_ON, R2 without rule S | hunger not a clock (faint forever, F12) | — | VERIFIED mechanism; class CONJECTURE: PSPACE-hard like L_OFF if faint/prayer cycles leave enough actions | — |
| L_ON, R3 (∀ outcomes) | ∈ PSPACE (poly horizon, AP) | upper | CONJECTURE | — |
| R3 full info, poly state | ∈ EXPTIME | upper | STRONG | APSPACE = EXPTIME |
| W_∞ | undecidable | lower | CONJECTURE (weak) | — |
| any | EXPTIME-hard | lower | unknown | — |

Nothing is VERIFIED at the theorem level: proofs are LLM-written drafts that each survived one adversarial review;
no witness has been run and nothing is formalized.

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
