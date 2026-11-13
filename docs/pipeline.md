# The release pipeline

How an idea becomes a submitted version. This process, more than any single technique, is
what moved the bot from rank 181 to rank 2 in a day: five versions shipped, every one of
them better in the arena than the one before, and about as many candidates stopped before
they could cost an arena run.

Read this before changing anything. [workflow.md](workflow.md) is the tool reference;
this file is the procedure and the reasons behind it.

- [1. Principles](#1-principles)
- [2. The pipeline at a glance](#2-the-pipeline-at-a-glance)
- [3. Stage by stage](#3-stage-by-stage)
- [4. Decision rules](#4-decision-rules)
- [5. Locking a version](#5-locking-a-version)
- [6. Machines, quotas and timings](#6-machines-quotas-and-timings)
- [7. Bookkeeping](#7-bookkeeping)
- [8. What each gate has caught](#8-what-each-gate-has-caught)
- [9. Checklists](#9-checklists)
- [10. Known weaknesses of the pipeline](#10-known-weaknesses-of-the-pipeline)

## 1. Principles

1. **One change, one measurement.** Every search feature is a `#define`, every net is a
   file, every data set is a tag. A candidate differs from the live version in a way that
   can be named in one line.
2. **Cheap filters first, expensive truth last.** A candidate passes through tests in
   order of cost: seconds (compile, exactness), minutes (fixed-node self-play), tens of
   minutes (real time, real opponents), an hour (the arena). Each stage exists to stop bad
   candidates before the next, more expensive one.
3. **Self-play is a filter, not a verdict.** Two bots that share an evaluation share its
   blind spots. Self-play has approved changes that the arena ignored (section 8). Only
   games against the real players above us decide.
4. **The live version is the baseline for everything.** Candidates are compared with the
   bot that is in the arena now, built from the same code path, not with an older
   reference.
5. **Fixed match lengths, written down before the match.** No stopping a match early
   because it looks good. 300 games give about ±40 Elo; anything inside that is "no
   evidence".
6. **Nothing ships on one kind of evidence.** A submit needs agreement between self-play
   at fixed nodes, self-play at real time, and games against real opponents.
7. **Keep the cycle short.** One generation of data, one net, one verdict in about 75
   minutes. A slow pipeline tests fewer ideas, and most ideas fail.
8. **Record the negative results.** Half of what was tried did nothing. Writing that down
   ([search.md](search.md), [nnue.md](nnue.md), [history.md](history.md)) is what keeps
   the same idea from being tried twice.

## 2. The pipeline at a glance

```
                      ┌──────────────────────────────────────────────────────────────┐
                      │                the newest net plays the next generation       │
                      ▼                                                              │
 ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───┴───────┐
 │ 0 idea    │──►│ 1 build   │──►│ 2 exact   │──►│ 3 data    │──►│ 4 train   │──►│ 5 pack    │
 │ one line  │   │ flag/net  │   │ simulator │   │ self-play │   │ GPU       │   │ + verify  │
 └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───┬───────┘
                                                                                      │
 ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐        │
 │ 10 record │◄──│ 9 arena   │◄──│ 8 submit  │◄──│ 7 real    │◄──│ 6 gates   │◄───────┘
 │ + lock    │   │ ~45 min   │   │ + mirror  │   │ opponents │   │ nodes, ms │
 └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘
```

A search-only change skips stages 3 to 5. A net-only change skips nothing.

| Stage | Question it answers | Cost | Typical kill rate |
|---|---|---|---|
| 2 exactness | Is the simulator still the referee? | seconds | rare, fatal when it happens |
| 6a fixed nodes | Is it better at equal work? | 3 min | about half of all ideas die here |
| 6b real time | Is it still better when speed counts? | 20–35 min | slow features die here |
| 7 real opponents | Is it better against players who are not us? | 15–35 min | self-play illusions die here |
| 9 arena | The truth | 45 min | should be none by now |

## 3. Stage by stage

### Stage 0 — the idea, stated as a hypothesis

Write one line: what changes, why it should help, and what result would kill it. Examples
from the log:

- "Reverse futility with the net: the net's static eval is steadier than the handcrafted
  one, so cutting on it should gain. Dead if below +10 Elo at fixed nodes."
- "A net trained on 20k-node games: a deeper teacher labels tactics the 8k teacher
  missed. Dead if it does not beat the live net in the gauntlet."

Sources of ideas, in the order they have paid: reading our own losses move by move,
measuring where time and nodes go, post-mortems of other players, engine literature.

### Stage 1 — build the candidate

**Search change.** Add it behind a flag with the old behaviour as default:

```cpp
#ifndef RFP          // reverse futility margin per depth (0 = off)
#define RFP 0
#endif
```

**Net change.** A net is a file `tools/nets/NAME.bin` plus the flags it needs
(`-DNN_H=64`). Nets are named by generation and variant: `n3a` = generation 3, first
variant.

**Rule:** the default build of `bot.cpp` must always reproduce the live version. After
adding a flag, check it:

```sh
sh end.sh | CW_NET=tools/nets/LIVE.bin CW_NODES=300000 ./build/new  | grep '^d'
sh end.sh | CW_NODES=300000 ./build/live                             | grep '^d'
# same depth, score and node count, e.g. "d12 s2265 n300000"
```

(`end.sh` prints a fixed position in the game's input format.) A fixed node count makes
the search deterministic, so identical output means identical behaviour.

### Stage 2 — exactness gate

Run whenever `apply()`, move generation, the bullet tables or the protocol code changed.

```sh
python3 tools/cg.py test out/candidate.cpp me        # self-play on CodinGame, both seats' stderr
python3 tools/checklog.py arena/logs/test-*.log      # replay every action, compare every state
python3 tools/mapgen.py --verify arena/logs/test-*.log
```

- The bot prints the raw unit list of every turn (`#S`) and the generator state it deduced
  (`#R`). The checker replays all actions of both players through the referee port; every
  later unit list must match.
- **Pass:** `OK n states matched` on every log, no `DESYNC` marker anywhere.
- **Fail:** stop. Nothing downstream means anything with a wrong simulator, and every
  training record made with it is wrong too.

For changes to the net inputs there is a second exactness check: the C++ evaluation must
match PyTorch on stored positions.

```sh
CW_NET=net.bin CW_EVALCHECK=data/x.bin ./build/nn64 > cpp.txt     # C++ evals of the first records
# compare with the PyTorch model on the same records: correlation 0.9999, max difference ~40 units
```

### Stage 3 — data (net changes only)

```sh
python3 tools/kaggle_gen.py upload tools/nets/n3a.bin                        # engine + net -> private dataset
python3 tools/kaggle_gen.py push g5 5 2000 15000 20000 n3a.bin "-DNN_H=64"   # account 1: 5 kernels
CW_KP=2 python3 tools/kaggle_gen.py push g5 5 2000 16000 20000 n3a.bin "-DNN_H=64"   # account 2
python3 tools/kaggle_gen.py fetch g5 5 g5 ; CW_KP=2 python3 tools/kaggle_gen.py fetch g5 5 g5
```

- Arguments: tag, kernels, games per process (4 processes per kernel), first seed, nodes
  per move, net, compile flags.
- **Seeds must not overlap.** Each kernel uses `seed + 10·i` and its four processes add
  0..3. Every generation gets a fresh seed block (see the table in section 7).
- The player is the best net available, with the live search. Nodes per move: 20k since
  generation 1x. Deeper teachers have paid more than more games (section 8).
- After `upload`, wait until the dataset is `ready` before pushing kernels, or they mount
  the previous version and die for lack of the net.
- Merge: a training kernel can read the outputs of its own account's kernels only. The
  other account's files are uploaded as a private dataset `cw-data-p2X` (one letter per
  generation).
- Sanity check on fetch: file count = kernels × 4, sizes within a few percent of each
  other, `positions … per minute` in the kernel log.

### Stage 4 — training

```sh
python3 tools/kaggle_train.py push n5a --gen g0:5 --gen g1x:5 ... --ds cw-data-p2 ... \
    -- '/kaggle/input/**/*.bin' --hidden 64 --epochs 40 --lam 0.6 --k 800
python3 tools/kaggle_train.py fetch n5a          # -> tools/nets/n5a.bin (+ .pt checkpoint, not tracked)
```

- The recipe is fixed (hidden 64, 40 epochs, result weight 0.6, score scale 800) unless
  the experiment is about the recipe. Change one thing at a time.
- Read the log: positions loaded (must equal the sum of the generations), the result
  split (about 40% wins, 21% draws for the side to move), validation loss per epoch,
  `max |W| 127` (the int8 clip is active, as intended).
- **Validation loss is not a gate.** Nets with lower loss have played worse (relational
  inputs, 128 hidden). It only tells whether training ran.

### Stage 5 — pack and verify the artifact

```sh
python3 tools/pack.py -n tools/nets/n5a.bin -H 64 -o out/n5a.cpp                  # the submission
python3 tools/pack.py -n tools/nets/n5a.bin -H 64 --keep-local -o out/n5a_l.cpp   # same, with local knobs
c++ -O3 -std=c++17 -march=native -DLOCAL -o build/n5a out/n5a_l.cpp
```

- **Size:** the packer prints the character count and flags anything over 100,000. v2.3 is
  97,325; there are about 2,600 characters of headroom for code.
- **Clipping:** a warning `n first-layer weights outside int8` means the net was trained
  without the clip and the packed net differs from the file. Retrain; do not ship.
- **Embedded = file:** the packed build and a build that loads the same net with `CW_NET`
  must give the same line at equal nodes (as in stage 1).
- `--keep-local` exists so the *embedded* net can be gated at fixed nodes. Gate that
  build, not a different one.
- Search flags baked in with `-D NAME=VALUE` must be listed in the tag of everything
  measured with them.

### Stage 6 — self-play gates

Opponent: the live version, packed the same way (`build/LIVE` from
`out/LIVE_l.cpp`).

**6a. Fixed nodes** (deterministic, eight games in parallel, three minutes):

```sh
python3 tools/league.py match build/n5a build/live -g 400 -n 20000
# build/n5a vs build/live: +183 -146 =71 (54.6%)  elo +32 +/- 34  first-seat wins 59%
```

- Every map is played twice with the seats swapped. Draws count half.
- Read: Elo and its error, faults (must be 0/0), first-seat share (around 60% is normal).
- For many variants at once: `tools/sweep.sh BASE GAMES NODES "flags1" "flags2" …`.
- **Pass:** lower bound of the interval above zero, or a point estimate of +30 or more
  for a change of a kind that has transferred before (a new net generation).
- **Stop:** inside ±20 with an interval straddling zero. Record it and move on. Do not
  rerun hoping for a better sample.
- A sweep that shows every neighbour of the current value within noise means the value is
  on a plateau: stop tuning that parameter.

**6b. Real time** (only this shows the cost of a slower net or feature):

```sh
python3 tools/kaggle_match.py push gate --games 300 --ms 50 out/n5a_l.cpp out/live_l.cpp
python3 tools/kaggle_match.py fetch gate
# … elo +68 +/- 57  faults 0/0  [50 ms/move, max 854/853]
```

- Run on Kaggle (x86, like CodinGame), two games at a time on four cores so each bot has a
  core. The laptop is only acceptable when idle; with a load average above 8 it produces
  time faults that say nothing about the bot.
- The referee gives each bot the same margins as the submission (44 ms of 50, 850 ms of
  1000). A harness that disagrees with the bot about time produces fake faults.
- **Pass:** not worse than the fixed-node result by more than the noise, and `faults 0/0`.
- Skip 6b only for a net of the same size with the same search.

**Soundness check for pruning changes** (optional, cheap): the candidate at 20k nodes
against a deliberately unpruned build at 60k. A pruning that only wins against itself
loses here.

### Stage 7 — real opponents

```sh
python3 tools/gauntlet.py run TAG out/n5a.cpp -g 3            # first seat vs the 8 players above us
python3 tools/gauntlet.py replay TAG_seat2 out/n5a.cpp -g 3   # second seat: replays of our arena battles
python3 tools/gauntlet.py show
```

- These are CodinGame test games through the official API, played at real speed on
  CodinGame's machines against the bots that are in the arena now.
- In a test game our bot always moves first, so the first-seat gauntlet says nothing about
  the second seat. The replay suite covers that: it replays our own lost-seat arena
  battles on their exact maps with the same opponents.
- Compare with the **live version's numbers on the same suite**, kept in
  `arena/gauntlet.jsonl`. Reference: v2.2 85% first seat (40 games), v2.3 52% second seat
  (21 games), 1–7–1 against the top three there.
- Look at the top three separately. A candidate that beats ranks 4 to 8 harder and loses
  more to ranks 1 to 3 is not an improvement where it counts.
- Check the `BAD` column: a timeout or a desync of ours is a blocker regardless of score.
- **Budget.** Test games are limited by sliding windows (section 6). Twelve games against
  the top three are the minimum check; 24 per seat is the normal one; 40 when two
  candidates are close.
- **Pass:** at least as good as the live version overall and against the top three, on
  the seats tested. With only twelve games available, "no losses to the top three and no
  faults" has been accepted together with strong stage 6 results.

### Stage 8 — submit

```sh
python3 tools/cg.py submit out/n5a.cpp     # submits, then mirrors the code into the CodinGame IDE
```

- One submit at a time. A submit resets the arena score and replays about 350 games; a
  second submit during the run discards the first one's information.
- The mirror step runs one extra test game with `overwrite_ide_code`. If it fails because
  another test game is running, repeat it; the submission itself is already in.
- Do not submit while a previous version's run is unfinished unless the decision is to
  abandon that measurement (done once, on purpose, for v1.1).

### Stage 9 — the arena run

```sh
python3 tools/cg.py progress        # percentage, score, rank
python3 tools/cg.py top 8
python3 tools/arena.py fetch && python3 tools/arena.py stats
```

- The score starts low and climbs for the whole run. Do not judge before 100%: v2.3 was
  at 28.6 at 65% and finished at 30.89.
- Two runs of the same code differ by a few tenths. A difference under 0.4 between
  versions is not a result.
- While it runs, the machines are free: start the next generation.
- On completion: per-opponent record, then
  `python3 tools/arena_data.py fetch` and the per-seat table (section 7).
- If the final score is clearly below the previous version (more than 0.5), resubmit the
  locked previous version (`out/` file of the last tag) and treat the candidate as failed
  at stage 7 in the notes. This has not been needed yet.

### Stage 10 — record and lock

See section 5. Then the loop continues from stage 3 with the new net as the player.

## 4. Decision rules

| Situation | Decision |
|---|---|
| Fixed-node result inside ±20 Elo, interval straddles zero | Dead. Record it. No rerun |
| Clear gain at fixed nodes, loss or faults at real time | Dead as built. The feature is too slow |
| Gain in self-play, no gain against real opponents | Do not ship. Self-play illusion |
| Gain in self-play and against real opponents | Ship |
| Two candidates tie in the gauntlet | Keep the live one; prefer the simpler or faster |
| Several small positives (+10 to +20 each) | Combine them and gate the combination once |
| All neighbours of a parameter within noise | Plateau. Stop tuning it |
| A new net generation gains less than +20 | The generation scheme is saturated: change the teacher (depth, search) or the data mix, not the count |
| Test-game budget nearly spent | Spend what is free on the top three; never wait for a reset |
| Laptop busy | Real-time gates go to Kaggle only |

What has transferred to the arena so far, and what has not:

| Kind of change | Self-play said | Arena said |
|---|---|---|
| Search pruning on the handcrafted eval (v1.1) | +91 Elo | 0 |
| First net (v2.0) | +206 | +5.3 points |
| Next generation, wider net (v2.1) | +144 | +2.0 |
| Deeper-teacher data (v2.2) | +46 | +0.85 |
| New generation + search changes on the net (v2.3) | +85 | +1.14 |

Rule of thumb from these: with the net, about 70 self-play Elo is one arena point, and
changes to the evaluation's training transfer more reliably than changes to pruning.

## 5. Locking a version

A version is locked when its submission is in. From then on it never changes.

1. `versions/vX.Y.cpp`: the submitted source with the weight literal replaced by a
   placeholder naming the net file (`tools/nets/n3a.bin`). The repository stays small and
   the source stays readable.
2. `tools/nets/NAME.bin`: the net, tracked in git. The `.pt` float checkpoint stays local.
3. The search flags baked into the submission become the defaults in `bot.cpp`, so a
   plain build is the live version again (stage 1 rule).
4. `out/NAME.cpp` and `out/NAME_l.cpp`: kept locally as the exact submitted file and its
   gate build. This is the rollback artifact.
5. One commit: `vX.Y: what changed`. No commit ever mentions tooling or authorship beyond
   the author.
6. `docs/history.md`: one row in the version table (change, self-play result, arena score
   and rank once final), plus rows in the net and gauntlet tables.
7. The live version's gauntlet numbers on both seats are recorded as the new baseline.

Naming: `v1.x` handcrafted eval, `v2.x` neural eval. Nets `n<generation><variant>`.
Generations `g<number><batch>`. Gauntlet tags are the net or candidate name, with
`_seat2` for the replay suite.

## 6. Machines, quotas and timings

| Machine | Capacity | Used for |
|---|---|---|
| Kaggle account 1 | 5 sessions at once (CPU and GPU together), at most 2 on GPU | generation, all trainings (the merged data lives here), gates |
| Kaggle account 2 (`CW_KP=2`) | 5 sessions | generation, gates |
| Laptop, 8 cores | | fixed-node gates and sweeps, packing, analysis, orchestration |
| CodinGame | test games and submits | stage 7 to 9 |

Kaggle notes:
- A kernel has 4 vCPUs: four generator processes, or two real-time games at once.
- Generation speed: about 100k positions per minute per kernel at 8k nodes, 40k at 20k
  nodes, 13k at 60k nodes.
- Training: 70M positions × 40 epochs in 25 minutes; 90M in about 35.
- A GPU job counts against the 5-session limit. An account full of CPU kernels refuses it
  with "Maximum batch CPU session count".
- Kernels sometimes sit `QUEUED` for a long time; status `RUNNING` does not mean progress.
  Check the fetch, not the status.

CodinGame limits (all sliding windows: capacity returns game by game as old games age out;
`resets_in_seconds` is only the next expiry):

| Limit | Value |
|---|---|
| Test games | 10 / minute, 20 / 5 min, 30 / 15 min, 80 / hour, 150 / 3 hours, 200 / 6 hours, 600 / day |
| Submits | 5 / 5 min, 20 / 30 min, 40 / hour, 100 / 5 hours |
| API requests | 120 / minute |
| One test game at a time | a second request answers 409 until the first ends |

`GET /limits?puzzle=cultist-wars` lists every window. Plan gauntlets against the
6-hour window: it is the one that runs out.

Typical cycle, with everything in parallel:

| Step | Minutes |
|---|---|
| Generation, 10 kernels at 20k nodes (11M positions) | 50 |
| Fetch, merge, upload | 5 |
| Training | 25–35 |
| Pack, fixed-node gate | 5 |
| Real-time gate (Kaggle) | 20–35 |
| Gauntlet, 24 games | 15 |
| Arena run | 45 |

The arena run of version N overlaps the generation for version N+1, so a full turn of the
loop is about 75 minutes.

## 7. Bookkeeping

**Generations and seed blocks** (never reuse a block):

| Tag | Player | Nodes | Seeds (account 1 / 2) | Positions |
|---|---|---|---|---|
| g0, g0b | v1.1 | 8k | 1000, 3000 / 2000, 4000 | 25.6M |
| g1, g1b, g1c, g1d | n0c | 8k | 5500, 5600 / 5000, 5100, 5700 | 11.7M |
| g1x | n0g | 20k | 6000 / 7000 | 10.1M |
| g2, g2b, g2c | n1a | 20k | 8000–8200 / 9000–9200 | 11M |
| g3 (+ local) | n1x | 20k | 10000 / 11000, 12000 local | 12M |
| g4 | n2a | 20k | 13000 / 14000 | 11M |
| g5 | n3a, v2.3 search | 20k | 15000 / 16000 | 11M |
| g6, g6b | n3a, v2.3 search | 60k | 17000 / 18000, 18500, 19000 local | running |

**Data sets on Kaggle account 1:** kernel outputs `cw-g*-N`, plus account 2's share as
`cw-data-p2` (g0, g0b), `p2b` (g1), `p2c` (g1x), `p2d` (g2), `p2e` (g3 + local), `p2f`
(g4), `p2g` (g5). Account 2 holds a full copy of account 1's early data as `cw-data-p1`.

**Local files** (not tracked): `data/` records, `arena/battles.jsonl` and
`arena/battle_logs/` every arena battle, `arena/logs/` every test game,
`arena/gauntlet.jsonl` every gauntlet game with its tag, `league/results.jsonl` matches
between frozen versions, `kaggle/` kernel folders and outputs.

**After each arena run:**

```sh
python3 tools/arena.py fetch && python3 tools/arena_data.py fetch
python3 tools/arena_data.py export data/arena_all.bin              # all battles as records
python3 tools/arena_data.py games /tmp/losses.txt --top --only loss --sub SUBMISSION_ID
CW_NET=tools/nets/LIVE.bin CW_NODES=150000 ./build/referee64 --analyze /tmp/losses.txt > /tmp/an.txt
```

The analysis prints, for every position we had in the lost games, the search score, the
unit counts, the move we played and the move the analyser prefers. Sorting games by peak
score and by the turn the score went negative is how the two failure modes were found
(thrown first-seat wins; second-seat games never in reach).

## 8. What each gate has caught

| Gate | Caught | What it saved |
|---|---|---|
| Exactness | The first probe game confirmed the fixed seed; the port of the map generator was checked on 167 boards before any analysis used it | Building on a wrong simulator |
| Embedded = file | The 15-bit packing was verified to give identical searches before the first packed net was submitted | A silently corrupted net |
| Packer clip warning | The first nets were trained without the int8 clip: 4,659 weights would have been cut | Shipping a net different from the one gated |
| Fixed nodes | Eval weight tweaks, IIR, deeper futility, WAIT pruning, late move pruning at all depths, 16 constant variations: all noise. Dropping neutral shots: −50 | About 30 dead ideas, three minutes each |
| Real time | 128 hidden: 14% slower for +24. Relational inputs: 27% slower for nothing. Using 95% of the turn: +5 | Three arena runs |
| Harness check | A real-time gate once reported 288 time faults: the harness gave 500 ms for the first turn, the bot planned for 850 | A false "the net times out" conclusion |
| Real opponents | The 64-hidden generation-0 net: +96 in self-play, 48% against the top eight where the live net had 56%. The generation-2 net and the relational net: ties | Three submits that would have gained nothing |
| Arena | v1.1: the one change shipped on self-play alone, for no gain | The lesson behind stage 7 |

## 9. Checklists

**Before any match**
- [ ] Both binaries built from the intended sources and flags (print them in the tag).
- [ ] Same net for both sides unless the net is the experiment.
- [ ] Games and nodes decided in advance.

**Before a submit**
- [ ] Exactness gate green if the simulator or protocol changed.
- [ ] Character count under 100,000; no clip warning.
- [ ] Embedded net gives the same search as the file at equal nodes.
- [ ] Fixed-node gate against the live version: positive.
- [ ] Real-time gate (or a same-size, same-search exemption): positive, `faults 0/0`.
- [ ] Real opponents: not worse than live, top three checked, no `BAD` games.
- [ ] No arena run in progress whose result is still wanted.
- [ ] Maximum turn time in the test logs below 46 ms.

**After a submit**
- [ ] IDE mirrored.
- [ ] `versions/`, net, defaults, commit (section 5).
- [ ] Next generation started with the new net.
- [ ] At 100%: score and rank in `history.md`, battles fetched, per-seat table, loss
      analysis.

**When something looks wrong**
- [ ] A burst of timeouts: check machine load and the harness's time margins before the
      bot.
- [ ] A result too good to be true: check both sides loaded the nets they should
      (`CW_NET` applies to every local binary that reads it).
- [ ] A Kaggle kernel `COMPLETE` in two minutes: it probably died for lack of the net;
      read its log.

## 10. Known weaknesses of the pipeline

- **Test games are the bottleneck.** 200 per six hours limits how finely two good
  candidates can be told apart. The second-seat suite has only been run for v2.3.
- **Gauntlet samples are small.** 24 games give about ±20 percentage points. The gauntlet
  rejects bad candidates reliably; it cannot rank two good ones.
- **The opponents move.** Three of the players above us resubmitted during the same days.
  A baseline measured against yesterday's opponents drifts.
- **One arena run is one sample** (about ±0.4). Rank changes between neighbours are partly
  noise.
- **Self-play Elo against the direct ancestor inflates.** A gauntlet of frozen older
  versions with different styles would give a second local opinion; it is not built yet.
- **Fixed lengths waste games.** A sequential test (SPRT) would stop clear cases sooner.
