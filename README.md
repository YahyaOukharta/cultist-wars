# Cultist Wars bot

A bot for the [CodinGame Cultist Wars arena](https://www.codingame.com/multiplayer/bot-programming/cultist-wars):
an exact simulator of the referee (including its "random" neutral moves), an alpha-beta
search and a small NNUE-style neural evaluation trained from self-play, in one C++ file
under the 100k-character limit.

**Result so far:** rank **2 / 401** on 2026-11-14 (`yhyoxx`, v2.3), from rank 181 the same
morning.

| Stage | Arena score | Rank |
|---|---|---|
| 2022 submission | 22.6 (Bronze) | 181 |
| Exact simulator + alpha-beta, handcrafted eval (v1.0) | 21.6 (Legend) | 9 |
| First net, 32 hidden (v2.0) | 26.9 | 5 |
| 64 hidden, generation 1 (v2.1) | 28.9 | 4 |
| + deep-search data (v2.2) | 29.75 | 4 |
| Generation 3 + search changes (v2.3) | 30.89 | 2 |
 Built with the same method as the Breakthrough bot
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
python3 tools/pack.py -n tools/nets/n3a.bin -H 64 -o out/v2.3.cpp   # single-file submission with the net
python3 tools/cg.py test out/v2.3.cpp           # test game on CodinGame, log saved
python3 tools/checklog.py arena/logs/*.log      # exactness gate on real logs
python3 tools/cg.py submit out/v2.3.cpp         # also mirrors the code into the IDE
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
| `tools/gauntlet.py` | Candidates against real arena bots, both seats |
| `tools/mapgen.py`, `tools/arena_data.py` | Rebuild our arena battles from seed + moves: training records, loss analysis |
| `tools/train.py` | PyTorch trainer, exports the quantized net |
| `tools/kaggle_gen.py`, `kaggle_train.py`, `kaggle_match.py` | Data generation, training and gate matches on Kaggle |
| `tools/nets/` | Trained nets |
| `versions/` | Every submitted version |
| `docs/` | [engine](docs/engine.md), [search](docs/search.md), [nnue](docs/nnue.md), [workflow](docs/workflow.md), [history](docs/history.md), [roadmap](docs/future.md) |
