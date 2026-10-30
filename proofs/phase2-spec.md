# Phase 2 spec: the two instance languages (fixed 2026-10-28; Ivan chose "both, report each")

Applies review-1 repairs 1-5. All phase-2 proofs are about exactly these languages. Source: NetHack 5.0.0 @ 16ff591.

## Common part (both languages)
- Generalized family: COLNO=w, ROWNO=h lifted (coordinates Θ(log n) bits); every other game integer keeps its C
  width (W_C). Turn cap 10^9 removed (H_cap variant is in P, dropped). Single level (L=1).
- Instance I = (w, h, S, g): a fresh game with a FIXED hero template (role, race, alignment, gender: chosen once by
  the proof team, must be a non-spellcaster, non-Knight, no intrinsic Fast at XL1, starting Str+Con ≥ 12 for EVERY
  setup RNG outcome; suggestion: human Valkyrie — verify in u_init.c/role.c), then S = a straight-line Lua script (no loops, no functions, no
  `nh.*`/`u.*` except the whitelist below) run as the level, then play begins. g = target cell.
- Whitelist: `des.level_init`, `des.level_flags`, `des.map` (explicit map), `des.terrain`, `des.object` with explicit
  coordinates and explicit otyp/curse state, `des.trap` with explicit type/coords, `des.region` (lit only),
  `des.teleport_region`/stair placement only if needed to place the hero, `u.clear_inventory()`,
  `u.giveobj(obj.new(...))`, `nh.debug_flags{mongen=false}`.
- External inputs fixed: Luck 0, god anger 0, not full moon, not new moon, not Friday 13th, not night (`night()`),
  no bones. Commands: all non-wizard commands except `#exploremode`. The game runs in normal mode
  (`flags.debug` = false, not wizard/debug mode, not explore mode) — Rev. 4 item 11.
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

## Revision 3 (2026-10-29, after review-3-pspace.md)
8. Branch stair pocket (MANDATORY, both languages): DL1 finalize can put the branch up-stair on the 1-cell start s,
   hero placement then fails (non-fatal `impossible()`), and the hero keeps a stale RNG position; under R2 prayer's
   "stuck in wall" fix (`safe_teleds`, src/pray.c:461-465) can then drop him on g. Repair: every instance contains a
   sealed 1-cell pocket P (walls on all 8 sides, unreachable) and declares
   `des.levregion({region={Px,Py,Px,Py}, type="branch"})` (src/sp_lev.c:5475-5479; precedent dat/Arc-strt.lua:58).
   Whitelist adds this call. Harness asserts: hero on s, stair in P, no monsters.
9. Push-1F enclosure (Lemma E, review-3 §2): put a one-cell empty margin around the Push-1F drawing BEFORE the wall
   ring (hu-off B.2). NO direction transfers unconditionally; YES needs that no block leaves its gadget in the
   intended solution (check once against Ani et al. Figs 32-37) [open].

## Revision 4 (2026-10-29, ADOPTED; from exptime/C-audit.md §1 + review-5-exptime.md §4-§5)
Defines the EXPTIME language **L_OFF^{W+C}** (R3 only). All Rev. 1-3 items stay. The theorem in
exptime/B-reduction.md is about exactly this language.
10. **L_OFF^{W+C}** = common part + L_OFF + Rev. 1-3, with:
   a. Level flags: `noteleport` **forbidden**; keep `noflip`, `sokoban`, `hardfloor`, `solidify` (`premapped`,
      `nomongen` allowed, unused).
   b. Traps: TELEP_TRAP only as `des.trap({ type = "teleport", coord = {x, y}, seen = true })` (`seen` defaults to
      false, sp_lev.c:4406, 4432). Keys `teledest`, `launchfrom` forbidden (fixed destination, trap.c:566-574,
      3009-3012). PIT, HOLE, TRAPDOOR as in Rev. 1.
   c. Exactly one `des.teleport_region({ region = {sx,sy,sx,sy}, region_islev = true, exclude = {zx1,zy1,zx2,zy2},
      exclude_islev = true, dir = "both" })` with zx1 ≥ 1, s ∉ Z, branch pocket P ∉ Z; a second call is forbidden
      (it would overwrite dndest/updest, mkmaze.c:611-632). Every TELEP_TRAP lies in Z.
   d. Objects: exactly one `u.giveobj(obj.new("cursed +0 fumble boots"))` added; inventory = {cursed loadstone,
      cursed fumble boots}.
   e. Mandatory prefix unchanged (`mongen=false, hunger=false`, `u.clear_inventory()`, `pettype:none`, Rev. 3
      pocket). Harness asserts: hero on s, stair in P, no monsters, every T `tseen`, boots cursed, `flags.debug` false.
   f. Semantics R3; counters wrap (SC3); **turn cap removed**: unmodified 5.0.0 ends the game at `moves` ≥ 10^9
      ("The dungeon capitulates", allmain.c:253), so every result for L_OFF^{W+C} is about the cap-deleted,
      wrapping variant. The coin is dead while `moves ≤ 0` (C-audit N1).
   g. No other teleport source exists (C-audit §2.2 J9).
11. **Normal play mode (review 5 §4).** The game runs with `flags.debug` = false (`wizard` macro, flag.h:30) and
    `flags.explore` = false. Reason: in wizard mode `scrolltele` (reached from `tele_trap` → `tele`) prompts for the
    destination (`|| wizard`, teleport.c:872-873), so the HERO would pick the coin's outcome: the game becomes
    one-player and the reduction fails. (The dead-phase test in `tele_trap`, teleport.c:1502-1505, has no wizard
    exception, so N1 is mode-independent.) The witnesses of exptime-feasibility §9 used wizard mode only to load levels
    (caveat recorded there).
12. **Hero template correction (C-audit N2).** "Str+Con ≥ 18" (old common-part text) is false under R3 setup:
    `vary_init_attr` (u_init.c:1391, attrib.c:764-776) can lower Str and Con by 2 each, so a Valkyrie may start at
    Str = Con = 8 (sum 16, wc = 450 < 520 ⇒ Burdened, speed only). The template line now asks for start
    Str+Con ≥ 12 for every setup outcome: Stressed needs Str+Con ≤ 11 (wc ≤ 346 ⇔ sum ≤ 11.84), unreachable
    without hero self-abuse (C-audit §2.4, J10-J11). Harmless for every earlier lemma (hu-off Lemma C reads
    "wc ≥ 450, at most Burdened").
13. **Design rules Z1-Z4** (C-audit §1, Z1 as restated after review 5) bind the instances produced by the reduction,
    not the language; membership (Thm M) holds for every instance of 10.
