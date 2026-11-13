# Search

Negamax alpha-beta in `search()` / `qsearch()` / `think()` in [`bot.cpp`](../bot.cpp).
Every feature sits behind a `#define`; a variant is one flag away:

```sh
tools/sweep.sh BASE 300 20000 "-DNN_H=64 -DRFP=220" "-DNN_H=64 -DQDMG=2"    # each variant vs BASE
```

Elo numbers are self-play (300–400 games, ±35–40). They are a filter, not a verdict: see
"What transfers" below.

## What is in v2.3

| Feature | Flag (value) | Notes |
|---|---|---|
| Iterative deepening + PVS | – | depth 25+ in quiet openings, 10–13 in shooting fights; ~2.6M nodes/s on CodinGame |
| Transposition table | `TT_BITS` 21 | key = units + the neutral-move generator state + turn, so transpositions are rarer than in chess |
| Move ordering | – | hash move, conversions, killing shots, shots by damage, leader steps that threaten a conversion, killers, history |
| Quiescence | `QMAX` 6, `QDMG` 1 | conversions and all shots on enemy units (v2.2: killing shots only) |
| LMR | `LMR_DIV` 1.1 | `ln(depth)·ln(i)/1.1` on quiet moves |
| Futility | `FUT` 450, `FUT_D` 2 | |
| Late move pruning | `LMP` 2, `LMP_D` 3 | skip quiet move `i ≥ 2 + depth²` |
| Null move | `NMP` 2 | the null move is a real WAIT; reduction `2 + depth/4` |
| Reverse futility | `RFP` 150, `RFP_MAXD` 4 | only with the net (see below) |
| Aspiration windows | `ASP` 60 | |
| Leader-threat moves | `THREAT` 1 | a leader step next to a convertible unit is never pruned and reduced half as much |
| Time | `MS_TURN` 44, `MS_FIRST` 850, `TM_PCT` 60 | no new iteration after 60% of the budget; mean use is 34 of 44 ms |

Moves generated for the search: steps, conversions, every shot deduplicated by the unit
actually hit (enemy and neutral), a killing shot on an own cultist standing next to the
enemy leader, and WAIT.

## Measured

With the handcrafted eval (v1.x), against v1.0:

| Change | Elo |
|---|---|
| Quiescence off | −92 |
| Reverse futility 80 / 150 / 300 | −54 / −46 / −35 |
| Futility 450 + LMP 2 + LMR 1.1 + null move + aspiration (v1.1) | +129 at 100k nodes, +91 at 50 ms |
| Neighbours of those values | plateau |

With the net:

| Change | Elo |
|---|---|
| Reverse futility 150 (250 / 90) | +36 (+41 / +16): the net's static eval can be trusted to cut |
| Shots in quiescence, any damage (`QDMG=1`) / damage ≥ 3 | +17 / −16 |
| Leader-threat moves | +21 |
| The three together (v2.3 search) | +52 |
| Dropping non-killing shots at neutrals | −50 |
| Never generating WAIT when another move exists | −8 |
| Late move pruning at every depth (`LMP_D=20 LMP_LIN=1`) | +8 / −6 |
| v2.3 neighbours: RFP 100 / 220, RFP depth 7, QDMG 2, QMAX 4 / 10, FUT 300 / 650, FUT depth 3, LMP 3, NMP 3, LMR 0.9 / 1.3, ASP 35, IIR | all within ±18: plateau |

## What the tree looks like

On a shooting endgame at 120k nodes: 57% search nodes, 43% quiescence; 2.2 moves searched
per node; 87% of beta cutoffs on the first move; node counts halve per depth level. More
forward pruning does not buy depth: the depth reached is the same with every pruning
option tried. Depth is not what separates us from the bots above.

## What transfers

- v1.1 was +91 Elo over v1.0 at real time and scored the same in the arena: both sides of
  a self-play match share the blind spots of the handcrafted eval.
- Net improvements transferred every time (+144 → +2 arena points, +46 → +0.85).
- The v2.3 search changes were shipped together with a new net after a 12-game check
  against the top 3 (10 wins, 2 draws).

A candidate is therefore judged against real opponents before it ships
([workflow.md](workflow.md)).
