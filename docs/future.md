# Roadmap

What to try next, ordered by expected gain per unit of work. Sources are at the end.
"Measured elsewhere" numbers come from other games and engines; nothing here is proven
for Cultist Wars until it passes a gate match.

## State after v2.3

Rank 3. Measured flat: net width, relational inputs, search constants, more self-play
generations at the same depth (+15 for the last one). Still open, in the order they will
be tried:

- [ ] **Second seat against the top three** (1–7–1 in the replay suite): the wall.
- [ ] **Deeper teacher**: generations searched at 60k–100k nodes per move; a net trained
  only on the 20k-node generations (dropping the 25M positions of handcrafted-eval games).
- [ ] **Time**: the search uses 34 of 44 ms on average (`TM_PCT`); real-time test running.
- [ ] **Holding won first-seat games**: 8 of 11 first-seat losses of v2.2 came from +1000
  or better and turned after turn 84 (rotation of damaged units, focused fire).
- [ ] Our arena battles (92k positions against real opponents) as a validation set and as
  weighted training data.

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
