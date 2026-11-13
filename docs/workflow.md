# Workflow

Rule: nothing is submitted unless it beats the current version in a gate match.

## Tools

| Tool | Use |
|---|---|
| `build/referee A B -g 300 -n 20000 -j 8` | Match between two binaries on random maps, each map played with both seats. `-n` nodes per move, or `-t` ms per move. JSON summary; `-v` one line per game |
| `build/referee --check FILE` | Replay of a recorded game (used by `checklog.py`) |
| `tools/league.py add / match / run / show` | Frozen versions, head-to-head with Elo ± error, rating table |
| `tools/pack.py -D NAME=VALUE` | Submission file, optionally a parameter variant |
| `tools/cg.py test / submit / progress / opponents / top` | CodinGame API |
| `tools/checklog.py LOG...` | Exactness gate |
| `tools/arena.py fetch / stats / losses` | Our arena battles per opponent |

## Exactness gate

The bot prints the raw unit list of every turn and its generator state to stderr.
`checklog.py` replays all actions of both players through the referee port and requires
every later unit list to match. Run it on fresh test games after any change to the
simulator. First run: 4 games (boss and self-play, both seats), 419 states, 560 actions,
all exact.

## Testing method

1. **Fixed nodes** (`-n 20000`): deterministic, immune to machine load, 8 games in parallel.
2. **Real time** (`-n 0 -t 50`) before shipping and whenever speed changes; idle machine.
3. Fixed match length (300+ games), no early stopping. About ±40 Elo at 300 games.
   About 20% of self-play games are draws.
4. Ship, then read the arena.

Reference points at 20k nodes, 300 games: quiescence off −92 Elo, LMR off −18 (noise),
4× nodes +105.

## CodinGame specifics

- 50 ms per turn, 1000 ms for the first. The bot uses 44 ms / 850 ms.
- About 4.3M nodes/s there; depth 10–19 in 44 ms.
- No compiler flags: optimisation pragmas at the top of the file (x86 only).
- Test games: 10 per minute, 600 per day. Submits: 5 per 5 minutes.
