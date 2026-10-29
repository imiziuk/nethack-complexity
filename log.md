# NetHack complexity: research log (newest first)

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
