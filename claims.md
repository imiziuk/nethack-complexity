# Live claims table

Labels: VERIFIED (source read by orchestrator + reasoning checked) · STRONG (argument complete, survived one review
or independently re-derived) · CONJECTURE · FAILED. Membership and hardness listed separately.
Updated 2026-10-28 after adversarial review 1 (proofs/review-1.md) and the blind theorist (proofs/independent-theorist.md).

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

## Complexity claims (axes: R randomness, W integers, Hu hunger; see proofs/milestone-1.md)

Main insight (STRONG: found by the team, re-derived blind by the theorist, survived review with repairs):
**the hunger clock decides NP vs PSPACE.** With faithful hunger and no renewable food, plays are poly-long.
With hunger off (debug flag, or poly-width nutrition) exponential plays exist and Sokoban-style PSPACE-hardness can apply.

| Variant | Claim | Kind | Status | Evidence / gap |
|---|---|---|---|---|
| Literal game | decidable in O(1) | upper | STRONG | finite constants |
| H_cap (10^9 kept), any W | in P (galactic constant) → cannot be NP-hard unless P=NP | upper | STRONG | constant horizon; axis dropped |
| Hunger ON, no renewable food (DET-answer, W_C) | ∈ NP | upper | CONJECTURE | needs rate lemma: prayer ≤ ~1250 nutrition per ~32.6k turns (F8) + nutrition-source audit |
| same | NP-hard | lower | CONJECTURE | Push-1 / Framework 1 with food = solution length |
| Hunger OFF (debug flag F9, or W_poly nutrition), DET-answer | ∈ PSPACE | upper | STRONG | poly state if no creators (mongen off, no #pray or anger 0/Luck 0) |
| same | PSPACE-hard | lower | CONJECTURE | Push-1F [ext, citation to verify] + simulation lemma (survived review) + loadstone + sentinel pit + role w/o force bolt |
| R2 (∃ RNG), hunger ON | PSPACE-hard | lower | CONJECTURE | magic fountain F10 as renewable food + Push-1F; exploit surface large |
| R2, unrestricted | ∈ PSPACE | upper | CONJECTURE (likely false w/o population cap) | unbounded farming (upper-bound.md) |
| R3 full info, poly state | ∈ EXPTIME | upper | STRONG (survived review) | APSPACE = EXPTIME [ext] |
| W_∞ | undecidable | lower | CONJECTURE (weak; theorist doubts: no enforced zero tests) | — |
| any | EXPTIME-hard | lower | unknown | — |

No class is declared for a single primary formulation yet: Ivan must pick hunger ON (faithful, likely NP-complete)
vs hunger OFF (debug flag / W_poly, likely PSPACE-complete) as primary, or report both.

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
