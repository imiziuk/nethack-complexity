# Open L_ON variants (b) and (c): classification

Proof agent, 2026-10-29. Source: NetHack 5.0.0 @ 16ff591, read-only; nothing built or run. Paths `src/<f>` =
`src/src/<f>`, `include/<f>` = `src/include/<f>`. Labels: **[src f:l]** read this session · **[conj]** my reasoning,
not machine-checked · **[ext]** published theorem · **[assump]** spec/modelling choice.
Binding: phase2-spec.md (incl. Revisions 1-2: harness order, mandatory prefix, `pettype:none`, whitelist W_ON),
hu-off.md (f, Lemmas S/C), hu-on-upper.md (Lemmas 1, 2, N, H), hu-on-lower.md, review-2.md.

## 0. Results

| Variant | Claim | Status |
|---|---|---|
| (b) L_ON^W, R2, **no rule S** | **PSPACE-complete** (Thm B1 hard via Push-1F, Thm B2 member) | STRONG-draft: new steps all source-read; inherits hu-off's [ext]/audit gaps |
| (c) L_ON^W, R3 (∀ outcomes, full information, adaptive hero) | **NP-hard** (Thm C1) and **∈ PSPACE** (Thm C2) | C2 solid modulo Lemma H/2; C1 inherits hu-on-lower's open items |
| (c) exact class | open: ∈ NP iff a "pessimal adversary" lemma holds (conj, water-free fragment); no PSPACE-hardness gadget found | §C.3 |
| (c') R3 open-loop (one fixed command sequence must win for all outcomes) | NP-hard, ∈ Σ2^P | §C.4 |

**Correction to claims F12 (and hu-on-upper G1 wording):** starvation is *also* checked while fainted. When
`is_fainted()`, `u.uhs == FAINTED (5) > WEAK (3)`, so the roll `rn2(20 - h/10) >= 19` is evaluated
[src eat.c:3414-3416] and a roll < 19 reaches the starvation test [src eat.c:3437]. This changes nothing under R2 (the
player picks ≥ 19) but matters for R3 (§C.1). Correct F12 to: "starvation is only checked when the faint roll fails;
the roll is made at every `newuhs` call with h ≤ 0 and u.uhs ≥ FAINTING, fainted or not."

## 1. The hunger mechanics, traced exactly

Enum: SATIATED 0, NOT_HUNGRY 1, HUNGRY 2, WEAK 3, FAINTING 4, FAINTED 5 [src include/hack.h:565-570].

**Tick structure** [src allmain.c:206-383]. The hero has speed 12 = NORMAL_SPEED (no Fast, XL1; hu-off I8), so each
`moveloop_core` iteration with `context.move` runs exactly one tick block. Inside it, in order: `ublesscnt--`
[allmain.c:276-277], ..., `gethungry()` [allmain.c:354], `exerchk()` [:356], then `if (multi < 0 && ++multi == 0)
unmul()` [allmain.c:375-382]. `unmul` calls `afternmv` [src hack.c:4200-4205]. After the block the hero acts iff
`multi == 0` (`rhack(0)` [allmain.c:536]).

**gethungry** [src eat.c:3163-3332]: returns at once if `u.uinvulnerable` [:3167]. Else `u.uhunger--` if
`!Unaware || !rn2(10)` (human, no Slow_digestion) [:3174-3179]; `accessorytime = rn2(20)` adds −1 only for
Stressed+ / Regeneration / Hunger / Conflict / rings / amulets (none in W_ON, unencumbered hero); then
`newuhs(FALSE)` [:3332]. `Unaware = multi < 0 && (unconscious() || is_fainted())` [include/youprop.h:399].

**newuhs** with h = u.uhunger ≤ 0 (newhs = FAINTING) [src eat.c:3410-3447]. Let hd = sgn(h)·((|h|+5)/10) ≤ 0.
- if fainted: newhs := FAINTED [:3414].
- if `u.uhs <= WEAK` (first entry from WEAK, **forced**) or `rn2(20 − hd) >= 19` (possible for every h ≤ 0 since
  20 − hd ≥ 20): if not fainted and `multi >= 0`, faint: `nomul(−d)`, d = 10 − hd = 10 + (|h|+5)/10,
  `afternmv = unfaint` [:3416-3432]; if already fainted, nothing.
- else (roll ∈ [0, 18], always possible): if h < thr := −(100 + 10·ACURR(A_CON)) the hero dies [:3437-3446];
  otherwise nothing, and the hero stays FAINTING and aware.
- `unfaint` sets `u.uhs = FAINTING` [src eat.c:3336-3343].

**One faint cycle** (hero aware, uhs = FAINTING, faint chosen at tick k): tick k decrements (aware) and sets
multi = −d, then `++multi` → −d+1. Ticks k+1..k+d−1 are Unaware (decrement only on `!rn2(10)`; the roll may be
≥ 19 = no-op). At tick k+d−1 multi hits 0, `unfaint` runs, and the hero gets **exactly one action** (a timed action
uses the tick's movement; speed 12). At tick k+d the hero is aware again: forced decrement, then a new roll.
So a cycle = d ticks, ≥ 1 forced unit of nutrition, exactly one hero action.

**Prayer** [src pray.c:2124-2175, 2259-2270, 2276-2330, 1071-1385, 398-411]. `in_trouble` returns major
TROUBLE_STARVING iff `u.uhs >= WEAK` [pray.c:216-217]. p_type 3 iff ublesscnt ≤ 200 (major trouble), Luck ≥ 0,
ugangr = 0, record ≥ 0. Then `nomul(−3)`, `uinvulnerable = TRUE` (gethungry inert, so uhs stays FAINTING), and
`prayer_done` → `pleased`. Valkyrie initrecord = 0 [src role.c:523-525 (xlev 10, initrecord 0), attrib.c:1094; field order
include/you.h:221-222], so `record < STRIDENT (4)` and `action = (record > 0 || !rnl(2)) ? 1 : 0` [pray.c:1129-1130];
record only rises (`adjalign(1)` when record < 2 and trouble ≤ 0 [pray.c:1088-1089]), so action ∈ {0,1} always.
Action 1 with trouble > 0 → `fix_worst_trouble(TROUBLE_STARVING)` → `init_uhunger()`: h = 900, uhs = NOT_HUNGRY,
ATEMP(Str) = 0 [pray.c:404-411, eat.c:126-134]. Then `ublesscnt = rnz(350)` (+ `min((moves−10^5)/100, 32767 −
ublesscnt)` if moves > 10^5) [pray.c:1356-1377]. `rnz(350)` ∈ [35, 3498] (tmp ∈ [1000, 1999]·rne(4), rne ≤ 5 at
XL1 [src rnd.c:192-229]). Hence ublesscnt ≤ 32767 after every success.

**Exercise** [src attrib.c:509, 598-640]: abuse adds `−rn2(2)` to AEXE, exercise adds `rn2(19) > ACURR`; a test
changes an attribute only if `rn2(50) ≤ |AEXE|·2/3`. Hunger abuse: Weak → Str, Fainting/Fainted → Con, Not Hungry →
Con exercise [attrib.c:520-547].

## B. Variant (b): L_ON^W under R2 without rule S

### B.0 Answer to the key question
Without prayer: the hero can **act forever** under R2. While h ≥ thr the player picks roll < 19 every tick: one
action per tick, 1 nutrition each. Below thr every non-faint branch is death, so the player picks ≥ 19 at every
`newuhs`: one action per faint cycle, h falls by exactly 1 per cycle (Unaware decrements skipped), and d = 10 +
(|h|+5)/10 grows. There is **no** point where all branches kill: the faint branch exists for every h ≤ 0. The only
limit is the int width of u.uhunger (W_C; `abs(INT_MIN)` at eat.c:3412 is the first overflow), after ≈ 2^31 cycles.
With prayer the overflow is never approached: h stays in [−720, 900] forever (Lemma B.1). So alive plays are
unbounded with ≥ 900 freely chosen actions per prayer cycle, and every extra RNG outcome only decides *when*
the hero acts.

### B.1 Lemma (perpetual action under R2) [src as cited in §1; arithmetic conj]
Policy Π for choosing outcomes, from any state with Luck 0, ugangr 0, record ≥ 0, no damage source:
(i) `newuhs` roll: < 19 if h ≥ thr (and not fainted), else ≥ 19; (ii) Unaware decrement: `rn2(10) ≠ 0` (skip);
(iii) exercise: `rn2(2) = 0` / `rn2(19) ≤ ACURR` (AEXE never moves, attributes constant); (iv) prayer: `rnl(2) = 0`,
`rnz` minimal; (v) everything else arbitrary. Hero rule: at the first hero turn with u.uhs ≥ WEAK and
ublesscnt ≤ 200, `#pray`; otherwise do the intended action.
Claim: under Π the hero never dies, gets a turn at least once per 86 ticks, and h ∈ [−720, 900].
Proof. Deaths from hunger need branch (else, h < thr), which Π never takes. The hero's turns: ≤ d ≤ 10 + 72 + 3
ticks apart. Between two prayers (or the start and the first), ublesscnt − 200 ≤ 32567 ticks pass before a
prayer is allowed (ublesscnt drops by 1 per tick [allmain.c:276-277]; after success ≤ 32767). h drops from 900 to 0
in ≤ 900 ticks; after that each cycle of d ≥ 10 + (|h|+5)/10 ticks costs at most 1 (the aware tick; at most one
"no-faint" tick per unit while h ≥ thr). Σ_{j=1}^{k}(10 + j/10) ≥ 32567 already at k = 713, so h ≥ −714 − 1 when
ublesscnt ≤ 200 is reached; the next hero turn (≤ 85 ticks later, ≤ 1 more unit) prays with p_type 3 (uhs ≥ WEAK →
major trouble; Luck/ugangr/record unchanged: no source in W_ON, hu-off I5) and `pleased` with action 1 restores
h = 900 [pray.c:404-411]. ∎ Moves overflow (W_C wrap, hu-off SC3) only makes `incr` 0 → shorter timeouts.

### B.2 Theorem B1: L_ON^W (R2, no S) is PSPACE-hard
Reduction f_ON(I) := hu-off's f(I) **without** `hunger=false` (S keeps `mongen=false`, `u.clear_inventory()`, cursed
loadstone, `noflip`, `sokoban`, sentinel pit, boulders, one-cell teleport region; template `pettype:none`). All of it
is in W_ON (BOULDER, LOADSTONE, PIT; walls/floor) [assump: spec Rev 1 item 3]. No food is placed.

**Lemma S_ON (soundness, every command, every outcome).** hu-off Lemma S holds verbatim, with invariant I9
("hunger inert") replaced by:
I9'. Hunger code changes only u.uhunger, u.uhs, ATEMP(Str) (−1 at Weak [eat.c:3449-3456]), HDeaf, multi/afternmv
(faint), AEXE/attributes (exercise), and can kill (starvation). `stop_occupation` and `selftouch("Falling, you")`
[eat.c:3421-3431] touch only the inventory (no cockatrice corpse exists). None changes π = (hero square, boulder set).
Exceptions to check, each closed:
- Encumbrance: I3 (never squeezable) needs only `inv_weight() > −850`, true for any wc ≤ 1000 with the 500 stone
  [hu-off I3; src hack.c:139-163]. Lower Str/Con only restricts movement (`carrying_too_much`), never adds moves.
- Prayer: hu-off §B.5 holds with one more reachable major trouble, TROUBLE_STARVING, whose fix is `init_uhunger`
  only. Action ∈ {0,1} always (§1), so case 2/3 never run: the loadstone stays cursed (I2), no minor fix.
  TROUBLE_HUNGRY (minor, −8 [pray.c:98, 275-276]) needs action ≥ 3: never fixed.
- Faint/Unaware: no monsters, no gas, nothing moves the hero while helpless (hu-off I1, I6). `reset_faint` callers
  (drown etc.) are unreachable (no water in f_ON).
- Starvation: death = loss; only removes plays.
So every reachable state of f_ON(I) has π reachable in Push-1F from (s, B₀), or the hero is dead. [conj, as hu-off]

**Lemma C_ON (completeness).** If Push-1F moves m₁..m_t reach g, then the R2 play "perform mᵢ at the hero's
turns in order, inserting `#pray` per the B.1 rule, outcomes per Π" ends alive on g at a player-turn start.
Proof. By B.1 the hero never dies and gets infinitely many turns, so all t moves are executed (t may be
exponential: fine, R2 asks for a finite play). Each mᵢ executes exactly as in hu-off Lemma C: hunger state does
not appear in `domove`/`test_move`/`moverock` [grep: hack.c reads u.uhunger only at :670, :730 (metallivore,
eating boulders/iron), not reachable for a human]; the hero is unencumbered even at Weak, since
wc = 25(Str+Con)+50 ≥ 25·19+50 = 525 > 500 with base Str+Con ≥ 20 (hu-off §1) and Π keeps attributes constant
[src hack.c:4311-4337 via hu-off]. Prayers do not move π (Lemma S_ON). The last action mₜ is followed by a
player-turn start with multi = 0 (if the tick after mₜ starts a faint, the hero is still on g at the next turn
start, alive). ∎

**Theorem B1.** I ∈ Push-1F ⇔ f_ON(I) ∈ L_ON^W(R2, no S). With [ext] Push-1F PSPACE-hard (F15), L_ON^W (R2, no S)
is PSPACE-hard. ∎ Note: f_ON is **not** answer-level DET (under ∀ the hero starves), so this says nothing about
R3; see §C.

### B.3 Theorem B2: L_ON^W (R2, no S) ∈ PSPACE
Lemma 1' (poly state, **no horizon needed**). hu-on-upper Lemma 1 bounds floor records by 52·(T+1); replace that
row: every object record has quan ≥ 1, the total quantity Σquan never increases (creators in W_ON: only `punish`,
≤ 2 records, once [src pray.c:744-750, read.c:3019-3035]; splits conserve Σquan; eating/plugging/burying/sinking
remove units), and cookie quantities are unary (spec Rev 1 item 3). So #records ≤ Σ initial quantities + w·h
(mineralize) + 2. Traps, engravings (≤ 1 per cell), terrain (pool → floor only) are ≤ w·h. Counters are W_C words
(u.uhunger, moves, multi, ublesscnt wrap per SC3). The faint duration is a counter in `multi`, not a structure.
Lemma 2 (poly step) is unchanged and does not use T. Hence a nondeterministic poly-space machine guesses commands
and (R2) outcome vectors tick by tick and accepts at "alive on g at a turn start" → NPSPACE = PSPACE
[ext: Savitch 1970]. ∎ [conj: same status as hu-off Thm A]
Corollary: **L_ON^W (R2, no S) is PSPACE-complete.**

Remark (any fixed integer semantics). B2 needs only that every scalar has a fixed width; whether overflow wraps or is
declared a loss does not matter. B1 never overflows (h ∈ [−720, 900]) except `moves`, handled as in hu-off SC3.

## C. Variant (c): L_ON^W under R3

Definition [assump]: R3 = full-information game; the hero wins iff some adaptive strategy (commands as a function of
the history, including all RNG outcomes so far) reaches "alive on g at a turn start" against **every** outcome
sequence. Infinite plays are losses. Per spec: no rule S (S is not needed: §C.1).

### C.1 Lemma K (kill nodes) [src eat.c:3410-3446; game-theoretic step conj]
Call a position a *kill node* if the next RNG call is the `newuhs` roll with h ≤ 0, u.uhs ≥ FAINTING and
h < thr (thr read at that moment). There the adversary picks a roll < 19 and the hero dies (eat.c:3437, fainted or
not, per the F12 correction). So in the R3 game every kill node is losing for the hero, and pruning all other
adversary moves at kill nodes does not change the winning region: in the attractor computation for the hero's
reachability objective a universal node with a losing successor is never in the attractor, in either game.
**Consequence:** every play that matters (passes no kill node) satisfies
h ≥ thr − 2 ≥ −352 at all times. Reason: h drops only in `gethungry` (≤ 2 units per call in W_ON: base 1, +1 for
Stressed+ [eat.c:3174-3196]), and every `gethungry` that does not return early ends in `newuhs`. A drop below thr
from h > 0 (uhs ≤ WEAK, the forced-faint branch without starvation test) is impossible since thr ≤ −130 (Con ≥ 3).
A Con decrease by `exerchk` can raise thr above h for at most the rest of that tick plus one hero action; the next
`newuhs` is a kill node. Con ≤ 25 gives thr ≥ −350 [hu-on-upper §1].

### C.2 Theorem C2: L_ON^W (R3) ∈ PSPACE
Proof. hu-on-upper Lemma H is a statement about **all** alive plays (any outcome sequence) satisfying h ≥ −350;
its ledger only used h ≥ −350 (faint duration ≤ 45) and the W_ON bans. With −352 the constants change by < 1%, and
the margin 29,548/32,567 = 0.907 becomes ≤ 0.91 < 1 [conj, re-derivation: 11·1252 + 45·353 + 3 = 29,660]. So
every play passing no kill node has T ≤ 4.2·10^6 + 620·N ticks, N = 40·(unary cookie count): poly(n).
Alternating machine: keep the current state (poly bits, Lemma 1 with poly T); at hero turns branch existentially
over the next command (free actions normalized as in Lemma N [conj, also for the game: free actions consume no
outcome that matters — to be audited]); at each RNG call branch universally over its (≤ 64-bit) outcome, except
reject immediately at a kill node (Lemma K); accept at "alive on g, multi = 0"; reject at death or level change.
By Lemma H every branch halts within poly(n) steps, each step poly time (Lemma 2). So L_ON^W(R3) ∈ APTIME = PSPACE
[ext: A. K. Chandra, D. C. Kozen, L. J. Stockmeyer, "Alternation", JACM 28(1):114-133, 1981]. ∎
(Without Lemma K the adversary could keep the hero alive below thr and the horizon would be unbounded; the
pruning is what makes AP applicable.)

### C.3 Theorem C1: L_ON^W (R3) is NP-hard
Use hu-on-lower's reduction g(φ) unchanged (with the review-2 N1 repair `pettype:none`).
- YES (φ satisfiable): the intended play of hu-on-lower §5.1 is RNG-independent: h stays in [855, 900] (one
  forced decrement per tick, aware, unencumbered, cookies +40 [src objects.h:1103]); no `newuhs` faint branch is
  ever reached (h > 150); exercise can only raise Str/Con (Not Hungry → Con exercise, no abuse source) so wc only
  grows; no damage source. So the fixed play wins for every outcome sequence: R3-YES.
- NO: hu-on-lower §5.2 is structural (first-entry/closing argument over all plays and outcomes); it never uses
  rule S. So no play reaches g under any outcome: R3-NO.
Hence φ ∈ PSMR-3SAT ⇔ g(φ) ∈ L_ON^W(R3), and L_ON^W(R3) is NP-hard. ∎ [conj; inherits hu-on-lower's open items:
§4 global routing, the exact de Berg–Khosravi statement T1, §6 prayer/ball side effects]

**Status: NP-hard and in PSPACE.** Same for (b)'s NP-hardness (subsumed by B1).

### C.4 Can it be pinned down? (NP vs PSPACE)
**Towards NP [conj].** If there were a *pessimal* poly-time adversary policy A* such that "hero wins vs every
adversary" ⇔ "hero wins vs A*", then R3 collapses to a one-player game with poly horizon and a fixed deterministic
environment, which is in NP (guess the play, simulate with A*'s outcomes). In the **water-free** part of W_ON every
reachable RNG call is non-positional: hunger decrement while Unaware, faint roll, accessorytime, exercise, HP regen,
pit-escape duration (`u.utrap`), pit damage, prayer (`rnl`, `rnz`, `angrygods` case), kick damage, cookie text,
`u_wipe_engr`, and ball/throw dispersion (thrown-object positions; the hero never needs to throw). The obvious A*
("most hunger, faint whenever legal, no prayer fix, longest timeout, attributes down, no regen, longest pit stay,
kill whenever possible") is plausible but **not proved dominant**, because time is double-edged: a forced faint burns
nutrition (bad) but also lowers ublesscnt and heals HP / wounded legs (good), while larger `moves` raises later prayer
timeouts (bad). A dominance proof needs an order on states closed under "the hero could have waited", which fails
on these mixed components. I did not find a counterexample either.
**Towards PSPACE-hardness.** A QBF reduction needs a gadget where the adversary makes a *forced, positional,
incomparable* choice. Candidates in W_ON:
- Drown crawl-out (hero steps into water): the exit square is random among `crawl_destination` neighbours
  [src trap.c:4947-4970, 5150-5165; hack.c:4079-4101]. **Useless as a ∀-gadget:** the entry square is always a legal
  exit, so the adversary returns the hero there forever (he then starves). Under R2 it is a real extra move (a
  corner-respecting "hop" over a pool); lower-bound gadgets must keep water away (hu-off/hu-on-lower use none).
- Boulder into pool: fills with `rn2(10) != 0`, else the boulder sinks and the pool stays [src do.c:61-68]. The two
  outcomes (floor vs. a still-usable boulder sink) are in principle incomparable, so this is the only candidate
  ∀-choice I found; I could not build a variable gadget where "sink" is strictly better for the hero than "floor"
  in a way the formula can exploit (in every layout I tried, the floor world simulated the sink world).
- Lava: fill only on `chance == 0`; same structure as pools.
So: **NP-hard, in PSPACE; conjecture NP-complete on the water-free fragment; open with water.** Banning
POOL/MOAT/LAVA from W_ON costs nothing for the NP-hardness proof (hu-on-lower uses none).

**Open-loop variant (c').** If the hero must commit to one command sequence for all outcomes, the certificate is
the sequence (poly by Lemma H + Lemma K: a sequence that ever reaches a kill node loses) and checking "for all
outcomes" is a coNP condition, so the problem is in Σ2^P; NP-hard by C3 (the YES play there is fixed).

## D. Weakest steps
1. (b) inherits everything hu-off rests on: [ext] Push-1F (border convention), the per-command audit (groups U/X),
   W_C wrap of `moves`. The new parts (faint cycle, prayer loop, B.1 arithmetic) are source-read.
2. (b) Lemma C_ON assumes base Str+Con ≥ 20 (hu-off §1) so that Weak's −1 Str keeps the hero unencumbered; if
   init_attr can give Str+Con = 18-19, the hero is Burdened at Weak, which still allows every move (Burdened does
   not block `domove`) — verify `carrying_too_much` [src hack.c:2616-2631] once.
3. (c) C2: the game version of Lemma N (free actions) is [conj]; Lemma K's "attractor" step is standard but not
   written out formally.
4. (c) C1 inherits hu-on-lower's open items (routing, T1). NP vs PSPACE for (c) is open (§C.4).
