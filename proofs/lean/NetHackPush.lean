/-
  NetHackPush.lean — machine-checked core of proofs/hu-off.md Thm B (L_OFF^W PSPACE-hard via Push-1F).
  Status: compiled with Lean 4 (v4.36.0-rc2) + Mathlib, no `sorry`, no axioms of our own
  (see the `#print axioms` lines at the end and proofs/lean/build-log.txt).

  Layers
    1. `Push1F.step`  — the external model (Ani–Chung–Demaine–Diomidov–Hendrickson–Lynch, FUN 2022),
                        enclosed-board version: the free set is a `Finset`, everything else is a fixed block.
    2. `nhMove`       — a restricted, branch-by-branch transcription of NetHack 5.0.0 @16ff591
                        `test_move` + `moverock_core` + `cannot_push` + `cant_squeeze_thru` + `bad_rock`
                        (src/hack.c) for ONE 8-directional hero step in the L_OFF^W fragment.
                        This transcription is TRUSTED (by inspection + witness scripts tools/witness/off_*.lua,
                        which passed in the real game); it is not derived from the C code mechanically.
    3. Theorems       — (i)  `nhMove_sound`: every nhMove step is the identity, one Push-1F step (orthogonal),
                             or a diagonal walk = two Push-1F walks through a free corner.
                        (ii) `push1F_step_nhMove`: every Push-1F step is an nhMove step (orthogonal key).
                        (iii)`reach_iff` / `simulation`: nhMove* and Push-1F* reach the same configurations,
                             hence the same goal (ReflTransGen both ways).
    4. The external theorem "Push-1F is PSPACE-hard" is NOT stated here (Mathlib has no complexity classes);
       it is cited in hu-off.md. Nothing in this file depends on it.
-/
import Mathlib.Data.Finset.Insert
import Mathlib.Data.Finset.Erase
import Mathlib.Logic.Relation

namespace NetHackPush

open Relation

/-- Map coordinates (x, y); NetHack convention: y grows downward (south). -/
abbrev Cell := Int × Int

def add (a b : Cell) : Cell := (a.1 + b.1, a.2 + b.2)

inductive Dir4 | N | S | E | W deriving DecidableEq, Repr
inductive Dir8 | N | S | E | W | NE | NW | SE | SW deriving DecidableEq, Repr

def Dir4.vec : Dir4 → Cell
  | .N => (0, -1) | .S => (0, 1) | .E => (1, 0) | .W => (-1, 0)

/-- (u.dx, u.dy) for the eight movement keys. -/
def Dir8.vec : Dir8 → Cell
  | .N => (0, -1) | .S => (0, 1) | .E => (1, 0) | .W => (-1, 0)
  | .NE => (1, -1) | .NW => (-1, -1) | .SE => (1, 1) | .SW => (-1, 1)

def Dir4.toDir8 : Dir4 → Dir8
  | .N => .N | .S => .S | .E => .E | .W => .W

theorem Dir4.toDir8_vec (d : Dir4) : d.toDir8.vec = d.vec := by cases d <;> rfl

/-- C test `u.dx && u.dy` (src/hack.c:442, 1153). -/
def Dir8.Diag (d : Dir8) : Prop := d.vec.1 ≠ 0 ∧ d.vec.2 ≠ 0

instance (d : Dir8) : Decidable d.Diag := by unfold Dir8.Diag; infer_instance

theorem Dir4.not_diag (d : Dir4) : ¬ d.toDir8.Diag := by
  cases d <;> simp [Dir8.Diag, Dir4.toDir8, Dir8.vec]

theorem Dir8.ortho (d : Dir8) (h : ¬ d.Diag) : ∃ d4 : Dir4, d4.vec = d.vec := by
  cases d <;> (try simp [Dir8.Diag, Dir8.vec] at h) <;>
    first | exact ⟨.N, rfl⟩ | exact ⟨.S, rfl⟩ | exact ⟨.E, rfl⟩ | exact ⟨.W, rfl⟩

/-- A diagonal vector (dx, dy) splits into a horizontal (dx, 0) and a vertical (0, dy) unit move. -/
theorem Dir8.diag_split (d : Dir8) (h : d.Diag) :
    ∃ a b : Dir4, a.vec = (d.vec.1, 0) ∧ b.vec = (0, d.vec.2) := by
  cases d <;> (try simp [Dir8.Diag, Dir8.vec] at h) <;>
    first | exact ⟨.E, .N, rfl, rfl⟩ | exact ⟨.E, .S, rfl, rfl⟩
          | exact ⟨.W, .N, rfl, rfl⟩ | exact ⟨.W, .S, rfl, rfl⟩

/-! ## 1. Push-1F (external model, enclosed board) -/

/-- `free` = cells that are not fixed blocks. Every cell outside `free` is a fixed block, so the playing
field is bounded by construction ("enclosed board"). The FUN 2022 paper does not state boundedness
explicitly; any finite instance can be given a fixed frame without changing its moves, and f(I) in
hu-off.md B.2 adds exactly such a wall ring, which is what this model describes. -/
structure Board where
  free : Finset Cell
  goal : Cell

structure Config where
  robot  : Cell
  blocks : Finset Cell
deriving DecidableEq

/-- One Push-1F move: step into an empty free cell, or push exactly one block into an empty free cell. -/
inductive Push1F.step (B : Board) : Config → Config → Prop
  | walk (c : Config) (d : Dir4) :
      add c.robot d.vec ∈ B.free → add c.robot d.vec ∉ c.blocks →
      Push1F.step B c { c with robot := add c.robot d.vec }
  | push (c : Config) (d : Dir4) :
      add c.robot d.vec ∈ c.blocks →
      add (add c.robot d.vec) d.vec ∈ B.free →
      add (add c.robot d.vec) d.vec ∉ c.blocks →
      Push1F.step B c { robot := add c.robot d.vec,
                        blocks := insert (add (add c.robot d.vec) d.vec)
                                    (c.blocks.erase (add c.robot d.vec)) }

def Push1F.solvable (B : Board) (c₀ : Config) : Prop :=
  ∃ c, ReflTransGen (Push1F.step B) c₀ c ∧ c.robot = B.goal

/-- Well-formed configuration: blocks lie on free cells. (In the game: boulders are never on wall/stone.) -/
def Config.WF (B : Board) (c : Config) : Prop := c.blocks ⊆ B.free

theorem Push1F.step_wf {B : Board} {c c' : Config} (hwf : c.WF B) (h : Push1F.step B c c') :
    c'.WF B := by
  cases h with
  | walk d _ _ => exact hwf
  | push d _ hu _ =>
    exact Finset.insert_subset_iff.mpr ⟨hu, (Finset.erase_subset _ _).trans hwf⟩

/-- Boundedness: from a well-formed start with the robot on a free cell, the robot and all blocks stay
inside the (finite) free set forever. -/
theorem Push1F.reach_inside {B : Board} {c₀ c : Config} (hwf : c₀.WF B) (hr : c₀.robot ∈ B.free)
    (h : ReflTransGen (Push1F.step B) c₀ c) : c.WF B ∧ c.robot ∈ B.free := by
  induction h with
  | refl => exact ⟨hwf, hr⟩
  | tail _ hs ih =>
    obtain ⟨hw, _⟩ := ih
    refine ⟨Push1F.step_wf hw hs, ?_⟩
    cases hs with
    | walk d hf _ => exact hf
    | push d ht _ _ => exact hw ht

/-! ## 2. NetHack: one hero step in the L_OFF^W fragment

Fragment (hu-off.md B.2/B.3), encoded by FIXING the corresponding C predicates to constants:
  * terrain: every cell is ROOM floor (in `B.free`) or obstructed wall/stone (outside `B.free`);
    `isok` failures are also outside `B.free`. No doors, iron bars, pools, traps on the board.
  * `Sokoban` flag on (invariant I4), so `bad_rock` counts boulders.
  * hero: XL1 human, not Passes_walls / Underwater / tunnelling / Levitation / Blind / riding / polymorphed
    (I8), plain move key (no `m` prefix, `context.run = 0`), not Punished.
  * heavy hero: cursed loadstone (I3) ⇒ `could_move_onto_boulder` = FALSE, hence `cannot_push` = −1.
  * no monsters (I1).
The state is projected to π = (hero cell, boulder set) = `Config`. At most one boulder per cell
(a `Finset`), so the `while (sobj_at(BOULDER, sx, sy))` loop of moverock_core runs at most once. -/

/-- `bad_rock(youmonst, x, y)` src/hack.c:939-946 with Sokoban = TRUE, not tunnelling, not Passes_walls:
`(Sokoban && sobj_at(BOULDER,x,y)) || IS_OBSTRUCTED(levl[x][y].typ)`. -/
def badRock (B : Board) (c : Config) (x : Cell) : Prop := x ∈ c.blocks ∨ x ∉ B.free

instance (B : Board) (c : Config) (x : Cell) : Decidable (badRock B c x) := by
  unfold badRock; infer_instance

/-- One hero step in direction `d` (domove_core → test_move(DO_MOVE) → moverock → moverock_core).
Returns the new projected state; returning `c` unchanged = the move was refused. -/
def nhMove (B : Board) (c : Config) (d : Dir8) : Config :=
  -- test_move: x = ux + dx, y = uy + dy                                   src/hack.c:996-997
  let x := add c.robot d.vec
  -- `!isok(x,y)` → FALSE (1003-1004); `IS_OBSTRUCTED(tmpr->typ)`, not Passes_walls/Underwater/
  -- bars/tunnelling/autodig → final `else` → return FALSE                 src/hack.c:1003-1073
  if x ∉ B.free then c
  -- doors (1074-1152): none in the fragment.
  -- `dx && dy && bad_rock(ux, y) && bad_rock(x, uy)` → cant_squeeze_thru(&youmonst):
  --   not Passes_walls (958), not bigmonst (962), amt = inv_weight()+weight_cap() = total inventory
  --   weight 500 ≤ WT_TOOMUCH_DIAGONAL 600 (967-971), Sokoban → return 3 (974-975)
  --   → "You cannot pass that way." return FALSE                          src/hack.c:1153-1160, 953-979
  else if d.Diag ∧ badRock B c (add c.robot (0, d.vec.2))
                 ∧ badRock B c (add c.robot (d.vec.1, 0)) then c
  -- worm_cross (1172): no monsters. Travel/trap checks (1181-1203): mode = DO_MOVE, run = 0.
  -- diagonal out of a doorway (1208-1214): no doors.
  -- `sobj_at(BOULDER, x, y) && (Sokoban || !Passes_walls)`; run = 0 so 1217-1222 is skipped;
  --   not tunnelling → `moverock() < 0` → FALSE                           src/hack.c:1216-1230
  else if x ∈ c.blocks then
    -- moverock_core(sx, sy), sx = x; rx = ux + 2dx                        src/hack.c:347-379
    -- Blind (358), context.nopick (386), Levitation/air (415), verysmall (426): all excluded.
    let r := add x d.vec
    -- `isok(rx,ry) && !IS_OBSTRUCTED && != IRONBARS && (door ok) && !sobj_at(BOULDER, rx, ry)`
    --                                                                     src/hack.c:432-435
    if r ∈ B.free ∧ r ∉ c.blocks then
      -- "KMH -- Sokoban doesn't let you push boulders diagonally":
      --   cannot_push → not throws_rocks (264), could_move_onto_boulder FALSE (heavy, 304) → −1
      --                                                                   src/hack.c:441-448, 261-312
      if d.Diag then c
      -- revive_nasty (450), monster at r (455), closed door (485), trap at r (496-618),
      -- boulder_hits_pool (620): none in the fragment. dopush moves the boulder sx→rx (631);
      -- loop ends (no second boulder at sx), return 0; test_move returns TRUE and domove
      -- moves the hero onto sx.                                           src/hack.c:631-637, 1253-1254
      else { robot := x, blocks := insert r (c.blocks.erase x) }
    -- else: cannot_push_msg; cannot_push → −1 (heavy hero)                src/hack.c:632-635, 304-311
    else c
  -- legal place to move; domove_core moves the hero                      src/hack.c:1253-1254
  else { c with robot := x }

/-- nhMove as a relation: some key press produces `c'` from `c`. -/
def NHStep (B : Board) (c c' : Config) : Prop := ∃ d : Dir8, nhMove B c d = c'

def NH.solvable (B : Board) (c₀ : Config) : Prop :=
  ∃ c, ReflTransGen (NHStep B) c₀ c ∧ c.robot = B.goal

/-! ### Source facts, now theorems about the transcription (were axioms in the skeleton) -/

/-- SourceFact.no_diag_push (src/hack.c:441-448): a diagonal step never moves a boulder. -/
theorem nhMove_diag_blocks (B : Board) (c : Config) (d : Dir8) (hd : d.Diag) :
    (nhMove B c d).blocks = c.blocks := by
  simp only [nhMove]
  split_ifs <;> rfl

/-- SourceFact.corner_rule (src/hack.c:1153-1171, 953-979): no diagonal squeeze between two bad rocks. -/
theorem nhMove_corner_rule (B : Board) (c : Config) (d : Dir8) (hd : d.Diag)
    (h1 : badRock B c (add c.robot (0, d.vec.2))) (h2 : badRock B c (add c.robot (d.vec.1, 0))) :
    nhMove B c d = c := by
  simp only [nhMove]
  split_ifs with hx hc <;> first | rfl | exact absurd ⟨hd, h1, h2⟩ hc

/-- SourceFact.heavy_no_squeeze + push_rule: stepping into a boulder that cannot be pushed is a no-op. -/
theorem nhMove_blocked_push (B : Board) (c : Config) (d : Dir8)
    (hb : add c.robot d.vec ∈ c.blocks)
    (hr : add (add c.robot d.vec) d.vec ∉ B.free ∨ add (add c.robot d.vec) d.vec ∈ c.blocks) :
    nhMove B c d = c := by
  generalize hm : nhMove B c d = m
  simp only [nhMove] at hm
  split_ifs at hm <;> subst hm
  all_goals first
    | rfl
    | exact (hr.elim (fun h => h ‹add (add c.robot d.vec) d.vec ∈ B.free ∧
                                   add (add c.robot d.vec) d.vec ∉ c.blocks›.1)
                     (fun h => ‹add (add c.robot d.vec) d.vec ∈ B.free ∧
                                   add (add c.robot d.vec) d.vec ∉ c.blocks›.2 h)).elim

/-! ## 3. Simulation -/

private theorem add_split (p u v : Cell) : add (add p u) v = add p (u.1 + v.1, u.2 + v.2) := by
  simp only [add, Prod.mk.injEq]; constructor <;> omega

/-- Push branch of nhMove is one Push-1F push. -/
private theorem sound_push (B : Board) (c : Config) (d : Dir8) (h5 : ¬ d.Diag)
    (h3 : add c.robot d.vec ∈ c.blocks)
    (h4 : add (add c.robot d.vec) d.vec ∈ B.free ∧ add (add c.robot d.vec) d.vec ∉ c.blocks) :
    Push1F.step B c { robot := add c.robot d.vec,
                      blocks := insert (add (add c.robot d.vec) d.vec)
                                  (c.blocks.erase (add c.robot d.vec)) } := by
  obtain ⟨d4, hd4⟩ := Dir8.ortho d h5
  have hs := Push1F.step.push (B := B) c d4 (by rw [hd4]; exact h3) (by rw [hd4]; exact h4.1)
    (by rw [hd4]; exact h4.2)
  rw [hd4] at hs
  exact hs

/-- Walk branch of nhMove: orthogonal = one Push-1F walk; diagonal = two walks through a free corner. -/
private theorem sound_walk (B : Board) (c : Config) (d : Dir8)
    (hx : add c.robot d.vec ∈ B.free) (h3 : add c.robot d.vec ∉ c.blocks)
    (h2 : ¬ (d.Diag ∧ badRock B c (add c.robot (0, d.vec.2))
                    ∧ badRock B c (add c.robot (d.vec.1, 0)))) :
    (¬ d.Diag ∧ Push1F.step B c { c with robot := add c.robot d.vec }) ∨
    (d.Diag ∧ ({ c with robot := add c.robot d.vec } : Config).blocks = c.blocks ∧
      ∃ m, Push1F.step B c m ∧ Push1F.step B m { c with robot := add c.robot d.vec }) := by
  by_cases hd : d.Diag
  · refine Or.inr ⟨hd, rfl, ?_⟩
    obtain ⟨a, b, ha, hb⟩ := Dir8.diag_split d hd
    rcases not_and_or.mp (fun hh => h2 ⟨hd, hh⟩) with hc | hc
    · -- corner (ux, y) = robot + (0, dy) is not bad rock: walk b, then a
      unfold badRock at hc
      rw [not_or, not_not, ← hb] at hc
      have key : add (add c.robot b.vec) a.vec = add c.robot d.vec := by
        rw [add_split, ha, hb]; simp
      refine ⟨{ c with robot := add c.robot b.vec }, Push1F.step.walk c b hc.2 hc.1, ?_⟩
      have hw := Push1F.step.walk (B := B) { c with robot := add c.robot b.vec } a
      simp only [key] at hw
      exact hw hx h3
    · -- corner (x, uy) = robot + (dx, 0) is not bad rock: walk a, then b
      unfold badRock at hc
      rw [not_or, not_not, ← ha] at hc
      have key : add (add c.robot a.vec) b.vec = add c.robot d.vec := by
        rw [add_split, ha, hb]; simp
      refine ⟨{ c with robot := add c.robot a.vec }, Push1F.step.walk c a hc.2 hc.1, ?_⟩
      have hw := Push1F.step.walk (B := B) { c with robot := add c.robot a.vec } b
      simp only [key] at hw
      exact hw hx h3
  · obtain ⟨d4, hd4⟩ := Dir8.ortho d hd
    refine Or.inl ⟨hd, ?_⟩
    have hs := Push1F.step.walk (B := B) c d4 (by rw [hd4]; exact hx) (by rw [hd4]; exact h3)
    rw [hd4] at hs
    exact hs

/-- (i) Soundness of one step: identity, an orthogonal Push-1F step, or a diagonal walk that equals two
Push-1F walks through a free corner (and moves no boulder). -/
theorem nhMove_sound (B : Board) (c : Config) (d : Dir8) :
    nhMove B c d = c ∨
    (¬ d.Diag ∧ Push1F.step B c (nhMove B c d)) ∨
    (d.Diag ∧ (nhMove B c d).blocks = c.blocks ∧
      ∃ m, Push1F.step B c m ∧ Push1F.step B m (nhMove B c d)) := by
  generalize hm : nhMove B c d = m
  simp only [nhMove] at hm
  split_ifs at hm <;> subst hm
  all_goals first
    | exact Or.inl rfl
    | exact Or.inr (Or.inl ⟨‹_›, sound_push B c d ‹_› ‹_› ‹_›⟩)
    | exact Or.inr (sound_walk B c d ‹_› ‹_› ‹_›)

theorem nhMove_reach (B : Board) (c : Config) (d : Dir8) :
    ReflTransGen (Push1F.step B) c (nhMove B c d) := by
  rcases nhMove_sound B c d with h | ⟨_, h⟩ | ⟨_, _, m, h1, h2⟩
  · rw [h]
  · exact ReflTransGen.single h
  · exact (ReflTransGen.single h1).tail h2

/-- (ii) Completeness of one step: every Push-1F move is the hero pressing the matching orthogonal key. -/
theorem push1F_step_nhMove {B : Board} {c c' : Config} (hwf : c.WF B) (h : Push1F.step B c c') :
    ∃ d4 : Dir4, nhMove B c d4.toDir8 = c' := by
  cases h with
  | walk d hf hnb =>
    exact ⟨d, by simp [nhMove, Dir4.toDir8_vec, hf, hnb, Dir4.not_diag]⟩
  | push d ht hu hu' =>
    exact ⟨d, by simp [nhMove, Dir4.toDir8_vec, hwf ht, ht, hu, hu', Dir4.not_diag]⟩

theorem nh_to_push {B : Board} {c₀ c : Config} (h : ReflTransGen (NHStep B) c₀ c) :
    ReflTransGen (Push1F.step B) c₀ c := by
  induction h with
  | refl => exact ReflTransGen.refl
  | tail _ hs ih =>
    obtain ⟨d, rfl⟩ := hs
    exact ih.trans (nhMove_reach B _ d)

theorem push_to_nh {B : Board} {c₀ c : Config} (hwf : c₀.WF B)
    (h : ReflTransGen (Push1F.step B) c₀ c) : ReflTransGen (NHStep B) c₀ c := by
  have : ReflTransGen (NHStep B) c₀ c ∧ c.WF B := by
    induction h with
    | refl => exact ⟨ReflTransGen.refl, hwf⟩
    | tail _ hs ih =>
      obtain ⟨hr, hw⟩ := ih
      obtain ⟨d4, hd⟩ := push1F_step_nhMove hw hs
      exact ⟨hr.tail ⟨d4.toDir8, hd⟩, Push1F.step_wf hw hs⟩
  exact this.1

/-- (iii) Reachability equivalence (any target configuration). -/
theorem reach_iff {B : Board} {c₀ c : Config} (hwf : c₀.WF B) :
    ReflTransGen (NHStep B) c₀ c ↔ ReflTransGen (Push1F.step B) c₀ c :=
  ⟨nh_to_push, push_to_nh hwf⟩

/-- (iii) Simulation lemma (hu-off.md Thm B, Lemmas S + C restricted to movement keys): the hero can reach
the goal cell under nhMove* iff the Push-1F instance is solvable. -/
theorem simulation (B : Board) (c₀ : Config) (hwf : c₀.WF B) :
    Push1F.solvable B c₀ ↔ NH.solvable B c₀ := by
  constructor
  · rintro ⟨c, h, hg⟩; exact ⟨c, push_to_nh hwf h, hg⟩
  · rintro ⟨c, h, hg⟩; exact ⟨c, nh_to_push h, hg⟩

/-! ## 4. Sanity checks on a concrete board (mirroring the witness scripts tools/witness/off_*.lua)

Board (y down):   row 0:  . . .
                  row 1:  . . .      free = {0,1,2} × {0,1}, plus (3,1)
Hero at (0,1). -/
namespace Example

def B0 : Board := { free := {(0,0), (1,0), (2,0), (0,1), (1,1), (2,1), (3,1)}, goal := (3,1) }

/-- off_push_orth: hero (0,1), boulder (1,1); pressing E pushes it to (2,1). -/
example : nhMove B0 { robot := (0,1), blocks := {(1,1)} } .E = { robot := (1,1), blocks := {(2,1)} } := by
  decide

/-- push into the wall ring is a no-op (boulder at (3,1), beyond is (4,1) = wall). -/
example : nhMove B0 { robot := (2,1), blocks := {(3,1)} } .E = { robot := (2,1), blocks := {(3,1)} } := by
  decide

/-- off_diag_push: diagonal push refused under Sokoban. -/
example : nhMove B0 { robot := (0,1), blocks := {(1,0)} } .NE = { robot := (0,1), blocks := {(1,0)} } := by
  decide

/-- off_diag_squeeze: (0,1) → (1,0) with both corners (0,0) and (1,1) holding boulders: refused. -/
example : nhMove B0 { robot := (0,1), blocks := {(0,0), (1,1)} } .NE =
    { robot := (0,1), blocks := {(0,0), (1,1)} } := by
  decide

/-- diagonal walk with one free corner succeeds. -/
example : nhMove B0 { robot := (0,1), blocks := {(1,1)} } .NE = { robot := (1,0), blocks := {(1,1)} } := by
  decide

end Example

end NetHackPush

#print axioms NetHackPush.nhMove_sound
#print axioms NetHackPush.push1F_step_nhMove
#print axioms NetHackPush.reach_iff
#print axioms NetHackPush.simulation
