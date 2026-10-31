**Status (2026-10-29, global-construction sub-agent):** the §4 sketch is replaced by a complete construction:
explicit tile coordinates and routing (§4.2-4.4), isolation Lemma 4.1 (proved), planarity/crossover Lemma 4.2
(routine case analysis [conj], asserted mechanically by the generator on every instance built), explicit size
polynomials (§4.6), Claim A reworded per review-2 and soundness/completeness restated with an explicit play and
food bound (§5). `tools/gen_on_instance.py` (instance JSON → Lua level + move string) and `tools/check_small.py`
(exact brute force): all 370 satisfiable small levels won by the replayed play; exhaustive BFS proves g unreachable on 16 of
the 23 unsatisfiable levels (7 larger ones timed out, no counterexample) [auto-experimentally verified, n, m ≤ 3]. Open: exact de Berg–Khosravi statement (§4.1 P4), §6 ball details, Lemma 4.2 not machine-proved
in general, no generated level loaded in the real game (the smallest level is 132×132 cells; stock build is 80×21).
