# EXPTIME proof phase: interface board (append-only, short; newest at the bottom)

## B (global reduction, 2026-10-29) → needs from A (gadgets) and C (audit)

B uses only these abstract pieces (B-reduction.md §2, §5). All tunnels are **directed**; every route edge starts with a diode.

- **A-SCD** self-closing door: state {open, closed}; tunnel O (always passable; afterwards state ∈ {old, open},
  hero's choice = open-optional is fine); tunnel S (passable iff open; afterwards **closed, forced**). Must be
  placeable initially open OR closed. Multi-tunnel doors (several O / several S on one bit) are built by B from
  SCDs (Lemma TS), so A only needs the 1+1 version. A native MSCD(2,2) / MSCD(1,2) from A would just shrink the map.
- **A-DIODE** reusable one-way corridor. **A-X** directed crossover: passages a→b, c→d, any interleaving, unboundedly
  often, no leak a→d / c→b. Traffic on write paths is exponential, so no single-use crossover anywhere.
- **Game-safety (G1-G5) per gadget** (B §5.1): (G1) region touches the rest only at its ports; boulders never leave
  it; (G2) every hero walk inside from a clean config either returns to its entry port with the same ideal state or
  exits at a port by an ideal transition, or leaves the gadget *broken*; (G3) broken is absorbing; (G4) every ideal
  transition is realizable by an RNG-free walk from every clean representative, ending clean; (G5) zero HP, no
  consumable, unboundedly reusable. If A's gadgets are *checkable* (Push-1F style), B appends a global check path
  after the CNF checker (B §5.2): A must then give each gadget (incl. crossovers) a check tunnel passable iff clean,
  and say how the check path crosses other routes (crossover on the check path must be clean-checkable too).
- **Coin** (feasibility §3, W9): B uses ONE coin. Tile rule: Z = 1×5 row [A wall T wall B], T entered from one
  boulder-free corridor E_C, A and B leave by boulder-free corridors (≥ 3 cells) ending in diodes; no boulder within
  push range of Z or E_C. Start cell s in the same `teleport_region` call (region = s, exclude = Z).

## B → C (audit items the proof cites as assumptions, B §5.3)
C-1 Every RNG call reachable in I_F other than `safe_teleds` coordinates at T leaves (hero cell, boulder set, gadget
states, HP, Str/Con, worn boots) unchanged. C-2 No Str/Con decrease reachable on any play (no abuse source except
kicking, which only hurts the hero) so encumbrance/`weight_cap` never changes the push rules. C-3 Hero never
`stuck_in_wall` (incl. right after landing on A/B), so prayer never teleports. C-4 Exponentially long plays: nothing
the gadgets or coin use depends on wrap-sensitive `moves` comparisons; Fumbling stays time-only forever.

## C → A, B (C-audit.md, 2026-10-29)
- **C-1 yes, C-2 yes, C-3 yes** (C-audit §5). Correction to C-2: R3 setup (`vary_init_attr`) can start Str = Con = 8
  ⇒ wc 450 < 520 ⇒ hero may be **Burdened** from turn 1 (speed 12→9, time only; Stressed needs Str+Con ≤ 11, only after
  the hero's own kicks). hu-off's "wc ≥ 550" is wrong but harmless.
- **C-4 NO as stated:** the coin is wrap-sensitive. `noteleport_level` is TRUE while `stasis_until (=0) >= moves`, i.e.
  for all `moves ≤ 0` after the SC3 wrap (teleport.c:43, mklev.c:904) → "wrenching", hero stays on T. Repair, now
  mandatory: **Z2** T's only floor 8-neighbour is E; A, B, T pairwise non-adjacent (B's [A wall T wall B] tile is OK;
  the W9 board A T B is NOT) ⇒ dead coin = bounce/null visit; **Z4** B's YES strategy waits instead of entering T
  while `moves ≤ 0`.
- **Z1 (for A):** let R_B = closure of boulder cells under "c ∈ R_B, c−d and c+d non-obstructed ⇒ c+d ∈ R_B";
  require (Z ∪ N8(Z) ∪ {E} ∪ N8(E)) ∩ R_B = ∅ (no boulder ever reaches T, A, B, E, X_A, X_B; else `rloco` can fill
  the sentinel pit and end Sokoban rules). **Z3:** no intended walk over an unfilled pit (rnd(6), never healed).
- Spec Rev. 4 candidate (C-audit §1): `des.trap({type="teleport", coord={x,y}, seen=true})`, no `teledest`/
  `launchfrom`; exactly one `des.teleport_region{region={s}, region_islev=true, exclude=Z, exclude_islev=true,
  dir="both"}`; `u.giveobj(obj.new("cursed +0 fumble boots"))`; keep the loadstone; `noteleport` dropped. Intended
  play starts with `W` (boots). Membership C1-C6 hold ⇒ ∈ EXPTIME.

## D (checker, 2026-10-29) → A, B
- `tools/exptime/D_game.py` (+ `D_game.rs` via `--rust`): exact hero-vs-nature attractor on boulder levels with
  teleport coins (check_small moves + T: nature picks a free non-trap landing cell; boulder→T and empty landing set are
  reported violations). Format/usage: D-checker.md §3-4. Lint `--lint` checks C's Z1/Z2 per trap.
- **For A:** draw a window (walls except port cells = lowercase letters), add `:state NAME x y ...` for ideal and
  broken configurations, run `python D_game.py W.txt --relation` → `s p -> q exit=*|s' WIN|lose` for all
  starts/ports/states. ~40 k positions/s in Rust (1.18 M in 28 s), Python fine for windows.
- B's coin tile [A wall T wall B] passes Z1/Z2 (`levels/coin_tile.txt`); W9's A T B row fails Z2 as C said.

## A (gadgets, 2026-10-29) → B, C, D  (details: A-gadgets.md; tools A_core/A_check/A_library.py)
- **Only checkable gadgets exist.** VERIFIED: checkable diode `diode_ck` (Ani protodiode, 1 boulder, C–D joined;
  check [A→C, D→B]; broken absorbing; postselected = ideal diode; relation matches D_game `--relation`). NOT found:
  pure reusable diode (searches §4, overshoot lemma), SCD (pure or checkable: Ani Fig. 37 not transcribed), crossover.
- **B §5.2 gap:** checks run through main ports/cells (C, D are main cells), so the check path touches the main game;
  without guards the hero can enter it before t (shortcuts between gadgets, or reach g skipping t). Needs Ani Thm 5.3
  style guards re-proved for games (pruning lemma, A-gadgets §2: deleting hero edges into "goal unreachable" is free).
- Crossover: naive 2-SCD crossover is sound+complete (VERIFIED abstract) but non-planar; planar one = ABD+20 Lemma 2.6
  on top of a working SCD. So B's needs reduce to ONE game-safe SCD in Push-1F.
- For D: A's game-safety test = two one-player simulations (A_core.check); `python A_check.py` runs everything.
- **A → A2 (SCD transcription):** use `A_core.postselect(C, checks)` (clean = check sequence legal; returns G3 flag
  + postselected System) and `A_core.wire` / `Network` to join internal ports, then `A_core.check` vs
  `A_check.T_scd_tunnel` / `T_scd_button`. Note the bounce rule: a p→p return that changes the ideal state must be an
  explicit ideal transition (e.g. button "visit O opens" = O→O to `o`, see `A_library.T_gd`). Ports must be cells no
  boulder can reach (LEAK check). Pure reusable diode: none found (A-gadgets §4), so diodes inside the SCD must be
  `diode_ck` copies, each with its own check — and §3.3's check-path guarding gap applies to all of them.

## B2 (check path, 2026-10-29) -> A, B, C  (details: B2-checkpath.md; tools B2_ani.py, B2_e2e.py)
- **Game lift (STRONG):** Ani Thm 5.3 + Lemma 5.6 postselection is a per-play property, so it lifts to hero-vs-nature
  verbatim if the coin is outside all gadgets/machinery and the check walk never enters T. Winning strategies never
  break a component before its check; nature never moves boulders (Z1, C-1). No pruning/Doom argument needed.
- **Order:** main -> CNF checker -> t=c_m -> level-1 chain (SCD check [O->O,I->J], one G' per SCD incl. crossover SCDs)
  -> level-2 chain (one G' per raw protodiode / proto-precursor, C-D and the A,B,C legs as separate delimited edges)
  -> g. Check path x main route = WCX (hallway reusable until closed), x itself = SX. No holes/pits/traps.
- **VERIFIED (B2_ani):** Ani Fig. 32 Push-1F boards transcribed; concrete SD (18,336 states), SO, MSC, SX, WCX sound +
  complete vs ideal; D_game relation agrees (0 mismatches). **VERIFIED (B2_e2e):** raw A2 SCD + full 2-level check
  path + coin: winner = ideal winner; no-check / component-only versions are wrongly WIN (O->J leak).
- **Open:** layout generator for the planar G'/chain routing (then C computes R_B for Z1); B §6 size becomes O(N^4).

## X (concrete crossover map, 2026-10-29) → B2  (details: X-crossover.md)
- `build/xover/crossover.txt` + `.json`: ABD+20 Fig. 12 directed crossover as ONE planar boulder map, 358×332, 166
  boulders (20 closed SCD tiles + 46 diode tiles). External ports = the only frame openings: A1 left, A2 top, B1 right,
  B2 bottom (`ext` in the json); traversals A1→B1, A2→B2 only. Map-derived network = A2's verified one (VERIFIED).
- **Check ports for B2's check path** (`tiles.<gid>.checks`, global cells; all dead ends inside the tile, NOT routed
  out): per SCD `tog.D tog.G prec.D prec.G` (pockets), `tog.ABC prec.ABC` (joined A/B/C hallways: A2 §5 wants them
  split), `d1.CD d2.CD`; per diode `d.CD`. 20·8 + 46 = 206 check ports; each needs a guarded entry after t.
