# NetHack complexity: research log (newest first)

## 2026-10-29 — L_ON NP-hardness: global construction (sub-agent)
- hu-on-lower §4 sketch replaced: 11×11 tile grid (ports at side midpoints, stone rings), explicit row/column
  formulas (token sweep), routing of P (main line, branches, spikes) and K (clause gadgets, dive/step/switch arcs),
  Lemma 4.1 isolation (proved), Lemma 4.2 planarity + #crossovers ≤ 6m²+24m+1 [conj, case analysis], size bounds
  w ≤ 132m+22n+44, h ≤ 77m+77. Claim A reworded (gates open from upstream; first entry may come via S or N), §5
  restated with explicit play and food bound (hunger ≥ 857).
- Found: Lemma 3.2(d) "Z_σ is a dead end" holds only while σ's door is closed; harmless for the proof (K↔P link
  between visited regions), but it kills the tempting BFS pruning "W on Q dominates W further in" (unsound).
- tools/gen_on_instance.py (JSON → Lua + move string; deletes unused variables; S-bend wires so stray boulders stick)
  and tools/check_small.py (exact BFS, no pruning). Result: 370/370 SAT levels won by replay, 20/20 SAT BFS find g, UNSAT exhaustive 16/23 levels unreachable (max 734,784 states), 7 timed out at 25 min, 0 mismatches. Not run in the game
  (levels ≥ 132×132 need lifted COLNO/ROWNO).

## 2026-10-28 — Session 1 (milestone 1)
- Version check: `NetHack-5.0.0_Released` tag EXISTS on github.com/NetHack/NetHack -> commit
  `16ff59115315917b93185d026aeefea06db9b0f4` (2026-05-02, "check_mongen_order shouldn't be compiled into release builds").
  include/patchlevel.h: VERSION_MAJOR 5, MINOR 0, PATCHLEVEL 0. Shallow clone in `src/` (gitignored). [auto-extracted]
- Source size: 130 files in src/, ~250k lines of C.
- Orchestrator spot-check [auto-extracted, human-read]: `reseed_random(rn2)` on level reload (src/do.c:1709) and in mklev
  (src/mklev.c:1579); no RNG state in save.c/restore.c -> seeded-RNG input is non-native. `moves >= 1000000000L` ->
  "The dungeon capitulates", done(ESCAPED) (src/allmain.c:253): literal game has a constant horizon. makemon returns
  NULL iff `!level.flags.rndmongen && !ptr` (src/makemon.c:1168): flag blocks RANDOM spawns only, explicit creation still works.
- tools/extract_facts.py: 907 #define constants, 2706 RNG call sites (top: makemon.c 187, uhitm.c 161, trap.c 147).
- Gadget-interference find + repair [auto-extracted, orchestrator-read]: `maybe_finish_sokoban()` (src/trap.c ~7057)
  clears the Sokoban flag once no non-hero PIT/HOLE remains -> diagonal pushes/squeezes become legal mid-instance.
  REPAIR (STRONG): place one sentinel PIT in a sealed, unreachable wall pocket; it is never deleted, so `Sokoban`
  stays true. `cant_squeeze_thru()` (src/hack.c ~955) returns 3 (forbidden) for the hero whenever Sokoban is set,
  independent of weight. `bad_rock()` treats Sokoban boulders as rock for diagonal-squeeze purposes.
- Independent theorist (proofs/independent-theorist.md), blind to the team hypothesis, independently found the
  hunger + prayer-throttle horizon: DET/C-width variant in NP, PSPACE-hardness needs renewable food. Convergence = STRONG signal.
- Orchestrator check of theorist's "fountains at depth>=20 never dry up": NOT found. dryup() (src/fountain.c:201)
  dries with rn2(3) at any depth. Real renewable source: MAGIC fountain (blessedftn) on "cool draught" (fate<10)
  returns BEFORE dryup (src/fountain.c:279-284) -> unlimited nutrition, but only via an RNG outcome (R2, not DET).
- FAILED attempt: "Lua level + standard hero -> Push-1F hardness". Counterexample: hero drops inventory, squeezes
  onto boulders (src/hack.c:145-163, WT_SQUEEZABLE_INV). Responsible mechanic: squeeze. Surviving variant: hero
  record in input with an undroppable cursed loadstone.
- FAILED attempt: "DET + C-width + no turn cap is PSPACE-hard via Push-1F". Counterexample: hunger clock bounds
  every play to O(n) turns (eat.c:3163, pray.c:1371). Surviving variants: W_poly integers, or R2 with a magic fountain.
- Adversarial review 1 (proofs/review-1.md): X1 Lua debug_flags disables hunger, no wizard gate [orch-verified
  src/nhlua.c:1463-1489]; X2 strict DET near-empty; X3 god-anger prayer block backfires. All repaired; claims.md
  updated. Prayer cap LARGEST_INT 32767 [orch-verified include/global.h:135].
- Milestone 1 closed: 8 agents used (3 Sonnet + 5 Opus). Next phase proposed in milestone-1.md §8.

## 2026-10-28 — Session 1, phase 2 (Ivan: "both, report each")
- Spec fixed: proofs/phase2-spec.md (L_ON faithful hunger, L_OFF hunger off via nh.debug_flags).
- Citations (proofs/citations.md): Push-1F authors = Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch (FUN 2022,
  LIPIcs 226). Push-1 (no fixed blocks) PSPACE-complete per two Aug-2025 arXiv preprints (2508.17602, 2508.19759).
  No prior NetHack complexity paper found.
- NP side (proofs/hu-on-upper.md): FATAL G1 [orch-verified src/eat.c:3416-3437]: starvation is checked only when the
  faint roll fails; while fainted it is never checked. Under R2 the hero faints forever and never starves; with
  prayer (every <=32567 turns) alive plays are infinite. => under R2 faithful hunger is NOT a clock. Under R3 the
  adversary picks "no faint" and starvation happens. Repair S [assump]: below the starvation threshold = loss.
  G4 [orch-verified src/sp_lev.c:3732]: des.object quantity loops for non-mergeable objects (exponential objects
  from one line) -> quantity 1. G2 rotten-food sleep loop, G3 sleeping-gas+#sit: banned. L_ON* (R2 + S + whitelist)
  ∈ NP: proof draft, margin thin (0.907).
- PSPACE side (proofs/hu-off.md + 5 witness scripts, not run): L_OFF^W PSPACE-complete draft. Found run-order bug
  [orch-verified allmain.c:807-815] and missing `noflip` [orch-verified sp_lev.c:3804]. Unrestricted L_OFF upper bound
  likely false (thrones: unbounded wishes under R2).
- NP-hardness (proofs/hu-on-lower.md + 3 witness scripts, not run): Planar Monotone Rectilinear 3-SAT, cookies on
  every cell, holes for the crossover. FAILED sub-attempt: pits as barriers (hero climbs out). Conjecture: no
  walls+boulders-only crossover exists.
- Review 2 (proofs/review-2.md): FATAL-as-written: starting pet survives reset [orch-verified dog.c:225, nhlua.c:1473,
  cmd.c:1047]; repaired with pettype:none (spec Revision 2). All three theorems survive with the repair.
- Phase 2 result: L_ON* NP-complete, L_OFF^W PSPACE-complete (both STRONG, not machine-checked). 13 agents total.
- Oct 28 late: tools/run_witnesses.sh (WSL headless build + pexpect #wizloadlua driver, NOT run) and
  proofs/lean/NetHackPush.lean (Lean 4 skeleton: Push-1F model, NHSoko abstraction, source facts as provenance
  axioms, simulation lemma = sorry; NOT compiled, no toolchain). Witness run waits for Ivan to be away.

## 2026-10-29 — witness run (Ivan off the laptop)
- Built 16ff591 headless in WSL Ubuntu (fresh LF clone; the Windows checkout's CRLF broke setup.sh). Driver:
  tools/witness_driver.py (pexpect, #wizloadlua). Harness fixes: `!tutorial` option; Lua prompt "Load which lua file?";
  level-1 branch stair turned back into floor after finalize (as in src/test/testmove.lua); build retry when the random
  branch stair lands on the 1-cell start region ("Couldn't place lregion type 6" -> hero not placed). Setup-only fixes;
  no gadget assertion was changed.
- Result: 8/8 witnesses PASS in 3 of 3 full runs (24/24). Every earlier failure was the stair/setup issue, never a
  mechanics assertion. [auto-experimentally verified]
- Caveat: the run happened at a real full moon (game printed "You are lucky! Full moon tonight", +1 Luck). The spec
  wants Luck 0, but these witnesses test movement/push rules only, which do not read Luck.

## 2026-10-29 (day/night) — final round
- Lean 4 + Mathlib installed in WSL (~10.4 GB: ~/.elan 3.1 G + ~/nh-lean 7.3 G; estimate was 6-8 GB). `simulation` lemma
  compiled, no sorry, standard axioms only (claims L1).
- Variants (proofs/variants.md): no rule S -> PSPACE-complete; R3 -> NP-hard, in PSPACE. F12 corrected.
- Review 3 (PSPACE side): Lean bridge HOLDS; enclosure Lemma E (one figure check open); NEW HOLE: DL1 branch stair can
  take the 1-cell start, hero stays at a stale position, prayer teleport can reach g -> Rev. 3 stair pocket. Witnesses
  passed only because the event has ~1/#floor probability per seed.
- Review 4 (NP side): Lemmas 4.1/4.2, §5 HOLD; generator lacked the pocket (fixed). Rust exact BFS tools/fastbfs:
  UNSAT 18/23 exhaustive, 5 largest re-running overnight (build/fastbfs5/results.log).
- Prior-work search (proofs/prior-work.md): no NetHack complexity result found; NP side = standard time-limit pattern.
- Tile video (media/), layout picture (media/layouts/), interactive page site/proof-explorer.html published as private
  artifact https://claude.ai/artifact/PKfbmsL3ZzF1qm6aAwyMsZ (depth switch, Text/Tiles map toggle, playable puzzle).
