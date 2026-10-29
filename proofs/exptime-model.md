# R3 game model for an EXPTIME-hardness attempt (generalized NetHack 5.0.0)

Theory sub-agent, 2026-10-29. Source NetHack 5.0.0 @ 16ff591, read-only (`src/<f>` = `src/src/<f>`); game not run;
nothing committed. Binding inputs: phase2-spec.md (Rev. 1-3), problem-definition.md §5, hu-off.md (Thm A, Lemma 1,
Lemma 2, Thm B/C), upper-bound.md §4, variants.md §C, review-3-pspace.md.
Labels: **VERIFIED** = I read the cited lines this session and the reasoning is a direct reading;
**STRONG** = complete argument, not independently reviewed (or inherited STRONG from an earlier file);
**CONJECTURE** = plausible, not proved. **[ext]** = published theorem.

## 0. Results

| # | Claim | Status |
|---|---|---|
| D | Definition of the R3 game G_I (positions = interpreter configurations at input/RNG requests; full information; reachability objective, infinite plays lost) | definition |
| L-col | Collapsing nature's per-call choices inside one segment into one outcome-vector move does not change the winner | STRONG |
| M | L_X^{R3} ∈ EXPTIME for every whitelist X meeting conditions C1-C6 (§2.1); W (hu-off) and W + doors / + one bounded monster / + web, bear trap meet them | STRONG for W; STRONG for the three extensions under the stated side conditions |
| A | Under R3, on f(I) (hu-off) nature has no effect on the answer: Thm C re-checked against an explicit R3 audit | STRONG (inherits hu-off) |
| P | Under R3, a p_type-3 prayer cannot hurt; the first "too soon" prayer cannot kill; a later angering prayer kills iff 3·ugangr − Luck ≥ 10 at `angrygods` | VERIFIED (pray.c) |
| V | "Veto lemma": success/fail rolls whose failure is a self-loop are useless to the hero under R3 | CONJECTURE |
| T | Target: L_X^{R3} EXPTIME-complete; hardness needs H1-H8 (§4) | open |

## 1. The R3 game

### 1.1 Positions
Fix an instance I = (w, h, S, g) of the spec's language (L_OFF^W, or an extension X), run through the harness
(newgame, `des.reset_level(); S; des.finalize_level()`, Rev. 1 item 1, with the Rev. 3 branch pocket).

A **configuration** κ is the full state of the C program at a point where it requests either an input token or a
core random number:
- all game globals and heap records (map incl. `levl[][]`, objects, monsters, traps, engravings, timers, `struct you`,
  `svm.moves`, `svc.context`, `iflags`, ...), after quotienting write-only logs (hu-off [assump Q]);
- the **continuation**: C call stack (return addresses + locals) at the request, and the request's argument
  (the range x of `RND(x)`, or the kind of input request: top-level command, direction, y/n, menu, object letter, count);
- **not** the ISAAC64 state: under R3 nature picks values directly, so the generator state is unobservable and
  dropped (it is read only through `RND` / `rn2_on_display_rng`, src rnd.c:60-73) [VERIFIED for the read path;
  STRONG that nothing else reads `rnglist[]` during play].

Node kinds:
- **P-node** (player): κ at an input request (`rhack`/getdir/yn_function/menu/getobj/getcount).
- **N-node** (nature): κ at a call of the core primitive `RND(x)` [src rnd.c:60-64]. Every `rn2`, `rnd`, `rn1`,
  `rnl`, `rne`, `rnz`, `d` reduces to `RND` calls (rnl: rnd.c `RND(x)` then `rn2(37+|adj|)`; rne/rnz: loops of `rn2`)
  [VERIFIED rn2/rnl/rne/rnz; STRONG for `d`, `rnd`, `rn1` macros].
- **Terminal**: hero dead (`done()` with a death reason), game ended (quit, save, `<` off DL1, "dungeon capitulates" is
  removed by spec), hero on another level (any `goto_level`/`schedule_goto`), or a **win node**.
- **Win node**: a P-node at the top-level command request of `moveloop_core` (`rhack(0)`, src allmain.c:536) with
  `multi == 0`, hero alive, on dlvl 1, `(u.ux,u.uy) = g`. (Same predicate as spec "alive on g at the start of a player
  turn".) [definition]

Edges:
- P-node: one edge per input token (byte / menu choice); successor = run the C code until the next P-node, N-node or
  terminal. Player moves are **single tokens**, so a player answering a prompt that appears after random events in the
  same command sees those events (adaptivity is automatic).
- N-node with request `RND(x)`, x ≥ 1: one edge per value v ∈ {0, …, x−1} (**range restriction**: nature may only
  return values the primitive can return; for `rn2(x)` that is 0..x−1, for `rnd(x)` 1..x, for `rnl(x)` 0..x−1 for every
  Luck, since nature also controls the inner `rn2(37+|adj|)` and can always skip the luck adjustment
  [VERIFIED rnd.c rnl]). Modulo bias is irrelevant: R3 only uses the support. Full support of ISAAC64 mod x is a
  modelling assumption [assump, as problem-definition §5.2].
- `rn2_on_display_rng` (DISP stream, rnd.c:70-73) is also an N-node. Its values only select glyphs/hallucinatory
  names (display.c, do_name.c, detect.c, invent.c, dothrow.c call sites; do.c:1710 reseed on level change = loss),
  so letting nature choose them changes no winner [STRONG; the conservative definition is "nature chooses all RNG"].

Information: **full** (both players see κ). Initial position: the configuration after the harness; if setup
randomness remains (mineralize in sealed stone, branch stair in the 1-cell pocket P), R3 quantifies **universally** over
it; with Rev. 3 the reachable part of every setup outcome is identical [STRONG, inherits review-3 §4.1 repair].

**Objective.** The hero wins a play iff it visits a win node. Plays that never reach a terminal (infinite sequences of
free actions, endless waiting, an RNG-driven loop that nature keeps alive) are **losses** for the hero. A position is
R3-winning iff the hero has a strategy (any function of the history; by positional determinacy a memoryless one
suffices, §2.2) that wins against every nature strategy. **L_X^{R3}** = instances whose initial position is
R3-winning.

### 1.2 Subtle points

1. **Sequential vs. vector choice (L-col, STRONG).** Inside one segment (between two P-nodes) the N-nodes form a
   finite tree T(κ, token) (finite by C2 below: every RNG-driven loop reachable is capped), with no P-node inside.
   Collapse it to one nature move whose options are the leaves (complete outcome vectors ρ, each value in range given
   the earlier ones). Standard fact: in a reachability game, merging a finite subtree of nodes owned by the same
   player into one node with the leaves as successors preserves the winning region (induction on subtree depth: a
   universal subtree root is in the hero's attractor iff every leaf is). Nature choosing call k "after seeing" calls
   1..k−1 gives nothing extra, because nature already knows the whole deterministic continuation. **Caveat:** a prompt
   between two RNG calls in one command (e.g. "Kick it?" after `#open` fails is queued, lock.c:885-890; failed
   `#untrap` → move_into_trap) ends a segment; the coarse model must split there. Single-token player moves (1.1)
   handle this uniformly.
2. **Unused RNG calls.** Calls whose value influences only messages or the DISP stream (e.g. `"Thwack"/"Whammm"`
   dokick.c:966; `fountain_msg[rn2(3)]`), or whose value is consumed but discarded under the instance's invariants
   (`maybe_generate_rnd_mon` → `makemon` returns NULL under `debug_mongen`, makemon.c:1168; `rn2(2)` in `climb_pit`
   evaluated before `sobj_at(BOULDER,u.ux,u.uy)`, trap.c:4198), produce leaves that are equal after the log
   quotient. Nature's choice there is irrelevant to every winning region [STRONG].
3. **Range dependencies.** Ranges can depend on earlier outcomes in the same segment (`rne` loop length, `rnz`,
   `d(n,x)` with random n). The leaf set of T is still well defined; the alternating machine branches value by value.
4. **Count / occupation commands** (`n20s`, run, travel, multi-turn engrave) are sequences of segments with
   internal interrupts; the player cannot intervene except by the game's own rules. Allowed, never needed: the hero
   can always issue one-step commands instead [STRONG: every multi-turn command is a sequence of one-step effects].
5. **Save / quit** are losing terminals [assump]. hu-off modelled save as identity; either choice gives the same
   winner because the hero can avoid them.
6. **Integer widths (W_C).** `long` is 64-bit under LP64 (Linux build used by the witnesses) and 32-bit under
   LLP64 (Windows). The spec must fix one data model; both give O(1)-bit counters [assump]. Signed overflow is UB in
   C; spec SC3 declares two's-complement wrap.

## 2. Membership

### 2.1 Conditions on a whitelist X (C1-C6)
- **C1 poly state.** Every configuration reachable from an instance of size n has an encoding of p(n) bits:
  bounded number of map/object/monster/trap/engraving/timer/region records (creators audited), each O(1) words or
  coordinates of O(log n) bits; scalar counters of fixed width; the continuation has bounded stack depth with
  poly-size frames (no unbounded recursion reachable) [CONJECTURE for the stack, spot-checked; hu-off Lemma 1 covers
  the globals].
- **C2 poly segments.** From any reachable κ, every segment runs in time poly(n) and makes poly(n) RNG calls,
  **independently of the values nature returns** (every RNG-driven loop has an explicit cap: `rne` ≤ 5 at XL<15
  [rnd.c:192-200, VERIFIED], `impaired_movement` ≤ 51 tries [hack.c:2430-2438, VERIFIED], `place_lregion` 200 tries +
  scan, `safe_teleds` bounded, `rndcurse` over inventory). An uncapped `do { v = rn2(k) } while (bad(v))` would let
  nature produce a non-terminating segment; C2 forbids it (alternatively treat it as a hero loss, which keeps the
  model well defined but breaks the time bound only if detection is undecidable; with C1 it is decidable by cycle
  detection on poly-size configurations).
- **C3 bounded branching.** Each RND range x ≤ INT_MAX, so an N-node has ≤ 2^31 successors; a P-node has ≤ 2^8
  (or poly(n) menu entries).
- **C4 decidable predicates.** "win node", "dead", "left level" are poly-time computable from κ.
- **C5 single level.** No reachable mechanism generates a new level except as a losing terminal (holes, trapdoors,
  `<` on DL1: loss).
- **C6 fixed external inputs.** Moon phase, Friday 13th, `night()`, bones: fixed by spec; no wall-clock read during
  play changes state [assump; spec "External inputs fixed"].

### 2.2 Theorem M (STRONG)
If X satisfies C1-C6 then L_X^{R3} ∈ EXPTIME.
Proof. Build the game graph G_I: nodes = reachable configurations (≤ 2^{p(n)}, C1), edges by simulating one segment
(poly time, C2), out-degree ≤ 2^31 (C3, constant). Compute the hero's attractor Attr of the win nodes: Attr_0 = win
nodes; Attr_{k+1} = Attr_k ∪ {P-nodes with some successor in Attr_k} ∪ {N-nodes, all successors in Attr_k};
terminal non-win nodes never enter. Fixpoint after ≤ |V| rounds, each O(|V|·2^31·poly(n)) = 2^{O(p(n))} time. The hero
wins iff the initial node ∈ Attr: reachability games are positionally determined, nature's complement strategy
(stay outside Attr) defeats the hero otherwise, and plays that avoid Attr forever are losses by definition. ∎
Equivalent route: an alternating TM keeps κ (poly space), branches ∃ over tokens and ∀ over RND values (bit by bit),
plus a step counter of p(n) bits (a winning attractor rank is ≤ |V|), so the problem is in APSPACE = EXPTIME
[ext: A. K. Chandra, D. C. Kozen, L. J. Stockmeyer, "Alternation", JACM 28(1):114-133, 1981].
Note: the RNG state dropped in 1.1 is what makes R3 *smaller* than R1 positions; ISAAC64 is constant size anyway.

### 2.3 Is W (hu-off A.0, incl. Rev. 1-3 additions) OK? (STRONG)
hu-off Lemma 1 bounds globals by poly(n) for **every** play and every outcome sequence (it never used R2), Lemma 2
gives poly segments with capped loops; the continuation is the only new component (C1 stack: CONJECTURE, standard).
Pits/holes/trapdoors (Rev. 1 item 3): holes and trapdoors = losing terminals (C5); a boulder into a pit/hole deletes
the trap deterministically (do.c:185-245 "plugs a hole"/"fills a pit", no RNG; VERIFIED). So W is fine.

### 2.4 Extensions: what a new mechanism must satisfy, checked for (a)-(c)

General rule: a mechanism is admissible iff it (i) adds O(1) words per instance-declared item, (ii) has no creator of
new records except a bounded, audited one (≤ c per declared item, over the whole play, under every outcome),
(iii) introduces no uncapped RNG loop, (iv) reaches no `morehungry` caller (hunger off is gated only in `gethungry`:
`if (u.uinvulnerable || iflags.debug_hunger) return;` eat.c:3167, VERIFIED; `morehungry` (eat.c:3281) is **not**
gated and is called from jumping/apply, fountains, spells, `^T`, vomiting, polymorph egg-laying, a hunger attack
[apply.c:2121,2161; fountain.c:296,322,677; spell.c:1367; teleport.c:1160; timeout.c:245; sit.c:394; uhitm.c:3795;
VERIFIED by grep], none reachable in W or (a)-(c)), (v) creates no other level.

**(a) Door states + door traps.** Door state is `levl[x][y].doormask` inside `struct rm` (already in Lemma 1 item 1,
O(1) bits per cell). Transitions: CLOSED→ISOPEN or →NODOOR if trapped (`#open`, lock.c:904-911), ISOPEN→CLOSED
(`#close`, lock.c:1038-1042), CLOSED/LOCKED→BROKEN/NODOOR (kick, dokick.c:930-948), SDOOR→DOOR (search, kick:
`cvt_sdoor_to_door`, dokick.c:976-995). All per-cell O(1). `b_trapped` (trap.c:6694-6707) creates no object: damage
rnd(5+lvl) = rnd(6) at depth 1, Str/Con abuse, stun timeout (in `u.uprops`, O(1)). No shops/towns (no
`add_damage`/watch). Lemma 1 item 1 must change from "terrain never changes" to "typ never changes except SDOOR→DOOR;
doormask changes". **C1-C6 hold** [STRONG]. Locks need tools (not whitelisted); locked doors open only by kicking.

**(b) One specific harmless monster.** One `struct monst` (O(1) words: position, HP, speed/movement, flee/frozen/
sleep/trapped flags and timers, `mux/muy`, `mtrack[]`, `mlstmv`, strategy) [STRONG]. Side conditions the species and
instance must meet so C1/C2 survive, each source-anchored in the audit to be done for the chosen species:
- no new monsters: `debug_mongen` stays on, so shrieks/summons/eggs/cloning via `makemon` return NULL
  (makemon.c:1168); **no splitting**: `clone_mon` (makemon.c:837-850) refuses only if mhp ≤ 1 or extinct and does not pass the `debug_mongen` gate as far as read → exclude species that split;
  no revival (trolls, Riders);
- no items: no pickup/use (not `likes_objs`/`M2_COLLECT`/`throws_rocks` (giants lift boulders)); no `minvent`;
- **death products bounded**: a kill makes a corpse (1 record + ROT/REVIVE timer, absolute `moves` timeout) and, with
  `!rn2(6)` and the species not `G_NOCORPSE`, a **random object** `mkobj(RANDOM_CLASS)` (mon.c:3587-3594, VERIFIED);
  a random object may be a wand of wishing, so C1 then fails to be provable. Require `G_NOCORPSE`, or that the hero
  cannot kill it in any play (note: under R3 alone nature can always make the hero miss when to-hit ≤ 20, but C1
  must hold for the definition of the game graph, so pick the species, not the semantics);
- not an engulfer/sticker (`u.ustuck`), no displacement of the hero (no pet: `pettype:none`), not a long worm;
- speed: `mcalcmove` rounds randomly (`rn2(NORMAL_SPEED) < mmove % 12`, mon.c:1162-1165) unless speed ≡ 0 mod 12;
  harmless for C1, but it is a nature choice (audit 3.4).
With these, monster state is O(1) words and **C1-C6 hold** [STRONG]. Candidate class: a no-attack, no-hands,
`G_NOCORPSE`, non-splitting species (e.g. a shrieker is no-attack but leaves corpses; check flags before choosing).

**(c) Hero trap timers (web, bear trap).** `u.utrap` (unsigned) and `u.utraptype` are in `struct you` (O(1)).
Bear trap: `set_utrap(rn1(4,4))` = 4..7, wounded legs `rn1(10,10)` (trap.c:1506, ~1517); web: duration by Str, Str ≥
69 (18/51) tears the web and **deletes the trap** (trap.c:2148-2202, VERIFIED); pit: `rn1(6,2)` = 2..7
(trap.c:1920). `#untrap` of a bear trap converts trap → object (record count conserved); applying it back converts
object → trap. So Σ(traps + trap objects) never grows [STRONG; `cnv_trap_obj` not re-read]. **C1-C6 hold**.

### 2.5 Hunger off under R3 (VERIFIED)
`iflags.debug_hunger` is set by the mandatory prefix and never cleared in play (only nhlua.c sets debug flags); the
early return in `gethungry` precedes every RNG call (eat.c:3167 vs. accessorytime eat.c:3191). `u.uhunger` stays at
its start value, so `exerper`'s hunger check always sees NOT_HUNGRY → `exercise(A_CON, TRUE)` every 10 turns
(attrib.c:523-538). The only threat is `morehungry` (2.4 (iv)): unreachable in W, (a), (b) with a no-hunger-attack
species, (c).

### 2.6 `moves` and other wrapping counters

With the 10^9 cap removed (allmain.c:253, spec), `svm.moves` (long) increments once per turn (allmain.c:244) and
wraps (SC3). It is part of κ: 64 (or 32) bits, constant, so C1 is unaffected. Every `moves`-dependent effect
reachable in W ∪ (a)-(c) (grep of `svm.moves` over src/*.c, VERIFIED; display/log/pet/shop/priest/dig/eat/worm/mail
uses excluded as unreachable):

| Effect | Code | Kind | Matters for |
|---|---|---|---|
| Luck timeout | `moves % (ugangr ? 300 : 600) == 0` → Luck ±1 toward base 0 (timeout.c:606-620) | periodic | prayer type, `angrygods` maxanger |
| Prayer timeout increment | `moves > 100000` → `ublesscnt += min((moves−1e5)/100, 32767−ublesscnt)` (pray.c:1371-1377) | threshold | prayer availability; after wrap (negative) no increment |
| Exercise periodic checks | `moves % 10` hunger/encumbrance, `moves % 5` status (attrib.c:523, 570) | periodic | AEXE drift |
| Attribute test | `moves >= next_attrib_check`, then `+= rn1(200,800)` (attrib.c:605-673) | absolute | Str/Dex/Con change; **wrap-sensitive**: after moves wraps negative, tests stop until it climbs back (≈2^63 turns) |
| HP regen gate (polyd / encumbered) | `moves % 20` (allmain.c:643); non-polyd XL1 path uses `rn2(100)` only (allmain.c:659) | periodic | HP |
| Pw regen | `moves % ((MAXULEV+8−ulevel)·4/6)` (allmain.c:604) | periodic | Pw only (unused) |
| Overexertion while encumbered and moving | `moves % 30` / `% 10` (allmain.c:299-300); fighting at HVY: `moves % 3` (hack.c:3057) | periodic | HP, only if Punished and carrying the ball, or with a monster |
| Clairvoyance timer | `moves >= seer_turn`, reset `moves + rn1(31,15)` (allmain.c:409-415) | absolute | an RNG call every 15-45 turns; effect needs Clairvoyant (absent) |
| Boulder-push message | `bldrpushtime` (hack.c:183-202) | absolute | message only; the `exercise(A_STR, TRUE)` runs regardless |
| Engraving visibility | `engr_time <= moves` in `sengr_at` (engrave.c:255) | absolute, **wrap-sensitive** | Elbereth / engraving reads: matters only with a monster (b) |
| Monster bookkeeping | `mlstmv` (mon.c:1235), monster regen `moves % 20` (monmove.c:309) | periodic/absolute | (b) only |
| Object timers (corpse rot/revive) | `timeout <= moves` (timeout.c:2231) | absolute, wrap-sensitive | (b) only, if the monster can die |

Consequence: over exponentially long plays, wrapping changes behaviour only through absolute comparisons
(attribute tests, engravings, object timers, prayer-timeout increment). All are functions of κ, so Theorem M is
unaffected; but **a hardness gadget must not rely on any of them over > 2^31 turns** (or the spec must say how the
wrap is treated) [STRONG]. Other counters: `u.ublesscnt` (int; `+= rnz(250)` per too-soon prayer has no cap,
pray.c:2319, so it can wrap after ~10^6 angering prayers), `u.ugangr` (int, only grows without altars), AEXE
(schar-range sums), `u.utrap` (unsigned) — all O(1) bits.

## 3. Adversary power audit (R3: nature picks the worst outcome of every call)

### 3.1 Per command family, current whitelist hero (W: human Valkyrie XL1, cursed loadstone, hunger off, no monsters,
boulders, Sokoban flag, sentinel pit, holes/trapdoors = loss, Luck 0, ugangr 0, record 0, ublesscnt 300, HP 16/16)

| Family | Reachable RNG calls | Nature's worst choice → effect | Can it kill / move π? |
|---|---|---|---|
| Per-turn block (every turn) | `maybe_generate_rnd_mon` rn2(70) (allmain.c:239) → NULL; `seer_turn` rn1(31,15); `exerchk`: `exercise` rn2(19), test rn2(50) (attrib.c:509, 655, 673); `u_wipe_engr` rn2(40+3Dex), rnd(3) (allmain.c:360-361); `regen_hp` rn2(100) only if uhp < uhpmax (allmain.c:294, 659); `regen_pw` only if uen < uenmax | **No HP regeneration ever** (heal iff 1+Con > rn2(100); nature picks ≥ 1+Con). Attributes frozen (nature keeps every AEXE at 0: gain needs `rn2(19) > ACURR`, abuse adds `−rn2(2)`). Engraving under the hero wiped. | no / no [VERIFIED lines; STRONG conclusion] |
| Step (M1, M4, M5) | none beyond the per-turn block | — | no / no |
| Push (M2) | `exercise(A_STR, TRUE)` (hack.c:197) | AEXE(Str) +0 | no / no |
| Diagonal into boulder, refused moves (M3) | none | — | no |
| Punished drag (M6) | none in `drag_ball` without pools/pits under the chain | — | no / no (hu-off M6) |
| Sokoban pit/hole (only the unreachable sentinel in f(I); W gadgets in L_ON use holes) | forced fall in Sokoban (trap.c dotrap: "Air currents"), pit damage rnd(6), utrap rn1(6,2) (trap.c:1920, 1950); hole: leave level | max damage 6, 7 climb attempts (each `--u.utrap` deterministic, trap.c:4206) | pit: HP only, π unchanged; hole: loss |
| Wait `.`, search `s` | search: `rnl(7)` only next to SDOOR/SCORR, `rnl(8)` only next to an unseen trap (detect.c:2043-2083) | none in W | no |
| Kick `^D` | walls/stone: `kick_ouch`: wounded legs `!rn2(3)` rnd(5)+5, dmg rnd(5) (rnd(3) if Con > 15), Str/Dex abuse (dokick.c:881-905); empty air: `kick_dumb`, Dex ≥ 16 short-circuits the rn2(3) (dokick.c:864-878); boulder/ball/chain never move (dokick.c:517-519) | max damage each kick, then wounded legs block kicking (dokick.c:1279-1281); abuse lets nature lower Str/Dex later | **yes, self-inflicted** (≤ 16 HP, no regen: ≥ 4 wall kicks can kill); π never moves. Hero never needs to kick. |
| Throw ball (Punished only) | slip/flight rolls | landing = legal steps only (hu-off T1) | no / composes legal steps |
| Apply/rub stone, engrave in dust | `wipeout_text` rolls | garbled text | no |
| `#pray` | see 3.2 | | |
| Inventory, meta, `<` `>`, no-op U commands | none relevant | — | `<` = loss |

### 3.2 Prayer under R3 (VERIFIED, pray.c)
Initial: Luck 0, ugangr 0, record 0 (< STRIDENT), ublesscnt 300, cursed loadstone = minor trouble.
- **p_type 3** (not too soon, Luck ≥ 0, ugangr 0, alignment ≥ 0; can_pray pray.c:2150-2161): `uinvulnerable` during
  the prayer; `pleased`: if record < 2 and trouble ≤ 0 → `adjalign(1)` (pray.c:1088-1089); action =
  `(record > 0 || !rnl(2)) ? 1 : 0` (pray.c:1130). With record 0 nature picks action 0 ("blows you off"); with
  record ≥ 1 action is **1 deterministically** → fixes the worst *major* trouble only. Then `ublesscnt = rnz(350)`
  (≤ 3498 at XL1) plus the moves increment (pray.c:1356-1377). **No harmful branch.** Under R3, reliable prayer
  healing therefore needs one earlier "minor trouble only" p_type-3 prayer (ublesscnt ≤ 100) to make record ≥ 1.
- **p_type 0** (too soon): `ublesscnt += rnz(250)`, `change_luck(-3)`, then `gods_upset` → ugangr+1 → `angrygods`
  (pray.c:2318-2321, 1436-1443). maxanger = 3·ugangr − Luck (Luck ≤ 0, record < STRIDENT; pray.c:717-723), clamp
  [1,15]; `rn2(maxanger)`: 0-1 displeased, 2-3 Wis−1 + `losexp` (XL1, no drainer: exp reset, HP clamped ≥ 1,
  non-fatal, exper.c losexp), 4-5 curse items / remove an intrinsic, 6 punish (if maxanger ≥ 7), 7-8
  `summon_minion` (NULL under debug_mongen), ≥ 9 `god_zaps_you`: Valkyrie has no reflection and no shock resistance →
  `fry_by_god` → death (pray.c:610-700). **First too-soon prayer:** ugangr 1, Luck −3 → maxanger 6 → non-lethal, no
  punishment. A later angering prayer (p_type 0 or, once ugangr ≥ 1, every p_type 1) is lethal iff
  3·ugangr − Luck ≥ 10 at that call (e.g. second too-soon prayer within the Luck window: 3·2+6 = 12). With
  ugangr ≥ 1 the hero never gets p_type 3 again (no altars), so healing is gone for good.
- "You feel that Tyr is displeased" occurs both as `pleased` action 0 (harmless) and `angrygods` case 0-1.
- Luck enters R3 only through can_pray/maxanger/`rn1(Luck+2,1)` — not through `rnl`, whose outcome set is 0..x−1 for
  every Luck (1.1).
Net: under R3 prayer is a hero *option* that can at best heal (record ≥ 1) and at worst kill; the hero sees ublesscnt,
Luck, ugangr (full information) and is never forced to pray.

### 3.3 Answer-level DET of f(I) under R3 (STRONG, re-check of hu-off Thm C)
Lemma S quantifies over all outcomes, so R3 adds no reachable π. Lemma C's play (direction keys only) meets, in
order: per-turn block (3.1 row 1: HP full so `regen_hp` is not called; `makemon` NULL; exercise only raises AEXE or
leaves it, and higher Str/Con keeps `weight_cap ≤ 1000`, so I3 still holds), pushes (Str exercise). No prayer, kick,
trap, or monster on that path. So nature can change only AEXE/attributes upward (or not at all), `seer_turn`, and
which message is printed; the YES play wins against every outcome, and R3-answer = R2-answer for every f(I)
(also f_ON's YES-play remark in variants.md §C.3 for the hunger-on L_ON reduction). Remaining dependency: hu-off's
open items (Push-1F enclosure figure check, U/X audit) and Rev. 3 pocket (setup).

### 3.4 Extra random events a new gadget introduces (checklist the gadget proof must cover)

| Mechanism | New ∀-choices (nature) | R3 consequence |
|---|---|---|
| `#open` closed door | `rnl(20) < (ACURRSTR+Dex+Con)/3` (lock.c:904); human max 21+18+18 = 57 → threshold ≤ 19 < 20 | nature can make **every** open attempt fail forever: a closed door is a nature-controlled gate (open only when nature wants) |
| `#close` | `rn2(25) < …/3` (lock.c:1039) | closing can fail forever |
| Kick closed/locked door | `rnl(35) < avrg` (dokick.c:930); shatter `rn2(5)` if Str > 18 | can fail forever ("WHAMM", no damage); success → BROKEN/NODOOR |
| Trapped door | on success `b_trapped`: rnd(6) dmg, stun += dmg, Str/Con abuse (trap.c:6694-6707) | HP loss; **stun**: while stunned every move attempt gets a nature-chosen direction among non-`bad_rock` squares (`impaired_movement`, hack.c:2420-2438; `confdir` cmd.c:4304), incl. pushes. Hero can wait it out. |
| Secret door/corridor | search `rnl(7)` (detect.c:2043, 2053); kick SDOOR `rn2(30)` (dokick.c:977) | stays hidden forever = wall |
| Seen trap outside Sokoban | escape `!rn2(5)` (trap.c dotrap) | nature chooses trigger vs. pass (pits, webs, bear traps, holes: hole outside Sokoban = nature may end the game) |
| Bear trap | duration rn1(4,4); orthogonal escape attempts decrement only on `!rn2(5)`, **diagonal attempts always decrement**, and `trapmove` runs before `test_move` (hack.c:1575-1576, 2830-2843) | escape forced in ≤ 7 diagonal attempts (even toward a wall) [VERIFIED order]; wounded legs side `rn2(2)`, rn1(10,10) turns; dmg d(2,4) |
| Web | duration by Str (1 at Str 18..18/50; torn at ≥ 18/51); decrement deterministic (hack.c:1594) | deterministic once Str is fixed; nature can lower Str only after abuse |
| `#untrap` | success `rnl(chance)`; failure may `move_into_trap` = a `test_move`-legal step onto the trap + forced trigger (trap.c:5393-5420) | nature can fail forever; the forced step is legal (no new π move) |
| HP | no regen at XL1 (3.1); prayer heal needs record ≥ 1 and p_type 3 | HP is a finite budget: every damaging gadget must be shown not to exhaust it on the intended play |
| Attributes | abuse events (kick, door trap, wounded legs, stun, Ext encumbrance) let nature lower Str/Dex/Con | lowers `weight_cap` (encumbrance can refuse moves), door thresholds, web duration |
| One monster | speed rounding (mon.c:1152-1165), `m_move` tie-breaks and approach randomization, wake/`disturb`, flee timers (`monflee`), Elbereth `onscary` + erasure, to-hit both ways (`tmp > rnd(20)`), damage, trap escapes for the monster, monster blocking a push ("Perhaps that's why you cannot move it") | **the natural ∀-player**: positional choices among the monster's legal moves; hero to-hit ≤ 20 means nature can make the hero never hit; Elbereth reads use `engr_time <= moves` (wrap) |
| Divine anger | 3.2 | an angering prayer can only hurt |

### 3.5 Veto lemma (CONJECTURE)
If command c at position X has a "failure" outcome whose result X' equals X up to components that never help the hero
(moves, AEXE, seer_turn, messages), then deleting c's success edges does not shrink the hero's winning region.
Reason: nature may answer "fail" forever; a hero strategy that relies on c's success is beaten by permanent failure,
and since infinite plays are losses, nature loses nothing. Dominance fails only if the "irrelevant" components
matter (moves-based luck timeout, exercise tests), which is why it is a conjecture. Consequence for gadget design:
under R3, door opening, kicking, searching, untrapping are **useless to the hero** and **useful only to nature** (as
gates nature may open); every hero-side mechanic in a hardness gadget must be RNG-free (walking, pushing) or a forced
choice.

## 4. Target theorem and what the hardness reduction must provide

**Target.** For an explicit whitelist X ⊇ W meeting C1-C6: **L_X^{R3} is EXPTIME-complete** (membership: Thm M).

**Hardness.** A polynomial-time (preferably log-space) map φ ↦ I_φ from an EXPTIME-complete two-player game with a
reachability objective for player ∃ (infinite plays lost by ∃) — e.g. the Stockmeyer-Chandra formula games
G1-G6 [ext: L. J. Stockmeyer, A. K. Chandra, "Provably difficult combinatorial games", SIAM J. Comput. 8(2):151-174,
1979; check which variant has ∃-reachability with infinite plays = ∃ loses], or unbounded two-player constraint logic
[ext: R. A. Hearn, E. D. Demaine, *Games, Puzzles, and Computation*, A K Peters 2009; EXPTIME-complete] — such that
∃ wins φ ⇔ the hero has a winning strategy in G_{I_φ}. Requirements:
- **H1 instances in X** (C1-C6), produced by straight-line S within the whitelist, with the Rev. 1-3 harness
  (prefix, `pettype:none`, `noflip`, pocket).
- **H2 YES direction:** from a winning ∃-strategy build a hero strategy that wins against **every** nature strategy,
  i.e. against every outcome of every RNG call the hero's commands trigger (audit 3.1/3.4 on the intended plays,
  including HP budget and attribute drift).
- **H3 NO direction:** from a winning ∀-strategy build a **nature strategy using only legal RNG values** that keeps
  the hero away from g against **every** hero command sequence (a Lemma-S-style soundness over the full command
  table, now with nature's answers), and handle hero "cheats": waiting, prayer (3.2), kicking, untrap, using the
  monster, stalling.
- **H4 forced, positional ∀-choices:** a ∀-gadget where some RNG call's outcomes lead to **different, incomparable**
  positions and every outcome makes progress (no "fail = self-loop" vetoes, 3.5). Candidates: the monster's move
  choice; stun direction (but the hero can wait while stunned, so stun must be forced at a moment where waiting
  loses); trap escape roll (trigger vs. pass) at a seen trap the hero must cross outside Sokoban.
- **H5 alternation control:** ∃ and ∀ must move in the source game's order; the hero must not gain by waiting
  (time passes for the monster) nor be able to skip nature's turn; nature must not gain by stalling (infinite plays
  are already hero losses, so nature stalling is allowed in the source game only if it is a loss for ∃ there too).
- **H6 no randomness that helps the hero in a way the source game forbids**: e.g. a monster that can be killed,
  a door nature might open, extra moves from speed rounding; each either excluded by X or shown dominated.
- **H7 counters:** no gadget depends on wrap-sensitive comparisons (2.6) or on HP/attributes beyond their fixed range;
  plays may be exponentially long (the source game's plays are), so every per-play resource the intended play spends
  must be bounded per gadget visit, not per play (HP has no regen under R3: the intended play must take **zero**
  damage, or heal via record ≥ 1 prayers whose timeout fits the play's rhythm).
- **H8 transfer statements:** EXPTIME-hardness under R3 does not transfer to R2 (R2 is in PSPACE by Thm A), nor to
  R4 automatically; state it for R3 only.

## 5. Weakest steps
1. C1 for the continuation (bounded C stack at input/RNG requests): standard, not audited.
2. C2 "every reachable RNG loop capped": spot-checked (rne, impaired_movement, lregion, safe_teleds), not exhaustive;
   the monster code (b) needs its own pass.
3. (b) side conditions: no species chosen yet; splitting/cloning, corpse timers, death drops must be checked for it.
4. Veto lemma (3.5) is a conjecture; H4 has no gadget yet.
5. Data model for `long` (LP64 vs LLP64) and the wrap convention must be fixed in the spec before any gadget uses
   long clocks.
