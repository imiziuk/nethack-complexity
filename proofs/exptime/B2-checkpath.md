# B2: the global check path and its guards, lifted to the two-player R3 game

Workstream B2, 2026-10-29. Game not run, nothing committed. Files: this file, `tools/exptime/B2_ani.py` (Ani et al.
single-use machinery in our model), `tools/exptime/B2_e2e.py` (end-to-end hero-vs-nature check), an append to
INTERFACE.md. Inputs: B-reduction.md (§5.2), A-gadgets.md (§2, §3.3), A2-scd.md, C-audit.md (Z1-Z4), D-checker.md,
exptime-model.md, Ani–Chung–Demaine–Diomidov–Hendrickson–Lynch arXiv 2412.20079 §5 and §7 (PDF read this session:
text via PyMuPDF, Figs. 19-23 and 31-33 rendered and read; Fig. 32 boards transcribed from the vector drawings).
Labels: **VERIFIED** = machine-checked this session · **STRONG** = complete argument, not reviewed · **CONJECTURE** ·
**NEGATIVE**.

## 0. Results

| # | Claim | Status |
|---|---|---|
| R1 | Transcription of Ani's postselection machinery (Def. 5.2, Thm 5.3, Lemma 5.6, SO/MSC/SD/SX/WCX, Push-1F base gadgets) | VERIFIED read (§1) |
| R2 | **Game lift (Thm GL):** for a hero-vs-nature system whose only nature location is a coin outside every gadget, Ani's nonlocal simulation preserves the winner. Proof is per play: postselection is a property of single plays, so no pruning/Doom argument is needed | STRONG (§2) |
| R3 | No hero strategy that wins the concrete game ever breaks a gadget before its check; nature cannot break gadgets at all (coin moves only the hero, Z1) | STRONG (corollary of R2 + G3) |
| R4 | Fig. 32 Push-1F base boards (WMC, NR, WO) explored in our model: no block reaches a location cell (G1); D_game `--relation` agrees on all 135,276 entries | VERIFIED |
| R5 | Fig. 33 composites from the concrete boards = ideal Fig. 19 gadgets: **dicrumbler SD** (flat, 18,336 states), **SO** (concrete WO + verified SD), **MSC** (verified SD + concrete WMC): sound + complete | VERIFIED |
| R6 | Fig. 20 SX and Fig. 21 WCX from those = ideal SX / WCX (sound + complete), incl. WCX from concrete SO/MSC (286 states) | VERIFIED |
| R7 | Thm 5.3 needs G transitive; for the protodiode and proto-precursor the clean sets under chained check traversals equal A2's single-traversal clean sets (2 and 3 states) | VERIFIED |
| R8 | Global design (§3): order main game → CNF checker → t → SCD-level checks → component checks → g; every contact point between check machinery and main game is one of 5 guarded kinds; only single-use (LDAG) machinery on the check path, no reusable crossover needed there; no holes, pits or traps | STRONG |
| R9 | **End-to-end two-player instance** (raw checkable SCD from A2 = 2 proto-precursors + 2 protodiodes, coin, full two-level check path, a CHX on the coin hallway; 139 gadgets, 5.94 M positions): winner = ideal winner in both variants; without the check path the hero wins the "lose" variant by the O→J leak; with only component checks he still wins it (the SCD-level check is necessary) | VERIFIED (abstract gadget level, §4) |
| R10 | Size: polynomial, O(N⁴) check-path gadgets in B's bus layout (§3.6) | STRONG |

**Verdict:** with R2 the last structural gap of B §5.2 (A-gadgets §3.3) is closed at the level of argument, and the
reduction G6 ≤_p L_OFF^{W+C} (R3) is complete **modulo review** and modulo the layout items in §5 (planar routing of
the check path drawn by a generator, not machine-checked; a full NetHack-level D_game run is infeasible at this size).

## 1. Ani et al. §5: how checkable gadgets give a one-player reduction (transcription)

**Def. 5.1 (nonlocal simulation).** A set 𝒢 [planarly] nonlocally simulates H if for every gadget set 𝒢′ there is a
poly-time reduction from [planar] reachability with {H} ∪ 𝒢′ to [planar] reachability with 𝒢 ∪ 𝒢′. (Local simulations
are nonlocal ones, Lemma 2.2.)

**Def. 5.2 (postselection).** Gadget G, checking sequence C (traversals on L(G)), L′ ⊆ L(G). A state is *broken* iff
C is not legal from it. Assumption: broken is preserved by transitions on L′. Postselect(G, C, L′) = G restricted to
locations L′ and non-broken states. Key identity: X is legal for Postselect from q **iff XC is legal for G from q**
("forcing the agent to traverse C after solving reachability"). G is a *checkable* G′ if Postselect(G, C, L′) ≅ G′.

**Thm 5.3.** For any G, C, L′ as in Def. 5.2, {G, SO, MSC} planarly nonlocally simulates Postselect(G, C, L′).

Base gadgets (Fig. 19; all "LDAG", bounded state changes):
- **SO** single-use opening: 1 –(Op→Op)→ 2 –(In→Out)→ 3, state 3 dead.
- **MSC** merged single-use closing: 1: L↔R free; T→R → 2 (dead).
- **SD** dicrumbler: X→Y once, then dead (= state 2 of SO, = MSC on its closing pair).
- **SX** single-use crossover (Fig. 20, from SO + 3 SD): L→R once, then Tp→Bt once.
- **WCX** weak closing crossover (Fig. 21, from 3 SO + 3 MSC + 3 SD): 1: L↔R free (any number of times);
  Bt→Tp → 3 (dead); Bt→L or Bt→R → 2 ("leak"); 2: L↔R, L→Tp, R→Tp (→ 3). Property used: *exiting at Tp requires
  an earlier entry at Bt*. It is a "checkable hallway crossover" (Lemma 5.6's CHX).

**Def. 5.5 / Lemma 5.6 (global chain).** G′ is *simply checkable* G if L(G′) = L(G) ⊔ {c_in, c_out}, f: Q(G) → Q(G′),
(3) X legal for G ⇒ X·[c_in→c_out] legal for G′ from f(q), (4) every legal sequence of G′ **ending at c_out** has the
form X·[c_in→•, …, •→c_out] with X legal for G (sequences not ending at c_out may do anything). Lemma 5.6: replace
every copy G_i by G′_i, connect t → c_in,1, c_out,i → c_in,i+1, new target t′ = c_out,n; every crossing of this
chain with an existing edge gets a CHX whose check line lies on the chain. Proof (one player): backward induction —
c_in,i+1 is reachable only from c_out,i (ignoring CHX hallway traversals), c_out,i only after c_in,i (property 4), so a
solution reaching t′ visited t first; the prefix X up to the first visit of t, with CHX hallway traversals deleted,
is a solution of the original system, because every c_in,i is after t, so the G′_i-part of X is a prefix of a
legal X_i and X_i·C is legal.

**Thm 5.3 proof (construction G′, Fig. 23).** Locations of G on top; for each l ∈ L′ a long edge e_l up to l′ on a
line L. From c_in the *checking path* crosses every e_l in a rightward pass (top delimiter), turns down, crosses every
e_l again in a leftward pass (bottom delimiter). For each check a_i → b_i: SO O_i near b_i, SD D_i near a_i;
O_i's opening location → D_i entrance; D_i exit → a_i; b_i → O_i entrance; O_i exit → O_{i+1}'s opening; O_k exit →
c_out. Crossings of the checking path with e_l: WCX oriented so the path closes e_l; with itself: SX. Correctness:
backward from c_out: O_i exits only after its opening, WCX tops only after their bottoms, so the agent entered c_in,
crossed every e_l twice (closing all of them: **the gadget is cut off from the system**), then for each i opened O_i,
went through D_i, got from a_i to b_i *inside G only* (all e_l closed), and passed O_i. Between c_in and the end of
the delimiters the agent may leak through L′ (sequence Y); XYC legal ⇒ XC legal because broken is preserved by
L′-transitions. **Why broken states only hurt:** a broken state makes C illegal, so no solution can end in it, and
by preservation no solution can pass through it; postselection removes exactly the moves no solution uses.
Hidden locations L∖L′ (D, G of the proto-precursor) are wired only to check machinery.

**Push-1F realization (§7, Figs. 31-33).** Base boards: weak merged closing WMC (2 blocks; like MSC but closing
repeatable), no-return NR (3 blocks), weak opening WO (6 blocks; exit usable only after both inputs visited
separately). Fig. 33: SD = WMC + NR (vertical) + NR + WO; SO = WO + 4 SD; MSC = SD + WMC. Then Figs. 34-37:
checkable protodiode → diode, checkable proto-precursor → precursor → 1-toggle → checkable SCD (A2: VERIFIED).

## 2. Lift to the two-player R3 game

### 2.1 Setting
A *system with nature* 𝒮 = gadgets + hallways + **coin nodes** (arriving at a coin, nature picks the continuation
among its outcomes) + start s + target t. Full information; hero wins iff he forces reaching t; infinite plays lose
(B §2.1, exptime-model R3). 𝒮′ := Ani's construction applied to 𝒮 (Thm 5.3 G′ around every checkable gadget, Lemma
5.6 chain from t to t′, CHX at chain crossings), coin nodes unchanged. Hypotheses:
- **H1** coin nodes are hallway nodes of 𝒮 (never inside a gadget or inside check machinery); nature has no other
  choice (C-1: all other RNG leaves the π-relevant data unchanged).
- **H2** every checkable gadget G satisfies Def. 5.2 *and* Postselect(G, C, L′) is related to its ideal gadget by
  A's two **simulations** (sound + complete, A-gadgets §1; A2 VERIFIED for diode, precursor, 1-toggle, SCD).
- **H3** the single-use machinery (SO, MSC, SD, SX, WCX) satisfies Ani's one-player properties (R5-R6 VERIFIED).
- **H4** the intended check walk t → t′ never enters a coin node (the chain is drawn around the coin tile; §3.5).

### 2.2 Theorem GL — STRONG
Under H1-H4: the hero wins 𝒮′ (to t′) ⇔ the hero wins 𝒮 (to t), with every checkable gadget of 𝒮 read as its ideal.

*Single-play lemma (Ani's proof, unchanged).* Let π be one play of 𝒮′ (a sequence of gadget traversals and coin
outcomes) that reaches t′. Then π visits t, and the prefix π_t up to its first visit of t, with CHX hallway traversals
deleted, is a legal play of 𝒮 with every checkable G_i replaced by Postselect(G_i): the argument of §1 is about the
legality of one traversal sequence and never uses who chose the moves; coin steps are hallway steps for it.
Consequently every raw component is **clean at every time of π_t** (clean at its check, and broken is absorbing).

(⇒) Let σ′ win 𝒮′. Define σ on 𝒮-histories consistent with it: an 𝒮-history h fixes the coin outcomes so far; replay
σ′ against exactly these outcomes (nature in 𝒮′ has the same coin and nothing else, H1) to get the 𝒮′-history h′
whose projection is h; σ(h) := the projection of σ′'s continuation up to its next ideal traversal or coin entry
(finite: σ′ wins). Every σ-play π is the projection of a σ′-play π′ with the same coin outcomes; π′ reaches t′, so by
the single-play lemma π′ visits t with all components clean up to then, and each concrete clean→clean traversal is an
ideal traversal under the sound simulation (H2). So π reaches t: σ wins 𝒮.
(⇐) Let σ win 𝒮. The hero plays σ in 𝒮′ via the complete simulations (H2: every ideal traversal realized, ending
clean; machinery hallways — WCX in state 1 — are unboundedly reusable, H3); nature's coin outcomes are the same. At
t all components are clean, so by property (3) of each G′ and of each CHX the deterministic check walk exists, and it
needs no nature move (H4). So he reaches t′.

*Why no pruning lemma is needed.* A's pruning lemma (delete hero moves into Doom) is true but the per-play argument
is stronger: whatever a concrete winning strategy does after t (leaking back into the main game through a WCX, even
playing the coin again) is irrelevant, because the projection stops at the first t.

*Simulation vs. trace.* Ani's local simulations are trace-based. In a game that is not enough in general (a gadget
that makes the hero commit to an internal state before a coin flip is trace-equivalent but loses). GL needs
**simulation only for the gadgets used before t** (H2: A/A2 checked simulations). The single-use machinery is used
before t only through hallways (WCX state 1, MSC hallways) and dead ends (closed SO entrances, SD exits), and after t
the game is one-player, so trace facts (property (4), "Tp only after Bt") suffice for it.

### 2.3 R3 — who can break a gadget — STRONG
- **Nature:** the coin moves only the hero, to A or B (W9), never a boulder (Z1: no boulder closure R_B reaches
  Z ∪ N8(Z) ∪ {E} ∪ N8(E)); C-1: no other RNG moves boulders. So nature never changes a gadget state.
- **Hero:** by the single-play lemma no play consistent with a winning strategy breaks a component before its check
  (it would be broken at its check: absorbing, G3). Breaking after its check is harmless and possible (B2_e2e sees
  such winning positions only after the component's first SD was used).
- **Counterexample search:** none found. The candidate failure modes and why they fail: (a) leaving through a WCX
  leak after t and playing the coin again — irrelevant to the projection; (b) entering machinery before t — every
  contact point is guarded (§3.3); (c) a check passed by a detour outside the gadget — impossible after the
  delimiters cut every e_l; (d) the coin inside a check-path segment — excluded by H4; (e) trace-but-not-simulation
  gadgets before t — excluded by H2.

## 3. Design of the global check path

### 3.1 Order and goal — decision
g is reachable only if **F is true AND all gadgets are clean**: main game → P → CNF checker (c₀ … c_m, B §3.1 item 5)
→ **t := c_m** → chain level 1 → chain level 2 → **g**. The formula check comes first because it uses gadgets
(the S² tunnels of the literal doors); the cleanliness checks after it certify the whole play including the formula
check (single-play lemma covers every time before t).
- **Level 1 (SCD-level, Ani Fig. 37 check [O→O, I→J]):** one Thm 5.3 wrapper G′ per SCD (literal-door SCDs, TS
  context SCDs, nature-module context doors, the 20 SCDs of every Lemma 2.6 crossover), each around the SCD
  composite whose components are the *postselected* precursor / 1-toggle / diodes; Lemma 5.6 chain t → … → t₁.
- **Level 2 (components):** one G′ per raw component (every proto-precursor, checks [A→D, C→G, B→A, B→C],
  L′ = {A,B,C,E,F}, D/G hidden; every protodiode, checks [A→C, D→B], L′ = {A,B,C,D}, C–D joined *outside* G′),
  including the diodes at the start of every route edge and those inside SCDs; chain t₁ → … → g.
This is Lemma 5.4's composition of the two nonlocal simulations; under GL it is applied twice (level 2 first in the
proof: from a play reaching g, the prefix to t₁ is a legal level-1 system play; from that, the prefix to t is legal for
the ideal system). It matches A2's order (SCD check first, then component checks) and A2's NEGATIVE result that the
SCD-level check alone is unsound (B2_e2e "complevel"/"scdlevel" show both levels are needed).

### 3.2 Why the delimiters are needed in our setting (not just in Ani's)
Without cutting e_l, a check a_i → b_i can be passed by a detour through the rest of the level: e.g. the protodiode
broken state e2 fails [D→B] inside the gadget, but with C–D joined D→C→B succeeds (A-gadgets table: e2 has C→B).
Hence C–D (and the A, B, C legs of the precursor's T junction) must be separate e_l with delimiters, joined only
beyond the top delimiter. After both passes every component is an island, and the coin is unreachable.

### 3.3 Guards: every contact point between check machinery and the main game
| Contact | Main-side behaviour before t | Why safe |
|---|---|---|
| t = c_m | the only entry of the chain | checker is a dead end ending in t (B Fact R) |
| D_i (SD) exit at a_i | dead end (SD is one-way, X→Y) | SD state 1 has no Y-side traversal |
| O_i (SO) entrance at b_i | dead end until O_i's button is pressed | button reachable only from O_{i−1}'s exit / c_in |
| hidden D, G of a proto-precursor | private pocket reachable from inside the component | attached only to O_i entrances (closed); A2 VERIFIED broken absorbing with D/G pockets |
| WCX on e_l (delimiters) and CHX on chain crossings | plain hallway L↔R, any number of times | WCX state 1 = hallway; Tp only after Bt (VERIFIED R6) |
Guards are single-use (SO, SD, MSC, SX, WCX are LDAG) — fine because the check path is traversed once; the only part
used exponentially often is the WCX/MSC hallway in state 1, which is a stateless self-loop (VERIFIED complete: the
WMC board realizes L↔R from its initial state with no state change).

### 3.4 Crossovers and the recursion question
- **check path × main route:** a WCX (closing crossover) — no reusable crossover needed: the main traffic only uses
  its hallway, the check path crosses once and closes it.
- **check path × check path:** SX (Fig. 20), single use in the fixed time order (earlier segment = horizontal pass).
- **main × main:** Lemma 2.6 SCD crossover (A2 VERIFIED abstract), its 20 SCDs are ordinary SCDs checked at level 1,
  their diodes/precursors at level 2.
- **Recursion:** the machinery is *exact* (no postselection: R5-R6 show the Push-1F SO/MSC/SD/SX/WCX simulate the
  ideal ones outright), so there are no "checks of checks"; level-1 machinery is itself crossed by the level-2 chain
  through CHX hallways (Lemma 5.6 is generic). The recursion bottoms out after two levels.
- **Holes / G_D / G_X** (hu-on-lower) are not needed. Not using them keeps Z3 (pits) moot and avoids G_X's
  route-merging after its K pass.

### 3.5 The coin
The coin tile (B §6.2, [A wall T wall B], Z1/Z2) sits outside every gadget and outside all machinery. Place it on the
outer face below the tile row, so the chain can stay in the region above (H4); if a chain segment has to cross a coin
corridor (E_C or the ≥ 3-cell exit corridors), it does so with a CHX at Chebyshev distance ≥ 3 from Z ∪ {E}, so the
CHX boulders (confined to their windows, R4) keep Z1. The intended check walk never enters T, so Z4 (dead coin
phase) and C-4 do not apply to it.

### 3.6 Size and planarity — STRONG
Per G′: 2|L′| delimiter WCX, |C| SO + |C| SD, plus O(|C|·(|L′| + |C|)) routing SX/WCX: protodiode ≤ 8 + 4 + 16, proto-
precursor ≤ 10 + 8 + 36, SCD composite ≤ 6 + 4 + 10. Base cost: SO = 1 WO + 4 SD, SD = 1 WMC + 2 NR + 1 WO (11 blocks),
so SO = 50 blocks, MSC = 13, WCX ≈ 3·50 + 3·13 + 3·11 = 222 blocks. Chain (Lemma 5.6): n checkable gadgets, each chain
segment crosses ≤ E route edges: O(n·E) CHX. In B's layout n, E = O(N²) (crossovers dominate), so O(N⁴) machinery
gadgets, each O(1) cells: the map stays polynomial (O(N⁴) cells; B §6 said O(N²) — update). Planarity: Thm 5.3 and
Lemma 5.6 are planar constructions (WCX/SX at every crossing); our main network is planar after Lemma 2.6.
Log-space computability is unaffected (fixed patterns indexed by counters).

## 4. Machine checks

**B2_ani.py** (`python B2_ani.py`, ~1 min; `--full` adds the flat concrete SD, ~5 min):
| Item | Result |
|---|---|
| Fig. 32 boards (transcribed, below) | WMC 6 states, NR 147, WO 123; no block reaches a location cell; COMPLETE vs my reading of Fig. 31; NOT sound vs it (the "weak" gadgets have extra leaky traversals, e.g. WMC R→T after closing — harmless: they are never used alone) |
| SD = WMC + 2 NR + WO (flat concrete) | 18,336 states, SOUND + COMPLETE vs ideal SD |
| SO = concrete WO + 4 verified SD | 13 states, SOUND + COMPLETE, trace-sound |
| MSC = verified SD + concrete WMC | 2 states, SOUND + COMPLETE |
| SX (ideal parts / concrete SO,SD) | SOUND + COMPLETE (6 / 86 states) |
| WCX (ideal parts / concrete SO,MSC + verified SD) | SOUND + COMPLETE (11 / 286 states) |
| transitive vs single-traversal clean sets | equal (protodiode 2, proto-precursor 3) |
| D_game `--relation` vs A_core chained traversals, 3 boards | 252 + 43,512 + 91,512 entries, 0 mismatches |
Substituting a verified composite by its ideal inside a larger network uses "simulation equivalence is a congruence
for network composition" (STRONG, standard; the SD-level substitution is the only place it is used outside A/A2).

Fig. 32 transcriptions (`#` wall, `.` floor, `0` block, capitals = location cells at the openings):
```
WMC        NR            WO
###T#      ##########    ####T##
#.0.#      ####.0.###    L.##.##
##0##      L.##.0...#    #..00.#
##.##      #...0.##.R    #000.##
##..R      ###...####    #.0.###
L..##      ##########    ##.####
#####                    ##.####
                         ##....R
                         ##.####
                         #######
```

**B2_e2e.py** (`python B2_e2e.py`, ~15 min, dominated by the broken-position count of the flat run; modes can be
selected on the command line: `ideal raw scdlevel complevel checked`). Instance: start region holds the SCD button O and a hallway (with a CHX)
to the coin; coin outcome α → entrance I, β → back to start ("lose") or → I ("win"); exit J → t. SCD starts closed.
| Mode | lose variant | win variant | positions |
|---|---|---|---|
| ideal SCD, goal t | LOSE | WIN | 8 |
| raw A2 composite, goal t (no checks) | **WIN** (O→J leak) | WIN | 78,446 |
| postselected components + SCD-level G′, goal g | LOSE | WIN | 1,129 |
| raw components + component G′s only, goal g | **WIN** (leak undetected) | WIN | 2,518,901 |
| **raw components + both levels (flat), goal g** | **LOSE** | **WIN** | 5,936,813 |
In the flat run (139 gadgets: 4 raw windows, 43 WCX, 14 SO, 14 SD, hallways) 5,928,555 reachable positions have a
component that is broken while its own check has not started (first SD unused); **none of them is winning** (both
variants). Limits: the
machinery enters as ideal automata (verified in B2_ani), the planar-routing crossings inside G′ (SX on the delimiter
path, WCX on dead middle segments) are omitted, and walking is abstracted to gadget traversals (exact for windows
by G1; A2 cross-checked A_core against D_game). A NetHack-level D_game run of the same instance would need ≈ 43·222 +
14·50 blocks: infeasible, and not needed beyond R4.

## 5. What remains (ranked)
1. **Review** of GL (§2.2) and of the two-level composition (§3.1) — the only new mathematics here.
2. **Layout generator**: the planar drawing of Thm 5.3's G′ around each component and of the Lemma 5.6 chain in B's
   bus layout (port positions of the Fig. 32/35/36 windows, corridor bends, WCX/SX placement, coin on the outer
   face). Not built; only planarity-by-construction (Ani) is cited. C should then compute R_B for Z1 on a generated
   instance (C-audit §7 item 1).
3. B §6 size statement: O(N²) → O(N⁴) cells (still polynomial).
4. Fig. 31 reading: the base boards are not sound vs my reading of the state diagrams; irrelevant for the proof
   (only composites are used, and those are verified), but the paper's diagrams may have more transitions than I
   transcribed.
5. Unchanged from B §7: G6 conventions (who moves first) and C's open whitelist rows.
