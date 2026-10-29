# L_ON lower bound: NP-hardness of generalized NetHack reachability with faithful hunger

**Status (2026-10-29, global-construction sub-agent):** the §4 sketch is replaced by a complete construction:
explicit tile coordinates and routing (§4.2-4.4), isolation Lemma 4.1 (proved), planarity/crossover Lemma 4.2
(routine case analysis [conj], asserted mechanically by the generator on every instance built), explicit size
polynomials (§4.6), Claim A reworded per review-2 and soundness/completeness restated with an explicit play and
food bound (§5). `tools/gen_on_instance.py` (instance JSON → Lua level + move string) and `tools/check_small.py`
(exact brute force): all 370 satisfiable small levels won by the replayed play; exhaustive BFS proves g unreachable on 18 of
the 23 unsatisfiable levels (5 largest open, no counterexample; review-4) [auto-experimentally verified, n, m ≤ 3]. Open: exact de Berg–Khosravi statement (§4.1 P4), §6 ball details, Lemma 4.2 not machine-proved
in general, no generated level loaded in the real game (the smallest level is 132×132 cells; stock build is 80×21).

Source: NetHack 5.0.0 @ 16ff591, read-only. Language: `proofs/phase2-spec.md` (L_ON) plus the orchestrator's
repairs of 2026-10-28 (Rule S, mandatory `u.clear_inventory()`, fortune cookies only, quantity 1 for
non-mergeables, allowed traps PIT/HOLE/TRAPDOOR, leaving the level = loss; see `proofs/hu-on-upper.md`).
Labels: **[src f:l]** read in source (this session or quoted from lower-bound-strategies §2.1 / review-1, which
read it); **[conj]** my claim, argued here, not machine-checked; **[ext]** published theorem; **[assump]** modelling
choice. Author: reduction-design sub-agent, 2026-10-28. Nothing was built or run.

## 0. Result and status

**Theorem (conditional on [ext] T1 and [assump] A1-A3).** L_ON is NP-hard, via a polynomial reduction from
Planar Monotone Rectilinear 3-SAT. Outputs satisfy answer-level DET: every YES instance is won by one fixed
play under every RNG outcome, and every NO instance is lost under every play and every RNG outcome.

The reduction uses a two-phase "closing" design. Phase 1 is a variable chain whose branches are forced to push
boulders into the clause paths of false literals. Phase 2 is a check chain of clause gadgets, each three
parallel paths. It also needs a crossover. That crossover needs a **hole**: pure walls plus boulders do not seem
to be enough (§7). Holes become safe only through the repair "leaving the level = loss".

| Gadget | Status |
|---|---|
| Hero template, flags, sentinel pit, food (§1) | proved from source + A1-A3 |
| Movement lemma: 4-connectivity, Sokoban corner rule, holes in walled corridors (§2) | proved [src] |
| G_V variable fork (§3.1) | proved (trivial: no state) |
| G_C forced closing site (§3.2) | proved, case analysis incl. diagonals |
| G_D one-way door (§3.3) | proved |
| G_S clause path σ, G_K clause (§3.4) | proved |
| G_X crossover, "K over P", hole + token (§3.5) | proved for the order it is used in (K at most once, P any time) |
| Global layout: explicit coordinates, isolation, planarity, crossover count, size polynomials (§4) | Lemma 4.1 proved; Lemma 4.2 [conj, routine case analysis]; both asserted by the generator on 513 instances [auto-experimentally verified] |
| Global soundness (Claim A reworded), completeness with explicit play, food (§5) | proved modulo [ext] T1, Lemma 4.2; SAT side replayed on all 370 small levels, UNSAT side exhaustive on 18/23 (5 open; review-4) (§4.7) [auto-experimentally verified, partial] |
| RNG / prayer / ball-and-chain cannot help (§6) | prayer part [conj, source-backed] |

**Weakest step (2026-10-28 view; see Status line for the current one):** §6 prayer side effects (Punishment's iron ball as a pull/plug tool; argued harmless, not fully
traced), then T1's exact statement (positive and negative occurrences on opposite sides of the variable line;
verify in de Berg–Khosravi).

---

## 1. Instance template

### 1.1 Hero
- Human female lawful Valkyrie [assump A0, spec]. Base attributes Str 10, Int 7, Wis 7, Dex 7, Con 10, Cha 7
  [src role.c:519]; `init_attr` only adds points [conj, standard], so Str+Con ≥ 20. Weight cap
  wc = 25(Str+Con)+50 ≥ 550, capped at 1000 [src hack.c:4311-4337 via review L-5].
- Not a spellcaster, no Knight jump, no intrinsic Fast at XL1 (Valkyrie Speed comes at XL7, and XL never rises:
  there are no monsters).
- Script lines: `u.clear_inventory()` (mandatory: it removes the starting food ration [src u_init.c:164 per
  orchestrator]), then `u.giveobj(obj.new("cursed loadstone"))`. The loadstone weighs 500
  [src objects.h:1600]. Inventory weight 500 ≤ 550 ≤ wc, so the hero is **unencumbered** and stays so,
  because he never carries anything else (food is eaten from the floor, §1.3). Carrying more than 150 weight
  units means he can never squeeze onto a boulder [src hack.c:139-163]. The cursed stone cannot be dropped or
  thrown [src do.c:685-697].
- Squeezing is impossible, and Sokoban forbids corner-cutting between bad rock (`cant_squeeze_thru` case 3)
  [src hack.c:953-979, 1153-1171].

### 1.2 Level flags, terrain, sentinel
- `des.level_init({style="solidfill", fg=" "})` (all stone). `des.level_flags("noflip", "noteleport", "sokoban")`.
  **Not** `hardfloor` (see A1). Then `nh.debug_flags({mongen=false})`: no monsters at all, and no pet
  [src makemon.c:1168, nhlua.c:1470-1482].
- Terrain: only stone (` `), floor (`.` ROOM), boulders (`des.object({id="boulder",x=,y=})`, one per call, quantity 1
  per repair 3), holes (`des.trap("hole",x,y)`, only inside crossovers), and one **sentinel pit**.
- **Sentinel:** `des.trap("pit", xs, ys)` on a floor cell whose 8 neighbours are stone. No boulder can ever reach
  it (any push needs an adjacent floor cell). It is a non-hero-made PIT, so `maybe_finish_sokoban` (called when a
  hole is plugged, via `deltrap` [src hack.c:559, trap.c:6547, 7059-7095]) always finds a PIT left and never
  clears `sokoban_rules`. So the Sokoban rules (bad_rock boulders, no diagonal push, no corner squeeze) hold for
  the whole play.
- Hero placement: a one-cell `des.teleport_region` at the start cell s0 (whitelisted for placing the hero).
- **[assump A1]** The instance level is not the dungeon's bottom level and is not hardfloor, so
  `Can_fall_thru` holds [src dungeon.c:1662] and a hero entering a hole falls: in Sokoban he cannot avoid it
  [src trap.c:633-634, 694]. By the repair "leaving the level = loss", **entering a hole cell loses**.
- **[assump A2]** Rule S (orchestrator): the play is lost once u.uhunger < -(100+10·Con). The intended play keeps
  u.uhunger ≥ 850, so the rule never matters for YES instances.
- **[assump A3]** External inputs as in the spec: Luck 0, no full or new moon, not Friday 13th, not night.

### 1.3 Food (fortune cookies only, per repair 2)
- Fortune cookie: delay 1, weight 1, nutrition 40 [src objects.h:1103]. It is exempt from rot (orchestrator,
  eat.c). Place **one uncursed fortune cookie on every floor cell of the construction** except hole cells and the
  sentinel. That includes cells under boulders: the cookie stays when the boulder leaves; `bury_objs` runs only
  on a plugged hole [src hack.c:561].
- **Eating policy of the intended play:** when the hero enters a cell for the first time and u.uhunger ≤ 860, he
  eats the cookie lying there (one turn, +40).
- **Accounting [conj, elementary].** In the intended play (§5.1) each cell is entered at most twice. Only
  crossover centres s (§3.5) are entered twice: once by the P pass, once by the K pass. In the K pass, s is
  entered from n1 and is followed by s1 (a plugged hole, no cookie) and then s2 (cookie). So among any 4
  consecutive moves at least one enters a new cell holding a cookie.
- An unencumbered, awake hero with no rings, amulets or Regeneration loses exactly 1 nutrition per turn
  [src eat.c:3167-3270 via review F7]. With speed 12 he gets one action per turn. Hence u.uhunger stays in
  [855, 900]: never Hungry (>150), never Satiated (>1000), so no fainting, no choking, no Str/Con abuse.
  Total cookies = number of floor cells: polynomial.
- **NO instances:** food changes nothing structural. Cookies are not boulders, cannot plug holes and are not bad
  rock (§2), so the soundness proof (§5.2) ignores them.

---

## 2. Movement lemma (what the hero and boulders can do)

Facts used (all [src hack.c] unless noted):
- **F1 Push.** Moving orthogonally into boulder b at c pushes it to c' = c+d iff c' is not obstructed or iron bars,
  holds no boulder, and holds no monster [432-488]. The boulder moves to c' and the hero to c. On a HOLE at c' the
  boulder plugs it: the trap is deleted, the boulder is used up, and c' becomes plain floor [544-566].
  Otherwise the move fails: no squeeze, because the hero is heavy (§1.1) [262-312].
- **F2** In Sokoban there are no diagonal pushes [441-448].
- **F3 Diagonal step** a→b with corners k1, k2 is refused iff both corners are bad rock. In Sokoban, bad rock =
  wall/stone or a boulder [939-946, 953-979, 1153-1171]. A hole is **not** bad rock.
- **F4** Entering a hole cell = loss (A1). Kicking a boulder does nothing [dokick.c:517-519]. Boulders cannot be
  picked up in Sokoban [pickup.c:1713-1717]. There are no other boulder-moving or hero-moving actions
  (review L-2, L-3, E4).

**Design rule R.** Every hole lies in a straight 1-wide corridor whose two side cells are stone. Every boulder's
cell, and every cell adjacent to a boulder's possible positions, is in the explicit gadget maps below.

**Lemma 2.1 (diagonal = two orthogonal steps).** Under R, every legal diagonal step a→b has a corner k that is
floor without a boulder and is not a hole. So a→k→b is a legal pair of orthogonal steps with the same effect.
Proof. The step is legal, so some corner k is not bad rock (F3). So k is floor or a hole. If k is a hole, R puts
it in a straight corridor with stone sides. The two cells adjacent to k at perpendicular directions are then one
corridor cell and one stone cell, so a or b would be stone. Contradiction. □

So hero connectivity between pushes is 4-connectivity over cells that are floor, boulder-free and hole-free.
All proofs below reason in 4-connectivity and check the few diagonal pairs that touch boulders.

**Lemma 2.2 (corridor block).** In a 1-wide stone-walled corridor, a boulder can move only along the corridor
axis. At a corner cell it is stuck: each push direction there hits stone. While it sits between two corridor
cells x and y, there is no move sequence from x to y inside the corridor. Diagonal moves around it need a stone
corner plus the boulder corner, which F3 refuses. □

Notation in the maps: `#` stone, `.` floor, `0` boulder, `^` hole. Capital letters name cells. Coordinates are
(x,y) with y growing downward. All gadgets may be rotated and reflected: every rule above is invariant under
the dihedral group of the square.

---

## 3. Gadgets

### 3.1 G_V: variable fork (P territory)

```
   # # # # # # # # #
   # . . . . . . . #      top branch F_i (carries the spikes to positive clauses)
   # . # # # # # . #
 . . . # # # # # . . .    main line: Fork (left) ... Join (right)
   # . # # # # # . #
   # . . . . . . . #      bottom branch T_i (spikes to negative clauses)
   # # # # # # # # #
```
There are no boulders. The hero can walk both branches. Every branch contains forced closing sites (G_C)
oriented from Fork toward Join. **Fact V:** to get from Fork_i to Join_i without using K, the hero must pass
every closing site of one branch in its forward direction (Lemma 3.2(a)). Walking both only closes more (it
hurts the hero), so no irreversibility is needed.

Semantics: walking F_i ("x_i false") closes every clause path of literal x_i. Walking T_i closes every clause
path of literal ¬x_i. In a monotone instance positive clauses lie above the variable line and negative ones
below (§4), so F_i's spikes go up and T_i's go down. They never cross.

### 3.2 G_C: forced closing site (P branch meets clause path σ)

Branch direction: it comes down the column x=0 and leaves through x=2 upward. σ comes from the left (its back
segment), turns at Q, then goes down to corner c and on to the right (its forward part).

```
 x:   -2 -1  0  1  2  3
y=-2:  #  #  .  #  .  #      P in (0,-2)          P out (2,-2)
y=-1:  #  #  T  #  .  #      T=(0,-1); (1,-1) stone
y= 0:  #  #  0  .  .  #      N=(0,0) holds W; (-1,0) stone; (1,0),(2,0) P
y= 1:  .  .  Q  #  #  #      back segment (-2,1),(-1,1); Q=(0,1); (1,1) stone
y= 2:  #  #  .  #  #  #      (0,2) forward
y= 3:  #  #  C  .  .  .      corner C=(0,3); forward continues right (no crossovers, see §3.4)
y= 4:  #  #  #  #  #  #
```
P cells: (0,-2),T,N,(1,0),(2,0),(2,-1),(2,-2). K cells: back segment, Q, (0,2), C, forward.
Orthogonal P–K adjacencies: only N–Q. Diagonal P–K pairs: (1,0)/Q via corners {N, (1,1)=stone}, and
N/(-1,1) via corners {Q, (-1,0)=stone}. By Lemma 2.1 each is just a path through N or Q.

**Lemma 3.2.**
(a) *Forced.* From the P side upstream of T, the hero reaches (1,0) iff W has been pushed T→N→Q, i.e. from T
moving down. Proof: (1,0)'s neighbours are N, (2,0), and the stone cells (1,±1). The diagonal T→(1,0) has
corners N (W, bad) and (1,-1) (stone): refused. So the hero must enter N. W at N can be pushed: from T, down
into Q (if Q is free); from Q, up into T; from (1,0) left into (-1,0) = stone, which fails; from (-1,0)
impossible (stone). Reaching Q from the P side needs N free (Q's only P neighbour is N). So the first time N
becomes free, W went to Q. □
(b) *Closed stays closed.* Call σ **closed** once W has entered Q. From then on W ∈ {Q, (0,2), C}, unless the
hero has previously stood on a cell of σ's forward part beyond W (reached from the hub after the clause, see §5).
Proof: from Q, W can move down (hero at N), not up (that needs the hero at (0,2), beyond W), not left (needs
(1,1), stone), not right (into (1,1), stone). From (0,2) it can move down to C (hero at Q), or up (hero at C,
beyond W). At C it is stuck: down hits (0,4) stone, right needs the hero at (-1,3) (stone). □
(c) *Blocking.* While W ∈ {Q,(0,2),C}, no move sequence leads from {back segment, Q, N} to the forward part
beyond C. This follows from Lemma 2.2. The diagonals (-1,1)→(0,2) (corners Q, (-1,2) stone) and
(0,2)→(1,3) (corners C, (1,2) stone) are refused while W sits on the respective corner. □
(d) *Trapped segment.* After closing, the hero can step from N into Q only by pushing W down. He then reaches Q
and the back segment, but the back segment ends at the q-side of a one-way door (G_D), which cannot be opened
from that side (Lemma 3.3). So this region is a dead end: it touches no hub, no crossover and no other P cell.
*Correction (2026-10-29, §4.7):* this holds while σ's door is closed. After the door has been opened from its e side and W has left N and Q, Z_σ links σ's entry segment to N and P; both ends were visited already, so Claim A is unaffected.
(e) *Open σ.* If W was never pushed into Q, a hero standing on Q (arriving through the back segment) walks
Q→(0,2)→C→ forward. He may also push W up into T and enter P. That is a K→P move; §5.2 shows it is harmless.

### 3.3 G_D: one-way door on σ (entry side e, exit side q)

```
 x:  -2 -1  0  1  2  3
y=-1: #  #  #  #  #  #
y= 0: .  .  e  0  P  #      e=(0,0); X=(1,0) holds door boulder Kd; pocket P=(2,0)
y= 1: #  #  #  q  #  #      q=(1,1), continues down
y= 2: #  #  #  .  #  #
```
**Lemma 3.3.** The q-side becomes reachable from the e-side only after the hero, standing on e, pushes Kd into
P. From the q-side, Kd can never be moved and X cannot be passed.
Proof: from e, push right into P (free) works. From q, push up into (1,-1) (stone) fails. P's only floor
neighbour is X, so the hero cannot stand on P while Kd is on X. Diagonals q→e (corners X, (0,1) stone) and
q→P (corners X, (2,1) stone) are refused. □

### 3.4 G_S clause path σ and G_K clause gadget

σ = entry part E_σ (starts at the split junction of hub H_j; **crossovers allowed here**) → G_D (e-side first) →
back segment B_σ (no crossovers, a few cells) → Q_σ of a G_C → forward part F_σ (Q+d, C, then on to the merge
junction of hub H_{j+1}; no crossovers).

G_K for clause C_j = (ℓ1 ∨ ℓ2 ∨ ℓ3), for a positive clause (spikes arrive from below). Three horizontal paths
at rows r1 > r2 > r3 (σ1 lowest), all from split junction H_j on the left to merge junction H_{j+1} on the right.
The spike of the leg at x-position a < b < c must reach the Q of a different path. Assign σ1 ↔ leg c,
σ2 ↔ leg b, σ3 ↔ leg a. Put D_k and Q_k at the x-position of their own leg.
- The spike to Q3 (x=a) crosses σ1 and σ2 at x=a. Both are still in their entry parts there, since a < b < c,
  and their doors sit at b and c.
- The spike to Q2 crosses σ1 at x=b < c, also in its entry part.
- The spike to Q1 crosses nothing.
- All these are K-over-P crossings, built with G_X (§3.5).

*(Placement superseded by §4.3-4.4: leg k, counted left to right, gets the k-th path from the outside; forward parts merge on one forward row.)* Forward parts leave Q_k upward (2 cells), then go right on their own row band. Row spacing ≥ 6 keeps every pair
of distinct paths ≥ 2 cells apart. Negative clauses: mirror image. Two-literal clauses: two paths.

**Clause semantics (from Lemmas 3.2 and 3.3).** C_j is passable from H_j to H_{j+1} through σ_k iff σ_k is not
closed, i.e. its literal's falsifying branch has not pushed W_k into Q_k.

### 3.5 G_X: crossover, K over P (one-shot for K, unlimited for P)

K runs top to bottom, P left to right. K arrives from the left on row -2 and turns down at n2.

```
 x:  -3 -2 -1  0  1  2  3
y=-3: #  #  #  #  #  #  #
y=-2: #  .  .  0  .  #  #      K in (-2,-2),(-1,-2); n2=(0,-2) holds δ; pocket p=(1,-2)
y=-1: #  #  #  0  #  #  #      n1=(0,-1) holds token τ
y= 0: .  .  .  S  .  .  .      P row; S=(0,0) is a P cell
y= 1: #  #  #  ^  #  #  #      s1=(0,1) hole
y= 2: #  #  #  .  #  #  #      s2=(0,2); K continues down
```
**Lemma 3.5.**
(a) *P cannot enter K before a K pass.* Until the hero has stood on (-1,-2), the cells n2, n1, p, s1 and everything
below s1 are unreachable from the P row, and no boulder can be put into s1. From S: pushing τ up fails (δ is
behind it); stepping down is a hole (loss). The diagonals from S to (±1,±1) hit stone. From (±1,0), the
diagonal into n1 is a boulder cell (no diagonal pushes), and the diagonal into s1 is the hole itself.
P-row boulders move only along the row (F2: no diagonal push; a vertical push needs the hero on n1 or s1).
δ moves only right, from (-1,-2). Pushing it down needs the hero at (0,-3), stone. Pushing it left needs the
hero on p, which is only reachable through n2. Pushing it up needs the hero on n1, which holds τ. τ moves
only vertically, and moving it down needs the hero on n2. □
(b) *K passes once.* From (-1,-2): push δ into p, step to n2; push τ down to S, step to n1; push τ down into s1,
which plugs the hole [src hack.c:544-566]; the hero steps to S, then s1 (now floor), then s2. Each crossover
holds exactly one token, used here.
(c) *No upward K pass.* From s2 the hole s1 blocks. After plugging, s1 is plain floor. But by (a)/(b) that only
happens after the K pass from above.
(d) *After a K pass,* S joins P and K. §5.2 shows this only lets P re-enter K parts the hero has already
legitimately reached.
(e) Rule R holds: s1 sits in a vertical 1-wide corridor whose side cells (±1,1) are stone.

---

## 4. Global construction (replaces the 2026-10-28 sketch; 2026-10-29)

Everything in this section is implemented verbatim by `tools/gen_on_instance.py` (function `Layout`), which
asserts every disjointness claim below while it builds a level, and is exercised on all 513 small instances by
`tools/check_small.py` (§4.7). Notation: `depth` counts tile rows away from the main line (positive side upward,
negative side downward); "out" = away from the main line, "in" = towards it.

### 4.1 Source problem: what is assumed about PMR-3SAT

Assumptions used. They match the definition recorded in `proofs/citations.md` R2-1 (PARTIAL: de Berg–Khosravi's
full text not read; definition from secondary restatements, drawing part of the input). These are the only
properties used, so any definition implying them works:
- **(P1)** Variables x_1..x_n in this left-to-right order on a horizontal line. A clause is a set of 1 to 3
  distinct variables with one sign (all-positive or all-negative). Allowing 1- and 2-literal clauses only
  enlarges the class, so hardness of the exactly-3 version suffices.
- **(P2)** The instance comes with its rectilinear drawing, used only combinatorially: for each side
  (positive = above, negative = below) the left-to-right order of the *legs* (clause occurrences) along the
  variable line. Legs are sorted by variable index (a leg attaches to its variable's segment); the legs of one
  variable may be in any order.
- **(P3) Planarity:** on each side the partition of the leg sequence into clauses is *non-crossing*: there are
  no legs a < b < c < d with a, c in clause X and b, d in clause Y ≠ X. This is exactly the condition for the
  E-shapes (vertical legs, horizontal bar at a height = nesting level) to be drawable without crossings [conj,
  elementary: laminar intervals with no leg of the outer clause inside the inner one].
- **(P4)** [ext T1] Planar Monotone Rectilinear 3-SAT with (P1)-(P3) is NP-complete (de Berg–Khosravi 2010/2012;
  the drawing is part of the input and has polynomial size).

Derived structure (all poly time). For a side s: clause Y is a *child* of X if Y's legs all lie in one gap
between two consecutive legs of X and X is the innermost such clause; roots are clauses with no parent. By (P3)
this is a forest, and siblings occupy disjoint leg intervals. *Level* ℓ(X) = 1 + max ℓ(children), leaves have
ℓ = 1, so ℓ ≤ m_s (number of clauses on side s). *Pre-order*: roots left to right, each node before its
children, children left to right. `gen_on_instance.py` first deletes variables that occur in no clause (renumbering
the rest in order; satisfiability and planarity are unchanged), then takes the leg order from the input, or
(small inputs) picks by brute force the non-crossing order with the least nesting (sum of levels, then maximum
level), clauses sorted canonically.

### 4.2 Tiles and Lemma 4.1 (isolation)

The map is a grid of T×T **tiles**, T = 11; tile (c, r) is the cell square [11c, 11c+10] × [11r, 11r+10]. A
tile's **ports** are the side midpoints N=(5,0), E=(10,5), S=(5,10), W=(0,5) (tile-local coordinates). Every
tile pattern is stone (`#`) on its border ring except at the ports its corridors use. Patterns, positive-side
orientation (`0` boulder, `^` hole, `p` pocket, `k` K-in cell next to n2, S/T/Q/C/e as in §3):

```
   X  (G_X §3.5)   Cl (G_C §3.2)   door (G_D §3.3)  straight wire    junction (W,N,S)
   #####.#####     #####.#####     #####.#####     ###########      #####.#####
   #####...###     #####...###     #####.#####     ###########      #####.#####
   #######.###     #######.###     #####.#####     ###########      #####.#####
   #####...###     #####C..###     #####.#####     ##.......##      #####.#####
   ###p#.#####     #####.#####     #####e#####     ##.#####.##      #####.#####
   ..#00S^....     .....Q##...     #####0.....     ...#####...      ......#####
   #.#k#.#####     #####0...##     #####p#####     ###########      #####.#####
   #.#.#...###     #####T#####     ###########     ###########      #####.#####
   #...###.###     #####.#####     ###########     ###########      #####.#####
   #####...###     #####.#####     ###########     ###########      #####.#####
   #####.#####     #####.#####     ###########     ###########      #####.#####
```
- **X** = G_X rotated: K enters W, pushes δ (on n2=(3,5)) into p=(3,4) from k=(3,6), pushes τ (n1=(4,5)) through
  S=(5,5) into the hole s1=(6,5), leaves E. P runs N–S through S. Used in the 8 dihedral images that make K run
  in the needed direction (K W→E: identity; E→W: horizontal mirror; S→N on the main line: rotation).
- **Cl** = G_C mirrored for a positive clause: K back segment enters W → Q=(5,5) → (5,4) → C=(5,3) → leaves N;
  P T-lane enters S → T=(5,7) → N=(5,6) holding W → U-turn leaves E.
- **door** = G_D: K enters N → e=(5,4) → X=(5,5) holding Kd (pocket (5,6)) → q=(6,5) → leaves E.
- **wire**: corridors from the centre to each used port; a *straight* wire (two opposite ports) is the S-bend
  shown, with corners (2,5),(2,3),(8,3),(8,5) [rotated for N–S].
- **start** (s0 at the centre, port E), **goal** (g at the centre, one port), **sentinel** (centre = the pit,
  no ports, 8 stone neighbours).
- Negative side: every pattern is mirrored vertically (y ↦ 10 − y). All lemmas of §2-§3 are invariant under
  the dihedral group (§2), so the mirrored gadgets have the same behaviour.

Differences from the witnessed gadget maps, and why they do not matter: (i) G_C's P U-turn leaves N's row east
and climbs one row to the E port, and its forward part bends twice to reach the N port; (ii) G_X's P line bends
east at distance ≥ 2 from S (rows 0-3 and 7-10). In both, the 8-neighbourhood of every K cell, of S, N, T and of
the U-turn cell (6,6) is exactly the proved map, and the proofs of Lemmas 3.2 and 3.5 only inspect those
neighbourhoods [conj, checked by hand cell by cell; the global behaviour is also checked by §4.7]. The S-bends
are new; their purpose is Lemma 2.2 applied to stray boulders: a boulder pushed into a straight wire through a
port is stuck at a corner within 2 cells, so stray boulders never travel along wires (this keeps the abstract
state space small for the checker; the proof does not need it).

**Lemma 4.1 (isolation).** Two floor cells in different tiles are 8-adjacent only if they are a matching pair
of ports (E port of one tile and W port of its right neighbour, or S/N), and such a pair exists only where the
router (§4.4) connected the two tiles. Consequently no diagonal step ever crosses a tile boundary, independent
of the Sokoban corner rule, and the only interfaces between gadgets are their ports.
*Proof.* Every floor cell of a tile other than its ports lies strictly inside the border ring (checked on each
pattern above), and cells of different tiles that are 8-adjacent both lie on border rings, hence are ports. Ports sit at side midpoints, so
two ports of different tiles are 8-adjacent only when they face each other across a shared side, i.e. are
orthogonally adjacent; corner cells of rings are always stone. A tile gets a port on a side only when a route
continues into the neighbour, and the neighbour then gets the facing port. □ The generator re-checks this on
every cell (`check_separation`) [auto-experimentally verified, 513 instances].
*Minimum separation:* inside a tile, two corridor cells of different gadget parts are at Chebyshev distance ≥ 2
except at the designed interfaces of §3 (N–Q, (6,6)–Q diagonal, back–N diagonal, back–(5,4) diagonal in G_C;
S–n1, S–s1 and the P-line diagonals to n1/s1 in G_X; e–q diagonal and pocket–q diagonal in G_D). Distance ≥ 2
means no 8-adjacency, hence no move of any kind (step, diagonal step, push) between them.

### 4.3 Coordinates

Constants: T = 11, port offset 5, Λ = 7 tile rows per clause level. For side s ∈ {+, −} let
ℓ_s = max level on s (0 if s has no clauses) and D_s = Λ·ℓ_s + 3 (D_s = 0 if empty).
- **Rows.** Main-line tile row R_M = max(D_+, 2). A side-s object at depth δ sits in tile row R_M − δ (s = +) or
  R_M + δ (s = −). Grid height H_t = R_M + max(D_−, 1) + 1 tiles.
- **Clause X on side s, level ℓ, legs 1..L left to right:** Q row of leg k at depth q_k = 1 + Λℓ − 2(k−1);
  forward (top) row f = Λℓ + 2; entry row of leg k at depth q_k + 1 (so the entry row of leg 1 is f); hub column
  from depth f to q_L + 1; dive row d = q_L − 1. So X occupies depths [q_L − 1, f] ⊆ [Λℓ − 4, Λℓ + 2].
- **Columns (token sweep).** For each side, tok(X) = a(X), hL(X), leg(X,1), tok(children in gap 1), leg(X,2),
  tok(children in gap 2), …, leg(X,L), hR(X); the side's sequence is tok(r_1) tok(r_2)… over the roots. Widths:
  a, hL, hR one column each, a leg three columns (door column p, T-lane u = p+1, return lane u+1). Cursor x := 1
  (column 0 holds the start). For i = 1..n: on each side place (left to right, from x) the tokens before the
  first leg of x_i; fork_i := max of the two side cursors; x := fork_i + 1; on each side place all tokens up to
  and including the last leg of x_i; join_i := max of the two cursors; x := join_i + 1. Then place the remaining
  tokens. goal column := final + cursor; x_c := max(final + cursor + 1, final − cursor, x); x_E := x_c + 1;
  grid width W_t = x_E + 1. Along each side's sequence columns strictly increase, so tok(X) occupies a column
  interval I(X); children's intervals lie strictly between consecutive leg columns of X; siblings' intervals
  are disjoint; every leg of x_i has fork_i < u < u+1 < join_i.
- **Fixed tiles:** start (0, R_M); sentinel (0, depth 2 on +); main-line crossover (x_c, R_M).

### 4.4 Routes

A route is an axis-parallel polyline of tiles; consecutive tiles get facing ports. Classes P and K.
- **P main line:** (0,R_M) → (fork_1,R_M); (join_i,R_M) → (fork_{i+1},R_M); (join_n,R_M) → (x_E,R_M).
  fork/join tiles are junctions.
- **P branch of x_i on side s** (s = + is F_i, "x_i false"; s = − is T_i): (fork_i, 0) → (fork_i, 1) → for each
  leg (X,k) of x_i on s in column order: (u,1) → (u,q_k) [Cl tile] → (u+1,q_k) → (u+1,1) → … → (join_i,1) →
  (join_i,0) (depths). The T-lane column u is entered first (the branch runs left to right), as Lemma 3.2(a)
  requires; between u and u+1 the branch row is not connected (both are corner tiles).
- **K inside clause X:** hub column (hL, f)→(hL, q_L+1); for each k: entry (hL, q_k+1) → (u_k−1, q_k+1) →
  door (u_k−1, q_k) → Cl (u_k, q_k) → forward (u_k, f); forward row (u_1, f) → (hR, f). Junction tiles: (hL, ·)
  on the hub column, (u_k, f), (hR, f). Path σ_k = hub → entry_k → door_k → back segment (door E port to Cl W
  port) → Q_k → forward_k → forward row.
- **K chain:** clauses in the order C_1..C_m = negative pre-order, then positive pre-order. Arc into C_1 from
  the main-line end, arcs between consecutive clauses (from (hR, f) of the previous one to (hL, f) of the next),
  and a final arc to the goal:
  - *start:* (x_E, R_M) → if negative clauses exist: (x_E, D_−) → (a(r), D_−) → (a(r), f(r)) → (hL(r), f(r)),
    r the first negative root; else (x_E, 1_−) → (x_c, 1_−) → upward through (x_c, R_M).
  - *dive* (next = first child C of prev P): (hR(P), f(P)) → (hR(P), d(P)) → (a(C), d(P)) → (a(C), f(C)) →
    (hL(C), f(C)).
  - *step* (same side, otherwise; prev Z is then a leaf): (hR(Z), f(Z)) → (a(N), f(Z)) → (a(N), f(N)) →
    (hL(N), f(N)).
  - *switch* (last negative clause Z to the positive side or goal): (hR(Z), f(Z)) → (x_c, f(Z)) → north through
    the main-line crossover (x_c, R_M) → (x_c, D_+) → (a(r), D_+) → (a(r), f(r)) → (hL(r), f(r)) for the first
    positive root r; if there is no positive clause, end at the goal tile (x_c, 1_+).
  - *end:* (hR(Z), f(Z)) → (goal column, f(Z)) for the last positive clause Z.
- **Crossovers:** a tile used by one straight K run and one straight perpendicular P run becomes an X tile,
  oriented so K enters from the side it arrives on. Every other shared tile is a designed junction; anything
  else is an error (the generator asserts it).

### 4.5 Lemma 4.2 (planarity) and the crossover count

**Lemma 4.2.** (a) P routes never share a tile except at fork/join junctions; (b) K routes never share a tile
except at the junctions listed in §4.4; (c) every P–K shared tile is a straight K run crossing a straight P lane
or the main line perpendicularly, away from both runs' corners; (d) the only P–K crossings are: P lanes of leg
(X,k) with the entry rows of legs k' > k of X, with the dive row of X, and with step/switch runs at depth f = 9
leaving X's subtree or crossing a gap of X; and the main line with the switch at (x_c, R_M).
*Proof [conj, routine; every case is also asserted by the generator].* Bands: X uses depths ⊆ [Λℓ−4, Λℓ+2]; a
child C has ℓ(C) ≤ ℓ − 1, so f(C) ≤ Λℓ − 5 < d(X) = q_L − 1: every descendant lies strictly inward of X's dive
row. Columns: I(C) ⊂ (u_k+1, u_{k+1}−1) for a child in gap k; siblings disjoint (§4.3).
(a) P lanes of leg (X,k) are at columns u, u+1 (unique tokens) between depth 1 and q_k; branch rows are depth
1 and run between fork_i and join_i, disjoint for different i; main line is depth 0.
(b) Within X: entry rows at depths q_k+1 run from hL to u_k−1 < u_{k+1}−1, forward verticals at u_k rise from
q_k+1 to f, and since q_{k'}+1 < q_k+1 for k' > k the entry of leg k' passes below forward_k's start and ends
before column u_{k'}; the hub column is the unique column hL. Arcs: the dive of P uses column hR(P) (unique),
depth d(P) (no clause band touches depth d(P) inside I(P): children are inward, P's own band starts at q_L), and
column a(C) (unique). A step from leaf Z to N runs at depth 9 over the columns strictly between hR(Z) and a(N):
the tokens there are closing legs and hR's of Z's ancestors and legs of N's parent, never an a/hL, so it meets no
clause band; any dive vertical there (at hR(A), A an ancestor, ℓ(A) ≥ 2) spans depths ≥ d(A) ≥ 10 > 9. Distinct
steps use disjoint column ranges (they are consecutive pieces of the token order). Vertical pieces at a(N) or
a(C) stop at f(N) < d(parent), so they meet no ancestor dive row. The start/switch/end connectors run at depth
D_s (outward of all bands), at columns x_c, x_E (right of all tokens) or at depth 9 to the right of the last
clause, and the switch vertical (depths 0..9 on −) is left of the start vertical (x_E).
(c) K horizontal pieces have their corners only at token columns hL, u−1, hR, a, x_c, x_E, goal; P lanes are at
leg columns u, u+1 (other tokens), and lanes are straight between their turns at depth 1 (where K runs only at
columns ≥ x_c, right of every join) and at their Cl/B tiles (depth q_k, special tiles whose ports are fixed). The main line is crossed only at x_c by the straight switch vertical.
(d) A lane of (X,k) spans depths [2, q_k − 1]; the K pieces at those depths over column u are exactly the listed
ones (ancestors are outward of X, non-ancestor clauses have disjoint column intervals, and the arcs between them
cross I(X) only as steps/switch at depth 9 or as X's own dive). □

**Counts.** Let L_s ≤ 3m_s be the legs on side s, L = L_+ + L_−, so L ≤ 3m. Each leg has 2 lanes; a lane meets
≤ 2 entry rows, ≤ 1 dive row and ≤ (number of step/switch runs) ≤ m + 1 depth-9 runs. Hence
#X ≤ 1 + 2L(m + 4) ≤ 6m² + 24m + 1 = O(m²).

### 4.6 Size bounds (explicit polynomials in n, m)

- Tiles: W_t ≤ 12m + 2n + 4 (tokens of both sides ≤ 3m + 9m, plus fork/join slack 2n, start, x_c, x_E, goal);
  H_t ≤ 7m + 7 (two sides of ≤ 7ℓ_s + 3 rows, ℓ_+ + ℓ_− ≤ m, plus main line and margins).
- Map: w = 11·W_t ≤ 132m + 22n + 44, h = 11·H_t ≤ 77m + 77.
- Floor cells F ≤ 37·W_t·H_t (the X tile has the most floor, 37 cells).
- Boulders: one W per closing site, one Kd per door, two per crossover: #boulders = 2L + 2·#X ≤ 12m² + 54m + 2.
  Holes: #X. Sentinel pits: 1. Fortune cookies: one per floor cell except holes and the pit: F − #X − 1.
- Intended play (§5.1) length: every cell is entered at most twice (only crossover centres S are re-entered,
  see §5.1), so N_moves ≤ 2F + 2·(#cookies eaten) ≤ 4F ≤ 148·W_t·H_t turns.
- Lua script: 13 + #boulders + #X + F lines (one `des.object` per boulder and per cookie, one `des.trap` per hole).
All are polynomial; the generator runs in time O(F + leg-order search), the search being linear when the drawing
is given.

### 4.7 Generator and brute-force checker (results)

`tools/gen_on_instance.py instance.json -o level.lua --moves moves.txt` writes the Lua level (whitelist of
phase2-spec incl. Rev. 1-2: `nh.debug_flags{mongen=false}`, `u.clear_inventory()`, flags noflip/sokoban/
noteleport, solidfill, one `des.map`, `des.non_diggable/non_passwall`, one `des.object` per boulder and per
uncursed fortune cookie, `des.trap` holes + sentinel pit, one-cell `des.teleport_region` with `dir="both"`,
`u.giveobj(cursed loadstone)`), and the intended move string (vi-keys, `E` = eat the cookie here). The smallest
instances are 132×132 or 121×143 cells, so the stock 80×21 build cannot load any of them (expected: the language
lifts COLNO/ROWNO); no generated level was loaded in the game.

`tools/check_small.py` enumerates every monotone instance with n ≤ 3 variables and 1 ≤ m ≤ 3 distinct clauses of
1-3 literals: 513 instances, all of which satisfy (P3) (with n ≤ 3 every monotone set has a non-crossing leg
order), 455 satisfiable and 58 unsatisfiable. After deleting unused variables they give 393 distinct levels
(370 satisfiable, 23 unsatisfiable); every one of the 513 instances is mapped by the generator to one of these
levels, so checking the 393 levels covers all 513. For each level:
- **satisfiable:** replays the generator's intended play in the exact model of §2 (every step and push checked
  against F1-F4, hole entry = loss); it must end on g with hunger ≥ 150 throughout;
- **unsatisfiable:** exhaustive BFS over (hero position, boulder set, unplugged-hole set) under the same rules;
  g must be unreachable. The BFS works on a compressed graph (static floor components + every cell a boulder or
  hole can ever occupy); diagonal steps are kept with their corner condition, so no rule of §2 is abstracted
  away.
**Results (run 2026-10-29, `python tools/check_small.py --workers 11`, Windows, 12-core CPU, Python 3.14;
37 min wall, 11 workers, < 2 GB total memory; the 10-minute target was not met because exhaustive search of the larger unsatisfiable levels is inherently slow in Python):**

| Check | Result |
|---|---|
| levels built (generator asserts Lemma 4.1 isolation and Lemma 4.2 overlap rules on every tile) | 393/393 distinct levels (covering all 513 instances), no assertion failure |
| satisfiable levels: intended play replayed in the exact model reaches g | 370/370 levels (all 455 satisfiable instances) |
| hunger along the intended play (start 900, −1 per move, eat ≤ 860, 2 turns per meal) | min 859 (never Hungry); ≤ 2 visits per cell; longest cookie-less run 2 |
| satisfiable levels: exhaustive BFS finds g (sanity check of the search, 20 smallest) | 20/20 |
| unsatisfiable levels: exhaustive BFS, no pruning, g unreachable | 16/23 (Python), +2 with fastbfs (review-4 §5): **18/23**; 5 largest open (> 26-35 M states, g not reached) |
| largest exhaustive search | 734,784 states (BFS states = boulder set × unplugged holes × hero free region) |
| largest level / most crossovers / longest intended play | 440×286 cells / 23 / 4,241 moves |
| mismatches (reach ≠ sat) | 0 (no level where g is reachable but φ is unsatisfiable, or vice versa) |

Not covered: levels were never loaded in the real game (they exceed 80×21); the exhaustive part covers n, m ≤ 3
only (larger instances: layout + replay only, below).
- **Layout stress test (beyond n, m ≤ 3):** 767 random planar monotone instances with 2 ≤ n ≤ 6, 1 ≤ m ≤ 6 (seed 7,
  4 minutes): every level built with all Lemma 4.1/4.2 assertions holding, within the §4.6 bounds on w, h and #X
  (max 41 crossovers), and every satisfiable one won by the replayed intended play with ≤ 2 visits per cell
  [auto-experimentally verified; no exhaustive search at that size].

**Update (review-4, 2026-10-29).** `tools/fastbfs/` (Rust) runs the same exact search on models exported by
`check_small.py --only ... --export DIR`; validated by reproducing the exact state counts of all 36 earlier BFS
levels. [2][-2][1,3]: unreachable, 1,175,464 states; [2][-2][-1,-3]: unreachable, 2,139,544 states. Open (exceed
~35 M states within the memory available): [3][-3][1,2,3], [1][-1][-1,-2,-3], [3][-3][-1,-2,-3], [2][-2][1,2,3],
[2][-2][-1,-2,-3]. Rev. 3 pocket: the generator now emits the sealed branch-stair pocket + `des.levregion`
(sentinel tile, local (2,2)); cookies = F − #X − 2; replay re-run 370/370. Layout stress test extended: 660 random
instances, m ≤ 46, nesting ≤ 5, all assertions and §4.6 bounds hold, 379 satisfiable replays won.

**No pruning.** A tempting rule ("never push a closing-site W from Q further into Z_σ; W on Q dominates") is
**false**: once σ's door has been opened from its e side, W beyond Q leaves Q free, and Z_σ then links the entry
segment of σ (via door, back segment, Q) to N_σ and P, a link that W on Q blocks. This also corrects the wording of
Lemma 3.2(d): Z_σ is a dead end only while σ's door is closed; after the door was opened from e it is a K↔P link
between two already visited regions, which Claim A (§5.2) allows. The BFS therefore uses no pruning at all.

## 5. Correctness (restated for the §4 layout, 2026-10-29)

### 5.1 Completeness (φ satisfiable ⇒ YES, under every RNG outcome)
Let α satisfy φ. The explicit play (`intended_play` in `gen_on_instance.py`; "walk to c" = a shortest legal walk
without pushes, which exists by the remark in brackets):
1. **P phase.** For i = 1..n: at fork_i take T_i (negative side) if α(x_i) = true, else F_i. For each leg on the
   chosen branch, in column order: walk up the T-lane to T, push W from N into Q (Q is free: no K cell has been
   visited), continue through the U-turn and down the return lane. [Lanes pass crossovers only through S, which
   is free because every τ is still on its n1.] Walk to join_i. Only paths of literals false under α get closed.
2. **Main line → K.** Walk east along the main line, through S of the main-line crossover, to x_E.
3. **K phase.** Follow the K chain C_1, …, C_m. In C_j pick the first leg k whose literal is true under α; its
   closing site lies on the branch not taken, so W_k is still on N_k. At every crossover on the route: walk to k,
   push δ into p, push τ to S, push τ into s1 (plugs it); the hero ends on S (Lemma 3.5(b)). At the door: walk to
   e, push Kd into the pocket (Lemma 3.3). At Cl: back segment → Q → (5,4) → C → forward. The route is a simple
   path, so each crossover on it is used once.
4. Walk to g.

Every cell is entered at most twice: only a crossover centre S (P phase, then K pass) is re-entered, and the
re-entries are isolated (the K pass enters S from n1 and leaves to the plugged s1, then fresh cells).
[auto-experimentally verified: `max_visits = 2` on all 370 satisfiable levels.] No step depends on the RNG:
pushes, plugging and hunger are deterministic, and eating a fortune cookie only prints a random text.
**Food.** u.uhunger starts at 900 and drops by exactly 1 per move (unencumbered, no rings/amulets/Regeneration,
speed 12 ⇒ one move per turn; §1.3). Policy: on entering a cell that still holds a cookie, eat it iff
u.uhunger ≤ 860 (+40, at most 2 turns). At most two moves in a row end on a cell without a cookie (a re-entered
crossover centre S whose cookie was eaten in the P phase, then the plugged hole s1, which never had one), so
u.uhunger stays in [860 − 3, 900]: never Hungry, never Satiated, no fainting, Rule S never triggers.
[auto-experimentally verified on all 370 satisfiable levels, eating modelled as 2 turns: minimum 859, longest
cookie-less run 2, longest play 4,241 moves.] Length ≤ 4F turns (§4.6).

### 5.2 Soundness (NO ⇒ no play reaches g, for every RNG outcome)

Cell classes: **P** = start, main line up to x_E, forks, branches, lanes, U-turns, T and N cells, and the P
line of every crossover including S. **K** = every other floor cell except the sentinel. For a path σ (leg
(X,k)): **Z_σ** = Q_σ, (5,4)_σ, C_σ, the back segment and the q-side of its door (door X cell, pocket).

**Gates.** (i) every crossover (passage n2 → n1 → S → s1, opened by pushing δ off n2 from k, Lemma 3.5);
(ii) every door (e → X, opened by pushing Kd off X from e, Lemma 3.3); (iii) every forward exit of a closing
site, from {(5,4)_σ, C_σ} to the first forward cell beyond C_σ (Lemma 3.2(c)). **Segments** = connected
components of K ∖ (gate cells ∪ ⋃Z_σ). By Lemma 4.1 and §4.4 they are: the start segment K_0 (main-line end up
to the first crossover or the first hub), pieces of arcs and entry rows between consecutive crossovers, and for
each clause C_j its *hub segment* H_j (left hub plus the starts of all entry rows) and its *exit segment* E_j
(forward parts beyond every C_σ, the forward row, the outgoing arc up to its first crossover; E_j and H_{j+1}
coincide when that arc has no crossover). Each gate has one **upstream** part (the k side of a crossover, the e
side of a door, Z_σ for a forward exit) and one **downstream** segment. By the routing of §4.4 these form a
single chain K_0 → … → H_1 → (for each σ ∈ C_1, in parallel: entry pieces → door → Z_σ → forward exit) → E_1 →
… → E_m ∋ g; write ≺ for its order.

**Claim A (reworded per review-2: gates open in order).** For every segment Y ≠ K_0 and every Z_σ:
(a) no cell of Y is entered before the gate whose downstream is Y has been opened (crossover: δ pushed off n2;
door: Kd pushed off X);
(b) that opening push is made by the hero standing on a cell upstream (k, resp. e); so the hero stood on the
preceding segment before Y was first entered;
(c) if Y = E_j, then Y is first entered from Z_σ for some σ ∈ C_j that is *not closed* at that moment
(closed = W_σ has ever entered Q_σ), and the hero's first entry into that Z_σ was through the door of σ.
Review-2's point stands: the first entry into Y may come from S of a crossover after its K pass, or (for Z_σ)
from P through N_σ; the claim does not say through which cell Y is entered, only that the gate was opened from
upstream first, which is all that §5.2 uses.
*Proof.* By Lemma 4.1 a segment touches the rest of the map only at its gates, at S cells of its own crossovers
and, for exit segments, at the forward cells beyond C_σ. (a)+(b), crossover: until δ leaves n2, the cells n2, n1,
p, s1 and the downstream segment are unreachable from S and from upstream except through k, and δ moves only
into p by a push from k (Lemma 3.5(a)). Door: Kd moves only into the pocket by a push from e (Lemma 3.3).
(c) The cells of E_j adjacent to non-E_j cells are the first forward cell beyond each C_σ (neighbours C_σ and,
diagonally, (5,4)_σ), the k sides of crossovers on its outgoing arc (gates whose *upstream* is E_j), and S cells
of crossovers on that arc (passable only after a K pass started on E_j). So the first entry into E_j comes from
C_σ or (5,4)_σ for some σ ∈ C_j. If σ was closed, then W_σ ∈ {Q, (5,4), C} from the closing until the hero has
stood beyond W on E_j (Lemma 3.2(b)), which has not happened yet, and in each of these positions no move
sequence from Q_σ, the back segment or N_σ reaches the forward part beyond C_σ (Lemma 3.2(c); with W on C the
cell (5,4) is reachable but its diagonal to the forward cell has corners C (boulder) and stone). So σ is not
closed. The only access to Z_σ other than the door is from N_σ (orthogonally into Q_σ, or diagonally between
the U-turn cell and Q_σ or between N_σ and the back segment); it needs N_σ or Q_σ free of W, i.e. W pushed into
Q_σ (σ closed, and closed stays closed) or W pushed from N_σ into T_σ by a hero already on Q_σ. So the first
entry into Z_σ, for a σ never closed, is through the door. □

**Claim B (assignment at t_1).** Let t_1 be the first time the hero stands on K_0. Before t_1 the hero has
only been on P ∪ ⋃Z_σ: every other K cell lies in a segment Y ≠ K_0, and by Claim A(b) iterated along ≺ the
hero would have stood on K_0 earlier; Z_σ is reachable before t_1 only from N_σ, i.e. after σ was closed.
Each Z_σ is a dead end attached to P only at N_σ while its door is closed (Lemma 3.2(d), corrected in §4.7),
and doors are closed before t_1 (Claim A), so the P part of the walk is a walk in the P
graph: the main line plus, for each x_i, the two branches F_i, T_i, each a single path fork_i → join_i that goes
up and down every spike of its legs (§4.4). The main-line end x_E is reachable from s0 only through every
fork_i → join_i; a branch is passed fork → join only by passing each spike's T-lane first, which pushes W into
Q (Lemma 3.2(a)); a spike entered from the join side is blocked at the U-turn (push of W into stone; both
diagonals have corners N (boulder) and stone). Define α(x_i) = false if F_i was passed fork → join before t_1,
else true (then T_i was). Every σ whose literal is false under α was closed before t_1. □

**Conclusion.** Suppose g ∈ E_m is reached. For every j, E_j is entered for the first time at some time τ_j,
from Z_{σ_j} with σ_j ∈ C_j not closed at τ_j (Claim A(c)). The hero entered Z_{σ_j} through its door, after
standing on the entry segment of σ_j, hence (Claim A(b) along ≺) after t_1; so τ_j > t_1. Closing is a past
event, so σ_j was not closed before t_1 either, and by Claim B its literal is true under α. Hence α satisfies
every clause. K → P moves (through S after a K pass, or Q → N → T after pushing W down) only let the hero walk P
and close more paths; they cannot open a gate from the wrong side (Claim A holds for all plays) and cannot
change α, which is fixed at t_1. □

[auto-experimentally verified, partially: exhaustive search of the exact model of §2 finds g unreachable on 16 of
the 23 distinct unsatisfiable levels with n, m ≤ 3; the other 7 timed out without reaching g; §4.7.]

### 5.3 Answer-level DET
Unchanged: YES via §5.1 under every RNG outcome; NO via §5.2, which uses only the deterministic rules F1-F4;
§6 shows no random action adds boulder or hero motion. The checker of §4.7 models exactly F1-F4.

---

## 6. RNG-dependent actions available to the hero (why none helps)
- **#pray** [conj, source-backed by review-1 X3 and the repairs]. Luck 0 off an altar gives action ≤ 2, so only
  major troubles are fixed and the cursed loadstone stays cursed [src pray.c:1116-1146]. Major troubles that can
  occur: hunger (helps only YES), low HP (no damage sources), STUCK_IN_WALL.
  - STUCK_IN_WALL cannot occur: after any move, the cell left behind is free floor (review L-4). At the start,
    s0 has a free neighbour.
  - "Too soon" prayers → `angrygods`. Its outcomes: summon_minion (blocked by `mongen=false`
    [src makemon.c:1168]); curse items, lose level, lose Wis; zap (death); and **punish** (iron ball and chain).
  - Ball and chain [conj]: the ball is an object, so it cannot plug holes (only boulders do: F1). Throwing it,
    for a hero carrying a 500-weight stone, gives range 1, so it cannot pull him. Ball pulling also runs
    `test_move` per step (review L-2). Dragging only restricts movement.
  - *To verify in dothrow.c:* the range formula and the uball special case; whether `drag_ball` can move the
    hero onto a hole cell without falling.
- **Kicking** boulders is a no-op [src dokick.c:517-519]. Kicking walls only hurts.
- **Eating:** only fortune cookies, which never rot (repair 2); their random text has no effect.
- **Fainting:** never, because the hero is kept Not Hungry. Rule S closes the faint-forever loophole for NO
  instances: starving still loses.
- **Exercise / attributes:** they only change wc. The heavy-hero property holds for any wc ≤ 1000
  (500 > 150, [src hack.c:139-163]).

---

## 7. Notes for the spec and for the PI

1. **Pits are not barriers.** A Sokoban pit traps the hero for rn1(6,2) turns, deals rnd(6) damage, and then he
   climbs out [src trap.c:1920, 1948-1953, 4209-4217]. So pits only cost random time and HP; they are not
   one-use bridges. Holes are barriers only because of the repair "leaving the level = loss" plus A1.
   **Spec change needed:** state A1 explicitly (instance level is not the bottom level and not hardfloor;
   falling through a hole or trapdoor = loss). Otherwise `trapeffect_hole` calls `impossible` and the hole does
   nothing [src trap.c:2019-2023].
2. **Why holes are needed at all [conj].** Without holes (only walls and boulders, heavy hero), every change of
   state happens next to the hero. A K-over-P crossover then seems impossible: a P visitor standing on the
   shared cell S has, on the far side of P, at least the options of a later K traveler on S. The K traveler's
   earlier pushes on the near side can only add boulders to the far side, never remove them. Boulders only block
   in Push-1F, so this argument goes through by a monotonicity lemma: removing a boulder never hurts. That is
   why the token-plus-hole crossover G_X is used.
3. Rule 3 (quantity 1) holds: each boulder is its own `des.object`. The loadstone is given by one
   `u.giveobj`. Cookies are one per cell.
4. Traps used: HOLE (crossovers) and PIT (sentinel) only, both allowed. No fountains, sinks, altars, thrones,
   trees, water or lava.
5. Nothing in the reduction needs `des.region`, doors, stairs, or `nh.*` beyond `mongen=false`.

## 8. Witness scripts (run 2026-10-29: on_close, on_door, on_cross pass in 3 of 3 runs, see claims.md W1-W8)
`tools/witness/on_close.lua` (G_C), `tools/witness/on_door.lua` (G_D), `tools/witness/on_cross.lua` (G_X), in the
style of `src/test/testmove.lua` and the existing `off_*.lua` witnesses (same map-relative coordinate
convention). Each script builds the gadget with `des.map`, sets
`sokoban` plus a sentinel pit, gives the cursed loadstone, plays the intended keys and asserts hero positions,
and checks at least one forbidden move. The harness API (`obj.new` string form, `des.trap` signature) should be
checked when Ivan is off the laptop.
They use `nh.debug_flags({hunger=false})` only to keep the tests short; the instances themselves do not.
