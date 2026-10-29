# Workstream B: global reduction G6 ≤_p L_OFF^{W+C} under R3

B agent, 2026-10-29. Nothing run, nothing committed; only this file and an append to INTERFACE.md were written.
Inputs read: exptime-sources.md (G6, §5 sketch, N1-N5), exptime-feasibility.md (coin C, §3, §4.0-4.3, §9 W9-W11),
exptime-model.md (R3 game, Thm M, H1-H8), exptime-mech-monsters-traps.md §3.2 (≤ 2 boxes ⇒ ≤ 3 coins per level),
hu-off.md §B (simulation-lemma style), hu-on-lower.md §4-5 (global layout, Claim A/B style). A-gadgets.md, C-audit.md,
D-checker did not exist yet when this was written; their parts enter as named assumptions (INTERFACE.md).
Labels: **VERIFIED** (read in a source/witness this session or in a cited VERIFIED file) · **STRONG** (complete
argument, not reviewed) · **CONJECTURE**.

## 0. Result

| # | Claim | Status |
|---|---|---|
| L1 | G6 with "F checked only right after Player I's moves" has the same winner as G6 | STRONG (elementary) |
| TS | A k-user "multi-tunnel" self-closing door MSCD(a,s) is simulated by one SCD + context SCDs + diodes, sound and complete for the plays used | STRONG |
| T1 | **Abstract:** Player I wins G6(F, α₀) ⇔ the agent wins the one-agent nature game 𝒢_F built from SCD/MSCD, diodes, crossovers and ONE coin vertex (§3) | STRONG |
| T2 | **NetHack:** 𝒢_F realized in L_OFF^{W+C} (I_F) has the same winner under R3, given A's game-safe gadgets (G1-G5) and C's audit items C-1..C-4 | STRONG *conditional* on A and C; CONJECTURE overall until A/C land |
| S | I_F has O(N²) cells, O(N²) crossovers, ONE coin; computable in log space (N = |F| + |X| + |Y|) | STRONG |
| ⇒ | With Thm M (exptime-model §2.2): **L_OFF^{W+C} under R3 is EXPTIME-complete** | CONJECTURE (= T2's conditions) |

What the proof does NOT need: monsters, doors, any RNG other than the coin, any toggle gadget, more than one coin,
any timing race. Key design choices: (i) the CNF checker is a **dead end** ending only in g, so a failed check is a
loss and never changes the game state that matters; (ii) every "write" closes the complementary literal doors by an
**open-then-self-close pair** (forced), while openings may be declined (declining only hurts the hero); (iii) nature's
move is a depth-d walk through **one** coin, the tree node being carried by **context doors** (one open at a time).

## 1. Source problem: G6

### 1.1 Definition (VERIFIED as restated verbatim in Hearn 2006 §6.2.1 / Demaine–Hearn CCC 2008 §6.2, via exptime-sources.md §1; original SIAM text PARTIAL, paywalled)
Instance: CNF formula F = C₁ ∧ … ∧ C_m over disjoint variable sets X (Player I) and Y (Player II), and an assignment
α₀ of X ∪ Y. Players alternate; a move of Player I (II) changes **at most one** variable of X (Y); passing is allowed.
**Player I wins iff F ever becomes true.** Player II has no win condition; an infinite play is a non-win for I (Chung
2026: "draws are counted as wins for Player II", VERIFIED in exptime-sources.md). G6 is EXPTIME-complete [ext: SC79].
Clause width is unrestricted (the checker handles any CNF).

Positions: (α, p) with p ∈ {I, II} the player to move; the rules depend only on the position. G6 is a reachability
game on a finite arena (2^{|X|+|Y|+1} positions) for Player I, hence determined, with positional strategies on both
sides (attractor argument) [STRONG, standard].

Conventions the restatements leave open, and how B handles them:
- **Who moves first.** Not fixed in the restatement. B supports both: start the hero at h (I first) or at the nature
  entry N_in (II first); §3.1.
- **Does the initial position count?** "Ever becomes true": if F(α₀) is true, we treat it as an immediate I-win
  (pre-processing outputs a fixed YES instance). Under the other reading only the I-first case can differ, and there
  L1 shows it does not (I may pass). For II first + "initial excluded", start at N_in and skip pre-processing.
- **"After any move" vs. "after I's moves".** L1.

### 1.2 Lemma L1 (post-I checking) — STRONG
Let G6' be G6 except that Player I wins iff F(α) is true at a **post-I position** (directly after one of I's moves,
a pass included). Then Player I wins G6 from (α₀, p₀) ⇔ he wins G6' from (α₀, p₀) (when p₀ = II and F(α₀) true the
pre-processing above already answered).
*Proof.* G6' wins are G6 wins (post-I positions are positions), so a G6'-winning strategy is G6-winning. Conversely let
σ win G6. Define σ': play σ until the first position where F is true; if that is a post-I position, done; otherwise
it is a pre-I position (initial or post-II), and σ' passes, giving a post-I position with the same α, F true. Every
σ'-play is a σ-play up to that point, so it reaches such a position. ∎
Hence B only needs a checker accessible right after Player I's move module. Also: under II's positional winning
strategy τ (when I loses), F is **never** true at any position of any τ-play (else I would win G6).

## 2. Abstract target: one-agent nature games with doors

### 2.1 The game 𝒢 (definition)
A finite directed **route graph** whose vertices are *locations*: free corridor cells, **fork** vertices (out-degree
≥ 2, the hero chooses), **merge** vertices, gadget **ports**, one **coin** vertex T with two out-ports A, B, a start
s and a goal g. Every route edge is one-way (realized: diode at its start). Gadgets:
- **SCD** (self-closing door, Ani et al. door papers; Push-1F's source gadget): bit σ ∈ {open, closed}; tunnel O:
  always passable, afterwards σ' ∈ {σ, open} (hero's choice: *open-optional*); tunnel S: passable iff σ = open,
  afterwards σ' = closed (**forced**). Tunnels are directed. At a tunnel's entry the hero may also turn back
  (state unchanged).
- **MSCD(a, s)**: one bit, a O-tunnels, s S-tunnels, each with the SCD semantics. SCD = MSCD(1,1).
- **Coin**: arriving at T, the play continues at A or at B, **nature's choice**, every time (N1-N4 of
  exptime-sources.md §5; NetHack realization exptime-feasibility §3, W9 VERIFIED 1200/1200 landings on {A, B}).
- **Crossover**: two directed passages, used independently (realization requirement A-X).
Positions = (hero location, all door bits). Full information. The hero wins iff he reaches g; infinite plays (incl.
standing still forever and being stuck in a pocket with no exit) are losses. "Stuck" below = a region from which no
route reaches g; a hero there loses whatever he does.

### 2.2 Lemma TS (tunnel sharing) — STRONG
*Claim.* MSCD(a, s) can be replaced by one SCD D plus, for every tunnel kind with k ≥ 2 users, a **sharing region**,
such that (i) every realized option of the hero is an option of the ideal MSCD or leads to a stuck pocket, and
(ii) every ideal traversal "enter tunnel τ_p of user p, leave at its exit" is realized by a fixed walk.
*Construction (for one tunnel kind of D, users p = 1..k; e.g. the O-users):* user p's route arrives at u_p →
O-tunnel of a **context SCD** K_p (initially closed) → diode → merge m → D's real tunnel τ (O or S) → split m' →
for each q: S-tunnel of K_q → diode → continuation v_q of user q.
*Invariant J_TS:* whenever the hero is not strictly between some u_p and v_p, all K_q are closed.
*Proof.* Initially true. Entering at u_p (only possible from user p's route; m is reachable only from the K-O exits
by diodes) the hero may open K_p (no other K_q has an O-tunnel in reach). Between m and m' the only move is through τ
(directed; if τ is a closed S-tunnel he is stuck: no way back over the diode). At m' only open K's S-tunnels pass,
i.e. at most K_p; passing it closes it (forced) and leads to v_p. If he declined to open K_p he is stuck at m'. So
he leaves the region only at v_p, having traversed τ exactly once, with all K closed: J_TS holds again, and D's bit
changed exactly as the ideal traversal of user p's tunnel. Ideal options not realized: "turn back at the entry of a
closed S-tunnel" becomes "stuck" if the hero commits; the hero has full information, so this only removes options
the completeness proof never uses (§4.1 always enters S-tunnels of open doors). ∎
Consequence (monotone simulation, STRONG): replacing a gadget by a realization whose hero options are a subset of the
ideal ones plus stuck pockets, with nature's options unchanged, cannot turn a losing position into a winning one; and
if the ideal winning strategy uses only realized options, winning is preserved. B uses this pattern again in §5.

## 3. The construction 𝒢_F (abstract)

Notation: n_X = |X|, n_Y = |Y|, occurrences (ℓ, j) = literal ℓ ∈ C_j, N_occ = Σ_j |C_j|, N = N_occ + n_X + n_Y + m.
For variable v and bit b: true(v, b) = the literal of v true under v = b (v if b = 1, ¬v if b = 0), false(v, b) its
complement.

### 3.1 Components
1. **Literal doors.** For each occurrence (ℓ, j): D_{ℓ,j} = MSCD(2, 2) with tunnels O¹ (opener), O² + S¹ (forced
   closer), S² (checker). Initial bit: open iff ℓ is true under α₀ ("canonical state" Open(α₀)).
2. **Write path W(v := b)** (v ∈ X ∪ Y): a single directed route: diode → for every occurrence (ℓ, j) with ℓ =
   false(v, b), in any fixed order: O² then S¹ of D_{ℓ,j} (**forced close**) → then for every occurrence (ℓ', j') with
   ℓ' = true(v, b): O¹ of D_{ℓ',j'} (**optional open**) → exit. No other connections.
3. **Player I module.** Fork h (the **hub**) with 2n_X + 1 branches: W(x_i := b) for every i, b, and a **pass**
   corridor. All exits merge (diodes) into the post-I vertex **P**.
4. **P** is a fork with exactly two branches: diode → **checker**; diode → **nature entry N_in**.
5. **Checker** (dead end): vertices c₀ → c₁ → … → c_m → g. Between c_{j−1} and c_j, parallel branches, one per
   occurrence (ℓ, j) ∈ C_j: S² of D_{ℓ,j} → diode → c_j. No edge leaves the checker except toward g. (If A's gadgets
   are only *checkable*, c_m → global check path → g; §5.2.)
6. **Nature module.** Leaf menu M_II = {pass} ∪ {(j, v) : y_j ∈ Y, v ∈ {0,1}}, |M_II| = 2n_Y + 1.
   d = ⌈log₂(2n_Y + 1)⌉ (d = 0 iff n_Y = 0: then N_in leads directly to the pass leaf). Complete binary tree T_N of
   depth d, leaves labelled by a surjection λ: leaves → M_II (extra leaves labelled pass). For every internal node u a
   **context door K_u = MSCD(1, 2)** (O-tunnel; S^A, S^B), initially closed.
   - N_in → O of K_root → diode → merge **E_C** → coin T.
   - A → diode → fork **H_A** with one branch per internal u: S^A of K_u → diode → "arrive at left(u)".
     B → diode → fork **H_B**, branches S^B of K_u → diode → "arrive at right(u)".
   - "arrive at c", c internal: O of K_c → diode → E_C. "arrive at c", c a leaf: diode → leaf route of λ(c):
     W(y_j := v) for (j, v), or a pass corridor; then diode → h.
7. **Start**: s = h (Player I first) or s = N_in (Player II first). Goal g after c_m.

Every internal node u has exactly one "arrive at u" location (from its parent's demux branch, or N_in for the root),
so each tunnel of each K_u and each tunnel of each D_{ℓ,j} has exactly one user route, except the MSCD multi-users
listed in 1 and 6, which Lemma TS turns into plain SCDs (§6 counts them).

### 3.2 Picture of one round
`h ─(I picks W(x_i:=b) or pass)→ P ─┬→ checker → g` · `P ─→ N_in → [open K_root] → E_C → T ⇒ A|B (nature) →
H_A|H_B → [S of the one open K] → [open K_child] → E_C → T … (d times) → leaf route W(y_j:=v)|pass → h`.

## 4. Theorem T1 (abstract correctness) — STRONG

**T1.** Player I wins G6(F, α₀) (with the convention of §1.1) ⇔ the hero wins 𝒢_F from s.

Macro-structure fact (Fact R, by inspection of §3.1; every edge is one-way): the hero's location sequence, cut at
visits of h, P, N_in, is a word in the regular language
  (h · I-route · P · N_in · nature-walk · leaf-route)* · [h · I-route · P · (checker | N_in · nature-walk …)] ,
where a route once entered is left only at its own exit or never (stuck/stalling). In particular: h is reached only
from leaf routes (and s); P only from I-routes; the checker only from P; N_in only from P (and s); E_C/T only from
N_in's and "arrive at internal c" routes; H_A only from A, H_B only from B. No route leads from the checker back.

### 4.1 Lemma N (nature module integrity) — STRONG
Suppose the hero passes N_in at a moment when all K are closed. Let c₁, c₂, … be nature's coin outcomes in this
visit. Then the hero either never leaves the nature module (loses), or he enters exactly the leaf route of the leaf
reached in T_N from the root by the directions c₁..c_d, after exactly d coin uses; at that moment all K are closed.
*Proof.* Invariant J_k (k-th arrival at T in this visit): the set of open context doors ⊆ {K_{u_k}}, u_k = the depth-
(k−1) node on the path c₁..c_{k−1}. k = 1: only K_root's O-tunnel lies between N_in and E_C. Step: nature picks c_k;
the hero is at A (say) and H_A is the only continuation (diode). From H_A only S^A-tunnels leave, passable only for
open doors, i.e. only K_{u_k}'s (J_k); if it is closed (hero declined to open it) he is stuck. Passing it closes K_{u_k}
(forced), so **no** K is open, and leads to "arrive at left(u_k)" = u_{k+1}. If u_{k+1} is internal, the only
O-tunnel there is K_{u_{k+1}}'s, then E_C → T: J_{k+1}. If it is a leaf (k = d, the tree is complete), the hero is
in its leaf route with all K closed. He cannot reach T, H_A, H_B or any other demux branch by another way (Fact R),
cannot return from A/B to T (diodes), and waiting forever is a loss. ∎
So: **the leaf is a function of nature's answers only; the hero's sole alternatives are to stall or get stuck.**
The coin cannot stall nature's turn (it always lands on A or B: N2, W9) and every leaf label is a legal II move
(λ maps into M_II), so nature cannot make an illegal move either.

### 4.2 Literal invariant — STRONG
Define the **logical assignment** α_t along a play: α₀ at the start; when the hero leaves W(v := b) at its exit,
α(v) := b; nothing else changes α. Let Lit(t) = set of open literal doors.
**Inv-L:** whenever the hero is not strictly inside a write path, Lit ⊆ Open(α) := {D_{ℓ,j} : ℓ true under α}.
*Proof.* Literal doors change only in write paths (O¹, O², S¹) and the checker (S², which only closes; after it the
hero never leaves the checker except at g). Inside W(v := b) only doors of v change. On its exit every
D_{false(v,b), j} has passed O² then S¹ in that order, and no later tunnel of this path touches it, so it is closed;
doors D_{true(v,b), j} may be open or closed; doors of other variables unchanged. Hence Lit ⊆ Open(α_new). The hero
cannot leave a write path other than at its exit (Fact R; directed tunnels; a declined O² makes S¹ impassable = stuck).
∎ Conversely, **Inv-L⁺** (completeness side): if the hero opens every O-tunnel he traverses (always allowed), then
outside write paths Lit = Open(α) exactly.

### 4.3 Completeness (I wins G6 ⇒ hero wins 𝒢_F)
By L1 let σ be a positional winning strategy of I in G6'. Hero strategy H_σ (full information: he sees α_t = the
canonical door state):
- At h with assignment α (canonical: Lit = Open(α), all K closed): take the route of σ(α) (W(x_i := b) or pass),
  opening every O-tunnel; arrive at P with Lit = Open(α'), α' = α after I's move (Inv-L⁺).
- At P: if F(α') then enter the checker: for each j pick an occurrence (ℓ, j) with ℓ true under α' (exists); D_{ℓ,j}
  is open; pass its S²; reach g. (S² closes the door; the hero never needs it again.) Otherwise go to N_in.
- In the nature module: open K_root; at H_A/H_B take the unique branch with an open K (Lemma N: exactly K_{u_k} is
  open because he opened it); open the child's K. After d coin uses he is in the leaf route of some m_II ∈ M_II;
  walk it opening every O; arrive at h with Lit = Open(α''), α'' = α' after II's move m_II, all K closed.
Every nature strategy thus produces a G6' play consistent with σ: round r has I-move σ(α) and some legal II-move.
σ wins G6', so some round ends at P with F(α') true, and the hero reaches g. Each round takes O(N) steps and exactly d
coin uses; the number of rounds is ≤ the attractor rank of σ, ≤ 2^{n_X+n_Y+1}: **exponentially long plays occur**,
which only requires every gadget to be reusable without bound (no consumable anywhere: §5.1 G5). ∎

### 4.4 Soundness (I loses G6 ⇒ hero loses 𝒢_F)
By determinacy let τ be a positional strategy of II under which F is never true (§1.2). **Nature's strategy ν_τ:**
when the hero passes N_in in a round, let α' = α_t (logical assignment, §4.2) at that moment and m = τ(α'); fix a leaf
z with λ(z) = m; answer the k-th coin use of this visit with the k-th direction on the root-to-z path (any answer
for k > d, which cannot happen by Lemma N). ν_τ is a function of the visible history (full information).
Claim: no play consistent with ν_τ reaches g.
- By Fact R and Lemma N, every play is: rounds h → I-route → P → N_in → nature walk → leaf route of z → h, possibly
  ending in stalling/stuck inside a route, or with a final h → I-route → P → checker.
- The sequence of logical assignments at the round boundaries is a G6' play: the I-route exit applies an I-move
  (W(x_i := b) = "set x_i to b" = flip or pass; pass corridor = pass); by Lemma N the leaf route is z's, which applies
  m = τ(α'), a legal II move — **the hero cannot choose another leaf, skip, or repeat a nature turn**. A hero who
  stops inside a write path, or never finishes it, never reaches P or h again (stuck/stalling): loss.
- So it is a τ-play, F(α') is false at every P-visit. Suppose the hero enters the checker at P with assignment α'.
  Some clause C_j is false under α': every occurrence door D_{ℓ,j} with ℓ ∈ C_j is closed by Inv-L (Lit ⊆ Open(α'),
  ℓ false). Inside the checker no O-tunnel exists, S²-traversals only close doors, so the hero never passes from c_{j−1}
  to c_j: stuck, g unreachable.
- Plays that never enter the checker never reach g (g's only in-edge is from c_m). Infinite plays are losses.
Hence the hero loses against ν_τ. ∎ Combined with 4.3 and L1: **T1**.

### 4.5 Cheat checklist (all covered above)
| Cheat | Why harmless |
|---|---|
| Hero declines an opening (O¹, K-O) | only fewer open doors (Inv-L is "⊆"); a declined K-O or O² = stuck |
| Hero partially traverses / turns back at a tunnel entry | ideal: state unchanged; TS: may be stuck; never a new move |
| Hero revisits h, write paths, nature module | only via the round structure (Fact R); each visit = a legal G6 move |
| Hero tries the checker with F false | dead end: stuck forever (closed doors, no exit) |
| Hero waits / stalls anywhere | infinite play = loss; gadget bits change only by traversals, never by time |
| Hero skips nature's turn / takes two I-moves | P's only exits are checker and N_in; I-routes exit only into P |
| Hero chooses nature's leaf | at H_A/H_B only K_{u_k} is open (Lemma N) |
| Hero re-rolls the coin | A, B lead only into diodes; T is entered only from E_C (and even a re-roll would only give nature a new identical choice) |
| Nature stalls | coin always lands on A or B (W9); nothing else is nature's |
| Nature makes an illegal move | λ maps leaves into M_II; nature's only power is the coin (C-1) |
| Nature leaves gadgets broken | nature never touches gadgets: the coin moves only the hero, to boulder-free cells (feasibility §3.1) |
| Exponentially long play | no consumables; every gadget reusable unboundedly (G5); per-round cost bounded |

## 5. Theorem T2: realization in NetHack (L_OFF^{W+C}, R3) — STRONG conditional

### 5.1 What B assumes from A (INTERFACE.md "B → A")
For each gadget type (SCD, diode, directed crossover; MSCD only via Lemma TS) a boulder map (Sokoban rules, heavy
hero, hunger off) with a map π from *clean* realized configurations to ideal states, such that:
- **G1 locality:** the region meets the rest only at its ports; boulders never leave the region; no boulder ever
  reaches a cell within push range of the coin tile.
- **G2 soundness:** any hero walk that enters at a port from a clean configuration and leaves the region either
  (a) returns to the entry port with the same ideal state, or (b) exits at a port by an ideal transition with the
  new clean state, or (c) leaves the gadget **broken** (any position, possibly still passable).
- **G3** broken is absorbing (no walk makes it clean again).
- **G4 completeness:** every ideal transition used in §4.3 (O with "open", S of an open door, passages of diodes and
  crossovers) is realizable by an RNG-free walk from every clean configuration representing the state, ending clean.
- **G5** zero HP cost, no consumable, unboundedly reusable, both initial door states placeable.
Locally exact gadgets (no broken configurations) make §5.2 unnecessary.

### 5.2 Global check path (only if A's gadgets are checkable, Push-1F style) — STRONG given G1-G5 + checkability
Insert after c_m a path through every gadget's check tunnel (passable iff clean), then g. Game-level argument (the
risk noted in exptime-sources §5 risk 1): (i) the coin is not on it and the checker is a dead end, so nature acts only
before the hero enters it; (ii) any play reaching g passes the check path, so every gadget is clean at that time;
by G3 every gadget was clean **at every earlier time** of that play; hence the whole play is, through π and G2(a,b), a
play of 𝒢_F (null visits deleted) with the same coin outcomes. (iii) Nature's strategy in the realization: ν_τ applied
to the π-image of the history while everything is clean, anything after a break (such plays never win by (ii)).
(iv) Completeness: H_σ's realized play stays clean (G4), and the final check passes. **Open interface point:** the
check path itself must cross other routes; those crossovers must be checkable or locally exact (A's design).

### 5.3 What B assumes from C (INTERFACE.md "B → C")
- **C-1** every RNG call reachable in I_F other than the coordinates chosen in `safe_teleds` at T leaves π-relevant
  data (hero cell, boulder set, door/gadget configurations, HP, Str/Con, worn cursed boots) unchanged. Partly done:
  model §3.1 per-turn block (STRONG), feasibility §3.3 + W9 for Fumbling (`slip_or_trip`, `nomul(-2)`: time only;
  timeout.c:902-924 re-read here: no `exercise`/`losehp` on that branch, VERIFIED).
- **C-2** Str/Con never decrease (no abuse source except kicking, the hero's own choice), so `weight_cap` and the push
  and squeeze rules (hu-off I3) never change; weight 520 with the boots (feasibility §3.3 margin).
- **C-3** hero never `stuck_in_wall` (hu-off I7; after landing on A/B the exit corridor cell is free), so prayer's
  STUCK fix (a `safe_teleds` outside Z = global relocation, since `noteleport` is dropped) is unreachable.
- **C-4** exponentially long plays: no gadget/coin behaviour depends on wrap-sensitive `moves` comparisons (model
  §2.6) or on any counter beyond its fixed range.
Hero-side RNG commands (kick, #untrap, #pray, #open: none useful, veto lemma model §3.5) only add stuck/death
outcomes, i.e. options outside the ideal set that never reach g; C must confirm none moves π (hu-off §B.4 table +
the new whitelist items: TELEP_TRAP via #untrap, wearing/removing cursed boots).

### 5.4 T2 statement and proof
**T2.** Under G1-G5 (+ §5.2 if checkable) and C-1..C-4: the hero has an R3-winning strategy in I_F ⇔ he wins 𝒢_F.
*Proof sketch (STRONG modulo the assumptions).* (⇐) H_σ realized via G4: corridors are boulder-free walks, gadget
transitions RNG-free walks, the coin is entered at T with the boots worn (the hero puts them on first; cursed, they stay
on). By C-1 the only nature choice that matters is the landing cell ∈ {A, B} (VERIFIED W9: never T, never outside Z,
never "no move"), which is exactly the abstract coin. HP never drops (G5, coin zero damage, C-1), so the play survives
any length. (⇒ contrapositive) Given ν_τ for 𝒢_F, nature plays it on the π-image of clean histories (choosing the
`safe_teleds` coordinates of A or B), and arbitrary legal values for all other RNG calls (C-1: irrelevant). By G2 and
the monotone-simulation remark (§2.2) every realized hero option is an abstract option, a null visit, a stuck pocket,
a break (never wins by §5.2/G3), a death, or leaving the level (losses, model §1.1). So a realized play reaching g
projects to an abstract ν_τ-play reaching g, contradicting §4.4. ∎
Then T1 + T2 + pre-processing give G6 ≤_p L_OFF^{W+C} (R3), and with Thm M: EXPTIME-complete (CONJECTURE until A's
gadgets meet G1-G5 and C confirms C-1..C-4). R2 stays in PSPACE and R4 is not covered (re-triggerable coin, model H8).

## 6. Size, planarity, crossovers — STRONG

### 6.1 Gadget counts
- Literal doors: N_occ MSCD(2,2). Via TS each = 1 SCD + 2 context SCDs (O¹/O² users) + 2 (S¹/S² users) = **5 SCDs**.
- Context doors: I_N = 2^d − 1 ≤ 4n_Y + 1 internal nodes; K_u = MSCD(1,2) = 1 + 2 = **3 SCDs**.
- Total SCDs ≤ 5N_occ + 12n_Y + 3. Coins: **1** (≤ 3 fit per level; one suffices). Forks: h (2n_X+1 branches), P (2),
  H_A, H_B (I_N each), checker fans (N_occ total), TS splits (2 per shared tunnel kind, 2N_occ + I_N kinds).
- Route edges (each with a diode): E ≤ 4·#SCD + 3 + Σ fork branches ≤ (20N_occ + 48n_Y + 15) + (5N_occ + 2n_X + 16n_Y + 5)
  ≤ 25N_occ + 2n_X + 64n_Y + 20 ≤ 64N + 20.

### 6.2 Layout (bus embedding)
Gadget, fork and coin tiles (side c_A, A's constant; each drawn with all ports on its top side, which costs O(1)
internal crossovers per tile if A's port order differs) sit in one bottom row. Each route edge e gets its own
horizontal track row r_e above the tiles and its own column at each endpoint: up from the source port to r_e, along
r_e, down to the target port. Two routes meet only where a vertical column crosses a horizontal track; there a
**directed crossover tile** carries both. Columns ≤ 2E, rows ≤ E + 1 ⇒ crossovers ≤ 2E² = O(N²) and the map has
≤ c_A²(2E)(E+1) = O(N²) cells. Corners and merges are plain corridor cells (merges have diodes on every in-edge).
The coin tile: Z = 1×5 row [A, wall, T, wall, B] (A, B not adjacent to T, so no re-roll from A/B), entry E_C below T,
exits above A and B into diodes, all ≥ 3 cells boulder-free; one `des.teleport_region{region = s, exclude = Z,
…_islev = true}` call (feasibility §9 note 3). Crossovers on write-path routes are traversed exponentially often:
**single-use crossovers are not allowed anywhere** (requirement A-X).
Is a crossover avoidable? The literal-door/write-path/checker incidence is the incidence graph of F, non-planar in
general, and no planar G6 variant is known to B; so a reusable crossover (or A's planar MSCD layout via the
door-universality crossover, Ani et al. FUN 2020 Lemma 2.6 [secondary]) is required.

### 6.3 Size bound
|I_F| = O(N²) map cells + O(N²) boulder/trap lines (one trap: T) + the fixed harness. The construction is a fixed
pattern per route/gadget indexed by counters, so f is log-space computable. Pre-processing (F(α₀) true ⇒ fixed YES
instance) is a formula evaluation.

## 7. Weak points (ranked)
1. **A's game-safety (G1-G5)** for SCD, diode and especially the *reusable directed crossover*; if A only reaches
   checkable gadgets, the check path's own crossings (§5.2 open point). Everything in T2 hinges on this.
2. **C-1..C-4** not yet audited by C for the full W+C whitelist on exponentially long plays (Fumbling and per-turn
   block are covered; prayer/kick/#untrap on T and boot removal need the explicit row).
3. G6 conventions (first mover, initial position) read only from restatements; §1.1 handles all readings, but the
   theorem citation must match the variant used.
4. Lemma TS makes some ideal "turn back" options into stuck pockets; harmless here because the hero has full
   information (§2.2), but a reviewer should check no completeness step probes a closed door.
5. D-checker could test T1 end-to-end on tiny F (abstract 𝒢_F, attractor) — not done by B.
