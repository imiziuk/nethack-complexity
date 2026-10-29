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
