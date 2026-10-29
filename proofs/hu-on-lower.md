# L_ON lower bound: NP-hardness of generalized NetHack reachability with faithful hunger

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
| Planar layout without P×P / K×K crossings (§4) | [ext] T1 + routing argument [conj, routine] |
| Global soundness, completeness, poly size, food (§5) | proved modulo the above |
| RNG / prayer / ball-and-chain cannot help (§6) | prayer part [conj, source-backed] |

**Weakest step:** §6 prayer side effects (Punishment's iron ball as a pull/plug tool; argued harmless, not fully
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

Forward parts leave Q_k upward (2 cells), then go right on their own row band. Row spacing ≥ 6 keeps every pair
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

## 4. Source problem and layout

**[ext T1]** Planar Monotone 3-SAT is NP-complete even when a planar rectilinear drawing is given: variables are
segments on a horizontal line, every clause is all-positive or all-negative, positive clauses are drawn above
the line and negative ones below, as non-crossing E-shapes with vertical legs.
Citation: M. de Berg, A. Khosravi, "Optimal binary space partitions for segments in the plane", IJCGA 22(3)
(2012) 187-205 (COCOON 2010). *Verify the exact statement.* The background for planar 3-SAT is D. Lichtenstein,
SIAM J. Comput. 11 (1982) 329-343; the rectilinear drawing is from D. Knuth, A. Raghunathan, SIAM J. Discrete
Math. 5 (1992) 422-427.

**Why plain Planar 3-SAT (no crossover) cannot work here [conj, proved sketch].** P (start, forks, branches,
spikes) is connected and must not touch K except at closing sites. So P lies inside one face of the K network.
The three paths of a clause form a theta graph, and every face of a theta borders only two of its three paths.
So without P-crossing-K, at most two literals per clause can be closed. Only crossings of K over P are needed,
and §3.5 provides exactly those. P×P and K×K crossings are avoided by the layout below.

**Layout (poly time) [conj, routine].**
1. Scale T1's drawing by a constant (say 40) per unit.
2. The variable line becomes the main line with one G_V per variable segment. F_i runs above the segment and
   T_i below it.
3. Each leg becomes a spike: a down lane and an up lane separated by stone, joined at the top by a G_C.
   Legs do not cross in T1's drawing, and spikes of positive clauses stay above the line, so P is drawn
   without crossings.
4. Each clause's G_K is placed at its bar (§3.4).
5. After Join_n the main line ends in H_1. The K chain H_1 → G_K(C_1) → H_2 → ... → G_K(C_m) → H_{m+1} ∋ g is
   routed through the complement of the clause bands. That complement is connected: the bands are disjoint
   rectangles, and the K drawn so far plus the bands form a tree-like obstacle. Every arc crosses P lines
   perpendicularly, through a G_X placed ≥ 3 cells from any other gadget.
6. Crossovers on clause paths sit only on entry parts (§3.4). Hub arcs may carry any number of them.

Size: the drawing has O((n+m)²) unit cells, so O((n+m)²) cells after scaling. Each K arc is ≤ its area, so the
K length is O((n+m)^4). Crossovers number O((n+m)^4) (each K arc crosses O((n+m)²) P lines). Boulders: one per
G_C, one per G_D, two per G_X. Cookies: one per floor cell. All of this is polynomial, and the Lua script is
straight-line `des.*` calls.

---

## 5. Correctness

### 5.1 Completeness (φ satisfiable ⇒ YES, under every RNG outcome)
Let α satisfy φ. The intended play:
1. Walk the main line. At each G_V take T_i if α(x_i) = true, else F_i. Along the branch, at every closing site
   push W into Q (this is forced and only closes paths of literals false under α), then return down the other
   lane of the spike.
2. At Join_n continue into H_1.
3. For j = 1..m pick σ ∈ C_j whose literal is true under α. Its closer sits on the branch not taken, so
   W_σ is still on N_σ. Walk the entry part, passing each crossover by Lemma 3.5(b). Each crossover is used
   once, because K cells are visited once. Open the door (Lemma 3.3), walk the back segment to Q, then
   Q→(0,2)→C→ forward part → H_{j+1}.
4. Reach g.

Every cell is entered at most twice (only crossover centres S twice), so the length is ≤ 2·#cells + #cookies
eaten: polynomial. Food: §1.3. No step of this play depends on the RNG: pushes are deterministic, hunger costs
1 per turn, and eating a fortune cookie only prints random text. Attribute exercise can only raise Str and Con
(no abuse source occurs), and that only increases wc. HP never drops.

### 5.2 Soundness (NO ⇒ no play reaches g, for every RNG outcome)
Cell classes:
- **P**: start, main line, forks, branches, spikes, closing cells T and N, and the P row of crossovers incl. S.
- **K**: everything else except the sentinel.
- **Trapped region Z_σ** = Q_σ ∪ B_σ ∪ {X, P of D_σ} (the q-side of σ's door).
- **K segments**: maximal parts of K∖⋃Z_σ that do not cross a gate. Gates are the crossover passage n2→s1,
  the doors (e→q), and the forward step Q→Q+d. Segments are linearly ordered along the intended direction:
  H_1's first arc, ..., the entry parts of C_j (one branch per σ, all after H_j), the forward parts of C_j
  together with H_{j+1}'s arc, and so on, ending with the segment containing g.

**Claim A (first entries are in order).** The first time the hero stands on a cell of a segment Z (other than the
first segment, entered from the main-line end at a time we call t_1), he arrives from the segment that
immediately precedes Z through its gate. Moreover, if Z is the forward/hub segment after C_j, he arrives through
Q_σ→Q_σ+d for some σ ∈ C_j that is **not closed** at that moment.

Proof by induction on time, case by case on the cell he comes from:
- From a P cell. The only P–K adjacencies are N–Q (into Z_σ, not a segment), S–n1 and S–s1 (crossovers), and
  main-line end → H_1. Via S: n1 and s1 become enterable only after that crossover's K pass (Lemma 3.5a), and that
  pass started on (-1,-2), a cell of the preceding segment. So S's K-side segments were already visited and this
  is not a first entry. The main line gives only the first segment.
- From a later segment, backwards. A door cannot be passed backwards (Lemma 3.3). A crossover cannot be passed
  upward before its K pass (Lemma 3.5c). A forward part cannot be entered backwards from its hub into a
  never-entered segment: the hub is later in the order.
- From Z_σ into F_σ through Q→Q+d. If σ was closed earlier, W_σ ∈ {Q,(0,2),C} blocks (Lemma 3.2b,c). The
  exception in 3.2(b) needs prior presence beyond W, which is already in F_σ (not a first entry). So σ is not
  closed. Also, the hero's first presence on Q_σ came from B_σ, i.e. through D_σ from the entry segment.
  Coming from N_σ instead needs W off N, which means either "closed" or "W pushed up from Q", and the latter
  needs earlier presence on Q. So the entry segment of σ (after H_j) had already been visited. □

**Claim B (assignment at t_1).** Before t_1 the hero was only in P ∪ ⋃Z_σ (Claim A, plus the fact that Z_σ is a
dead end by Lemma 3.2d). Every Z_σ is a dead end attached at one N, so P's connectivity is just the main line plus
the two branches per variable. By Fact V and Lemma 3.2(a), for each i some branch was traversed in full before
t_1, which closed every σ of the corresponding literal. Define α(x_i) = false if F_i was fully traversed before
t_1, else true. Then every σ whose literal is false under α was closed before t_1. □

**Conclusion.** Suppose g is reached. By Claim A, for every j the hub after C_j was first entered at some time
τ_j > t_1, through some σ_j ∈ C_j not closed at τ_j. A closed σ stays closed (closing is the event "W enters Q").
By Claim B, σ_j's literal is not false under α. So α satisfies every clause, and φ is satisfiable. K→P moves
(through S after a K pass, or N after W was pushed up into T) only let the hero walk branches, which can only
close more paths. They do not affect Claims A and B, since those are about first entries and closings before
t_1. □

### 5.3 Answer-level DET
YES: §5.1 holds under every RNG outcome. NO: §5.2 uses only deterministic rules (F1-F4 and the gadget maps).
§6 shows that no random action can add boulder or hero motion beyond F1-F4.

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

## 8. Witness scripts (not run)
`tools/witness/on_close.lua` (G_C), `tools/witness/on_door.lua` (G_D), `tools/witness/on_cross.lua` (G_X), in the
style of `src/test/testmove.lua` and the existing `off_*.lua` witnesses (same map-relative coordinate
convention). Each script builds the gadget with `des.map`, sets
`sokoban` plus a sentinel pit, gives the cursed loadstone, plays the intended keys and asserts hero positions,
and checks at least one forbidden move. The harness API (`obj.new` string form, `des.trap` signature) should be
checked when Ivan is off the laptop.
They use `nh.debug_flags({hunger=false})` only to keep the tests short; the instances themselves do not.
