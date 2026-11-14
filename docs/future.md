# Roadmap

What to try next, ordered by expected gain per unit of work. Sources are at the end.
"Measured elsewhere" numbers come from other games and engines; nothing here is proven
for Cultist Wars until it passes a gate match.

## State after v2.8a (2026-11-14)

Rank 1 of 401 at 32.48, 0.4 ahead of second. Open:

- **Self-play from real positions.** `CW_STARTS`: 20,914 mid-game positions taken from our
  arena battles (turns 10–110), played out at 100k nodes per move: 1.77M positions. Nets
  n14a–n14d train on them with different weights; none has been through the arena yet.
- **Second seat** is the weak side: 43% against the top three, 72% against the rest (first
  seat 85% and 96%).
- **A cheaper predictor of arena strength.** One arena run resolves about 50 Elo; self-play,
  a pool of older versions and held-out battle accuracy all failed to predict it. Test
  games replaying many arena maps in pairs, or several arena runs per candidate, are the
  candidates.
- Tried after v2.5 and not kept: longer training of the same net (v2.6), the best net on
  held-out battles (v2.7c), more turn time (v2.7a, equal), endgame positions searched at
  1M nodes per move (v2.9a). Details in [history.md](history.md).

## Plan after v2.3: past rank 1, with margin (reached with v2.8a)

State then: rank 2 at 30.9; aCat 32.7. Target: 34+ (a full point clear of whoever is first).

### What the measurements say

| Measurement | Result | Consequence |
|---|---|---|
| Same bot, 2× nodes (20k→40k, 80k→160k) | +105, +103 Elo | Speed does not saturate. 10% more nodes ≈ +14 Elo ≈ +0.2 arena points |
| Same bot, 4× nodes | +178 Elo | |
| Our move at 100k nodes vs at 1.5M nodes (2,700 positions) | same move in 70–74% | A quarter of our moves change with more search |
| aCat's moves vs ours at 100k / 1.5M nodes | 49% / 49% | He is not us searching deeper: a different evaluation. Not something to copy |
| Net generations 2, 3, 4, 5 at 20k-node teacher | +27, +32, +15, +33 | Saturated at this teacher depth |
| Deep-only data (55M) vs all data (90M) | equal | The weak early generations add nothing |
| Net width 128, relational inputs, 16 search constants | flat | Not the lever |
| Optimised profile | search body 25%, move generation 18%, accumulator 13%, move picking 11%, eval 9%, shot resolution 7%, apply 7% | No single hot spot: many small wins |

The players above us (same university group, all resubmitting this month) say the same of
their own bots: "4× the evaluations was worth +7.65 points" (aCat), "efficiency is my
strength" (MSz). They run handcrafted evaluations fast; we run a learned one. Our edge is
the evaluation, theirs is speed. The plan is to take their edge without giving up ours.

### Steps, in order. Each ends in a gate from [pipeline.md](pipeline.md)

**Step 1. Speed sprint** (expected +40 to +70 Elo; in progress)
- [x] AVX2 output layer + static eval kept in the transposition table: +9–12% nodes/s on x86.
- [x] Hash move searched before any move is generated.
- [x] Single-pass accumulator update.
- [ ] Transposition table that fits in cache: 131k entries is +24–29% nodes/s, 262k +14–20%.
  Real-time gates decide the size (a smaller table also searches a little worse per node).
- [ ] Two-entry buckets with depth-preferred replacement, to get the small table's speed
  with the big table's memory.
- [ ] Staged generation: conversions and enemy shots first, quiet moves only if needed.
- [ ] Cheaper leader-threat scoring in the generator.
- Gate: Kaggle x86 benchmark (`kaggle_match.py bench`) for speed, then real time at 50 ms
  against v2.3. Fixed-node matches cannot see any of this.

**Step 2. Ship v2.4 = speed + generation-5 net** (expected +1 arena point)
- The deep-only generation-5 net is +33 Elo at equal nodes and independent of step 1.
- Gate: real time vs v2.3, then test games against the top three on both seats.

**Step 3. Time** (expected +5 to +10 Elo)
- 44 ms → 47 ms with a backoff after any slow turn (aCat runs 48 ms with one). Needs a
  timeout count over 100+ test games before it ships: one timeout costs more than it earns.

**Step 4. A deeper teacher** (expected +30 to +50 Elo per step, slower)
- Generation 6 is being played at 60k nodes per move. Each speed gain from step 1 also
  makes the teacher deeper at the same cost.
- Drop generations 0 and 1 from training; retrain from the deep generations only.

**Step 5. Spend the saved characters** (only after steps 1–4)
- The packer now strips comments: 93.5k of 100k. If width starts to pay with deeper data,
  there is room for about 72 hidden units.

**Step 6. Judge better**
- Second-seat replay suite for every candidate, not only the shipped one.
- A local gauntlet of frozen versions with different styles (v1.1 handcrafted, v2.0,
  v2.2) as a second opinion on self-play.
- SPRT on game pairs instead of fixed 300–400 games.

### What is deliberately not on the list

- More net capacity, more input features, more tuning of search constants: measured flat.
- Copying aCat's style: half his moves differ from ours at any depth, and we cannot see
  his evaluation.
- Anything that needs other players' game histories: the official API gives only our own
  battles, and that is the line.

The sections below are the original research notes; items already tried are in
[search.md](search.md) and [nnue.md](nnue.md).

## 1. Neural evaluation (in progress)

- [ ] First net: 1911 inputs → 32 hidden, 4 output buckets, trained on generation 0
  (v1.1 search, 8000 nodes per move). Gate against v1.1 at 50 ms.
- [ ] **Re-tune the pruning margins after every net.** Futility / LMP / aspiration are in
  eval units; a new eval changes the scale and the noise. (Sable chess: rescaling the
  output alone was worth ~60 Elo.)
- [ ] **Self-play generations**: newest net plays the next data set; train on all
  generations, not only the newest (Sable: +15 for all shards; a teacher 30 Elo stronger
  gave +23).
- [ ] **Target and filtering sweep**: result weight 0.1 / 0.4 / 0.6 / 0.75; drop positions
  whose best move is a kill or a conversion (flag bit 0 is already recorded).
- [ ] **Distillation**: train an unconstrained wide net offline, use it to relabel the
  data for the shipped net (reCurse: a big teacher beat direct training of the small net).

## 2. Fit a bigger net in 100k characters

A 32-hidden net is 61k characters at one int16 per character. Width is blocked until the
encoding changes.

- [ ] **int8 first layer + 15 bits per character**: 1.875 weights per character, so 64
  hidden fits where 32 does now. Needs quantisation-aware training (clip to the int8 range
  after each step; one-hot inputs with ≤ 15 active features cannot overflow int16 sums).
- [ ] **Entropy coding** on top (in-source range decoder, ~1–2k characters, or gzip as
  reCurse does): trained weights are peaked at zero and impossible features (units on
  obstacle-heavy cells, rare HP buckets) are exactly zero. reCurse reached ~2.4 parameters
  per character.
- [ ] **Factorised first layer**: W[type,hp,cell] = A[type,hp] + B[type,cell] (+ small
  residual), expanded at start-up. Cuts 1820 rows to ~500.
- [ ] Before width: **better inputs**. Sable found features beat width (64 vs 32 hidden
  was only +12). Candidates: line-of-sight / "can be shot next turn" bits, leader-alive
  regime in the output bucket (OldJohn's three regimes: no neutrals / one leader / other).

## 3. Search

MSz won 2022 with a simple eval and depth ~16 from heavy forward pruning; we reach depth
10–19 with nearly twice his nodes, so there is depth left to buy.

- [ ] **Relevance pruning**: drop or reduce moves of units far from every enemy, neutral
  and leader, tighter with depth. Biggest expected search gain.
- [ ] **Shot-exchange estimate** (SEE analogue): best enemy reply shot on the moved unit
  and on the target. Use for ordering, for pruning steps into fire lanes at low depth, and
  to make the stand-pat in quiescence honest. Attacks the eval volatility that made
  reverse futility lose 35–54 Elo.
- [ ] **ProbCut** instead of reverse futility: cut on a shallow *search*, not the static
  eval. Measure the shallow/deep error first.
- [ ] **Correction history**: learn search − static eval per structure key; may make
  static-eval pruning usable.
- [ ] **Continuation history** and a history table for shots; history-based LMR.
- [ ] Multi-cut, singular extensions (TT hits are rare because the RNG state is in the
  key, so expect less than in chess).
- [ ] Null-move threat detection: when the pass loses to a kill or a conversion, do not
  reduce moves of the threatened unit.
- [ ] Quiescence: add shots that set up a kill; delta pruning.
- [ ] Best-first minimax with the net (jacek's approach, 3rd in 2022): one test once the
  net is strong.

## 4. Evaluation ideas from the 2022 post-mortems

- HP matters more than it looks (TomAlard: +20% self-play after re-weighting).
- Distances between units in general, not only leader → neutral (MSz).
- Distribution of neutral distances, so the leader does not walk to a small group
  (KawattaTaido).
- Per-HP tables that depend on the side to move (OldJohn).
- Debug aid: plot the eval over a game and look for jumps (KawattaTaido).

## 5. Testing

- [ ] **SPRT** on game pairs (same map, seats swapped) instead of fixed 300 games.
- [ ] **SPSA** for the search constants once the net is in.
- [ ] **Gauntlet**: keep 3–4 frozen opponents of different styles (v1.0, v1.1, first net)
  and re-test accepted batches; self-play against the direct ancestor inflates gains.
- [ ] Check whether CodinGame counts an astral character as one or two (decides the
  packing ceiling).

## Sources

- Forum thread and post-mortems: https://forum.codingame.com/t/community-puzzle-cultist-wars/98099
- reCurse, weights at 15 bits per character + gzip: https://gist.github.com/reCurs3/7d4eb5b952790e3009337f61c3341074 ,
  distillation: https://gist.github.com/reCurs3/40793036b9800472eb219136a33f6997
- Sable chess net (int8 NNUE, data ablations): https://huggingface.co/shubhxho/sable-chess-net
- bullet trainer: https://github.com/jw1912/bullet
- Position filtering: https://arxiv.org/html/2412.17948v1
- ProbCut, multi-cut, singular extensions, SEE, history, SPRT, SPSA: https://www.chessprogramming.org
- Best-first minimax: https://arxiv.org/html/2505.04525v1 , https://ar5iv.labs.arxiv.org/html/2012.10700
- Fishtest FAQ: https://github.com/official-stockfish/fishtest/wiki/Fishtest-faq
