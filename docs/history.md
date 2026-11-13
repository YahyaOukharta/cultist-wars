# History

"Local" is the gate match against the previous version (self-play; inflated relative to
the arena).

## Versions

| Version | Change | Local | Arena | Rank |
|---|---|---|---|---|
| old | 2022 submission | | 22.59 (Bronze) | 181 |
| v1.0 | exact simulator (neutral moves predicted), ID alpha-beta: PVS, TT, LMR, quiescence, handcrafted eval | | Bronze → Silver → Gold in one run | |
| v1.1 | futility, late move pruning, null move (a real WAIT), aspiration, stronger LMR | +129 Elo at 100k nodes | | |

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

## Lessons so far

- The handcrafted evaluation is on a plateau: no weight change moved it.
- Reverse futility (trusting the static eval to cut) loses badly: the eval is volatile
  under shots. Pruning that only skips late quiet moves works.
- Null move is worth little at 20k nodes and a lot at 100k.
