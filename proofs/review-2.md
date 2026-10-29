# Review 2 (adversarial, round 2): hu-off, hu-on-upper, hu-on-lower

Reviewer sub-agent, 2026-10-28. Source NetHack 5.0.0 @ 16ff591, read-only, nothing built or run. Paths are
`src/src/<file>:line` unless noted. Binding spec: phase2-spec.md incl. Revision 1. Review-1 issues not repeated.

## Verdicts

| Doc / theorem | Verdict | One-line reason |
|---|---|---|
| hu-off Thm B (L_OFF PSPACE-hard) | **FATAL as written, one-line repair** | the starting pet survives the Revision-1 run order and can displace the hero to any free 8-neighbour of s at arrival (N1) |
| hu-off Thm C (answer-level DET) | **false as written**, same repair | pet can block pushes forever under ∀-RNG (N1) |
| hu-off Thm A (L_OFF^W ∈ PSPACE) | survives (fix the text) | pet + branch stairs add O(1) records (N1, N2) |
| hu-on-upper (L_ON* ∈ NP) | survives (fix the text) | horizon arithmetic re-checked; pet only adds a bounded corpse; two table rows wrong (N1, N4) |
| hu-on-lower (L_ON NP-hard, R2) | survives modulo N1 repair | gadgets, holes, sentinel, prayer, ball all re-checked; §6 ball text wrong but harmless (N3) |
| hu-on-lower §5.3 (DET) | **false as written**, same repair | kitten squeezes diagonally in Sokoban, can sit in the door pocket (N1) |

## N1 (FATAL as written; repair = spec one-liner): the starting pet is NOT removed

Chain, all read this session:
1. `newgame` makes the pet before the harness runs: `mklev(); u_on_upstairs(); ... (void) makedog();`
   [allmain.c:806-813]. The pet is adjacent to the hero.
2. `des.reset_level()` → `makemap_prepost(TRUE)` [sp_lev.c:6006] → `makemap_remove_mons()` [cmd.c:992] →
   `keepdogs(TRUE)` [wizcmds.c:116]: every adjacent tame follower is moved from `fmon` to `gm.mydogs`
   [dog.c:798-864, `relmon(mtmp, &gm.mydogs)` at 863].
3. Script S then runs `nh.debug_flags{mongen=false}`, whose cleanup loop walks **`fmon` only** [nhlua.c:1473-1481].
   The pet is on `mydogs`, so it survives. (Review-1 line 15 and hu-off I1 were correct for the old run order, not
   for Revision 1.)
4. `des.finalize_level()` → `makemap_prepost(FALSE)` [sp_lev.c:6061] → `u_on_rndspot` then **`losedogs()`**
   [cmd.c:1045-1046]. Arrival does not go through `makemon`, so `debug_mongen` [makemon.c:1168, its only reader
   besides wizcmds] does not stop it. With chance 1/10 the pet is put **on the hero's square** [dog.c:474-475];
   then `u_collide_m` [cmd.c:1050-1051] with `!rn2(2)` moves the **hero** to a random `enexto` spot adjacent to s
   [do.c:1429-1431]. `enexto`/`goodpos` only test accessibility and boulders [teleport.c:172-179], not walls
   between, the Sokoban corner rule, or traps.

Consequences:
- **hu-off soundness (Lemma S / Thm B ⇐) breaks under R2:** the hero may start on any free diagonal neighbour d
  of s even when both corners are fixed/movable blocks, a move Push-1F forbids. A Push-1F NO instance whose g is
  reachable from such a d maps to an L_OFF YES instance.
- **DET breaks (hu-off Thm C, hu-on-lower §5.3):** the pet (kitten or little dog) is a monster: a boulder with a
  monster beyond it cannot be pushed [hack.c:476-505]. Monsters are exempt from the Sokoban corner rule
  [hack.c:973-974; mfndpos mon.c:2345-2346], so the kitten passes diagonals the hero cannot, e.g. into the G_D
  pocket P=(2,0) from q=(1,1) (corners X=boulder, (2,1)=stone), where the hero can never reach it. Under ∀-RNG it
  stays there forever: R3-answer ≠ R2-answer. hu-on-lower §1.2 claim "no pet" is false for the same reason.
- hu-on-upper Lemma 1 row "Monsters: 0" is false; one pet (bounded inventory, one corpse that rots on a timer)
  adds O(1) and a bounded amount of food/sleep, so Lemma H only gains a constant.

Under R2 the pet cannot otherwise help: it cannot push boulders or plug holes; displacing it uses the hero's own
`test_move`. So the only R2 damage is the arrival displacement.

**Repair (pick one, add to the spec's fixed template):** (a) option `pettype:none` (makedog returns NULL
[dog.c:225]); or (b) run `nh.debug_flags{mongen=false}` **before** `des.reset_level()` (the pet is still on
`fmon` then and is `mongone`d). Add a harness assertion `gm.mydogs == NULL` and "no monster on the level" after
finalize. With either repair hu-off Thm B/C and hu-on-lower DET go through as written.

## N2 (minor, text fix): DL1 is a branch level, so finalize places an up staircase on a random floor cell

`dat/dungeon.lua:45-49`: "The Elemental Planes" branch has `base = 1`, so `Is_branchlev` is true on DL1
[dungeon.c:1464-1473]. `finalize_level` → `fixup_special` → `place_lregion(0,...,LR_BRANCH)` [mkmaze.c:640-642];
with `nroom == 0` it samples the whole map [mkmaze.c:366-400] for a `ROOM` cell with no trap/pool/furniture
(`bad_location`, `occupied` do **not** exclude boulders [mkmaze.c:341-351, mklev.c:1806-1811]) and
`place_branch` makes STAIRS there [mklev.c:1731-1738]. This is why `test/testmove.lua:18-20` deletes stairways
after finalize. Effects: one extra exit (`<` on DL1 = leave the dungeon = loss); STAIRS is not obstructed and
`moverock` has no stairs test [hack.c:432-631], so pushes and steps are unchanged. Wrong statements to fix:
hu-off A.1 item 7 and group U ("no stairs"), witness assertion "no stairways exist" (it will fail); hu-off Harness
H text "fixup_special places only declared lregions". Nothing in any proof depends on it.

## N3 (hu-on-lower §6, text wrong, conclusion right): iron-ball throw range is up to 5, not 1

For a heavy iron ball `range = urange - owt/100`, capped at 5 for `uball` [dothrow.c:1615-1633]; the 500-weight
loadstone does not reduce it. The ball still cannot carry the hero past anything: each flight step stops on a
boulder square, and for `uball` runs `test_move(x-d, d, TEST_MOVE)` (corner rule included), and **under Sokoban
stops on a pit/hole** [zap.c:4096-4117]; `drop_ball` puts the hero one short of the ball, or **into** the hole/pit
if the ball stopped on one [ball.c:931-941] (then he falls = loss). So the ball = a sequence of legal steps.
Note for the spec: without the Sokoban flag the hole stop at zap.c:4112-4116 is absent and the hero is placed
beyond holes without triggering them, so the sentinel pit is load-bearing for the ball too, not only for corners.

## N4 (hu-on-upper, text): pat_on_head has a second trigger

`if (!trouble && u.ualign.record >= DEVOUT) { if (p_trouble == 0) pat_on_head = 1; }` [pray.c:1105-1108]. The
table row "pat_on_head cases need action ≥ 5" is incomplete. Outcome unchanged: at Luck 0 the boon is
`rn2((Luck+6)>>1) = rn2(3)` ∈ {nothing, weapon fix, golden glow} [pray.c:1164ff], golden glow raises h by ≤ 750
(< the 1250 already budgeted per prayer), and it needs `ublesscnt == 0`, so prayers are no denser.

## Checks that came back clean (attack → evidence)

hu-on-lower:
- Boulder onto a cookie square: `moverock_core` tests only obstruction, bars, diagonal doors, boulder, Sokoban
  diagonal, `revive_nasty` (corpses; none), monster, closed door, traps, pools [hack.c:432-631]. Objects never
  block. Boulder into hole: plugs it, `deltrap`, `useupf`, `bury_objs`, hero advances (`return 0`) [hack.c:544-566].
- Sentinel: `maybe_finish_sokoban` keeps the flag while any non-hero-made PIT/HOLE exists, with **no** `tseen`
  requirement [trap.c:7059-7072], called from `deltrap` [trap.c:6546-6547]. Sound.
- Holes are real barriers: in Sokoban there is no dexterity escape [trap.c:3013-3021] and no "don't fall"
  [trap.c:633-634]; DL1 is not bottom and not hardfloor. Squeezing onto a boulder needs `inv_weight() ≤ -850`
  [hack.c:139-140, include/weight.h:24]: impossible with the 500 stone.
- Cookies as tools: thrown/dropped objects never plug holes (only the boulder branch of moverock does);
  picking many up only adds weight (and Stressed adds hunger [eat.c:3195]) — only hurts. Cursed cookies (rndcurse)
  stay rot-exempt [eat.c:3026-3037].
- Crossover/clause diagonals next to holes: by Rule R no diagonal step has a hole corner (checked all four corner
  roles of s1 in G_X); stepping diagonally into s1 is just falling.
- Prayer anger: `angrygods` cases [pray.c:704-786]: displeased; −Wis + `losexp`; `punish` (case 6, needs
  maxanger ≥ 7, reachable after repeated anger); black glow `rndcurse`/`attrcurse`; `summon_minion` → `makemon`
  [minion.c:222,232,239] → NULL; `god_zaps_you` hits only the hero (no reflection/shock/disint resistance on a
  Valkyrie → death) [pray.c:610-693]: no map or boulder effect.
- Claim A wording: after a K pass the downstream segment can be first entered from S (P row), not through n2→s1.
  The invariant actually used ("a gate opens only after the hero stood in the preceding segment") still holds;
  reword Claim A that way. Not a gap.
- Layout: routing the K chain without K×K crossings is always possible (disjoint arcs never separate the plane);
  fine as [conj, routine].

hu-on-upper:
- Faint hovering: faint starts only from `newuhs` at h ≤ 0 when not already fainted, duration ≤ 45 under S;
  decrements while Unaware are `!rn2(10)`-gated [eat.c:3174-3179]; the ledger charges each faint to one F
  decrement in [-350,0]. Re-derived 11·1250 + 45·351 + 3 = 29,548 < 32,567: margin 0.907 confirmed. Prayer gap:
  `ublesscnt += min((moves-100000)/100, LARGEST_INT - ublesscnt)` [pray.c:1366-1374], success needs ≤ 200
  [pray.c:2151-2153]. V ticks only from p_type 3. No other Unaware source in the whitelist.
- Kelp from `mineralize` in pools [mklev.c:1465-1468] is unreachable: filling a pool buries its objects
  [do.c boulder_hits_pool → bury_objs], and a non-swimmer is ejected from water at once. Gold/gems are in solid
  stone with 8 stone neighbours [mklev.c:1501-1514].

hu-off / run order:
- `noflip` survives: `finalize_level` calls `create_des_coder()` which only allocates if NULL [sp_lev.c:6444-6448],
  so the script's coder (allow_flips = 0) is used by `flip_level_rnd` [sp_lev.c:6041].
- Hero placement: one-cell teleport region → `place_lregion` oneshot [mkmaze.c:393-397] → deterministic,
  **except** the pet collision of N1. hu-on-lower must also pass `dir="both"` (or down) like hu-off, since
  `u_on_rndspot(0)` reads the down destination.
- Whitelist creators at Luck 0: only punish (≤ 2 records) and, with N1 unrepaired, one pet corpse. Golden glow /
  weapon fix create nothing.
- Push-1F border [verify, not a flaw found]: citations.md 1a gives an agent on a unit grid with fixed blocks; it
  does not say whether instances are enclosed. hu-off assumes "outside = fixed". If the paper's grid is unbounded,
  argue that its hardness instances are walled (typical for checkable-gadget constructions) or add a lemma.

## Required edits (summary)
1. Spec: add `pettype:none` to the template **or** move `mongen=false` before `des.reset_level()`; assert no
   monsters after finalize. (Fixes hu-off Thm B/C, hu-on-lower §1.2/§5.3, hu-on-upper Lemma 1 row.)
2. hu-off: fix "no stairs" statements and witness assertion (N2); cite N1 in I1.
3. hu-on-lower §6: replace the ball paragraph with N3; reword Claim A; state `dir` of the teleport region.
4. hu-on-upper: fix the pat_on_head row (N4) and the monsters row (N1).
