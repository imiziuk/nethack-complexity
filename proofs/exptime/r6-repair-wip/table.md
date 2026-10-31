### sym
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/pass/every/init | 600 (398) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 0 |
| II-first/pass/every/init | 600 (367) | 0 / 99 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 99 |
| I-first/pass/every/noinit | 600 (402) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0 |
| II-first/pass/every/noinit | 600 (284) | 82 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 0 |
| I-first/pass/postI/init | 600 (396) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | startfork 0 |
| II-first/pass/postI/init | 600 (339) | 0 / 81 | 0 / 0 | 0/300 | 0/10 | startfork 81 |
| I-first/pass/postI/noinit | 600 (391) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | - |
| II-first/pass/postI/noinit | 600 (259) | 105 / 0 | 0 / 0 | 0/300 | 0/10 | startfork 0 |
| I-first/pass/postII/init | 600 (361) | 26 / 26 | 0 / 0 | 0/300 | 0/10 | qcheck 26, startfork 95 |
| II-first/pass/postII/init | 600 (333) | 10 / 101 | 0 / 0 | 0/300 | 0/10 | qcheck 10, startfork 95 |
| I-first/pass/postII/noinit | 600 (269) | 132 / 132 | 0 / 0 | 0/300 | 0/10 | qcheck 132 |
| II-first/pass/postII/noinit | 600 (275) | 85 / 9 | 0 / 0 | 0/300 | 0/10 | qcheck 9, startfork 0 |
| I-first/nopass/every/init | 600 (497) | 80 / 80 | 0 / 0 | 0/300 | 0/10 | gates 80, qcheck 26, startfork 9 |
| II-first/nopass/every/init | 600 (505) | 90 / 194 | 0 / 0 | 0/300 | 0/10 | gates 90, qcheck 45, startfork 36 |
| I-first/nopass/every/noinit | 600 (510) | 70 / 70 | 0 / 0 | 0/300 | 0/10 | gates 70, qcheck 34 |
| II-first/nopass/every/noinit | 600 (468) | 122 / 131 | 0 / 0 | 0/300 | 0/9 (+1 cap) | gates 131, qcheck 47, startfork 0 |
| I-first/nopass/postI/init | 600 (505) | 54 / 54 | 0 / 0 | 0/300 | 0/10 | gates 54, startfork 28 |
| II-first/nopass/postI/init | 600 (474) | 69 / 175 | 0 / 0 | 0/300 | 0/10 | gates 69, startfork 45 |
| I-first/nopass/postI/noinit | 600 (462) | 102 / 102 | 0 / 0 | 0/300 | 0/10 | gates 102 |
| II-first/nopass/postI/noinit | 600 (426) | 94 / 107 | 0 / 0 | 0/300 | 0/10 | gates 107, startfork 0 |
| I-first/nopass/postII/init | 600 (453) | 86 / 86 | 0 / 0 | 0/300 | 0/10 | gates 54, qcheck 73, startfork 54 |
| II-first/nopass/postII/init | 600 (473) | 80 / 170 | 0 / 0 | 0/300 | 0/10 | gates 81, qcheck 71, startfork 73 |
| I-first/nopass/postII/noinit | 600 (420) | 119 / 119 | 0 / 0 | 0/300 | 0/10 | gates 136, qcheck 119 |
| II-first/nopass/postII/noinit | 600 (416) | 149 / 119 | 0 / 0 | 0/300 | 0/10 | gates 116, qcheck 84, startfork 0 |
24 variants
### asym
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/passI/every/init | 200 (165) | 39 / 39 | 0 / 0 | 0/200 | 0/5 | gates 39, qcheck 0, startfork 0 |
| II-first/passI/every/init | 200 (174) | 33 / 70 | 0 / 0 | 0/200 | 0/5 | gates 33, qcheck 0, startfork 15 |
| I-first/passI/every/noinit | 200 (159) | 36 / 36 | 0 / 0 | 0/200 | 0/5 | gates 36, qcheck 0 |
| II-first/passI/every/noinit | 200 (144) | 54 / 56 | 0 / 0 | 0/200 | 0/5 | gates 56, qcheck 0, startfork 0 |
| I-first/passI/postI/init | 200 (168) | 28 / 28 | 0 / 0 | 0/200 | 0/5 | gates 28, startfork 0 |
| II-first/passI/postI/init | 200 (152) | 37 / 69 | 0 / 0 | 0/200 | 0/5 | gates 37, startfork 6 |
| I-first/passI/postI/noinit | 200 (164) | 41 / 41 | 0 / 0 | 0/200 | 0/5 | gates 41 |
| II-first/passI/postI/noinit | 200 (154) | 42 / 60 | 0 / 0 | 0/200 | 0/5 | gates 60, startfork 0 |
| I-first/passI/postII/init | 200 (160) | 29 / 29 | 0 / 0 | 0/200 | 0/5 | gates 35, qcheck 2, startfork 8 |
| II-first/passI/postII/init | 200 (156) | 35 / 76 | 0 / 0 | 0/200 | 0/5 | gates 38, qcheck 0, startfork 12 |
| I-first/passI/postII/noinit | 200 (144) | 44 / 44 | 0 / 0 | 0/200 | 0/5 | gates 72, qcheck 9 |
| II-first/passI/postII/noinit | 200 (146) | 53 / 71 | 0 / 0 | 0/200 | 0/5 | gates 77, qcheck 0, startfork 0 |
| I-first/passII/every/init | 200 (146) | 0 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 0, startfork 8 |
| II-first/passII/every/init | 200 (129) | 0 / 25 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 1, startfork 25 |
| I-first/passII/every/noinit | 200 (132) | 8 / 8 | 0 / 0 | 0/200 | 0/5 | gates 8, qcheck 0 |
| II-first/passII/every/noinit | 200 (116) | 21 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 3, startfork 0 |
| I-first/passII/postI/init | 200 (144) | 0 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, startfork 9 |
| II-first/passII/postI/init | 200 (122) | 1 / 28 | 0 / 0 | 0/200 | 0/5 | gates 1, startfork 28 |
| I-first/passII/postI/noinit | 200 (135) | 5 / 5 | 0 / 0 | 0/200 | 0/5 | gates 5 |
| II-first/passII/postI/noinit | 200 (114) | 23 / 1 | 0 / 0 | 0/200 | 0/5 | gates 1, startfork 0 |
| I-first/passII/postII/init | 200 (131) | 10 / 10 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 10, startfork 25 |
| II-first/passII/postII/init | 200 (123) | 6 / 33 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 4, startfork 30 |
| I-first/passII/postII/noinit | 200 (113) | 30 / 30 | 0 / 0 | 0/200 | 0/4 (+1 cap) | gates 1, qcheck 26 |
| II-first/passII/postII/noinit | 200 (108) | 26 / 5 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 5, startfork 0 |
24 variants
### dnf
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/pass/every/init | 150 (118) | 57 / 57 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 0 |
| II-first/pass/every/init | 150 (113) | 28 / 88 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 22 |
| I-first/pass/every/noinit | 150 (108) | 55 / 55 | 0 / 0 | 0/150 | 0/3 | qcheck 0 |
| II-first/pass/every/noinit | 150 (87) | 48 / 81 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 0 |
| I-first/pass/postI/init | 150 (120) | 46 / 46 | 0 / 0 | 0/150 | 0/3 | startfork 0 |
| II-first/pass/postI/init | 150 (115) | 26 / 84 | 0 / 0 | 0/150 | 0/3 | startfork 24 |
| I-first/pass/postI/noinit | 150 (119) | 56 / 56 | 0 / 0 | 0/150 | 0/3 | - |
| II-first/pass/postI/noinit | 150 (91) | 49 / 82 | 0 / 0 | 0/150 | 0/3 | startfork 0 |
| I-first/pass/postII/init | 150 (115) | 59 / 59 | 0 / 0 | 0/150 | 0/3 | qcheck 8, startfork 30 |
| II-first/pass/postII/init | 150 (95) | 30 / 91 | 0 / 0 | 0/150 | 0/3 | qcheck 3, startfork 24 |
| I-first/pass/postII/noinit | 150 (90) | 87 / 87 | 0 / 0 | 0/150 | 0/3 | qcheck 33 |
| II-first/pass/postII/noinit | 150 (85) | 52 / 83 | 0 / 0 | 0/150 | 0/3 | qcheck 3, startfork 0 |
| I-first/nopass/every/init | 150 (131) | 44 / 44 | 0 / 0 | 0/150 | 0/3 | gates 13, qcheck 5, startfork 1 |
| II-first/nopass/every/init | 150 (127) | 31 / 77 | 0 / 0 | 0/150 | 0/3 | gates 18, qcheck 10, startfork 9 |
| I-first/nopass/every/noinit | 150 (133) | 47 / 47 | 0 / 0 | 0/150 | 0/3 | gates 19, qcheck 12 |
| II-first/nopass/every/noinit | 150 (125) | 34 / 68 | 0 / 0 | 0/150 | 0/3 | gates 36, qcheck 17, startfork 0 |
| I-first/nopass/postI/init | 150 (123) | 56 / 56 | 0 / 0 | 0/150 | 0/3 | gates 15, startfork 3 |
| II-first/nopass/postI/init | 150 (120) | 30 / 74 | 0 / 0 | 0/150 | 0/3 | gates 7, startfork 9 |
| I-first/nopass/postI/noinit | 150 (126) | 45 / 45 | 0 / 0 | 0/150 | 0/3 | gates 18 |
| II-first/nopass/postI/noinit | 150 (116) | 48 / 85 | 0 / 0 | 0/150 | 0/3 | gates 29, startfork 0 |
| I-first/nopass/postII/init | 150 (115) | 50 / 50 | 0 / 0 | 0/150 | 0/3 | gates 14, qcheck 22, startfork 10 |
| II-first/nopass/postII/init | 150 (122) | 40 / 83 | 0 / 0 | 0/150 | 0/3 | gates 30, qcheck 15, startfork 15 |
| I-first/nopass/postII/noinit | 150 (101) | 77 / 77 | 0 / 0 | 0/150 | 0/3 | gates 25, qcheck 26 |
| II-first/nopass/postII/noinit | 150 (102) | 55 / 90 | 0 / 0 | 0/150 | 0/3 | gates 29, qcheck 23, startfork 0 |
24 variants
{'symn': 14400, 'symyes': 9683, 'symmscd': 0, 'symts': 0, 'syms1': 7200, 'syms1b': 0, 'syms2': 239, 'syms2b': 0, 'symcap1': 0, 'symcap2': 1, 'asymn': 4800, 'asymyes': 3399, 'asymmscd': 0, 'asymts': 0, 'asyms1': 4800, 'asyms1b': 0, 'asyms2': 119, 'asyms2b': 0, 'asymcap1': 0, 'asymcap2': 1, 'dnfn': 3600, 'dnfyes': 2697, 'dnfmscd': 0, 'dnfts': 0, 'dnfs1': 3600, 'dnfs1b': 0, 'dnfs2': 72, 'dnfs2b': 0, 'dnfcap1': 0, 'dnfcap2': 0}
