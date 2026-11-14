# History

"Local" is the gate match against the previous version (self-play; inflated relative to
the arena).

## Versions

| Version | Change | Local | Arena | Rank |
|---|---|---|---|---|
| old | 2022 submission | | 22.59 (Bronze) | 181 |
| v1.0 | exact simulator (neutral moves predicted), ID alpha-beta: PVS, TT, LMR, quiescence, handcrafted eval | | 21.62 (Bronze → Legend in one run) | 9 |
| v1.1 | futility, late move pruning, null move (a real WAIT), aspiration, stronger LMR | +129 Elo at 100k nodes, +91 at 50 ms | ~21.5 (replaced at 75%) | 9 |
| v2.0 | first net: 1911 inputs → 32 hidden, 8.4M positions played by v1.1 | +206 Elo at 50 ms; gauntlet 56% | 26.62 → 26.91 | 6 → 5 |
| v2.1 | 64 hidden, generation 1: 25.6M positions by v1.1 + 11.7M by the first net | +144 Elo at 20k nodes; gauntlet 79% | 28.36 → 28.9 | 4 |
| v2.2 | + 10M positions searched at 20k nodes per move (47M in total) | +46 Elo at 20k nodes; gauntlet 85% (40 games) | 29.75 | 4 |
| v2.3 | generation-3 net (70M positions); reverse futility, shots in quiescence, leader-threat moves | +85 Elo at 20k nodes, +68 at 50 ms; 10–0–2 against the top 3 | 30.89 at the end of its run (drifted to 31.9 afterwards) | 2 |
| v2.4 | generation-5 net trained on the 20k-node generations only (55M); +13% nodes/s on CodinGame (AVX2 output layer, static eval in the TT, hash move before generation, 524k-entry table) | +44 Elo at 20k nodes, +42 ± 28 at 50 ms (600 games); top 3 first seat 9–0–2 vs 7–3–2 for v2.3 side by side | 30.91 | 3 |
| v2.5 | net with a new recipe (result weight 0.4, result softened by the final margin) on 65M deep positions; history penalties + singular extensions; leader-threat scoring off | +34 ± 20 at 20k nodes (1,200 games); parts: recipe +19 ± 17, search pair +15 [+7, +23] over 7,200 games; top 3 first seat 7–1–4 vs 8–3–1 for v2.4 side by side | **31.56** | **3** |
| v2.6 | n7e80 net (v2.5 recipe, 80 epochs); transposition table in quiescence; packer strips indentation (94.7k chars) | +34 ± 14 at 20k nodes vs v2.5 (2,400 games); QTT +13.5 [+4, +23] over 4,800 games; aCat first seat on 9 fixed maps 2.5/9 then 6.5/9 on a re-run (v2.5 6/9): nine test games cannot separate versions; second-seat suite 5–5 vs 5–4–1 for v2.5 | 29.54 (128 battles): first seat 36–8–5 against 71–3–4 for v2.5, five first-seat losses to aCat after leading by up to +1,400; reverted to v2.5 | 4 |
| v2.5 again | resubmitted unchanged (baseline), twice | | **31.97**, then 30.65 | 3 |
| v2.7a | v2.5 + new iterations allowed until 85% of the turn (`TM_PCT` 85, mean 39 ms per turn instead of 33) | +16, +12, +6 at 50 ms (3,600 games, pooled +11 ± 12) | 30.87, then 31.69 (rank 2); on v2.5's pooled mix 71.2% over both runs against 72.3% for v2.5's three: equal | 2–3 |
| v2.7c | v2.5 with the n11d net (generations 3–12, 65.6M positions, result weight 0.6, 40 epochs): best on held-out real battles (AUC 0.9421, log-loss 0.360 against 0.383 for n7a, 34k positions from 247 battles) | −7 ± 14 at 20k nodes (2,400 games) | 29.55; on v2.5's mix 67.4% (v2.5 71.2 / 75.5): top 3 first seat 10/16, second 5/22. Reverted to v2.5 | 3 |
| v2.8a | v2.5 search with the n12a net: n7a's data and recipe + 224k positions from our 1,622 arena games, each searched again at 300k nodes for its label, repeated 10× | +4 ± 17 at 20k nodes (1,600 games) | **31.82** at 100%, drifting to **32.51** (aCat 32.52) over the next 1.5 hours; on v2.5's pooled mix 75.4% (v2.5 72.3% over three runs): top 3 first seat 18/22, second 6/16 | **2** |

## Measured (300 games each, ±40 Elo, vs v1.0)

| Change | 20k nodes | 100k nodes |
|---|---|---|
| Quiescence off | −92 | |
| 4× nodes | +105 | |
| Eval weights (HP 20/70/110, neutral distance, leader value, leader HP) | −39…+9: flat | |
| Reverse futility 80 / 150 / 300 | −54 / −46 / −35 | |
| Null move + reverse futility | −74 | |
| Internal iterative reduction | −24 | |
| Null move alone | +7 | |
| Aspiration 60 / 200 | +14 / −29 | |
| LMR divisor 1.4 / 3.0 | +32 / −10 | |
| Futility 200 / 400 | +32 / +41 | |
| Late move pruning 6 / 3 | +17 / +51 | |
| Futility 450 + LMP 2 + LMR 1.1 | +101 | |
| + null move + aspiration 60 (**v1.1**) | | **+129** |
| v1.1 with LMR 0.8 / futility 700 / LMP 1 / null move R3 / IIR / aspiration 30 / LMP depth 5 | | +107 / +117 / +119 / +96 / +111 / +102 / +137: plateau |

## Nets (gate at 20k nodes, 300 games)

| Net | Data | Hidden | vs | Elo |
|---|---|---|---|---|
| n0a | 8.4M gen 0 | 32 | v1.1 | +242 |
| n0b (result weight 0.3) | 6.7M gen 0 | 32 | n0c (0.6) | −73 |
| n0e | 8.4M gen 0 | 64 | n0c | −39 (equal at 50 ms) |
| n0f | 25.6M gen 0 | 32 | n0c | +73 |
| n0g | 25.6M gen 0 | 64 | n0c | +96 |
| n1b | 37.3M gen 0 + 1 | 32 | n0g | +105 |
| n1a (**v2.1**) | 37.3M gen 0 + 1 | 64 | n0g | +144 |

| n1x (**v2.2**) | 47.4M, incl. 10M at 20k nodes | 64 | n1a | +46 |
| n2a | 58M gen 0–2 | 64 | n1x | +27 |
| n2w | 58M | 128 | n2a | +24, 14% slower |
| n1t / n2t (relational inputs: units under fire, convertible units) | 37M / 58M | 64 | n1a / n2a | −5 / −16, 27% slower |
| n3a (**v2.3**) | 70M gen 0–3 | 64 | n1x | +32 |
| n4a | 80M gen 0–4 | 64 | n3a | +15 |

## v2.6: a self-play gain that lost in the arena

v2.6 beat v2.5 by +34 ± 14 over 2,400 self-play games and finished its arena run 1.6–2
points below it. Every part looked sound on its own: the n7e80 net (+17 self-play), the
quiescence table (+13.5 at fixed nodes, −1% node speed in test games). In the arena it
lost first-seat games it led: at turn 108 of one, five units (7, 3, 2 and 5 hp cultists)
against aCat's three healthy ones, evaluated +665, lost all four cultists to focused fire.
Self-play never produces that opponent, so no self-play number can see it.

What the episode showed:
- An arena run takes about 35 minutes to reach 100% (128 battles), and the battle logs
  include our stderr: depth, nodes and speed of every arena turn. Arena node speed varies
  with the time of day (v2.4 2.35M nodes/s, v2.5 3.14M, v2.6 2.83M, same per-node cost).
- Nine test games against aCat on fixed maps gave v2.6 2.5/9 and then 6.5/9: test games
  cannot separate versions; the arena run can.
- Nets scored on held-out real battles (v2.6's 128): AUC 0.928–0.934 for every net since
  generation 5 (n5d best, n7e80 among the worst); the arena-mixed net n10x overfits (0.965
  on its own training games, 0.928 held out).

One arena run is about 120 battles: its score on a fixed game mix has a standard error
near 4 points of percentage (about 30 Elo). v2.5 submitted three times, unchanged: 31.56,
31.97, 30.65; on the pooled game mix 72.3%, 76.3%, 69.4%. On that mix v2.7a scored 71.0%,
v2.7c 68.5%, v2.6 64.6%: only v2.6 is clearly worse. One run separates changes of about
50 Elo or more; smaller ones need several runs.

A local pool of frozen older versions does not replace it. At 20k nodes, 800 games each:

| | vs v2.2 (n1x) | vs v2.3 | vs v2.4 | arena |
|---|---|---|---|---|
| v2.5 | +105 | +41 | +21 | 31.56 / 31.97 |
| v2.6 | +146 | +79 | +46 | 29.54 |
| v2.7c (n11d) | +97 | +41 | +7 | 29.55 |

The pool ranks v2.6 first; the arena ranks it last. Older versions of the same bot share
its blind spots. Both arena failures changed the net (v2.6, v2.7c, about −2.2 points);
the one that kept v2.5's net (v2.7a) lost 0.9, inside the noise.

## What the arena battles say (676 games rebuilt from seed + moves)

Score against the eight players above us, by seat:

| | first seat | second seat |
|---|---|---|
| v1.0 | 41% | 19% |
| v2.0 | 66% | 30% |
| v2.1 | 69% | 38% |
| v2.2 | 67% | 33% |

v2.5 (submission 41711486, 170 battles), by opponent and seat (W–L–D):

| | first seat | second seat |
|---|---|---|
| aCat | 4–0–1 | 0–9–1 |
| Noobkins | 3–0–0 | 4–6–1 |
| MSz | 8–1–0 | 3–3–2 |
| ziele | 30–0–2 | 16–14–6 |
| Zylo | 4–1–0 | 8–2–2 |

Between the top bots the seat decides the game: every second-seat loss to aCat and ziele
was evaluated below −300 from our first move on (200k-node re-search with n7e80), mostly
−800 to −1500. The rating is made by second-seat results against the whole field; the
head-to-head against aCat is even once seats are counted (the 4–9–2 was 5 first-seat
games against 10 second-seat ones).

The first player has a large edge in this game (57–68% in self-play too). v2.2's 37 losses
to those players, searched again move by move: as second player we were never ahead in 23
of 26; as first player 8 of 11 were lost from an evaluation of +1000 or more, turning only
after turn 84.

## Gauntlet (test games against the 8 players above us, first seat, 24 games)

| Bot | Score | vs top 3 |
|---|---|---|
| v2.0 net (n0c) | 56% | 1–5–3 |
| n0c + leader-threat move handling | 56% | 1–5–1 |
| n0g (64 hidden, gen 0 only) | 48% | 0–8–1 |
| n1a (v2.1) | 79% | 6–3–0 |
| n1t (relational inputs) | 81% | 6–2–1 |
| n1x (v2.2), 40 games | **85%** | 10–2–3 |
| n2a | 81% | 6–2–1 |

## Lessons so far

- **Self-play Elo is not arena strength.** v1.1 was +91 Elo over v1.0 at real time and
  scored the same in the arena; n0g was +96 over n0c and did no better against the top
  bots. Both sides of a self-play match share the same blind spots. The gauntlet against
  real opponents decides what ships.
- What the top bots punished: we reached won positions (5 units against 3 at turn 86) and
  lost them in the last 50 plies to rotation of damaged units and focused fire. A new
  generation of self-play data fixed more of that than any search change.
- Width only pays with data: 64 hidden lost to 32 at 8M positions and won at 25M.

- The handcrafted evaluation is on a plateau: no weight change moved it.
- Reverse futility (trusting the static eval to cut) loses badly: the eval is volatile
  under shots. Pruning that only skips late quiet moves works.
- Null move is worth little at 20k nodes and a lot at 100k.
