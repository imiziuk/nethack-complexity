# Phase 2 spec: the two instance languages (fixed 2026-10-28; Ivan chose "both, report each")

Applies review-1 repairs 1-5. All phase-2 proofs are about exactly these languages. Source: NetHack 5.0.0 @ 16ff591.

## Common part (both languages)
- Generalized family: COLNO=w, ROWNO=h lifted (coordinates Θ(log n) bits); every other game integer keeps its C
  width (W_C). Turn cap 10^9 removed (H_cap variant is in P, dropped). Single level (L=1).
- Instance I = (w, h, S, g): a fresh game with a FIXED hero template (role, race, alignment, gender: chosen once by
  the proof team, must be a non-spellcaster, non-Knight, no intrinsic Fast at XL1, Str+Con ≥ 18; suggestion:
  human Valkyrie — verify in u_init.c/role.c), then S = a straight-line Lua script (no loops, no functions, no
  `nh.*`/`u.*` except the whitelist below) run as the level, then play begins. g = target cell.
- Whitelist: `des.level_init`, `des.level_flags`, `des.map` (explicit map), `des.terrain`, `des.object` with explicit
  coordinates and explicit otyp/curse state, `des.trap` with explicit type/coords, `des.region` (lit only),
  `des.teleport_region`/stair placement only if needed to place the hero, `u.clear_inventory()`,
  `u.giveobj(obj.new(...))`, `nh.debug_flags{mongen=false}`.
- External inputs fixed: Luck 0, god anger 0, not full moon, not new moon, not Friday 13th, not night (`night()`),
  no bones. Commands: all non-wizard commands except `#exploremode`.
- Randomness: semantics R2 (∃ outcomes) defines the language. Hardness reductions must additionally prove
  answer-level DET for their outputs: R2-answer = R3-answer (no RNG outcome can help or hurt reaching g), so the
  hardness transfers to R1/R3/R4.
- Question: is there a legal play after which the hero is alive and on g at the start of a player turn?

## L_OFF (hunger off)
Common part + whitelist adds `nh.debug_flags{hunger=false}`. Target: PSPACE-complete.

## L_ON (faithful hunger)
Common part; hunger NOT disablable; no fountains, sinks, altars, thrones; no monsters (mongen=false); food only as
explicit whitelisted objects. Target: NP-complete.

## Revision 1 (same day, after hu-on-upper.md, hu-off.md; repairs verified in source by the orchestrator)
1. Instance run order: after `newgame()` finishes (mklev runs BEFORE u_init_inventory_attrs, src/allmain.c:807-815,
   which would overwrite the hero kit), run `des.reset_level(); S; des.finalize_level()` as in src/test/testmove.lua.
2. Script prefix is MANDATORY: `nh.debug_flags{mongen=false}` + `u.clear_inventory()`; L_OFF also mandatory
   `hunger=false`. Level flags must include `noflip` (random flips, src/sp_lev.c:967/6482; flag at :3804).
   Use `des.non_diggable`/`des.non_passwall` calls (there are no such level flags).
3. Whitelist (both): objects BOULDER and LOADSTONE (quantity 1: sp_lev.c:3732 loops on non-mergeables);
   L_ON adds FORTUNE_COOKIE (explicit quantity, unary). Traps PIT, HOLE, TRAPDOOR. Terrain: stone, walls, floor,
   corridors, doors, water, lava. No fountains, sinks, altars, thrones (throne wishes unbounded under R2, sit.c),
   trees. `level_init` solidfill only. Leaving the level = loss.
4. Integers: fixed-width counters (`moves` etc.) wrap; turn cap removed.
5. L_ON rule S [assump]: the play is lost when u.uhunger < -(100+10·Con). Without S, under R2 the hero can faint
   forever and never starve (src/eat.c:3416-3437), so faithful hunger is not a clock under ∃-randomness.
   Hence report L_ON three ways: (a) R2+S → target NP-complete; (b) R2 without S → hunger is not a clock,
   PSPACE-hardness likely carries over from L_OFF if the faint/prayer cycle leaves enough actions [conj];
   (c) R3 (∀ outcomes) → starvation is real, horizon poly → ∈ PSPACE (AP = PSPACE) [conj].

## Revision 2 (after review-2.md)
6. Hero template includes option `pettype:none` (src/dog.c:225: preferred_pet 'n' → no pet). Reason: the starting
   pet is moved to gm.mydogs by des.reset_level (keepdogs, src/wizcmds.c:116), `mongen=false` only clears fmon
   (src/nhlua.c:1473-1481), and finalize restores it (losedogs, src/cmd.c:1047); it can displace the hero past
   walls and squeeze Sokoban diagonals. After finalize, assert no monsters.
7. DL1 is a branch level: finalize adds an up staircase on a random cell (harmless losing exit; leaving = loss).
