# Cultist Wars bot

A bot for the [CodinGame Cultist Wars arena](https://www.codingame.com/multiplayer/bot-programming/cultist-wars):
an exact simulator of the referee (including its "random" neutral moves) and an alpha-beta
search, in one C++ file. Built with the same method as the Breakthrough bot
(`~/Desktop/breakthrough`): native referee → local league → engine → search → neural eval.

Status and version table: [docs/history.md](docs/history.md).

## The game

13×7 grid with random symmetric obstacles, 14 units: one cult leader per player and 12
neutral cultists. One action per turn for the whole side: move one unit one step, shoot
with a cultist (damage 7 − distance, range 6, Bresenham line of sight), or convert an
adjacent cultist with the leader. After every action one neutral unit may step. 150 turns
in total; most units wins. 1000 ms for the first turn, 50 ms after.
[Statement](docs/statement.md), [official referee](https://bitbucket.org/Nixerrr/cultist-wars).

The neutral moves come from a fixed-seed generator, so the game is deterministic and has
perfect information: see [docs/engine.md](docs/engine.md).

## Quick start

```sh
make                                            # build/bot and build/referee
./build/referee build/bot build/bot -g 20 -n 20000 -v   # self-play, 20k nodes per move
python3 tools/league.py add v1.1                # freeze bot.cpp as a version
python3 tools/league.py match v1.1 v1.0 -g 400  # gate match
python3 tools/pack.py -o out/v1.1.cpp           # single-file submission
python3 tools/cg.py test out/v1.1.cpp boss      # test game on CodinGame, log saved
python3 tools/checklog.py arena/logs/*.log      # exactness gate on real logs
python3 tools/cg.py submit out/v1.1.cpp
```

## Layout

| Path | What |
|---|---|
| `bot.cpp` | Simulator, move generator, search, evaluation, protocol |
| `tools/referee.cpp` | Native referee (includes `bot.cpp` for the rules) and log replay check |
| `tools/league.py` | Freeze versions, play matches, Elo |
| `tools/pack.py` | Build the submission (strips `#ifdef LOCAL`, bakes `-D` overrides) |
| `tools/cg.py` | CodinGame API: test games, submit, progress, opponents |
| `tools/checklog.py` | Replays CodinGame logs through the simulator |
| `tools/arena.py` | Archive of our arena battles, score per opponent |
| `versions/` | Every submitted version |
| `docs/` | [engine](docs/engine.md), [workflow](docs/workflow.md), [history](docs/history.md) |
