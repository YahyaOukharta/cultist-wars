# Engine

Everything is in [`bot.cpp`](../bot.cpp).

## The game is deterministic

The referee moves a "random" neutral unit after every action, but the generator is
`model.Random`: a linear congruential generator with the **hard-coded seed 42**, unrelated
to the game seed.

```java
seed = (seed * 1_103_515_245 + 12_345) & 2_147_483_647;  return seed % bound;
```

So the bot carries the generator state in its position and searches the real future.
Checked on live games: every neutral move is predicted (see the exactness gate in
[workflow.md](workflow.md)).

## Referee rules that are easy to get wrong

Read from the [official source](https://bitbucket.org/Nixerrr/cultist-wars) and confirmed
on live logs.

| Rule | Detail |
|---|---|
| Turn order | `turn` runs 0..149, player `turn % 2` acts. 75 actions each |
| End | After any turn: a player with 0 units, or turn 149. Score = number of units (leader included). Equal = draw |
| Leader death | Does not end the game; that side can no longer convert |
| Neutral move | `idx = rand(12)` into the list of **neutral-owned units in id order, dead ones included**. `idx` past the end, or a dead unit: nobody moves and no second number is drawn. Otherwise the free neighbours in the order up, right, down, left; `rand(count)` picks one (`rand(1)` is still drawn when there is none) |
| Dead body | A unit killed this turn still blocks its tile for this turn's neutral move |
| Bullet line | Bresenham from the lower-y end to the higher-y end; from the target when y is equal. A→B and B→A are different lines |
| Indirect shot | `SHOOT id` always fires along the line to that unit; the first unit on the line is hit (an obstacle absorbs the shot). Damage = 7 − distance to the unit actually hit |
| Targets | Any living unit except the shooter: enemies, neutrals, own units |
| Convert | Leader next to any cultist that is not its own, enemy cultists included. Hit points are kept |
| Far targets | A MOVE/SHOOT/CONVERT at something out of reach becomes one pathfinding step. The bot only sends adjacent moves and in-range actions, so it never depends on this; the referee port implements it for opponents |
| Unit ids | 0, 1 = leaders of player 0, 1; 2..7 neutrals on the left, 8..13 their mirrors |

## State

```cpp
struct State { U128 occ; U64 hash; uint32_t seed; int16_t turn; int8_t cnt[2];
               int8_t pos[14], hp[14], own[14]; int8_t at[91]; };
```

Copy-make (about 150 bytes). `apply()` plays one referee turn: the action, then the
neutral move. The hash is Zobrist over (unit, cell), (unit, hp), (unit, owner); the search
key adds the generator state and the turn.

## Tables built on the first turn (`initTables`)

- `nbr[cell][4]`: neighbours in referee order, obstacles removed.
- `pathCell/pathLen/pathMask/pathWall[from][to]`: the bullet line for every ordered pair
  within range, produced by a line-for-line port of the referee's Bresenham; cells ordered
  from the shooter, cut at the first obstacle. A shot is resolved with one 128-bit AND
  (`resolveHit`), and a walk over at most 5 cells when something is in the way.
- `rangeMask[cell]`, `mdist`, `bfsD` (walking distance around obstacles, for the eval).

## Move generation (`gen`)

Per own unit: steps to free neighbours; conversions for the leader; for a cultist every
living unit in range is tried as a target and the shots are deduplicated by the unit
actually hit. Three modes: search (drops shots at nothing and at own units, except a
killing shot on an own cultist next to the enemy leader), full (to recognise what the
opponent did), tactical (conversions and killing shots, for quiescence).

## Protocol

The input never tells what the opponent did or the generator state. Each turn the bot
applies every legal opponent action to its predicted state and keeps the one that
reproduces the input (`syncFrom`). As second player the hidden start position is rebuilt
from the mirror symmetry of the map (`syncSecond`). A `DESYNC` marker on stderr would
flag a failure; none has been seen.
