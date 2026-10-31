# V: G6 rule variants vs the reduction G6 ≤_p L_OFF^{W+C}

Workstream V, 2026-10-30. Game not run, nothing committed; site/ and claims.md untouched. Files: this note,
`tools/exptime/V_variants.py` (imports `review5_t1`, `L_gen` read-only), outputs in `build/variants/` (gitignored).
Labels: **VERIFIED** = machine-checked or read in the source this session · **STRONG** = complete argument, not
reviewed · **CONJECTURE** · **FAILED**.

## 0. Verdict

**No plausible variant breaks the reduction.**
- Every reading the sources support is handled by B's arena **as is**: both players may pass; F checked after every
  move or after I's moves; either first mover; infinite play a non-win for I. The only convention-dependent step is
  B §1.1's pre-processing. Apply it iff the initial position counts and II moves first; B §1.1 already says so.
- Every other variant (no passing, one-sided passing, checks only after II's moves) needs at most three local
  changes built from the same gadgets: (G) gate SCDs, (Q) a post-II checker entry, (S) a start fork.
- After those changes, all 72 variant settings tested match G6 exactly: 48 CNF + 24 DNF, **22,800 random instances
  (15,779 YES / 7,021 NO)**. Mismatches: **0** for ideal doors, **0** for Lemma TS, **0/15,600** through L_gen's
  netlist (S1) and **0/430** through its bus layout + crossovers (S2); 2 S2 runs were skipped at the 8 M-position cap.
  Negative controls show each change is needed where it is applied.
- The only excluded reading is "infinite play = win for I", which makes every instance YES (§2.1).
- **Independent source:** Chung 2026 Thm 22 is proved without SC79 (latch game ← alternating LBA). Its complement is
  a reachability game of exactly our shape with a DNF checker, so it gives a citation that avoids the unread SC79
  text (§5.4).

| Variant group (count) | Source | Reduction change | Instances (S1 / S2) | Mismatches ADAPT (BASE) | Label |
|---|---|---|---|---|---|
| I first; both pass; every or post-I; init yes/no (4) | S1-S5 (post-I: S3, S6) | none (s = h) | 2,400 (1,200 / 40) | 0 (0) | VERIFIED tests, STRONG proof (T1 + L1) |
| II first; both pass; every or post-I; init counts (2) | S1, S2, S4, S5 ("ever"); τ in input S4, S6 | none + B pre-processing (or start fork S) | 1,200 (600 / 20) | 0 (0; 180 without pre-processing) | VERIFIED / STRONG |
| II first; both pass; every or post-I; init not counted (2) | S3 (check after own turn) | none, s = N_in, **no** pre-processing | 1,200 (600 / 20) | 0 (187 with pre-processing) | VERIFIED / STRONG |
| both pass; post-II only (4) | none | Q (+ S) | 2,400 (1,200 / 40) | 0 (10-132 / 600) | VERIFIED / STRONG |
| neither passes (exactly one flip) (12) | none for G6 (G3's rule); EXPTIME-c via S3 Lemma 3 | G (+ Q if II's moves checked, + S) | 7,200 (3,600 / 119) | 0 (54-149 / 600) | VERIFIED / STRONG |
| only I may pass (12) | none | G on Y (+ Q, S) | 2,400 (2,400 / 60) | 0 (28-54 / 200) | VERIFIED / STRONG |
| only II may pass (12) | none | G on X where needed (+ Q, S) | 2,400 (2,400 / 59) | 0 (0-30 / 200) | VERIFIED / STRONG |
| DNF checker, all 24 settings incl. Chung Thm 22 complement | S3 Thm 22 (complement) | DNF checker (+ G, Q, S as above) | 3,600 (3,600 / 72) | 0 | VERIFIED / STRONG |
| infinite play = win for I | none (contradicts S3) | excluded: every instance YES | — | — | VERIFIED (argument) |
| flip any number / any variable | none (not G6, S3) | excluded | — | — | STRONG (S3 classification) |

**Verdict (one line):** the reduction is correct under every plausible G6 convention. The source-supported ones need
no change beyond B §1.1's start/pre-processing choice; all other tested ones need ≤ 3 local gadget-level changes,
with 0 mismatches on 22,800 instances. The tests are VERIFIED for these instance sizes and the proofs are STRONG.

## 1. What the sources say (read this session)

SC79 itself (SIAM J. Comput. 8(2):151-174) is still unread: the SIAM page is paywalled and no open copy was found.

| # | Source (read this session) | G6 rules as stated | First mover | Pass | When F is checked | Infinite play |
|---|---|---|---|---|---|---|
| S1 | Hearn, PhD thesis 2006, §6.2.1 (PDF, groups.csail.mit.edu/mac/users/bob/hearn-thesis-final.pdf) | CNF F over X ∪ Y, assignment α; "Players I and II take turns"; ≤ 1 own variable per move | not stated (his 2CL proof lets White start) | "passing is allowed" | "Player I wins if F ever becomes true" (every position, initial ambiguous) | II "can hope [for] a draw" (= non-win for I) |
| S2 | Demaine–Hearn, CCC 2008 §6.2 | same text as S1 (verbatim, via exptime-sources.md §1; not re-read) | — | allowed | "ever" | — |
| S3 | Chung, MIT S.M. thesis 2026, Ch. 2 Def. 1, Lemma 3, Table 1.1 (erikdemaine.org/theses/lchungM.pdf) | turn = change own variables, **then check one's own formula**; Single-formula: only I has a formula, "Player II's moves cannot end the game"; G6 = Single-formula Flip-Zero-Or-One Win CNF | not in the decision problem's wording; WLOG "Player I moves first" used in other reductions | 0 or 1 flips; Lemma 3: pass-allowed ≤ pass-forbidden (fresh unused variable per player) | **only after I's moves** | "For G5 and G6, draws are counted as wins for Player II" |
| S4 | Ying & Ying, arXiv 1406.6146 §5.2 (qMDP reachability) | CNF; each player changes ≤ 1 own variable, alternately; "Once F becomes true, Player 1 wins" | **part of the input**: a position is (τ, F, α), τ ∈ {1, 2} the current player; deciding a given position is EXPTIME-complete [SC79] | "at most one" | "once F becomes true" | — |
| S5 | Witter, arXiv 2106.16172 Def. 7 (Backgammon) | alternate changing ≤ 1 own variable; "Player 1 wins if the formula ever becomes true" | Player 1 first in his reduction | yes ("skipped their turn (which is an acceptable move in G6)") | "ever" | — |
| S6 | Šámal–Valla, arXiv 1112.6140 §3, restating SC79 **G2** (not G6) in SC79's own notation | position 4-tuple (τ, F_R, F_C, α), τ ∈ {1, 2} "serves only to differentiate the positions where the first or the second player is to move" | part of the position | "either player may pass since changing no variable amounts to a 'pass'" | after the mover's own move ("true after some move of player I") | infinite play: not in the language (I does not win) |

Reading: S4 + S6 strongly suggest that SC79's G-games are decision problems **on positions (τ, …, α)**, so the
player to move is part of the input, not a rule (STRONG, from two independent restatements; SC79 unread). Passing
is allowed in every source (S1-S5). The check time is the one real ambiguity: "ever" (S1, S2, S4, S5) vs "after I's
moves" (S3, and SC79's frame for G2 per S6). Who wins an infinite play is stated only by S3 (II) and implicitly by
S1 (draw ≠ I-win).

## 2. Variant space

A variant is v = (first, pass, check, init); infinite play = non-win for I throughout (§2.1 for the other reading).

| Axis | Options | Supported by |
|---|---|---|
| first mover | I · II | S4, S6: τ in the input (both occur); S5: I; S1 silent |
| passing | both may pass · neither (exactly one flip, as in G3) · only I · only II | both: S1-S5. Neither: none for G6 (it is G3's rule); EXPTIME-c anyway by S3 Lemma 3. Asymmetric: no source (tested for robustness) |
| F checked | after every move ("ever") · only after I's moves · only after II's moves | every: S1, S2, S4, S5. post-I: S3, S6 (G2 frame). post-II: no source (tested for robustness) |
| initial position counts | yes · no | "ever becomes true" reads either way; S3's "check after your own turn" says no |
| infinite play | non-win for I · win for I | non-win: S3 (explicit), S1, S6. Win for I: no source |
| who may flip what | own variables only · any variable · any number of own variables | own only, ≤ 1: all sources. Any variable = impartial-variable games, need a ko rule (S3 Ch. 2), not G6. Any number = Flip-Any-Number (G1 style; S3 Table 1.1 puts Single-formula Flip-Any-Number Win in the polynomial hierarchy), not G6 |
| tie-breaks | none exist: one formula, one winner, no simultaneous moves | — |

### 2.1 Excluded readings (no reduction needed)
- **Infinite play = win for I.** II has no winning condition, so II can never win: every instance is YES. This
  reading is trivial and not EXPTIME-hard, so it cannot be SC79's G6. **VERIFIED** (one-line argument).
- **Flip any number of own variables.** By S3 (Thm 8 / Table 1.1) Single-formula Flip-Any-Number Win is in Σ₃ᴾ/Π₃ᴾ,
  so it is not the EXPTIME-complete G6 unless EXPTIME ⊆ PH. Not tested.
- **Flip any variable (shared variables).** Impartial-variable; trivial without a ko rule (S3 Ch. 2). Not G6.

## 3. The reduction, adapted per variant (V_variants.py `build_variant`)

The base arena is B §3 exactly as `review5_t1.build` makes it (= what `L_gen` generates), with B §1.1's
pre-processing (II first and F(α₀) true ⇒ fixed YES). Three local changes cover every variant; each uses only pieces
the generator already has (SCDs, diodes, forks, the one coin):

- **(G) gates, for every player who may not pass.** For each of that player's variables v, two gate SCDs G_v^0,
  G_v^1, exactly G_v^{α₀(v)} open. Each write path becomes a flip: W(v: 1−b → b) = S(G_v^{1−b}) (passable only if v
  = 1−b now; forced close) → B's forced closes → B's optional opens → O(G_v^b) → exit. The pass corridor (player I)
  or the pass leaf (player II) is removed; II's menu is {flip y_j} and each leaf route forks into the two gated flips,
  only one of which is passable. Padding leaves repeat menu items (no pass leaf exists to pad with).
- **(Q) checker placement.** All leaf routes exit into a new fork Q (post-II position), Q → h. The dead-end checker
  c₀ is reachable from P iff I's moves are checked, and from Q iff II's moves are checked.
- **(S) start fork.** s₀ → c₀ iff the initial position counts; s₀ → h (I first) or N_in (II first). This replaces
  B's pre-processing.

Why each is correct (STRONG; same patterns as T1, B §4):
- (G) *Gate invariant:* outside write paths, the open gates of v ⊆ {G_v^{α(v)}}, equality if the hero opens every O
  (H_σ does). So a gated path is passable only for a real flip; a declined gate opening leaves both gates closed,
  which only freezes v: for an I-variable it deletes I's own options; for a II-variable nature can still pick that
  leaf, and then the hero is stuck (loss). Nature's options are unchanged, so ν_τ (B §4.4) works verbatim; the fork
  inside a II leaf is not a real hero choice (one branch is closed). Completeness: H_σ opens every gate it crosses.
- (Q) Q, like P, is reached only at a round boundary with Inv-L holding (B §4.2), so the checker reached from Q
  passes iff F(α) is true; it is a dead end, so it never changes the state that matters. Completeness: H_σ enters
  the checker at the first checked position where F is true.
- (S) The start fork is a checked position "before any move"; same argument.
- Why (Q) is needed when passing is forbidden: B's Lemma L1 (post-I checking suffices) uses "I may pass". Without
  passing, a II move that makes F true may be undone by I's forced flip, so the post-II check is needed.

## 4. Results

### 4.1 CNF, both players same passing rule (seeds 1 + 2: 300 + 300 per variant; S1 on seed 1)
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/pass/every/init | 600 (398) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 0 |
| II-first/pass/every/init | 600 (367) | 0 / 99 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 99 |
| I-first/pass/every/noinit | 600 (402) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0 |
| II-first/pass/every/noinit | 600 (284) | 82 / 0 | 0 / 0 | 0/300 | 0/10 | qcheck 0, startfork 0 |
| I-first/pass/postI/init | 600 (396) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | startfork 0 |
| II-first/pass/postI/init | 600 (339) | 0 / 81 | 0 / 0 | 0/300 | 0/10 | startfork 81 |
| I-first/pass/postI/noinit | 600 (391) | 0 / 0 | 0 / 0 | 0/300 | 0/10 | - |
| II-first/pass/postI/noinit | 600 (259) | 105 / 0 | 0 / 0 | 0/300 | 0/10 | startfork 0 |
| I-first/pass/postII/init | 600 (361) | 26 / 26 | 0 / 0 | 0/300 | 0/10 | qcheck 26, startfork 95 |
| II-first/pass/postII/init | 600 (333) | 10 / 101 | 0 / 0 | 0/300 | 0/10 | qcheck 10, startfork 95 |
| I-first/pass/postII/noinit | 600 (269) | 132 / 132 | 0 / 0 | 0/300 | 0/10 | qcheck 132 |
| II-first/pass/postII/noinit | 600 (275) | 85 / 9 | 0 / 0 | 0/300 | 0/10 | qcheck 9, startfork 0 |
| I-first/nopass/every/init | 600 (497) | 80 / 80 | 0 / 0 | 0/300 | 0/10 | gates 80, qcheck 26, startfork 9 |
| II-first/nopass/every/init | 600 (505) | 90 / 194 | 0 / 0 | 0/300 | 0/10 | gates 90, qcheck 45, startfork 36 |
| I-first/nopass/every/noinit | 600 (510) | 70 / 70 | 0 / 0 | 0/300 | 0/10 | gates 70, qcheck 34 |
| II-first/nopass/every/noinit | 600 (468) | 122 / 131 | 0 / 0 | 0/300 | 0/9 (+1 cap) | gates 131, qcheck 47, startfork 0 |
| I-first/nopass/postI/init | 600 (505) | 54 / 54 | 0 / 0 | 0/300 | 0/10 | gates 54, startfork 28 |
| II-first/nopass/postI/init | 600 (474) | 69 / 175 | 0 / 0 | 0/300 | 0/10 | gates 69, startfork 45 |
| I-first/nopass/postI/noinit | 600 (462) | 102 / 102 | 0 / 0 | 0/300 | 0/10 | gates 102 |
| II-first/nopass/postI/noinit | 600 (426) | 94 / 107 | 0 / 0 | 0/300 | 0/10 | gates 107, startfork 0 |
| I-first/nopass/postII/init | 600 (453) | 86 / 86 | 0 / 0 | 0/300 | 0/10 | gates 54, qcheck 73, startfork 54 |
| II-first/nopass/postII/init | 600 (473) | 80 / 170 | 0 / 0 | 0/300 | 0/10 | gates 81, qcheck 71, startfork 73 |
| I-first/nopass/postII/noinit | 600 (420) | 119 / 119 | 0 / 0 | 0/300 | 0/10 | gates 136, qcheck 119 |
| II-first/nopass/postII/noinit | 600 (416) | 149 / 119 | 0 / 0 | 0/300 | 0/10 | gates 116, qcheck 84, startfork 0 |
### 4.2 CNF, only one player may pass (seed 3, 200 per variant)
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/passI/every/init | 200 (165) | 39 / 39 | 0 / 0 | 0/200 | 0/5 | gates 39, qcheck 0, startfork 0 |
| II-first/passI/every/init | 200 (174) | 33 / 70 | 0 / 0 | 0/200 | 0/5 | gates 33, qcheck 0, startfork 15 |
| I-first/passI/every/noinit | 200 (159) | 36 / 36 | 0 / 0 | 0/200 | 0/5 | gates 36, qcheck 0 |
| II-first/passI/every/noinit | 200 (144) | 54 / 56 | 0 / 0 | 0/200 | 0/5 | gates 56, qcheck 0, startfork 0 |
| I-first/passI/postI/init | 200 (168) | 28 / 28 | 0 / 0 | 0/200 | 0/5 | gates 28, startfork 0 |
| II-first/passI/postI/init | 200 (152) | 37 / 69 | 0 / 0 | 0/200 | 0/5 | gates 37, startfork 6 |
| I-first/passI/postI/noinit | 200 (164) | 41 / 41 | 0 / 0 | 0/200 | 0/5 | gates 41 |
| II-first/passI/postI/noinit | 200 (154) | 42 / 60 | 0 / 0 | 0/200 | 0/5 | gates 60, startfork 0 |
| I-first/passI/postII/init | 200 (160) | 29 / 29 | 0 / 0 | 0/200 | 0/5 | gates 35, qcheck 2, startfork 8 |
| II-first/passI/postII/init | 200 (156) | 35 / 76 | 0 / 0 | 0/200 | 0/5 | gates 38, qcheck 0, startfork 12 |
| I-first/passI/postII/noinit | 200 (144) | 44 / 44 | 0 / 0 | 0/200 | 0/5 | gates 72, qcheck 9 |
| II-first/passI/postII/noinit | 200 (146) | 53 / 71 | 0 / 0 | 0/200 | 0/5 | gates 77, qcheck 0, startfork 0 |
| I-first/passII/every/init | 200 (146) | 0 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 0, startfork 8 |
| II-first/passII/every/init | 200 (129) | 0 / 25 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 1, startfork 25 |
| I-first/passII/every/noinit | 200 (132) | 8 / 8 | 0 / 0 | 0/200 | 0/5 | gates 8, qcheck 0 |
| II-first/passII/every/noinit | 200 (116) | 21 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 3, startfork 0 |
| I-first/passII/postI/init | 200 (144) | 0 / 0 | 0 / 0 | 0/200 | 0/5 | gates 0, startfork 9 |
| II-first/passII/postI/init | 200 (122) | 1 / 28 | 0 / 0 | 0/200 | 0/5 | gates 1, startfork 28 |
| I-first/passII/postI/noinit | 200 (135) | 5 / 5 | 0 / 0 | 0/200 | 0/5 | gates 5 |
| II-first/passII/postI/noinit | 200 (114) | 23 / 1 | 0 / 0 | 0/200 | 0/5 | gates 1, startfork 0 |
| I-first/passII/postII/init | 200 (131) | 10 / 10 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 10, startfork 25 |
| II-first/passII/postII/init | 200 (123) | 6 / 33 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 4, startfork 30 |
| I-first/passII/postII/noinit | 200 (113) | 30 / 30 | 0 / 0 | 0/200 | 0/4 (+1 cap) | gates 1, qcheck 26 |
| II-first/passII/postII/noinit | 200 (108) | 26 / 5 | 0 / 0 | 0/200 | 0/5 | gates 0, qcheck 5, startfork 0 |
### 4.3 DNF checker (seed 6, 150 per variant): Chung Thm 22 complement = rows pass/postII/noinit and nopass/postII/noinit
| variant | instances (YES) | BASE pre / raw | ADAPT mscd / ts | S1 | S2 | NC (gates, qcheck, startfork) |
|---|---|---|---|---|---|---|
| I-first/pass/every/init | 150 (118) | 57 / 57 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 0 |
| II-first/pass/every/init | 150 (113) | 28 / 88 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 22 |
| I-first/pass/every/noinit | 150 (108) | 55 / 55 | 0 / 0 | 0/150 | 0/3 | qcheck 0 |
| II-first/pass/every/noinit | 150 (87) | 48 / 81 | 0 / 0 | 0/150 | 0/3 | qcheck 0, startfork 0 |
| I-first/pass/postI/init | 150 (120) | 46 / 46 | 0 / 0 | 0/150 | 0/3 | startfork 0 |
| II-first/pass/postI/init | 150 (115) | 26 / 84 | 0 / 0 | 0/150 | 0/3 | startfork 24 |
| I-first/pass/postI/noinit | 150 (119) | 56 / 56 | 0 / 0 | 0/150 | 0/3 | - |
| II-first/pass/postI/noinit | 150 (91) | 49 / 82 | 0 / 0 | 0/150 | 0/3 | startfork 0 |
| I-first/pass/postII/init | 150 (115) | 59 / 59 | 0 / 0 | 0/150 | 0/3 | qcheck 8, startfork 30 |
| II-first/pass/postII/init | 150 (95) | 30 / 91 | 0 / 0 | 0/150 | 0/3 | qcheck 3, startfork 24 |
| I-first/pass/postII/noinit | 150 (90) | 87 / 87 | 0 / 0 | 0/150 | 0/3 | qcheck 33 |
| II-first/pass/postII/noinit | 150 (85) | 52 / 83 | 0 / 0 | 0/150 | 0/3 | qcheck 3, startfork 0 |
| I-first/nopass/every/init | 150 (131) | 44 / 44 | 0 / 0 | 0/150 | 0/3 | gates 13, qcheck 5, startfork 1 |
| II-first/nopass/every/init | 150 (127) | 31 / 77 | 0 / 0 | 0/150 | 0/3 | gates 18, qcheck 10, startfork 9 |
| I-first/nopass/every/noinit | 150 (133) | 47 / 47 | 0 / 0 | 0/150 | 0/3 | gates 19, qcheck 12 |
| II-first/nopass/every/noinit | 150 (125) | 34 / 68 | 0 / 0 | 0/150 | 0/3 | gates 36, qcheck 17, startfork 0 |
| I-first/nopass/postI/init | 150 (123) | 56 / 56 | 0 / 0 | 0/150 | 0/3 | gates 15, startfork 3 |
| II-first/nopass/postI/init | 150 (120) | 30 / 74 | 0 / 0 | 0/150 | 0/3 | gates 7, startfork 9 |
| I-first/nopass/postI/noinit | 150 (126) | 45 / 45 | 0 / 0 | 0/150 | 0/3 | gates 18 |
| II-first/nopass/postI/noinit | 150 (116) | 48 / 85 | 0 / 0 | 0/150 | 0/3 | gates 29, startfork 0 |
| I-first/nopass/postII/init | 150 (115) | 50 / 50 | 0 / 0 | 0/150 | 0/3 | gates 14, qcheck 22, startfork 10 |
| II-first/nopass/postII/init | 150 (122) | 40 / 83 | 0 / 0 | 0/150 | 0/3 | gates 30, qcheck 15, startfork 15 |
| I-first/nopass/postII/noinit | 150 (101) | 77 / 77 | 0 / 0 | 0/150 | 0/3 | gates 25, qcheck 26 |
| II-first/nopass/postII/noinit | 150 (102) | 55 / 90 | 0 / 0 | 0/150 | 0/3 | gates 29, qcheck 23, startfork 0 |

Columns: *BASE* = the current generator's arena (+ B's pre-processing / without it), mismatches with the variant's
G6 value; *ADAPT* = §3 arena with ideal doors (mscd) and with Lemma TS (ts); *S1* = ADAPT-ts through
`L_gen.netlist` + `solve_net` (diodes, SCDs, coin); *S2* = also through `L_gen`'s bus layout, concrete-block
re-read and crossovers (`Level.network`); *NC* = mismatches when one adaptation is switched off (negative control:
shows it is needed). Instances: review5_t1's distribution (|X|, |Y| ≤ 2, ≤ 3 clauses, width ≤ 3); a player who may
not pass gets ≥ 1 variable (else he has no legal move; S3 Lemma 3 adds a fresh variable).

## 5. Which variant to cite

**5.1 Every reading the sources support needs no arena change.** These readings are: both players may pass, F
checked after every move or only after I's moves, initial position counted or not, either first mover, infinite
play a non-win for I. They fall into three G6 problems, checked by solving G6 under all 48 variants on 1,500
random instances (|X|, |Y| ≤ 3, ≤ 4 clauses; `V_variants.py --equiv`; equal values on all 1,500 = VERIFIED empirically; the I-first collapse is STRONG by L1):
- I first: every/post-I × init/noinit give one problem (L1: I may pass to "register" F). Use B's arena with s = h.
- II first, initial position counts: every = post-I. Use B's arena with s = N_in **plus** B §1.1's
  pre-processing (F(α₀) true ⇒ YES). Without it: 39-53 mismatches per 300.
- II first, initial position does not count: every = post-I. Use B's arena with s = N_in and **no**
  pre-processing. With it: 41-60 mismatches per 300. B §1.1 already says this ("skip pre-processing").
So B §1.1 is correct as written. The only care point is that the pre-processing step must follow the initial-position
convention. The start fork (S) removes even that choice, so one arena serves both readings.

**5.2 Recommended statement.** Cite the source game in SC79's own form, a decision problem on positions (τ, F, α)
with τ = player to move (S4, S6), passing allowed, I wins iff F holds at a position reached after some move of I
(Chung's frame, S3), draws for II. That is Chung's "Single-formula Flip-Zero-Or-One Win CNF" = G6. The theorem then
covers both τ, through s = h or s = N_in, with no pre-processing. Under this convention the checker is reached
only from P, exactly as B §3 builds it. The "ever becomes true" wording (Hearn) is the same problem by L1 when I
moves first, and when II moves first it is the same problem plus the pre-processing.

**5.3 Readings without a source also work, with small local changes:**
- (G) gates when a player may not pass;
- (Q) a post-II checker when II's moves are checked and I cannot always pass;
- (S) a start fork.

Each change uses only SCDs, diodes and forks, so the size stays O(N⁴) (gates add 2 SCDs per variable; Q and s₀
add 2 forks). L_gen builds and lays out the adapted arenas unchanged (S1/S2 columns).

**5.4 Is some variant EXPTIME-complete independently of the SC79 text?**
- *Flip-exactly-one G6* (no passing, CNF): EXPTIME-c by SC79 + Chung Lemma 3, a fresh unused variable per player
  (S3 Table 1.1). This still rests on SC79.
- *Chung 2026, Thm 22* (VERIFIED, read): "Single-formula Flip-Zero-Or-One Lose 12DNF (draws count as wins for
  Player I)" is EXPTIME-complete, and so is its Flip-Exactly-One version. The proof chain is entirely in the thesis
  and does **not** use SC79's games: Thm 20 (latch game, from linear-bounded alternating TMs), then Thm 21 (G̃3,
  5DNF/constant formula), then Thm 22.
  - Its complement is "Player II forces F (12-DNF) to be true right after one of Player I's moves; infinite play is
    a non-win for II". EXPTIME is closed under complement, so this complement is EXPTIME-hard too.
  - That is exactly our game shape with the hero = Chung's II, nature = Chung's I, check = after nature's moves,
    and a **DNF** checker. Our variant (pass, postII, noinit) with `--dnf` is this game. The DNF checker is c₀
    forking over terms, each term a chain of S² tunnels into c_m, still a dead end.
  - It is tested in §4 (DNF block).
  - **So a fallback citation exists that avoids SC79 entirely:** reduce from the complement of Chung's Thm 22
    game with arena changes (Q) and the DNF checker. One convention is still not stated in Chung: who moves
    first. Our arena handles both. STRONG for the reduction; VERIFIED on the tested instances.
  - Caveat: Chung is an S.M. thesis (not peer-reviewed as a paper). Its Thm 22 proof was read here, not
    re-checked line by line.

## 6. Reproduce
```
python tools/exptime/V_variants.py --trials 300 --seed 1 --pas pass --s1 --s2 10      # 4.1 seed 1, pass rows (~12 min)
python tools/exptime/V_variants.py --trials 300 --seed 1 --pas nopass --s1 --s2 10    # 4.1 seed 1, nopass rows (~45 min)
python tools/exptime/V_variants.py --trials 300 --seed 2 --sym                        # 4.1 seed 2, arena only (~10 min)
python tools/exptime/V_variants.py --trials 200 --seed 3 --asym --s1 --s2 5           # 4.2 (~35 min)
python tools/exptime/V_variants.py --dnf --sym --trials 150 --seed 6 --s1 --s2 3      # 4.3 (~30 min)
python tools/exptime/V_variants.py --equiv                                            # §5.1 equivalence classes
python tools/exptime/V_variants.py --only II,nopass,every,init --trials 50            # one variant
```
Per-variant RNG = crc32(variant name) + 7919·seed, so a `--pas` run reproduces the matching rows of a `--sym` run.
Reports: `build/variants/report_*.json`, logs `build/variants/run_*.log`. The seed-1 pass rows come from a run made
before the cap handling was added (`run_seed1.log`; that run then stopped at an S1 cap in the nopass block, which was
re-run with `--pas nopass`). The seed-3 passII rows were re-run the same way.

## 7. Side observations
- **One-sided redundancy (STRONG, seen in 4.2).** If II may pass and post-II positions are checked, I's pass is never
  needed except at the start. If (α, I) is won only through I's pass, then (α, II) is won, which includes II's pass
  back to (α, I). By attractor rank, (α, I) was won earlier through another move. This is why the `gates` control
  shows 0 on I-first/passII/every/init and the like.
- B §1.1's text is right on every point tested. Suggested wording for B §1.1 / the paper: "G6 [SC79] as a decision
  problem on positions (τ, F, α) (τ = player to move; restated in [Ying–Ying 2014], [Šámal–Valla] for G2); passing
  allowed; Player I wins iff F holds after one of his moves (Chung 2026 Def. 1); draws are wins for II." Then T1 is
  stated for both τ with s = h / N_in and no pre-processing. Not applied: this workstream edits only its own files.
- Not done: SC79 itself is still unread, so the source table is secondary only (no open copy found; the SIAM page is
  paywalled). The instances are small (|X|, |Y| ≤ 2, ≤ 3 clauses), like review 5's.
