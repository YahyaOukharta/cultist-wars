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

## Judging a candidate

Self-play Elo is a filter. Before shipping, a candidate plays real arena bots through
CodinGame test games:

| Tool | What |
|---|---|
| `tools/gauntlet.py run TAG SRC -g 3` | first seat against the eight players above us (ids looked up each round) |
| `tools/gauntlet.py replay TAG SRC -g 3` | second seat: replays of our own arena battles (same map, opponent and seats), a fixed suite |
| `tools/gauntlet.py show` | results per tag and per opponent |

Test-game limits are sliding windows (10 per minute, 30 per 15 minutes, 80 per hour, 150
per 3 hours, 200 per 6 hours, 600 per day): capacity comes back game by game, there is no
reset to wait for. Twelve games against the top three are enough to catch a bad candidate.

The first player has a large edge (first seat about 67% against the top eight, second
seat about 33%), so both seats matter.

## Our arena battles as data

| Tool | What |
|---|---|
| `tools/arena.py fetch / stats / losses` | battles of every submission, score per opponent |
| `tools/arena_data.py fetch` | text log of every battle |
| `tools/mapgen.py SEED` | the referee's map generator (Java `SplittableRandom`): the board from the game seed. Checked on 167 logged games |
| `tools/arena_data.py export OUT.bin [--top]` | every position of those battles as training records (result as label) |
| `tools/arena_data.py games OUT.txt --top --only loss` + `CW_NET=net.bin build/referee --analyze OUT.txt` | our search re-run on every position we had in lost games: where the evaluation turned |

A battle log holds only the seed and both players' outputs; the game is deterministic, so
that is enough to rebuild it.

## Cloud (Kaggle)

Two accounts: `~/.kaggle/user` + `access_token`, and `user_2` + `access_token_2`
(`CW_KP=2`). Each runs 5 sessions at a time (CPU and GPU together), up to 2 on GPU.

```sh
python3 tools/kaggle_gen.py upload tools/nets/n3a.bin                    # engine + net as a private dataset
python3 tools/kaggle_gen.py push g5 5 2000 15000 20000 n3a.bin "-DNN_H=64"   # 5 kernels, 4 processes x 2000 games, 20k nodes
python3 tools/kaggle_gen.py fetch g5 5 g5                                # -> data/g5_*.bin
python3 tools/kaggle_train.py push n5a --gen g5:5 --ds cw-data-p2 -- '/kaggle/input/**/*.bin' --hidden 64 --epochs 40
python3 tools/kaggle_train.py fetch n5a                                  # -> tools/nets/n5a.bin
python3 tools/kaggle_match.py push gate --games 300 --ms 50 out/a_l.cpp league/src/v1.1.cpp
```

A training kernel reads the outputs of generation kernels of its own account; the other
account's data is uploaded as a private dataset (`cw-data-p2*`).
One improvement cycle (generate, merge, train, gate, check against the top three) takes
about 75 minutes.

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
- About 4.3M nodes/s there with the handcrafted eval, 2.6M with the 64-hidden net.
- 100k characters per source file: v2.3 is 97.3k, 65k of them weights.
- No compiler flags: optimisation pragmas at the top of the file (x86 only).
- Test games: 10 per minute, 600 per day. Submits: 5 per 5 minutes.
