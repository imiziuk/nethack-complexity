# Lean proof: Push-1F ↔ NetHack hero movement (core of hu-off.md Thm B)

`NetHackPush.lean` compiles with Lean 4 `v4.36.0-rc2` + Mathlib (`v4.36.0-rc2`), with **no `sorry`, no `admit`,
no `native_decide`, no project axioms**. `#print axioms` on the main theorems lists only Lean's standard
`propext`, `Classical.choice`, `Quot.sound` (see `build-log.txt`).

## What is proved
- `Push1F.step` — Push-1F, enclosed-board version: `Board.free` is a finite set; every other cell is a fixed block.
  (The FUN 2022 paper does not state boundedness explicitly; f(I) adds a wall ring, which is exactly this model.)
  `Push1F.reach_inside`: robot and blocks stay inside the finite free set.
- `nhMove B c d` — one 8-directional hero step, a branch-by-branch transcription of `test_move`,
  `moverock_core`, `cannot_push`, `cant_squeeze_thru`, `bad_rock` (src/hack.c, NetHack 5.0.0 @16ff591) for the
  L_OFF^W fragment (floor/wall/boulders only, Sokoban on, heavy hero, no monsters/traps/doors, plain move keys).
  Every branch carries its C file:line in a comment; fragment assumptions are fixed as constants.
- The old placeholder axioms are now theorems about `nhMove`: `nhMove_diag_blocks` (no diagonal push),
  `nhMove_corner_rule` (no squeeze between two bad rocks), `nhMove_blocked_push` (unpushable boulder = no-op).
- (i) `nhMove_sound`: every step is the identity, an orthogonal Push-1F step, or a diagonal walk equal to two
  Push-1F walks through a free corner (moving no boulder).
- (ii) `push1F_step_nhMove`: every Push-1F step is `nhMove` with the matching orthogonal key (needs `Config.WF`:
  blocks lie on free cells).
- (iii) `reach_iff`: `ReflTransGen NHStep c₀ c ↔ ReflTransGen Push1F.step c₀ c`; `simulation`:
  `Push1F.solvable B c₀ ↔ NH.solvable B c₀`.
- `Example`: 5 concrete checks by `decide`, mirroring the witness scripts (orth push, push into wall,
  diagonal push refused, diagonal squeeze refused, diagonal walk via free corner).

## What is trusted (not proved here)
1. **The transcription `nhMove` vs. the real C code** — checked by inspection (line comments) and by the witness
   scripts `tools/witness/off_*.lua`, which passed in the real game. It covers movement keys only; the other
   commands (Lemma S table: prayer, kicks, throws, inventory, ...) and invariants I1–I9 remain paper proofs in
   `hu-off.md` §B.3–B.5.
2. **The projection** of a full game state to (hero cell, boulder set) and the fragment assumptions (I1–I9).
3. **Push-1F is PSPACE-hard** (Ani et al., FUN 2022) — external; not stated in Lean (no complexity classes in
   Mathlib), and nothing here depends on it.

## Rebuild
Lean lives in WSL (`~/nh-lean/nhproof`, a lake project; this folder holds copies of `lakefile.toml`,
`lean-toolchain`, `lake-manifest.json`). To reproduce elsewhere: `lake new nhproof math`, replace those three
files with the copies here, `lake exe cache get`, put `NetHackPush.lean` in `Nhproof/`, then
```
lake env lean Nhproof/NetHackPush.lean
```
(about 1 min with the Mathlib cache warm; output should be just the four `#print axioms` lines).
