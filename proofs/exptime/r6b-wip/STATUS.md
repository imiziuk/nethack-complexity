# r6b WIP status (review-6 round 2), 2026-10-31

Done (commit 6816237): tile-leg stubs SCD_TV=3 + variant-2 J at top-left (XB_SCD_GEOM=r6a = round 1, checked
identical), crossover rebuilt 556x560 (round-1 copy build/xover/*_r6a.*), legs now serialise stub/port (round-1 bug),
P=587/MID=293, bar comb (LGEN_JN=fan old), template library (ttemplate_r6_<kind>_<par>.json + floor_hash), L_lua.py.
X_verify --moves 100000 ALL AS EXPECTED; review5_abc / review5_cd pass; check_tile_spacing ok; tile templates
dio 0/1, scdc 0 (l2first), scdc 1 (l1first: l2first failed at tile.J Wt) validate + rules clean;
L_e2e tiles ALL AS EXPECTED (library templates).

Crossover templates (build/lgen/xtemplate_r6_<fx><fy><p>.json):
- plain l2first (logs r6b_a_x*.log, r6b_failrun_a_*): 000 ROUTED (10,064 s, validate ok, rules clean: 372 checks,
  68 GX on finished legs). FAILED at level 1 after level 2 was drawn (records r6b_fail_l2first_*.json):
  001 g029 tile.J Wb; 010 g018 tile.J Wb; 100 g028 tile.J Wb; 101 g055 tile.O Wb; 110 g034 'no SO wire 1 J';
  111 g029 tile.O Wt. 011 running (l2first).
- l1first (level 1 drawn first): level 1 done in ~210 s, then level 2 made no progress in 50 min (001, 010; killed).
- LGEN_L1_KEEP=1 (box-spot keep-out for all SCDs): killed after ~1 h for time (no result).
- NEW targeted keep-out `LGEN_L1_KEEP_TILES=<failing SCDs>` (slot side points + box spots of those SCDs reserved while
  level 2 is drawn; L_gen._block_template): running for 001:g029, 101:g055, 110:g034, 100:g028; queued 010:g018,
  todo 111:g029 (logs r6b_t_x*.log; driver scratchpad xqt.py = same env + LGEN_L1_KEEP_TILES).
Next: when all 8 exist: stamp floor_hash into each xtemplate (logic: rec['floor_hash'] =
L_gen.floor_hash(L_gen.x_block(fx, fy))), `python L_e2e.py xtemplates`, `python L_gen.py --run 20 3`, one fresh seed,
review6_weak --generated, review6_hooks, review6_hooks2; docs L-generator §10 (10.2 results, 10.3 = draft in
scratchpad sec103.md), B2 §3.7, review-6 §8, claims row (keep CONJECTURE).
