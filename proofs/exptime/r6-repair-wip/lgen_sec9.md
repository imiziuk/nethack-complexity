## 9. Review-6 repairs (2026-10-31): drawn check walks, GX rule, L_e2e

**What changed in `Router` (default; the old behaviour is kept only behind env flags for the positive controls).**
- **GX rule (F1).** A GX (WCX on a leg's g-side stub) is allowed only on a leg of a G′ that FINISHED earlier in time
  (`dead` without `own`). Before, every G′'s hooks were searched with `dead = own | finished`, i.e. they could cross
  the stubs of the component's own legs during its own checks. Own middle segments stay crossable after both passes
  (dead). `LGEN_GX_RULE=own` restores the old rule (positive control only).
- **Ani placement, drawn (F2).** After pass 2, `_checks` draws Ani's Fig. 23 walk on the chain itself, per check
  i = (a_i, b_i): Out_{i−1} → Op_i (the chain passes a point j next to the SO_i box p) → SD_i (the piece ends at the
  SD_i box q); a new piece starts at p (Out_i). Boxes are joined to their location by a **wire**: a path of
  reserved wall points from the box to the location's non-floor 4-neighbours (reserved for every location from the
  start, `reserve_locations`). A wire crosses no floor, no other wire, and is never used or crossed by any chain;
  it may cross an already drawn chain piece only by an SX in which the wire is the LATER line (`WSX` events; a level-1
  wire never crosses a level-2 piece). Wire length is penalized (`LGEN_WIRE_PEN`, ending cost only), so most wires
  have length 0. The old reachability-only hooks are `LGEN_PLACEMENT=hk` (positive control only).
- **Bookkeeping.** `Router.gseg` (one record per routed G′: trace and event range, own legs, checks, locations),
  `ev_ti` (trace index of every event), events `OP` / `SD` / `OUT` / `WSX`; `res` is now part of the snapshot;
  `dijkstra(..., tpen=)` charges a target's cost only when the path ENDS there.
- **`validate_rules`** (called by `validate`, every template): replays F1 by time order (level-1 G′s, then level-2,
  each in routing order), independently of the router's `dead` sets: every GX on a leg of a G′ finished earlier and
  never own; own middles crossed only after the G′'s last Wb; never the own SCD interior at level 1; F2 contact
  geometry: OP, SD, OUT per check in order; box–wire–location 4-paths (wire SX: straight perpendicular chain point,
  level rule); wires never on a chain point, floor or the coin halo.
- **`gprime_items` → `template_record['gseq']`**: every routed G′ as an item list for `L_e2e.py`.
- Crossover templates of the repaired router are `build/lgen/xtemplate_r6_<fx><fy><p>.json` (`LGEN_TPL_TAG`); the
  review-6 state's `xtemplate_<fx><fy><p>.json` are kept unchanged for comparison.
- `assemble`: `contacts_drawn` (OP = SD = OUT = #checks) is part of `coverage_ok`; wire SX count in machinery SX.

**`L_e2e.py` (new): the abstract end-to-end test WITH the crossings inside G′.** Each routed G′ is rebuilt from its
`gseq` as a gadget network: RAW window (A_core: protodiode 4 states, proto-precursor 28; level 1: the SCD composite
of postselected components, both initial states), one WCX per delimiter, per GX (in series on its stub), per CHX on
an own middle, runs of crossings of foreign floor as one WCX(world, world), ideal SX for chain×chain and wire×chain
crossings inside the piece, SO/SD at the drawn contacts with their wires; every outer node and every foreign hallway
is one node `world` (over-approximation). Claim: c_out reachable from (world, q) ⇔ q clean. Controls: delimiters
removed (must fail), old GX rule with Ani placement, review-6 HK placement with the old rule (must fail: these are
the review-6 counterexamples), HK placement with the new rule (fails too on the diode: the F2 wormhole alone), and
the two-player diode game (coin; ideal LOSE/WIN, raw without check path WIN/WIN, repaired G′ LOSE/WIN, review-6 G′
WIN/WIN).
