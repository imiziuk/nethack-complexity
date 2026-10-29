# R: boulder gadgets brute-forced in the real NetHack 5.0.0 engine (2026-10-29)

**Question.** Ivan suspected the boulder gadgets were broken. Does our Python movement model (`A_core.py`, plus the hole rules
from `check_small.py`/`D_game.py`) agree with the real compiled game, move by move, on every gadget?

**Answer: yes. There are 0 mismatches.** I ran 62,025 single-key queries (every reachable state × all 8 keys on every small
gadget, plus a stratified sample of the full SCD). I also replayed 13,300 traversal walks (≈ 215,000 keys) key by key, and
typed 350 walks and steps (1,360 keys) into the tty. All of them matched the model exactly: the final hero cell, the boulder
set, the hole set, the hero cell after every key, and fall versus no fall. So the verdicts in `A-gadgets.md`,
`A2-scd.md` and `hu-on-lower.md` §3 hold in the real engine. They do **not** rest on a model bug. Gadgets that are
"broken" stay broken in the real game too (SLOT1 overshoot, raw-SCD leaks), as the model says. The postselected
behaviour checks out as intended.

## 1. Method

- **Engine:** the headless WSL build of NetHack 5.0.0 (`~/nh-witness/install`, tty, wizard mode). It runs in private
  HACKDIR copies `~/nh-witness/realgame/h*`, created by `tools/exptime/R_setup.sh`, so these runs never share lock or
  save files with other witness runs. The hero is a Valkyrie (`pettype:none`) carrying one cursed loadstone, so she is
  heavy and cannot squeeze. Hunger and monster generation are off.
- **Level per query** (`R_oracle.py`): the same template every time.
  - `des.reset_level`, then the flags `noflip`, `sokoban`, `noteleport`, `solidify`, `premapped`. No `hardfloor`, so
    holes are real.
  - Solidfill stone, with `des.map` of the gadget window. Port cells are just floor at the window edge, with stone
    beyond.
  - `des.object` boulders and `des.trap("hole")`.
  - A sealed sentinel pit, so the Sokoban rules survive plugging a hole.
  - The branch stair goes into a sealed pocket through `des.levregion`.
  - A one-cell `teleport_region` on the hero cell, then `finalize`. The hero cell is checked after every build (retry
    up to 10 builds); 0 builds failed.
- **Fast mode:** one `#wizloadlua` script runs 100–300 queries in one game session. For each query it builds the
  level, sends the key(s) through the game's command queue (`nh.pushkey` + `nh.doturn` = `rhack`→`domove`, the same
  path a typed key takes), and reads the engine state back:
  - `u.ux`/`u.uy`;
  - `u.dlevel`: a change means the hero fell through a hole, which is the loss outcome;
  - every boulder on the level, from the `fobj` chain;
  - the remaining holes.

  Messages are hidden in this mode (`MSGTYPE=hide`) for speed. After a fall the batch stops and the driver restarts
  the game.
- **Screen mode:** the same level, but the keys are **typed into the tty** with pexpect. After each key, the `@` glyph
  is decoded from the pyte screen (after `^R`), and every message line is recorded, `--More--` included. A dump script
  then reads the true state.
- **Model:** `R_model.py` imports `A_core.Board.moves` read-only and runs it on the window with the ports turned into
  floor. Windows with holes (G_X) use `HoleModel`, which is A_core plus F1/F4 of `hu-on-lower.md` §2:
  - pushing a boulder onto a hole plugs it;
  - stepping onto a hole is a loss;
  - a hole is not bad rock.

  On every hole-free state, `HoleModel` agrees with A_core: 0 differences.
- **State sets:**
  - **Local states:** `A_core`-style traversals with an external link between all ports; the counts equal
    A_core/A2's own (diode 4, proto-precursor 28, UTURN2 115, flat SCD 10,927).
  - **Hero states:** everything reachable inside the window from the hero standing on any port in any local state.

## 2. Results

| gadget | local states | hero states | step queries (state × key) | **mismatches** | walks replayed (keys) | walk FAIL | typed in tty: items (keys) | tty FAIL |
|---|---|---|---|---|---|---|---|---|
| checkable diode (protodiode, A_library) | 4 | 28 | 224 | **0** | 38 (110) | 0 | 34 (52) | 0 |
| G_D one-way door (GD_ROWS) | 2 | 11 | 88 | **0** | 4 (19) | 0 | 13 (22) | 0 |
| G_D tile (gen_on_instance `door`) | 2 | 21 | 168 | **0** | 4 (38) | 0 | 23 (41) | 0 |
| SLOT1 (= diode with C–D joined; negative) | 4 | 40 | 320 | **0** | 12 (58) | 0 | 28 (35) | 0 |
| UTURN2 (negative) | 115 | 2,451 | 19,608 | **0** | 7,580 (128,090) | 0 | 28 (48) | 0 |
| proto-precursor (Fig. 36a) | 28 | 588 | 4,704 | **0** | 1,467 (10,325) | 0 | 48 (142) | 0 |
| precursor (A, B, C joined to T) | 28 | 840 | 6,720 | **0** | 1,829 (24,842) | 0 | 58 (277) | 0 |
| 1-toggle (same window, T closed) | 28 | (= precursor) | (= precursor) | **0** | 1,682 (31,609) | 0 | 24 (233) | 0 |
| G_C closing site (tile `Cl`) | 8 | 201 | 1,608 | **0** | 209 (2,538) | 0 | 34 (115) | 0 |
| G_X hole crossover (tile `X`) | 9 | 298 | 2,384 (27 falls, 1 plug) | **0** | 71 (834) | 0 | 31 (96) | 0 |
| full SCD, flat (6 boulders) | 10,927 | 1,027,901 | 26,201 (sample) | **0** | 404 (16,879) | 0 | 29 (299) | 0 |

- **Small gadgets** were checked exhaustively: every hero state × all 8 keys.
- **Full SCD:**
  - 2 random hero states for each of the 12,544 boulder configurations a hero can meet: the 10,927 local states plus
    mid-traversal configurations, one random key each.
  - Every state on the intended walks, with all 8 keys.
  - Walks: the 4 intended walks, plus 150 random local states × 1 random port × up to 5 traversals.
- **"Walks"** means every traversal p→q from every local state, using the shortest model walk. The SCD uses the sample
  above instead. Each walk was replayed key by key, comparing the hero cell after every key and the final
  ports/boulders/holes.
- **"Typed"** means each initial state's port relation (the shortest walk per p→q), plus about 25 single steps per
  gadget. The step sample leans towards pushes and refusals, and includes every hole entry of G_X.
- **Negative traversals** ("B→A refused", "I→J refused when closed") cannot be replayed. They still follow from the
  table: the enumerated hero-state set is closed under the model's moves, and every move in it matches the game, so
  the game's reachable set from any of these states is exactly the model's.

**SCD automaton in the real game** (flat physical layout below, typed into the tty):

| walk | result |
|---|---|
| closed → O→O (94 keys) | opens: precursor at track 4,6 |
| → I→J (43 keys) | closes: precursor back at 3,5; the state is again exactly the closed initial state |
| → O→O | re-opens |
| open initial state → I→J | closes |

Model relations, counting only traversals that end clean (A2 §5b):

| state | relation |
|---|---|
| closed | {I→I, O→O} |
| open | {I→I, **I→J**, O→O} |

So I→J is refused while closed.

The raw (unchecked) SCD also does its documented bad things in the real game. 82 sampled raw walks include
**O→J leaks**, and the shortest raw walks overshoot the diode blocks.

**Failure modes are real too:**
- SLOT1: after the overshoot (block on e2), **B→A (`by`)** works in the game.
- Raw protodiode: B→A works in its broken state.

These failures are exactly the ones the library files record.

**Messages seen while typing:**

| count | message |
|---|---|
| 590 | "With great effort you move the boulder." |
| 20 | "Air currents pull you down into a hole!" (Sokoban hole: 5 of them also "You fall down a (deep) shaft!", i.e. several levels) |
| 18 | "The boulder falls into and plugs a hole in the floor!" |
| 11 | "You cannot pass that way." (diagonal corner rule) |
| 10 | "You try to move the boulder, but in vain." |

Wall bumps print nothing.

## 3. Negative controls (the 0 is not vacuous)

The real results of the 62,025 step queries were re-scored against deliberately wrong movement models
(`R_controls.py`, `build/realgame/controls.json`). Each wrong rule is caught many times:

| wrong rule | steps where the real game disagrees |
|---|---|
| no diagonal corner rule | 1,112 |
| boulders are not bad rock | 1,112 |
| diagonal pushes allowed | 312 |
| hero squeezes onto stuck boulders | 735 |
| boulder on a hole does not plug it | 1 |

Real outcome classes:

| outcome | count |
|---|---|
| pushes | 674 |
| refused by a boulder | 1,760 |
| refused by the corner rule | 1,112 |
| wall | 35,122 |
| orthogonal steps | 15,441 |
| diagonal steps | 7,888 |
| falls | 27 |
| plugs | 1 |

"Holes are bad rock" is never tested by any state. That is expected: Rule R (`hu-on-lower.md` §2) keeps holes out of
every diagonal corner.

## 4. Layouts that are new here

These windows did not exist as single maps before:

**Precursor / 1-toggle window.** This is the proto-precursor with A, B and C joined by a corridor. T is on it (a port
only for the precursor). D and G are dead-end pockets.
```
##########
##...T..##
##.#.##.##
##.#.##.##
##.#..#.##
#...0.0..#
#.#.##.#.#
#D#E##F#G#
```
**Flat Fig. 37 SCD (`R_model.scd_rows`)**, built from these parts:
- the precursor (left);
- the 1-toggle (right, mirrored vertically; its A, B and C are joined by a private corridor; E = O; F goes to T);
- the joined diodes d1 (I → precursor E) and d2 (precursor F → J);
- the T corridor across the top.

`A_core.explore` on this single board gives **10,927** states, the same as A2's flat network count. So the physical
wiring adds no interactions.
```
#######################
###.................###
###.#.##.##########.###
###.#.##.#####.#O##.#.#
##...0.0..####...0.0..#     (open initial state; closed: precursor blocks at x=4,6)
##.#.##.#.#####.#..#.##
##.#.##.#.#####.#.##.##
####.##.#######.#.##.##
##I#.##.#J#####......##
##.0..#.0..############
###.#.##.#.############
###...##...############
#######################
```
G_C, G_X and G_D are the exact 11×11 tiles from `gen_on_instance.py` (`pat_Cl`, `pat_X`, `pat_door`), with ports
N/E/S/W.

**G_C as an isolated window.** P's W boulder can be pushed out through port S. A_core flags this as a LEAK. In the
level it is fine, because the boulder enters the next tile, which `check_small` covers. In the window the boulder
stops at the frame, and the game agrees.

## 5. Speed

| mode | measured speed |
|---|---|
| Fast mode | ≈ 410–510 queries/s with 6 parallel games (one query = a fresh level + 1 key + state readback). Per game: 70 q/s (SCD, 23×14 window) to 210 q/s (small windows). |
| All 62,025 step queries | about 3 min of game time |
| Walk replays | ≈ 40 s for ≈ 215,000 keys |
| Typed (screen) mode | ≈ 1.5 keys/s per game: one level build, then per key a typed key, the `--More--` handling, a `^R` redraw, and a screen decode |
| SCD model enumeration | Python, about 8 min, cached in `build/realgame/scd_local_states.json` |

## 6. Files

- `tools/exptime/R_setup.sh` creates the private HACKDIRs. `R_run.sh <steps|walks|screen|all> [gadgets]` runs
  everything (WSL venv).
- `R_game.py`: tty session; `R_oracle.py`: Lua generator and readback; `R_model.py`: windows and model;
  `R_run.py`: the phases; `R_controls.py`: negative controls; `R_report.py`: tables; `R_try.py`: single-gadget
  debug probe.
- `build/realgame/`:
  - `steps_<gadget>.tsv`: every query, with the real and predicted state;
  - `walks_<gadget>.tsv`;
  - `screen_<gadget>.json`: typed keys, messages, screen hero per key, and truth;
  - `*_summary.json`, `controls.json`, `log_*.txt`.
