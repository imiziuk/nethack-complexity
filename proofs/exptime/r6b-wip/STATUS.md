# r6b status (review-6 round 2), 2026-11-01 — read L-generator.md §10 first

## Done (verified)
- Geometry r6b: tile-leg stubs SCD_TV=3, variant-2 J port top-left (XB_SCD_GEOM=r6a = round 1, identical cells).
- Crossover 556x560 (round-1 copy build/xover/*_r6a.*); legs serialise stub/port (round-1 bug fixed); P=587, MID=293.
- X_verify --moves 100000 ALL AS EXPECTED; review5_abc, review5_cd pass; check_tile_spacing ok.
- Library tile templates build/lgen/ttemplate_r6_{scdc,dio}_{0,1}.json (floor_hash), validate + rules clean;
  scdc 1 only by l1first. L_e2e tiles ALL AS EXPECTED (uses the library files; LE2E_LIBRARY=0 re-routes).
- Bar comb (LGEN_JN=bar), template_for library assertion, L_lua.py (F5 window + lint), F3/F4 argument (§10.3),
  F6-F10 text, review-6 §8, claims row (CONJECTURE kept).

## Not done
- Crossover templates: only xtemplate_r6_000.json (l2first). All other 7 flips FAILED under l2first at level 1
  (records build/lgen/r6b_fail_l2first_*.json). l1first / l1first+LGEN_L2_KEEP: level 2 stalls. Targeted keep-out
  LGEN_L1_KEEP_TILES failed for 110:g034.
- Targeted keep-out LGEN_L1_KEEP_TILES also FAILED for 101:g055 (same slot); 001, 010, 100 runs were stopped
  unfinished. No jobs are left running.
- Blocked on all 8: stamp floor_hash into each xtemplate (rec['floor_hash'] = L_gen.floor_hash(L_gen.x_block(fx, fy)));
  `python L_e2e.py xtemplates`; `python L_gen.py --run 20 3` + one fresh seed; review6_weak --generated,
  review6_hooks, review6_hooks2 on the new templates.

## Next ideas (round 3)
(a) rip-up in l2first: when level 1 is stuck at SCD g, undo the level-2 G's of g's four components, route g's
level-1 G', re-route the four (time order unchanged); (b) SCD_TV 5-6 and more room between tile legs and crossover
corridors (X_build scale), rebuild, re-route. Run each flip as
`cd tools/exptime; LGEN_STRATS=l2first LGEN_PROGRESS=1 LGEN_TILE_SECS=3000 LGEN_BUDGET=30000 python L_gen.py --xblock FX FY P`
(2-4 h each under load; ≤ 4-5 jobs in parallel, laptop is shared).
