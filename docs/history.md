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
| v2.3 | generation-3 net (70M positions); reverse futility, shots in quiescence, leader-threat moves | +85 Elo at 20k nodes, +68 at 50 ms; 10–0–2 against the top 3 | 30.89 → 31.9 | 2 |
| v2.4 | generation-5 net trained on the 20k-node generations only (55M); +13% nodes/s on CodinGame (AVX2 output layer, static eval in the TT, hash move before generation, 524k-entry table) | +44 Elo at 20k nodes, +42 ± 28 at 50 ms (600 games); top 3 first seat 9–0–2 vs 7–3–2 for v2.3 side by side | 30.91 | 3 |
| v2.5 | net with a new recipe (result weight 0.4, result softened by the final margin) on 65M deep positions; history penalties + singular extensions; leader-threat scoring off | +34 ± 20 at 20k nodes (1,200 games); parts: recipe +19 ± 17, search pair +15 [+7, +23] over 7,200 games; top 3 first seat 7–1–4 vs 8–3–1 for v2.4 side by side | running | |

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

## What the arena battles say (676 games rebuilt from seed + moves)

Score against the eight players above us, by seat:

| | first seat | second seat |
|---|---|---|
| v1.0 | 41% | 19% |
| v2.0 | 66% | 30% |
| v2.1 | 69% | 38% |
| v2.2 | 67% | 33% |

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
