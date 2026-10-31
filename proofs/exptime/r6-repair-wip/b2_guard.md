### 3.7 Placement rule and guard lemma (review 6 repairs F1 + F2) — STRONG (argument), rule VERIFIED on the generated templates

Review 6 found that §3.3 is complete only under a placement rule nobody had stated: the HK placement (SO_i and SD_i
together on the chain, hooks to b_i and a_i) lets a b-hook that crosses floor become a wormhole before t (F2), and
L_gen's hooks crossed the g-side stubs of the component's own legs (GX) during its own checks (F1). The rule below
is Ani's own (Fig. 23) and is now what `L_gen.Router._checks` draws; `L_gen.validate_rules` replays it.

**Notation.** For a component (or, at level 1, an SCD composite) c with G′(c): its *region* R(c) = its window ∪ every
leg's g-side stub (location .. Wb) ∪ its hidden pockets ∪ its *wires* (below). M = all main-game floor (everything
that is not a chain corridor or a machinery interior); R(c) ⊆ M. The *chain* = the corridors of the check path
between machinery gadgets, walked in the Lemma 5.6 time order (level 1, then level 2; inside G′(c): pass 1 (Wt),
pass 2 (Wb), then the check walks).

**Placement rule P.**
- P1 (crossing gadgets) Every crossing gadget has its check line on the chain: a WCX's Bt→Tp line (delimiters,
  CHX, GX) or both lines of an SX (chain × chain, earlier line L→R). A WCX's hallway L–R lies on M. No port of
  check-line type (Bt, Tp, SX ports, SO Op/Out, SD entrance X) lies on M.
- P2 (Ani placement) For check i = (a_i, b_i) of G′(c): SO_i sits at b_i and SD_i at a_i: SO_i's In and SD_i's exit Y
  are joined to b_i resp. a_i by *wires*, corridors of M that cross nothing (length 0 after the box redraw); Op_i,
  Out_i and SD_i's entrance are on the chain. So the only chain edges of G′(c) after the passes are the chain-only
  edges Out_{i−1} → Op_i → SD_i (Out_0 = the end of pass 2, Out_k = c_out).
- P3 (no crossing of a wire) No chain crosses or touches a wire of c while c's check walks are pending. (L_gen: never
  at all; wires are reserved points.)
- P4 (no crossing of a pending region, F1) A crossing gadget whose hallway lies in R(c) (a GX on one of c's stubs,
  or a WCX on c's wire) is allowed only on a chain piece walked after G′(c) is finished. Crossings of c's middle
  segments (between Wb and Wt) are allowed on c's own chain piece only after both passes (they are dead then).
  At level 1 the own SCD's interior (= R(SCD) minus its tile legs) is never crossed by its own piece.

**Lemma G (guard: no machinery entry before t).** Under P1-P2, in every play prefix that has not visited t: the hero
stands on M, every SO, SD, SX is in its initial state, and every WCX is in state 1. Hence before t the level behaves
exactly as the main system with every WCX hallway read as a plain corridor and every wire as a dead end.
*Proof.* Induction on hero moves. Initially the hero is at s ∈ M and all machinery is fresh. Suppose the claim holds
up to some move and the hero stands on M. The gadget ports he can touch from M are, by P1-P2, exactly: (a) WCX
hallway ends L, R; (b) SO_i In (through b_i's wire); (c) SD_i exit Y (through a_i's wire); (d) t. In state 1 a WCX
allows from L or R only L↔R, back to M, state unchanged (B2_ani I_WCX, VERIFIED = concrete board, M-machinery.md);
a fresh SO has only Op→Op, so In is a dead end; a fresh SD has only X→Y, so Y is a dead end; (d) ends the prefix.
No chain corridor touches M except through such gadget ports (P1: the chain lives on wall points and crosses floor
only inside crossing gadgets; wires cross nothing, P2), so the hero cannot step onto the chain. ∎
Consequence: before t a winning strategy plays the main system (with raw components), which is exactly hypothesis
H1-H2's setting in GL; the wormhole of review 6 F2 (b-hook WCX entered from b_i) does not exist because no hook
carries a crossing.

**Lemma C (check walk).** Under P1-P4, every play that reaches c_out of G′(c) contains, after its first visit of t,
for each i in order: Op_i, SD_i (X→Y), a sequence of traversals of c's window from a_i ending at b_i that leaves R(c)
nowhere, and SO_i (In→Out); and every traversal of c's window between c's last Wb crossing and c_out is part of one
of these sequences.
*Proof.* (1) Chain monotonicity (Ani's "Tp only after Bt"): the first visit to any chain point after Out_i happens
after the first exit at Out_i, because a chain point is entered only from its corridor neighbours or from a gadget
port on it; a WCX's Tp needs an earlier Bt (I_WCX), an SX's second line needs its first, and those ports lie on the
chain before the point; induction over chain order. So Op_{i+1} (and every later SO) is unopened while the hero has
not left SO_i. (2) After both passes every leg of c is cut at Wb (WCX state 3 = hallway closed), so R(c) touches the
rest of the level only through gadget ports in R(c). By P2-P4 those are SD_j exits (one-way into R(c)), SO_j Ins,
and the closed delimiters: no crossing hallway lies in R(c) during c's checks (P4), and no wire is crossed (P3).
(3) Hence during check i the hero enters R(c) only through SD_i's exit at a_i (SD_j, j < i, used; j > i not yet
reachable by (1)), and leaves only through the In of an opened, unused SO, which by (1) is SO_i at b_i. Inside R(c)
he can only traverse c's window between its locations (the stubs and wires are dead-end corridors at locations).
∎ This is Thm 5.3's "got from a_i to b_i inside G only" for the drawn G′; with it, GL's H2 holds for the drawn G′
(Postselect(G, C, L′) with Ani's C, not a weaker C′ as in review 6 F1).

**Why P4 is stated with "finished" and not just "not own".** A WCX on c's stub crossed by an earlier G′'s piece is
harmless in the end (it is closed, state 3, before c's checks by (1)), but closing it would cut c's leg, and a WCX
on a pending component's stub is a live crossing of an undelimited region. L_gen therefore implements the stronger
rule of review 6: GX only on legs of G′s finished earlier in time.

**Machine evidence.** `L_gen.validate_rules` (every routed template): P2 contact geometry (OP / SD / OUT per check
in order, box–wire–location 4-paths, wires never used by a chain, wires off the coin halo), P4 replayed by time
order independently of the router's bookkeeping. `L_e2e.py`: every routed G′ rebuilt WITH its crossings
(ideal machinery, raw window): c_out reachable ⇔ clean, on all tile and crossover templates; positive controls
(review-6 HK placement + old rule: protodiode 2 → 3, the B→A state; HK placement with the new GX rule: still
not exact on the diode tile, i.e. F2 alone breaks it) and negative control (no delimiters) behave as required.
