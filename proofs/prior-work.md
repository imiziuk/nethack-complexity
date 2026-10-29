# Prior-work search: complexity of NetHack / roguelikes (Oct 29, 2026)

Question: are these new?
- (1) generalized NetHack (hunger off, boulder/Sokoban rules) is PSPACE-complete via Push-1F;
- (2) with faithful hunger it is NP-complete;
- (3) any complexity result (NP/PSPACE/EXPTIME-hard, undecidable) about NetHack, Rogue, Hack, Angband, Brogue, DCSS, ADOM, Moria or roguelikes in general; Sokoban-in-a-roguelike; hunger-clock / resource-bounded pushing.

Builds on `citations.md` row 15 (arXiv/web search, Oct 28: nothing NetHack-specific). Searches below are new.

## 1. Searches run

| # | Source | Query / scope | Result | URL |
|---|---|---|---|---|
| 1 | DBLP (API + site) | nethack, roguelike, rogue-like, dungeon crawl, sokoban | **NOT SEARCHED**: dblp.org and dblp.uni-trier.de now sit behind an Anubis bot-challenge page; not bypassed. OpenAlex (row 3) used as substitute (it indexes the DBLP venues). | https://dblp.org/search?q=nethack |
| 2 | OpenAlex title/abstract search | nethack (426 hits), roguelike (1237), rogue-like, angband (118), brogue, dungeon crawl, "roguelike complexity", "nethack complexity", "roguelike NP-hard", "sokoban hunger", "sokoban move limit NP-complete", "sokoban bounded moves", "rogue game complexity" | No complexity result about any roguelike. NetHack hits are RL/agents/benchmarks (NLE, MiniHack, Katakomba, "NetHack is Hard to Hack" NeurIPS 2023 = neurosymbolic agents, not complexity). | https://api.openalex.org/works?search=nethack |
| 3 | OpenAlex boolean title+abstract filter | ("nethack" / "roguelike" / "rogue-like" / "angband" / "brogue" / "dungeon crawl" / "ADOM" / "moria" / "Dungeon Crawl Stone Soup") AND ("NP-hard" / "NP-complete" / "PSPACE" / "undecidable" / "computational complexity") | 0 hits for every game name; "rogue" hits are rogue taxa / rogue devices (irrelevant). | https://api.openalex.org/works?filter=title_and_abstract.search:... |
| 4 | OpenAlex FULL-TEXT search | nethack / roguelike + NP-hard / NP-complete / PSPACE / undecidable | Only passing mentions (FLAIRS 2026 Alvin; Taylor 2015 Sokoban generation thesis; RL papers). None proves anything about a roguelike. | https://api.openalex.org/works?filter=fulltext.search:nethack%20PSPACE |
| 5 | Semantic Scholar API | 16 queries (nethack PSPACE / NP-hard / complexity; roguelike NP-complete / PSPACE / complexity; sokoban limited moves; energy-constrained sokoban; Push-1F; brogue; angband ...) | **PARTIAL**: API rate-limited (HTTP 429) on 13/16 queries even with retries. The 3 that returned (nethack computational complexity, roguelike PSPACE, video game hunger complexity, sokoban limited moves) had no roguelike complexity paper. | https://api.semanticscholar.org/graph/v1/paper/search?query=nethack+PSPACE |
| 6 | Google Scholar | "NetHack" "PSPACE" | 1 hit: MIT Hardness Group Push-1 paper (mentions NetHack only as an example game with block puzzles). | https://scholar.google.com/scholar?q=%22NetHack%22+%22PSPACE%22 |
| 7 | Google Scholar | "NetHack" "NP-hard" (17 hits) | Passing mentions only (Wolczyk et al. 2024 says NetHack's Sokoban is modelled on an NP-hard puzzle; Netzer-Weaver 1994 used NetHack as a debugging workload). | https://scholar.google.com/scholar?q=%22NetHack%22+%22NP-hard%22 |
| 8 | Google Scholar | "NetHack" "NP-complete" | Nothing about NetHack's complexity. | https://scholar.google.com/scholar?q=%22NetHack%22+%22NP-complete%22 |
| 9 | Google Scholar | "NetHack" "Sokoban" "PSPACE-complete" | Taylor 2015 (cites Culberson), Push-1 paper. No NetHack theorem. | https://scholar.google.com/scholar?q=%22NetHack%22+%22Sokoban%22+%22PSPACE-complete%22 |
| 10 | Google Scholar | "roguelike" "NP-complete" / "NP-hard" / "PSPACE" | Only roguelike-flavoured complexity claim: Thompson FDG 2015 (Spelunky NP-hard). Rest = PCG theses, a Czech NetHack-bot thesis (Kraj..., Charles Univ. 2015) citing Culberson. | https://scholar.google.com/scholar?q=%22roguelike%22+%22PSPACE%22 |
| 11 | Google Scholar | NetHack / roguelike + "Turing complete" / "undecidable" / "EXPTIME" | Nothing. Borenstein 2015 (MIT thesis on tabletop games) asserts in passing that roguelikes "are Turing complete", no proof. | https://scholar.google.com/scholar?q=%22roguelike%22+%22undecidable%22 |
| 12 | Google Scholar | Sokoban / pushing blocks + time limit / move limit / energy / hunger + "NP-complete" | Found Polishchuk CCCG 2004 (box mover, <=k moves), Forisek FUN 2010 (time-limit metatheorem), Cormode FUN 2004 (Lemmings with time limit). No hunger/energy pushing paper. | https://scholar.google.com/ (query in col. 3) |
| 13 | Google Scholar | "hunger" game "NP-hard"/"PSPACE-hard" | Nothing about a hunger mechanic. | https://scholar.google.com/scholar?q=%22hunger%22+game+%22NP-hard%22 |
| 14 | FUN 2018 (LIPIcs 100), 2021 (LIPIcs 157), 2022 (LIPIcs 226), 2024 (LIPIcs 291), 2026 (LIPIcs 366) full TOCs on DROPS | titles + abstracts scanned for NetHack/rogue/dungeon/hunger/food/energy/Sokoban | None roguelike or hunger related. Pushing papers: Push-1F (FUN 2022), Pushing Blocks by Sweeping Lines (2022), Torus push number (2026). | https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-366 |
| 15 | FUN 1998-2016 (Springer LNCS) | via OpenAlex/Scholar title search (rows 2-12) | No roguelike paper surfaced. TOCs not read page by page. | - |
| 16 | CCCG 1999-2015 HTML TOCs + CCCG 2022 full proceedings PDF | grep nethack/rogue/dungeon/hunger/sokoban/push | Only the known push papers (Hoffmann 2000, DDO 2000, Demaine-Hoffmann 2001 Push-X, Push-2-F 2002) and Polishchuk 2004. CCCG 2016-2025 index pages return 403 (only 2022 PDF readable). | https://cccg.ca/proceedings/2001/ |
| 17 | JCDCG^3 | web search | No roguelike/hunger result; 2022 has a Demaine talk "Pushing Block Puzzles" (talk only). Proceedings abstracts not fully read. | https://www.rs.tus.ac.jp/jcdcggg/ |
| 18 | IEEE CoG/CIG, FDG, AIIDE, ICGA J., TCS | via OpenAlex rows 2-4 + Scholar | CoG/AIIDE NetHack papers are RL/agents. FDG 2015 Spelunky paper (row 25 below). ICGA J. 2026 has the Push-1 paper. TCS: Aloupis et al. 2015, Hearn-Demaine 2005, Pull/PushPull 2016; nothing roguelike. | - |
| 19 | erikdemaine.org full paper list (456 KB) | grep rogue/nethack/dungeon/hunger/food/energy/fuel; push/video game titles | No roguelike or hunger paper. Relevant: all Push papers, Zelda mechanics, Portal, Mario, gadget-framework papers. | https://erikdemaine.org/papers/ |
| 20 | erikdemaine.org/pushingblocks | categorization page | All pushing variants between NP-hard and PSPACE; no time/energy-bounded variant listed. | http://erikdemaine.org/pushingblocks/ |
| 21 | Theses: Bosboom PhD 2020 (MIT), Hearn PhD 2006 (MIT), Coulombe PhD 2023 (MIT) full text; Lynch PhD 2020 (abstract only, PDF not open) ; Hendrickson thesis (not located) | grep nethack/rogue/angband/hunger/food/time limit | No roguelike mention. Hearn: "Bounded NCL is NP-complete" (Thm 5/6) and "one-player puzzle with bounded length ... odds are NP-complete". Lynch (abstract): bounded 1-player gadget motion planning is NL vs NP-complete. | https://dspace.mit.edu/handle/1721.1/129245 ; https://dspace.mit.edu/handle/1721.1/37913 ; https://dspace.mit.edu/handle/1721.1/151237 |
| 22 | Wikipedia "Game complexity", "List of PSPACE-complete problems", "List of NP-complete problems" | game lists | No NetHack/Rogue/roguelike. Lemmings listed (NP-complete with polynomial time limit; PSPACE-complete without). | https://en.wikipedia.org/wiki/List_of_NP-complete_problems |
| 23 | Eppstein "Computational Complexity of Games and Puzzles" | grep | No roguelike; Sokoban/pushing only. | https://ics.uci.edu/~eppstein/cgt/hard.html |
| 24 | NetHackWiki (MediaWiki search API) | "NP-complete", "NP-hard", "PSPACE", "complexity class", "Turing complete", complexity, computational | 0 hits each (the API works: "sokoban" gives 47 hits). | https://nethackwiki.com/mediawiki/api.php?action=query&list=search&srsearch=PSPACE |
| 25 | r/nethack (PullPush archive, posts + comments) | NP-complete, NP-hard, PSPACE, undecidable | 0 relevant (only "complexity" in the gameplay sense). r/roguelikes and r/roguelikedev: **NOT SEARCHED** (PullPush rate-limits agents; reddit.com JSON blocked). | https://api.pullpush.io/reddit/search/comment/?q=PSPACE&subreddit=nethack |
| 26 | rec.games.roguelike.nethack (Usenet) | web search | Nothing found; Google Groups archive not reachable with these tools. | - |
| 27 | General web (extended) | "NetHack" + PSPACE/NP-hard; roguelike complexity; hunger mechanic complexity; Sokoban + fuel/energy/hunger | Nothing NetHack- or hunger-specific. | - |

## 2. Closest related work

| Work | Relation to our results |
|---|---|
| MIT Hardness Group (Brunner, Chung, Demaine, Diomidova, Hendrickson, Lynch), "Pushing Blocks Without Fixed Walls via Checkable Gizmos: Push-1 Is PSPACE-Complete", **ICGA Journal 48(3):86-114, Aug 2026**, DOI 10.1177/13896911261472776; arXiv 2508.19759 | **Closest.** Intro lists "roguelike games such as NetHack" among games with block puzzles, but proves nothing about NetHack. Shows the Push community knows NetHack has block puzzles and has not claimed the result. Cite as the venue version of citations.md 1d. |
| Ani, Chung, Demaine, Diomidov, Hendrickson, Lynch, "Push-1F ... PSPACE-complete", FUN 2022 | The source problem for (1). Our (1) is a reduction FROM it; the novelty is the NetHack embedding, not the hardness core. Also notes its base gadgets are bounded-use, so reachability with them alone is in NP (relevant to (2)). |
| Thompson, "'With Fate Guiding My Every Move': The Challenge of Spelunky", FDG 2015 | **Only prior complexity claim about a roguelike-style game found.** Spelunky (roguelike-platformer) is in PSPACE and NP-hard via Viglietta's metatheorems (location traversal + single-use paths; consumable items as tokens/toll roads). No PSPACE-hardness, not NetHack, no hunger. |
| Forisek, "Computational complexity of two-dimensional platform games", FUN 2010 (Metatheorem 2) | NP-hardness from a **tight time limit** on traversing a grid graph. Direct technique precedent for "hunger clock as a time limit" in (2). |
| Cormode, "The hardness of the Lemmings game, or Oh no, more NP-completeness proofs", FUN 2004; Viglietta, "Lemmings is PSPACE-complete", FUN 2014 / TCS 2015 (arXiv 1202.6581) | Same pattern as (1)+(2): with a polynomial time limit the game is NP-complete; without it, PSPACE-complete. Strongest analogy; reviewers will cite it. |
| Viglietta, "Gaming is a hard job...", FUN 2012 / ToCS 2014 | Metatheorem 2 (collectible/cumulative tokens + toll roads, NP-hard) matches food items as a consumable resource. |
| Aloupis, Demaine, Guo, Viglietta, "Classic Nintendo games are (computationally) hard", TCS 2015 | Metroid proof uses a health counter (resource) inside an NP-hardness proof. Not hunger, but a resource meter. |
| Hearn, "Games, Puzzles, and Computation", MIT PhD 2006 (also the Hearn-Demaine book) | Bounded NCL is NP-complete; general principle "bounded-length one-player puzzle => NP-complete". |
| Lynch, "A Framework for Proving the Computational Intractability of Motion Planning Problems", MIT PhD 2020; Demaine et al. gadget papers (FUN 2018, ITCS 2020) | Bounded 1-player gadget motion planning is NP-complete in general. Gives a generic route to NP membership/hardness when every move consumes a budget. |
| Papadimitriou, Raghavan, Sudan, Tamaki, "Motion planning on a graph", FOCS 1994 (as cited by Dor-Zwick 1999) | Movable obstacles on a graph: reachability is linear time, but "within at most k steps" is NP-complete. Step-budget precedent. |
| Polishchuk, "The box mover problem", CCCG 2004, pp. 36-39 | Sokoban-like optimization version (solution with fewer than k box moves) is NP-complete on trivially solvable instances (from secondary sources; PDF not read). Closest "move-limited pushing" result; not hunger, not Push-1F reachability. |
| Demaine-Demaine-O'Rourke, "PushPush and Push-1 are NP-hard in 2D", CCCG 2000; Demaine-Hoffmann, "Pushing blocks is NP-complete for noncrossing solution paths", CCCG 2001 | Push NP-hardness reductions; the Push-X result is the only pushing variant shown to be IN NP (by a path restriction, not a budget). |
| Wolczyk et al., "Fine-tuning RL models is secretly a forgetting mitigation problem", ICML 2024 (arXiv) | Informal remark that NetHack's Sokoban is modelled on an NP-hard puzzle. No theorem. |
| Alvin, "Computational Models of Player Strategy in Roguelike Games", FLAIRS 39(1), 2026, DOI 10.32473/flairs.39.1.141675 | Names NetHack/Angband; maps roguelike strategies to CSP/MDP/bandits; mentions knapsack NP-hardness for inventory. No complexity result about a roguelike. |
| ZenoRogue, "Life, Complexity, and Roguelikes" (Medium essay; citations.md 15) | Informal: no roguelike known to be PSPACE-complete. Supports novelty. |
| Kuttler et al., NetHack Learning Environment (NeurIPS 2020) and the NetHack RL literature | Describe NetHack as a hard POMDP; no complexity theorem. |

## 3. Verdicts

**(1) Generalized NetHack (hunger off, boulder/Sokoban rules) PSPACE-complete via Push-1F: NOVEL as far as found.**
No paper, thesis, wiki page or forum post proves any complexity result for NetHack. The MIT Hardness Group (ICGA J. 2026) names NetHack as a block-puzzle game without claiming hardness. Caveat for the write-up: the hardness core is the known Push-1F theorem (Ani et al., FUN 2022), so reviewers may see (1) as a corollary. The contribution must be the faithful embedding: NetHack boulder rules (diagonal moves, squeezing past boulders, Sokoban-level restrictions, monsters/items neutralized) and PSPACE membership for the generalized game.

**(2) With faithful hunger, NP-complete: NOVEL for NetHack, PARTLY KNOWN as a technique.**
No hunger, food-clock or energy-bounded pushing result exists. But "a polynomial time limit puts the game in NP, while hardness survives" is standard: Lemmings (Cormode 2004 NP-complete with time limit vs Viglietta 2014/15 PSPACE-complete without), Forisek 2010 Metatheorem 2, Hearn's bounded NCL, Lynch's bounded gadgets, step-bounded movable-obstacle planning (Papadimitriou et al. 1994), Polishchuk 2004. Cite them and present (2) as the NetHack instance of this pattern. The new part is showing that faithful hunger really bounds the useful play length polynomially (food supply, prayer, etc.) and that NP-hardness survives under that budget.

**(3) Any complexity result about a roguelike:** only Thompson FDG 2015 (Spelunky NP-hard, informal metatheorem application). Nothing for NetHack, Rogue, Hack, Angband, Brogue, DCSS, ADOM or Moria. No undecidability or EXPTIME claim found (only an unproven "roguelikes are Turing complete" aside in Borenstein 2015).

## 4. Not searched / gaps
- **DBLP**: blocked by a bot-challenge page; OpenAlex used instead. Re-check by hand in a browser: dblp.org/search?q=nethack, ?q=roguelike, ?q=sokoban%20hard.
- **Semantic Scholar**: 13 of 16 queries rate-limited (429).
- **Reddit r/roguelikes, r/roguelikedev**: archive API rate-limited; r/nethack covered. **rec.games.roguelike.nethack** Usenet archive (Google Groups) not reachable.
- **CCCG 2016-2025** TOC pages return 403 (2022 checked via the full PDF); **FUN 1998-2016** Springer TOCs only via indexes; **JCDCG^3** abstract books not read.
- **Paywalled full texts not read**: Forisek FUN 2010 (metatheorem statement taken from Viglietta's summary), Polishchuk CCCG 2004 (result from secondary sources; the cccg.ca/proceedings/2004/52.pdf link serves a different paper), Cormode FUN 2004 (abstract only), Lynch PhD thesis (abstract only), ICGA J. 2026 version of Push-1 (arXiv text read), IEEE CoG/CIG and FDG proceedings beyond the indexed abstracts.
- Hendrickson's thesis was not located.
