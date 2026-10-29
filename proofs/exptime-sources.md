# EXPTIME-complete source problems for an R3 (nature-as-adversary) NetHack reduction

Author: literature sub-agent, 2026-10-29. No game run, nothing committed, no other file edited.
Context: claims.md (L_OFF^W PSPACE-complete via Push-1F), problem-definition.md §5.2 (R3 = adaptive, fully informed
∀-nature, sure-win, unbounded horizon ⇒ ∈ EXPTIME by APSPACE = EXPTIME), exptime-mech-doors.md (doors = useless veto).
Labels: **VERIFIED** = statement read in the source text this session (PDF/HTML fetched); **PARTIAL** = read only in
a secondary source or the venue/details not seen; **[conj]** = my reasoning, not in any source.

## 0. Answer in five lines

1. The exact model we want ("one agent; the player moves it; nature resolves binary branches at cells the player
   reaches; full information; unbounded") is **not settled in the gadget literature**. The closest published model,
   *two-player shared-agent motion planning* (Ani-Demaine-Hendrickson-Lynch), is **open between PSPACE-hard and
   EXPTIME** for input/output gadgets (§3.2). Its abstract form (fully observable nondeterministic planning) **is**
   EXPTIME-complete (Littman 1997; Rintanen 2004), but with succinct propositional operators, not gadgets (§4).
2. So we need our own reduction. Best source: **Stockmeyer-Chandra G6** (single CNF formula, each player flips ≤ 1 own
   variable or passes, Player I wins if F ever becomes true). It is a reachability objective for the player, draws
   count against the player (= REACH semantics), and Player II's move is a bounded menu, which nature can pick with
   ⌈log₂(2|Y|+1)⌉ binary choices.
3. 2CL (Hearn-Demaine) and the DHL20 two-robot games are **bad fits**: their EXPTIME proofs depend on move-for-move
   timing races between two agents (fast/slow win pathways, timers), which a single hero + triggered nature cannot
   express.
4. Gadgets needed for G6 → R3-NetHack [conj, sketch in §5]: (a) directed open-optional **self-closing door** (SCD,
   the Push-1F source gadget), (b) **diode**, (c) **crossover** for the agent, (d) one new piece, a **nature fork**: a
   reusable, non-stallable, forced binary branch. (a)-(c) exist in Push-1F; (d) is the open NetHack mechanics question.
5. Theorem to cite for hardness: G6 EXPTIME-complete (Stockmeyer & Chandra 1979, as restated verbatim by Hearn 2006
   and Demaine-Hearn 2008). Membership: R3 ∈ EXPTIME via APSPACE = EXPTIME (Chandra-Kozen-Stockmeyer 1981).

## 1. Stockmeyer & Chandra 1979: the G-games

**Citation:** L. J. Stockmeyer, A. K. Chandra, "Provably difficult combinatorial games", SIAM J. Comput. 8(2):151-174,
1979, doi 10.1137/0208013. **PARTIAL**: SIAM page is paywalled (HTTP 403); definitions below are from two secondary
sources that restate them: L. Chung, *Complexity of Unbounded Boolean Formula Games*, MIT S.M. thesis (supervisor
Demaine), Jan 2026, https://erikdemaine.org/theses/lchungM.pdf (VERIFIED, read), and Hearn 2006 / Demaine-Hearn 2008
for G6 (VERIFIED, verbatim). Original clause widths for G5/G6 not seen.

Common frame (Chung Ch. 2): two players, disjoint variable sets X (Player I) and Y (Player II), formulae φ1, φ2;
a turn changes some of one's own variables, then checks one's own formula; game ends when it holds.
Chung's classification of the originals (all EXPTIME-complete in [SC79]):

| Game | Formula ownership | Move | Outcome when own formula true | Formula form |
|---|---|---|---|---|
| G1 | partizan | set any subset of own vars (+ turn var τ) | lose | 4CNF with τ in each clause (= "Lose 3DNF") |
| G2 | partizan (I-WIN, II-WIN) | flip ≤ 1 own var or pass | win | 12-DNF |
| G3 | partizan (I-LOSE, II-LOSE) | flip exactly 1 own var (no pass) | lose | 12-DNF (VERIFIED verbatim in Zhang, arXiv 2208.05376 §3) |
| G4 | impartial (one shared formula) | flip ≤ 1 own var or pass | first to satisfy wins | 13-DNF (Chung's intro says 12-DNF; table says 13; ACDDGHL23 says 13) |
| G5 | single formula (only Player I) | flip ≤ 1 or pass | I wins | (form not stated by Chung) |
| **G6** | single formula | flip ≤ 1 or pass | I wins if F ever true | **CNF** |

**G6, verbatim (Hearn 2006 §6.2.1; Demaine-Hearn 2008 §6.2):** "INSTANCE: CNF Boolean formula F in variables X ∪ Y,
(X ∪ Y) assignment α. QUESTION: Does Player I have a forced win in the following game? Players I and II take turns.
Player I (II) moves by changing at most one variable in X (Y); passing is allowed. Player I wins if F ever becomes
true." Player II has no win condition; infinite play is a non-win for I (Chung: "For G5 and G6, draws are counted as
wins for Player II").

Newer refinements (Chung 2026, VERIFIED): G2 and G4 EXPTIME-complete already with 6-DNF (Thm 17); G3 with φ1 5-DNF
and φ2 a fixed constant formula (Thm 21); **latch game** (Def 19, Thm 20): Player II's whole turn is setting ONE bit
y, Player I resets a copy and rewrites all its variables, Player I loses if a 3DNF holds, wins if play is infinite.
Its proof is a direct alternating-LBA simulation where y = the universal successor bit. Conceptually this is exactly
"nature makes one binary choice per round", but the objective is safety, not reachability, and Player I's move is
"rewrite everything", so it fits a motion game worse than G6 [conj].

Which are natural for planar gadgets [conj]: G6 (single CNF, reachability for I, monotone clause checker, ≤ 1 flip
per move) is the one used for Go (Robson) and 2CL (Hearn); G3 for Chess (Fraenkel-Lichtenstein); G4 for the impartial
shared-robot game (§3.3) and for Littman's planning result (§4). For us G6 wins: our player must *reach* a goal.

## 2. Hearn & Demaine: Two-Player Constraint Logic (2CL)

**Citations:** R. A. Hearn, *Games, Puzzles, and Computation*, MIT PhD thesis, June 2006,
https://groups.csail.mit.edu/mac/users/bob/hearn-thesis-final.pdf (VERIFIED, Ch. 6 read).
E. D. Demaine, R. A. Hearn, "Constraint Logic: A Uniform Framework for Modeling Computation as Games", Proc. 23rd
IEEE Conf. on Computational Complexity (CCC 2008), pp. 149-162, https://erikdemaine.org/papers/CL_Complexity2008/
(VERIFIED text; pages from Demaine's page). Book: Hearn & Demaine, *Games, Puzzles, and Computation*, A K Peters 2009
(PARTIAL: not opened; the thesis is its basis).

**2CL (verbatim definition):** INSTANCE: AND/OR constraint graph G, partition of the edges of G into sets B and W,
and edges e_B ∈ B, e_W ∈ W. QUESTION: does White have a forced win when White and Black alternately reverse one edge
of their own colour (each move must keep every vertex's inflow ≥ 2), and White (Black) wins on reversing e_W (e_B)?
(Bounded 2CL adds "each edge may be reversed at most once".)

| Theorem | Statement | Source |
|---|---|---|
| Thesis Thm 19-20 | Bounded 2CL PSPACE-complete, even planar | from Schaefer's G_pos(POS CNF) |
| Thesis Thm 21 | planar Bounded 2CL with vertex set {CHOICE, AND, FANOUT, OR, Variable} (Fig. 6-2) | |
| Thesis Thm 22 / CCC'08 Thm 5 | **2CL is EXPTIME-complete** | reduction from **G6** |
| Thesis Thm 23 | **2CL EXPTIME-complete even for planar graphs** (crossovers monochrome = one-player crossover, Thm 15; pad paths) | |

The unbounded reduction does **not** come with a small stated vertex set. It needs a white/black *variable gadget*,
"locking" moves that threaten a *fast win* pathway (Black must answer each lock with a 4-move sequence A, B, C, D),
*slow win / slower win* pathways, and *path-length equalizers* (Fig. 9: x+6 vs 2x+12 reversals). Correctness rests on
exact race lengths between the two players. **Fit to us: poor** [conj]: our nature has no "own moves" to race with;
it acts only when the hero triggers it, so threat/response timing cannot be enforced. Use 2CL only as background.

## 3. Gadget frameworks with adversaries (Demaine, Hendrickson, Lynch and coauthors)

### 3.1 DHL20: two robots, one per player
**Citation:** E. D. Demaine, D. H. Hendrickson, J. Lynch, "Toward a General Theory of Motion Planning Complexity:
Characterizing Which Gadgets Make Games Hard", ITCS 2020, LIPIcs 151, 62:1-62:42, doi 10.4230/LIPIcs.ITCS.2020.62,
arXiv 1812.03592 (VERIFIED, §1, §3 read).
- **Model (verbatim gist):** "two players alternate moving their own robot by traversing a single gadget", full
  information on robot locations and gadget states; connection-graph moves are free; Player 1 wins if their robot
  reaches its goal first, against every response.
- **Lemma 11:** 2-player motion planning with any set of gadgets is in EXPTIME (APSPACE = EXPTIME).
- **Thm 12:** EXPTIME-complete with the locking 2-toggle (L2T). **Thm 13:** EXPTIME-complete with **any
  interacting-k-tunnel reversible deterministic gadget**. Reduction from 2CL using per-player *timers*
  (exponential-length counters), an *edge-selection* area, a central L2T, delay lines of 1-toggles.
- **Planar case open** ("the crossover created by the locking 2-toggle ... does not suffice"); also open whether
  non-interacting gadgets suffice; 1-toggle alone open (§9 Q1).
- Fit: **poor**. Two agents and race-to-goal timers; NetHack has one hero and nature has no robot [conj].

### 3.2 ADHL: one shared agent, branch owners (the model closest to ours)
**Citation:** H. Ani, E. D. Demaine, D. H. Hendrickson, J. Lynch, "Trains, Games, and Complexity: 0/1/2-Player Motion
Planning through Input/Output Gadgets", WALCOM 2022; journal version Theoretical Computer Science (2023),
ScienceDirect PII S030439752300258X (DOI not read: PARTIAL); arXiv 2005.03192v2 (VERIFIED, §4, §6 read; TCS PDF from
erikdemaine.org/papers/GadgetsIO_TCS has the same §4 text).
- **Definition 4.1 (two-player shared-agent motion planning):** branchless system of input/output gadget G and
  fan-out gadgets, each labelled Black or White; one agent from a start location; "When the agent reaches a gadget,
  the player matching the gadget's label chooses a transition to take. White's goal is to reach a designated goal
  location, and Black's goal is to prevent this."
- Lemma 4.2: in EXPTIME. Thm 4.3: PSPACE-hard with the toggle switch or set switch (from Geography).
- **Status: "We do not show EXPTIME-hardness ... with any gadget"; conjectured EXPTIME-hard; listed open in §6**
  ("two-player one-agent motion planning, or two-player reachability switching games, which is between PSPACE-hard
  and EXPTIME"). Same gap for reachability switching games: J. Fearnley, M. Gairing, M. Mnich, R. Savani,
  "Reachability Switching Games", LMCS 17(2):10, 2021, doi 10.23638/LMCS-17(2:10)2021 (VERIFIED abstract:
  two-player case "PSPACE-hard and in EXPTIME").
- Our model = Def. 4.1 with Black fan-outs = nature cells, but with *non*-input/output gadgets (Push-1F's SCDs are
  directed tunnels with a separate opening port, re-usable, state-carrying). I/O gadgets are a strict special case,
  so the open problem there does not block us; it does mean **no citation gives the theorem we need** [conj].

### 3.3 ACDDGHL23: one shared robot, impartial, with ko
**Citation:** H. Ani, M. Coulombe, E. D. Demaine, J. Diomidova, T. Gomez, D. Hendrickson, J. Lynch, "Complexity of
Motion Planning of Arbitrarily Many Robots: Gadgets, Petri Nets, and Counter Machines", arXiv 2306.01193 (2023,
"Presented at SAND 2023"; no proceedings reference on arXiv: PARTIAL for venue; text VERIFIED, §5 read).
- Model: two players control the same robot; **each turn = one gadget traversal**; ko rule: no traversal of the gadget
  the opponent just traversed; a player with no legal move loses.
- Thm 5.2 (from G4) and **Thm 5.3: EXPTIME-complete for any interacting-k-tunnel reversible deterministic gadget**.
- Fit: **poor**. Control alternates on every traversal and the ko rule is essential; in NetHack the hero makes every
  move and nature only acts at designated cells.

## 4. Games against nature, planning

| Result | Statement | Status |
|---|---|---|
| C. H. Papadimitriou, "Games against nature", JCSS 31(2):288-301, 1985 | Games against a *random* (disinterested) opponent with polynomially many moves = PSPACE (SSAT etc.) | PARTIAL (abstract/secondary only). Bounded horizon only. |
| A. K. Chandra, D. C. Kozen, L. J. Stockmeyer, "Alternation", JACM 28(1):114-133, 1981 | APSPACE = EXPTIME; AP = PSPACE | VERIFIED earlier (citations.md 12b). Gives R3 ∈ EXPTIME. |
| M. L. Littman, "Probabilistic propositional planning: representations and complexity", AAAI-97, pp. 748-754 | Plan existence (goal with prob ≥ c, full observability, succinct operators) EXPTIME-complete; PSPACE-complete for poly-length plans; hardness from **G4** with c = 1 | PARTIAL (abstract + Rintanen's restatement) |
| J. Rintanen, "Complexity of Planning with Partial Observability", ICAPS 2004, pp. 345-354 | Full observability + nondeterministic operators: EXP-complete; **Thm 10**: EXP-hard even for acyclic plans, by direct poly-space ATM simulation (∀ state = one nondeterministic operator, ∃ = player's operator choice) | VERIFIED (§"Planning with Full Observability" read) |
| Peterson, Reif, Azhar, "Lower bounds for multiplayer noncooperative games of incomplete information", Comput. Math. Appl. 41(7-8):957-992, 2001 | team/hidden-info games (NEXPTIME, undecidable); background | not fetched |
| Fraenkel & Lichtenstein, JCTA 31(2):199-214, 1981 (Chess, from G3); Robson, SIAM J. Comput. 13(2):252-267, 1984 (Checkers); Robson, IFIP 1983 (Go, from G6 per Hearn) | background | not fetched (Chess→G3 VERIFIED via Zhang 2022) |

Rintanen Thm 10 is the clean statement of the *abstract* claim the user asked about: a one-agent reachability game
where the agent picks actions and nature resolves nondeterministic outcomes, on an exponentially large implicitly
given state space, is EXPTIME-complete (sure-win = "strong plans"; Littman's c = 1 version too). It cannot be cited
directly for NetHack because its instances are arbitrary propositional operators; the geometric version is §5.

Note on semantics: Littman's c = 1 and R3 sure-win coincide for his construction but **not in general**. If nature's
fork can be re-triggered, a probability-1 (R4) player may retry until lucky; under R3 retries never help. So a
G6-based reduction proves R3 hardness only; R4 needs forks that cannot be retried [conj].

## 5. Recommended reduction: G6 → one hero + Push-1F gadgets + nature forks [conj, sketch, not reviewed]

Target game M: system of gadgets with one agent; White (player) controls all free movement; "nature forks" are
Black-labelled fan-outs (ADHL Def. 4.1 style); White wins iff the agent reaches t. Literals are SCD copies, one copy
per clause occurrence plus routing.

- **Hub** h (start). From h: a diode into a *White selector* (free branching) to one of |X|+1 *set paths* (x_i := 0,
  x_i := 1, or pass), or into the *checker*.
- **Set path x_i := 1**: visit the opening port of every D_{x_i} copy; for every D_{¬x_i} copy, visit its opening port
  and then traverse it (an SCD closes on traversal), which is a **forced close regardless of its prior state**.
  Diode at the path entrance, so the agent cannot back out with a door left open. Symmetric for x_i := 0.
- **Nature tree**: every set path ends (diode) in a balanced tree of nature forks with 2|Y|+1 leaves (pad with
  "pass"). Leaf (j, v) leads (diode) to the forced set path y_j := v, then back to h. Passing = choosing v = current.
- **Checker**: clauses in series; clause = parallel SCD copies of its literals (traverse); after the last clause, t
  (then the postselection checking phase of the checkable-gadget framework). From each inter-clause point a diode back
  to h.
- Why the player cannot cheat: checker passability is **monotone** in the set of open doors, and the only ways to open
  a door are the legitimate set paths, which also force the complementary closes. A failed check only closes doors
  (hurts the player). Leaving set paths only through the nature tree forces "≤ 1 flip, then nature moves". Infinite
  play = no reach = G6 draw = Player II. Hence White wins M ⇔ Player I wins G6.
- Turn structure check: G6 lets Player I win "if F ever becomes true", including after II's move; here the player may
  enter the checker from h at any time. ✓.

**Gadget requirements** (what NetHack must provide):

| # | Gadget | Property needed | Available? |
|---|---|---|---|
| R1 | Directed open-optional SCD (opening port + one-way tunnel, closes on traversal, reusable unboundedly) | as ABD+20 / Push-1F Fig. 8 | Push-1F builds it (Ani et al. FUN 2022 §7) via *checkable gadgets + postselection*; the hu-off reduction already uses this machinery |
| R2 | Diode | one-way corridor | Push-1F (DDO00-style) |
| R3 | Crossover for the agent (planarity) | no leak that bypasses a diode or a nature fork | 1-player planar Push-1F/SCD results imply crossovers exist; their game-safety is unproved |
| R4 | **Nature fork** | (N1) when the hero enters, nature fixes which of 2 exits is the only way on; (N2) **no stalling**: nature cannot hold the hero forever without resolving (a stall = draw = player loss, which would make nature win every instance); (N3) both exits one-way, hero cannot refuse; (N4) **reusable exponentially often** with no consumed resource; (N5) R4 only: no re-roll | **Open: NetHack mechanics task** |
| R5 | No other outcome-dependent RNG on the map | answer-level DET elsewhere | as in L_OFF^W (§5.1 of problem-definition) |

Consequences for the current NetHack candidates [conj]:
- Doors (exptime-mech-doors.md): a veto, monotone, nature may stall → fails N1/N2.
- Drowning crawl-out (variants.md §C.3): nature returns the hero to the entry forever → fails N2.
- Boulder into pool / lava (variants.md §C.3): incomparable outcomes, but each use **consumes a boulder** → fails N4.
  It yields only polynomially many nature moves, so at best a PSPACE-hardness route for bounded R3 (via QBF / Bounded
  2CL), never EXPTIME.
- Something like a monster that must step to one of two cells and then stays (or a deterministic follower whose only
  random bit is a tie-break) would meet N1-N4 if nature cannot keep it oscillating while the hero waits. That is the
  kind of mechanic to look for next.

**Risks to check before writing the proof:**
1. The Push-1F correctness is stated as a *nonlocal simulation* = a Karp reduction between **one-player reachability**
   problems (Ani et al. Def. 5.1, Thm 5.3), not a strategy-preserving simulation, so it cannot be cited for games.
   Argument that should lift [conj]: broken states are absorbing on L (Def. 5.2 assumption) and every winning play must
   pass the final checking traversals, so a winning strategy never enters a broken state on any branch, and the play
   maps causally to the ideal gadget system. This must be re-proved for every simulation layer (diode, SCD,
   weak-closing/no-return/weak-opening, SO/MSC, crossovers), with nature forks kept off the checking route.
2. G6's original clause width (CNF unrestricted vs k-CNF) not seen (paywall). Not needed: the checker handles any CNF.
3. G6 with R3: nature is the *adversary*, so "pass" and "flip y_j" must all be leaves of the tree; never give nature an
   option that is not a legal G6 move, and never let the hero choose among nature's leaves.

## 6. Table: source problem → required gadgets → fit to NetHack R3

| Source | Status | Required gadgets / mechanism | Fit (one hero + triggered binary nature) |
|---|---|---|---|
| **G6** (SC79) | EXPTIME-c [PARTIAL orig; VERIFIED restatement] | SCD literal doors with forced close, diode, crossover, nature fork tree | **Best**: reachability for player, nature's move = bounded menu = O(log |Y|) forks |
| G4 / G2 (SC79; 6-DNF, Chung Thm 17) | EXPTIME-c | as G6, plus a check that Player II's satisfaction ends the game in II's favour (a nature-reachable "trap" exit) | Possible, but II "winning by satisfying" needs nature to drive the hero into a trap: harder |
| G3 (SC79; Chung Thm 21: φ2 constant) | EXPTIME-c | flip-exactly-one, lose-if-own-formula | Safety flavour; worse |
| Latch game (Chung Thm 20) | EXPTIME-c | one nature bit per round, player rewrites all vars, safety objective | Nature side ideal, player side (copy + rewrite + audit) heavy; safety ≠ REACH |
| Alternating LBA (CKS81; Rintanen Thm 10) | EXPTIME-c | tape in doors, transition audit | Generic, but needs an audit for every cell update; G6 packages this |
| 2CL (Hearn Thm 22-23, planar) | EXPTIME-c | variable gadgets, threat/lock races, timing-equalized pathways | Poor: needs two agents' move timing |
| DHL20 2-player (Thm 13) | EXPTIME-c (non-planar) | two robots, timers, any interacting RD gadget | Poor: two agents |
| ACDDGHL23 impartial shared robot (Thm 5.3) | EXPTIME-c | control alternates per traversal + ko | Poor: control alternation |
| ADHL shared-agent I/O (Def. 4.1) | PSPACE-hard, ∈ EXPTIME, **open** | Black/White fan-outs + I/O gadgets | Model matches; theorem missing |
| Bounded 2CL / QBF / Geography | PSPACE-c | single-use nature choices | Fallback if the nature fork is not reusable (N4 fails) |

## 7. Recommendation

Cite **G6** (Stockmeyer & Chandra 1979; restated verbatim in Hearn 2006 Thm 22 / Demaine-Hearn CCC 2008 Thm 5) for
hardness, and CKS81 for membership. Prove a new lemma: *one-agent motion planning with {directed open-optional SCD,
diode, crossover} plus nature forks is EXPTIME-hard (from G6)*, as in §5; mention that ADHL leave the I/O-gadget
version of this model open and that Rintanen's Thm 10 is its non-geometric analogue. Then the NetHack work reduces
to (i) re-checking that the Push-1F simulation layers are game-safe (risk 1) and (ii) finding a NetHack nature fork
satisfying N1-N4. Without a reusable fork (N4), the honest ceiling is PSPACE-hardness of R3 via bounded games.
