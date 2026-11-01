# R-neighbourhood: the movement model against the real C code, on every gadget neighbourhood (2026-10-30)

**Question.** Every gadget proof and the layout generator rely on one movement model: `A_core.Board.moves`. This is
hu-off M1-M3 and hu-on-lower F1-F3, the same rule as `D_game.py` / `D_game.rs`, plus D_game's coin rule: stepping
onto T lands the hero on a free cell of T's landing set. Does that model match the compiled NetHack 5.0.0 @16ff591?
The check covers every gadget the EXPTIME reduction uses, under the exact L_OFF^{W+C} template (phase2-spec Rev. 4),
in **normal (non-wizard) mode**.

**Answer: yes, with 0 mismatches.** The test used 370,733 queries, and 2,685,138 keystrokes were compared one at a
time. After every key the check compared the hero cell, the full boulder set and the dungeon level; the trap set was
compared at the end of every query. A refused move shows up as an unchanged state, so refusals are compared too.
Two parts of the result:
- **Exhaustive single steps.** Every hero cell of every gadget map was tested with all 8 keys and every boulder
  pattern on the cells the move rule can read. This is a superset of the reachable states.
- **Coin.** The real game landed the hero only on A or B (73 / 87 of 160 entries), never on T, as the model says.

**Label.**
- The claim "the model equals the C code on all gadget neighbourhoods" is **VERIFIED**, within the scope in §4: the
  8 direction keys, the Rev. 4 template with the fumble boots worn, and the gadget maps listed.
- The step from "every neighbourhood" to "every state of every gadget" uses the locality lemma L (§1). L is
  **STRONG**: it rests on a source reading, and a random-context probe found 0 mismatches.

Tools:
- `tools/exptime/R_neigh.py` (gen / run / report / controls / try);
- `tools/exptime/R_neigh.sh` (WSL setup + run).

Logs and raw results are in `build/rgame/` (gitignored):
- jobs: `jobs_*.json`;
- results: `res_*_{wear,nowear}.json`;
- summaries: `summary.json`, `controls.json`;
- logs and reports: `report.txt`, `log_*.txt`.

## 1. Why neighbourhoods suffice (locality)

**Lemma L (STRONG; source reading, hack.c @16ff591).** Fix the global state that the reduction holds fixed:
- the Sokoban flag on (the sentinel pit keeps it on);
- no monsters;
- the hero not levitating, blind or polymorphed;
- the inventory fixed.

Then the outcome of one direction key from hero cell h depends only on the cells it reads, and those lie within
Chebyshev distance 2 of h:
- the target t = h+d;
- the cell beyond, h+2d, for orthogonal pushes;
- the two corner cells for diagonals.

What the code reads:
- `test_move` (hack.c:991) uses the corner rule `bad_rock(ux, y) && bad_rock(x, uy)` (hack.c:1152-1159;
  `bad_rock` = Sokoban boulder or obstructed terrain, hack.c:939-946). It sends a boulder on t to `moverock`
  (hack.c:1216-1229).
- `moverock_core` (hack.c:348) reads only `sx = h+d` and `rx = h+2d`, with their boulders, trap, monster and door
  (hack.c:380-600).
- The coin is the one non-local effect: the landing set comes from the level's `exclude` zone. It is therefore tested
  only on the whole coin tile, together with its zone.

The model reads exactly the same cells (`A_core.Board.orth` / `.diag`). So "model = C" on every gadget state follows
from "model = C" on every (neighbourhood, key) class, and multi-key walks follow by induction.

Two things test this empirically:
- The neigh phase fills the other dynamic cells within distance 4 at random. Each class is run in up to 2 different
  contexts, often from different gadgets.
- The seq and walk phases re-check the inductive step directly.

**Big maps.**
- The crossover v2 (453×432) and the v2 SCD tiles (19×37, 21×43) do not fit the 80×21 level.
- They were cut into a fixed tiling of 72×19 windows that overlap by 8. Every cell lies at least 4 from the cut edges
  of some window.
- For single steps, each hero cell is tested in a window where it lies at least 4 from the cut.
- Long walks on the full map (model trajectories) were cut into pieces. Each piece stays inside one window, with every
  hero cell at least 2 from the cut, so every cell the piece reads lies inside the window.
- The window's stone beyond the cut is never read, so the windowed run equals the full-map run.

## 2. Harness (the Rev. 4 template, normal mode)

**One query.** Each query is one fresh level. It is built by a Lua script that uses only whitelisted calls:
- `des.reset_level`;
- `level_flags("noflip", "sokoban", "hardfloor", "solidify", "premapped")`, with **no `noteleport`**;
- solidfill stone, then `des.map`;
- boulders via `des.object`;
- teleport traps via `des.trap{type="teleport", seen=true}`;
- a sealed sentinel pit;
- the branch stair, put into a sealed 1-cell pocket by `des.levregion`;
- **exactly one** `des.teleport_region`. It is a 1-cell region on the start cell s, with `exclude` = the coin zone Z on
  the coin tile, or a stone cell elsewhere, and `dir="both"`;
- `finalize`;
- `u.clear_inventory()`, then a cursed loadstone and a cursed +0 fumble boots, which are then **worn** (`W`);
- `nh.debug_flags{mongen=false, hunger=false}`.

**Hero and game.**
- The hero is a human female neutral Valkyrie with `pettype:none`.
- Every batch of queries runs in a **new game process**. The tty is started with `-D` only so that `#wizloadlua` can
  load the batch. The script's first action is `nh.parse_config("OPTIONS=playmode:normal")`, which sets wizard =
  flags.debug = FALSE and discover = FALSE (options.c:3485-3486). The game then never returns to wizard mode, because
  OPTIONS can be parsed once per game (`duplicate_opt_detection`, options.c:6782). Every level build and every key
  therefore runs with `flags.debug` false.

**Checks after every build** (the build is retried, at most 10 times, if one fails):
- the hero is on s;
- the boots are cursed and worn, and the loadstone is cursed;
- playmode is normal.

**Checks once per batch:**
- the branch stair is in the pocket;
- the trap list is right: every T seen, and the sentinel pit present.

All 1,482 batches passed. No build failed, apart from 1 coin random walk that started on A, which lies inside Z and so
is not a legal start cell.

**Keys.**
- Each key goes in through `nh.pushkey`, followed by one `moveloop_core` call (`nh.doturn(false)` = `rhack` →
  `domove`, the typed-key path).
- After that, 3 more calls are fed ESC. ESC is a no-op that takes no time. These calls are needed because
  `moveloop_core` reads a command in the same call in which a helpless spell ends (allmain.c:380-392, 532). Without a
  queued key the game would block on the tty. Helpless spells come from the 2-turn dressing delay and from fumble
  trips.
- With the boots worn, a key that leaves the state unchanged is re-sent up to 3 times. A dropped key needs a trip, a
  trip needs elapsed time, and a refused key takes no time, so a retry never hides a refusal.
- Fumbling is really on. A 150-move probe took 161 turns with the boots and 150 without, about 6 trips. Every key was
  still executed within its own key slot: 0 retries were needed.

**The comparison runs in Lua**, against model predictions computed by `A_core`, after every key. A batch reports only
a status character per query and the real state at the first difference. In the coin (trace mode), Lua reports the
hero cell after every key. `report` then replays the model and branches on nature's observed landing.

**Sanity checks:**
- *Positive control:* `CORRUPT=1 R_neigh.py try` falsifies every 7th prediction, and exactly those were flagged.
- *Negative controls* (§3.2).
- *Boots-off control* (§3.3).

## 3. Results

### 3.1 Main runs (fumble boots worn)

| gadget (map) | size | neighbourhood classes (unique / dyn cells) | single steps (neigh) | short sequences (all 8^L) | walks: random + intended (pieces) | queries | keys compared | mismatches | label |
|---|---|---|---|---|---|---|---|---|---|
| protodiode (A_library) | 6×4 | 48 / 4 | 384 | L=4 from 4 ports: 16,384 | 60 + 38 traversals (4 local states) | 16,866 | 90,030 | **0** | VERIFIED |
| proto-precursor (A2, open + closed) | 10×5 | 158 / 8 | 1,264 | L=4 from 7 ports × 2 states: 57,344 | 60 + 1,467 (all 28 local states) | 60,135 | 264,965 | **0** | VERIFIED |
| SCD, flat Fig. 37 (open + closed) | 23×14 | 366 / 24 | 3,728 | L=4 from 3 ports × 2: 24,576 | 60 + 3,000 (sampled from 10,927 local states) | 31,364 | 285,490 | **0** | VERIFIED |
| v2 SCD tile, variant 0 | 19×37 | 135 new / 24 | 2,224 | L=3 from 3 ports (crop): 1,536 | 118 + 3,000 (13,370 window pieces) | 17,248 | 317,311 | **0** | VERIFIED |
| v2 SCD tile, variant 1 | 21×43 | 43 new / 24 | 952 | 1,536 | 120 + 3,000 (17,028 pieces) | 19,636 | 562,293 | **0** | VERIFIED |
| v2 SCD tile, variant 2 | 19×37 | 11 new / 24 | 320 | 1,536 | 118 + 3,000 (14,012 pieces) | 15,986 | 357,374 | **0** | VERIFIED |
| v2 diode tile | 4×11 | 4 new / 4 | 32 | L=4 from 2 ports: 8,192 | 60 + 12 | 8,296 | 56,978 | **0** | VERIFIED |
| coin tile [A # T # B] (L_gen.COIN) | 9×10 | 10 / 0 | 139 (20 trials per T entry) | L=4 from e, a, b: 12,288 | 60 + 122 (120 × e→E→T→landing→a) | 12,609 | 75,555 | **0** (landings A 73, B 87, T 0) | VERIFIED on the tested set (the ∀-claim "never T, never outside Z" rests on the C-audit §2.2 source reading, review 6 F6) |
| WMC (Fig. 32) | 5×7 | 112 / 7 | 896 | L=4 from 3 ports: 12,288 | 60 + 42 | 13,286 | 74,299 | **0** | VERIFIED |
| NR (Fig. 32) | 10×6 | 2,100 / 16 | 16,800 | 8,192 | 60 + 2,142 | 27,194 | 101,619 | **0** | VERIFIED |
| WO (Fig. 32) | 7×10 | 3,112 / 19 | 24,896 | 12,288 | 60 + 2,353 | 39,597 | 124,736 | **0** | VERIFIED |
| crossover v2 (build/xover/crossover.txt, 166 boulders) | 453×432, 113 windows | 1,798 new / 664 | 25,760 | L=3 from all 156 ports (4 external + 152 tile ports, crop): 79,872 | 120 random-window walks + X_verify's scripted A1→B1, A2→B2 crossings (8 crossings, 61,112 keys; 2,764 pieces) | 108,516 | 374,488 | **0** | VERIFIED |
| **total** | | **7,897** classes | **77,395** | **236,032** (859,648 keys) | **57,306** (1,748,095 keys) | **370,733** | **2,685,138** | **0** | |

Notes on the table:
- "Classes" are distinct pairs (5×5 terrain with dynamic-cell marks, boulder pattern on the 12 read cells).
- Dedup is global across the gadget order of the table, so "new" counts the classes not already tested on an earlier
  gadget.
- Every class of every gadget was run at least once, and in 2 contexts when it occurs twice or more.
- Rotated and reflected tile copies (crossover tiles use all 8 symmetries) are covered directly, because the crossover
  map itself was tested.

Run times:

| phase | time |
|---|---|
| neigh | 6 min (8 games) |
| seq | 12 min (10 games) |
| walk | 32 min (10 games) |

### 3.2 Negative controls (the 0 is not vacuous)

`R_neigh.py controls` checks 358,243 passing deterministic queries. On all of them the real game equals A_core after
every key. The table counts how many of those queries a deliberately wrong rule would have mispredicted, i.e. on how
many the real game disagrees with that rule:

| wrong rule | queries where the real game refutes it |
|---|---|
| no diagonal corner rule | 11,074 |
| boulders are not bad rock (corners) | 11,074 |
| diagonal pushes allowed | 3,750 |
| heavy hero squeezes onto a stuck boulder | 11,181 |
| a push into a boulder removes the front one | 3,590 |
| diagonal needs both corners free | 80,596 |

Outcomes of the compared keys:

| outcome | count |
|---|---|
| pushes | 81,488 |
| refused by a boulder | 38,696 |
| refused by the corner rule | 14,658 |
| refused by stone | 711,489 |
| orthogonal steps | 1,468,151 |
| diagonal steps | 295,220 |

### 3.3 Boots-off control (the hero carries the boots but does not wear them)

**Single steps (neigh).** Re-run with the boots unworn: 77,395 queries.
- All non-coin queries: 0 mismatches.
- Coin: 1 mismatch.

**Coin walks.** 182 queries, of which 35 failed.

**Every one of the 36 differences is the same event:** on entry into T the hero **stays on T**. This is the trap
escape `already_seen && !Fumbling && ... && !rn2(5)` (trap.c:3035). It happened in 36 of 160 entries, about 1/5.
Minimal repro: start at E = (6,7) on the coin tile, boots carried but not worn, key `k`. The real hero is on (6,6) = T;
the model lands on A (4,6) or B (8,6).

This is **not a model bug for L_OFF^{W+C}**: with the boots worn there were 0 escapes in 160 entries. It confirms why
the template needs the worn cursed fumble boots (C-audit §2.2, Fumbling short-circuits the escape test). Un-worn boots
add the "bounce at T" outcome that C-audit S^C already lists.

## 4. Scope, and what remains untested

**Covered:**
- the 8 direction keys (vi keys, `number_pad:0`), one step each;
- multi-key walks built from those steps;
- the Rev. 4 template with the boots worn;
- the maps listed above.

**Not covered here:**
- **Other commands:** wait, search, `#sit`, run, rush, travel (`G`/`_`), the `m`/`F` prefixes, kick, throw, apply,
  pray, engrave, wear/remove. They are argued in C-audit §2.2 (Lemma S^C, M5: run/travel = sequences of `domove` steps)
  but not run here.
- **Gadgets not drawn in cells:** the Fig. 33/20/21 composites (SD, SO, MSC, SX, WCX; B2_ani builds them as abstract
  nets), the machinery gadgets on the routed check path and the full L_gen level (about 40k×7k cells,
  L-generator.md). Each such neighbourhood class that also occurs in a tested map is covered by Lemma L. Classes that
  occur only there are not.
- **Holes, trapdoors, pits as gadget parts.** The `hardfloor` flag of Rev. 4 makes holes inert; the G_X hole crossover
  was checked earlier without `hardfloor` (R-realgame.md). The crossover v2 and these tiles have no holes.
- **Setup randomness.** Each batch is a fresh game, so Str/Con/Dex vary across 1,482 games, and the loadstone with or
  without Burdened was sampled at random rather than enumerated. Within a batch the levels are rebuilt in one game,
  so `moves`, attribute exercise and the Fumbling timer carry over between queries.
- **No-monster assertion.** `mongen=false` + `pettype:none` were used, but the absence of monsters was not asserted
  per build: the Lua API has no monster iterator.
- **Lemma L itself** is a source-reading argument (STRONG), backed by the random-context probe. It was not checked
  exhaustively over all contexts.

**Label summary:**
- "model = C on every neighbourhood class of every listed gadget, for single direction keys under Rev. 4 with boots
  worn": **VERIFIED**.
- "model = C on every reachable state / walk of those gadgets": **VERIFIED** given L (STRONG), and checked directly on
  2.68 M keys.
- Coin: landing ∈ {A, B} on every one of 160 entries, both outcomes seen: consistent with the model's nondeterministic
  rule (statistical, not exhaustive over RNG).
