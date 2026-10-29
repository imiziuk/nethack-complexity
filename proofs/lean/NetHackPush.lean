/-
  NetHackPush.lean — proof skeleton for L_OFF^W PSPACE-hardness (proofs/hu-off.md Thm B).
  STATUS: written 2026-10-28, NOT COMPILED (no Lean toolchain on the laptop yet). Target: Lean 4 + Mathlib.

  Trust layers (mission §12 / §8):
    1. `Push1F`            — the external model (Ani–Chung–Demaine–Diomidov–Hendrickson–Lynch, FUN 2022).
    2. `NHSoko`            — abstraction of NetHack 5.0.0 @16ff591 restricted to the L_OFF^W fragment.
    3. `SourceFact.*`      — axioms, each one a fact read from the C source (file:line). Trusted, not proved.
                             Their evidence is the witness scripts in tools/witness/.
    4. `simulation`        — the lemma linking 1 and 2 (to prove; currently `sorry`).
    5. `push1F_pspace_hard`— external theorem, stated as an axiom.
-/
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Int.Basic

namespace NetHackPush

abbrev Cell := Int × Int

inductive Dir4 | N | S | E | W deriving DecidableEq, Repr
inductive Dir8 | N | S | E | W | NE | NW | SE | SW deriving DecidableEq, Repr

def Dir4.vec : Dir4 → Cell
  | .N => (0, -1) | .S => (0, 1) | .E => (1, 0) | .W => (-1, 0)

def Dir8.vec : Dir8 → Cell
  | .N => (0, -1) | .S => (0, 1) | .E => (1, 0) | .W => (-1, 0)
  | .NE => (1, -1) | .NW => (-1, -1) | .SE => (1, 1) | .SW => (-1, 1)

def add (a b : Cell) : Cell := (a.1 + b.1, a.2 + b.2)

/-! ## 1. Push-1F (external model) -/

structure Board where
  free  : Finset Cell        -- cells that are not fixed blocks (everything outside is fixed)
  goal  : Cell

structure Config where
  robot  : Cell
  blocks : Finset Cell
deriving DecidableEq

/-- One Push-1F move: step into an empty free cell, or push exactly one block into an empty free cell. -/
inductive Push1F.step (B : Board) : Config → Config → Prop
  | walk (c : Config) (d : Dir4) :
      add c.robot d.vec ∈ B.free → add c.robot d.vec ∉ c.blocks →
      step B c { c with robot := add c.robot d.vec }
  | push (c : Config) (d : Dir4) :
      let t := add c.robot d.vec; let u := add t d.vec
      t ∈ c.blocks → u ∈ B.free → u ∉ c.blocks →
      step B c { robot := t, blocks := insert u (c.blocks.erase t) }

def Push1F.solvable (B : Board) (c₀ : Config) : Prop :=
  ∃ c, Relation.ReflTransGen (Push1F.step B) c₀ c ∧ c.robot = B.goal

/-! ## 2. NetHack-Sokoban abstraction of L_OFF^W (projection: hero cell, boulder set) -/

/-- "Bad rock" for the Sokoban corner rule: fixed wall/stone, or a boulder while Sokoban rules hold. -/
def badRock (B : Board) (c : Config) (x : Cell) : Prop := x ∉ B.free ∨ x ∈ c.blocks

inductive NHSoko.step (B : Board) : Config → Config → Prop
  | ortho (c c' : Config) (d : Dir4) : Push1F.step B c c' → NHSoko.step B c c'
  /-- diagonal walk: target free, no boulder, and at least one corner not bad rock (Sokoban squeeze rule). -/
  | diag (c : Config) (dx dy : Int) (hx : dx = 1 ∨ dx = -1) (hy : dy = 1 ∨ dy = -1) :
      let t := add c.robot (dx, dy)
      t ∈ B.free → t ∉ c.blocks →
      (¬ badRock B c (add c.robot (dx, 0)) ∨ ¬ badRock B c (add c.robot (0, dy))) →
      NHSoko.step B c { c with robot := t }
  /-- every other command of the game acts as the identity on the projection (hu-off.md Lemma S, ~60 cases). -/
  | noop (c : Config) : NHSoko.step B c c

/-! ## 3. Source facts (trusted axioms; provenance = NetHack 5.0.0 @16ff591) -/

namespace SourceFact
/-- Diagonal pushes are refused in Sokoban. src/hack.c:441-448 (moverock_core). Witness: off_diag_push.lua -/
axiom no_diag_push : True
/-- Hero cannot squeeze diagonally between bad rock in Sokoban. src/hack.c:953-979, 1153-1171. Witness: off_diag_squeeze.lua -/
axiom corner_rule : True
/-- Heavy hero (cursed loadstone, 500 wt > 150) can't move onto a boulder. src/hack.c:139-163, include/weight.h:24. Witness: off_heavy_no_squeeze.lua -/
axiom heavy_no_squeeze : True
/-- Sokoban flag persists while a non-hero PIT/HOLE remains. src/trap.c:7059-7095. Witness: off_sentinel_pit.lua -/
axiom sentinel_keeps_sokoban : True
/-- A push succeeds iff the next cell is floor without boulder (no monsters/traps/doors in L_OFF^W). src/hack.c:386-414. Witness: off_push_orth.lua -/
axiom push_rule : True
end SourceFact
-- NOTE: these are placeholders (`True`) until the C semantics fragment is modelled; the real statements
-- relate the abstraction in §2 to a model of `moverock_core`/`test_move`. That model is the next formal step.

/-! ## 4. Simulation lemma and reduction -/

/-- A diagonal NetHack walk is two orthogonal Push-1F walks through the free corner. -/
theorem diag_as_two_walks (B : Board) (c c' : Config) (h : NHSoko.step B c c') :
    Relation.ReflTransGen (Push1F.step B) c c' := by
  sorry

theorem push1F_step_is_NH (B : Board) (c c' : Config) (h : Push1F.step B c c') : NHSoko.step B c c' :=
  NHSoko.step.ortho c c' .N h   -- direction tag unused

theorem simulation (B : Board) (c₀ : Config) :
    Push1F.solvable B c₀ ↔
      ∃ c, Relation.ReflTransGen (NHSoko.step B) c₀ c ∧ c.robot = B.goal := by
  sorry

/-- External theorem (FUN 2022), stated abstractly: Push-1F reachability is PSPACE-hard. -/
axiom push1F_pspace_hard : True

end NetHackPush
