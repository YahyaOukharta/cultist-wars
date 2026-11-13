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
| v2.1 | 64 hidden, generation 1: 25.6M positions by v1.1 + 11.7M by the first net | +144 Elo at 20k nodes; gauntlet 79% | **28.36** | **4** |

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

## Gauntlet (test games against the 8 players above us, first seat, 24 games)

| Bot | Score | vs top 3 |
|---|---|---|
| v2.0 net (n0c) | 56% | 1–5–3 |
| n0c + leader-threat move handling | 56% | 1–5–1 |
| n0g (64 hidden, gen 0 only) | 48% | 0–8–1 |
| n1a (v2.1) | **79%** | 6–3–0 |

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
