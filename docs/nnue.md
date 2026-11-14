# Neural evaluation (NNUE style)

A small network evaluated at every leaf. Its first layer is a sum of weight rows, one per
active input, kept up to date incrementally as units move.

## Architecture

```
 side to move frame:  1911 sparse inputs ─┐                      ┌─ SCReLU ─┐
                                          ├─ W (1911 × 64), b ───┤          ├─ · O[bucket] + bias ─► logit
 other side's frame:  1911 sparse inputs ─┘   (same weights)     └─ SCReLU ─┘
```

- **Frame:** each player sees the board with its own leader starting on the left
  (mirrored left-right for player 1) and units labelled mine / enemy / neutral.
- **Unit inputs (1820):** `(type * 4 + hp bucket) * 91 + cell`. Types: my leader, enemy
  leader, my cultist, enemy cultist, neutral. HP buckets 1–2, 3–4, 5–6, 7–10 (a shot does
  at most 6, so 7+ cannot be killed in one).
- **Obstacle inputs (91):** `1820 + cell`. Constant during a game, so they are folded into
  the accumulator's start value once per map (`nnBase`).
- **Activation:** SCReLU, `clamp(x, 0, 1)²`.
- **Output buckets (4):** by plies left: more than 70, 31–70, 11–30, 10 or fewer.
- **Output:** logit of the side to move winning; `× NN_SCALE (800)` gives search units.

At most 14 unit inputs are active, so a move changes one or two rows of 64 int16.
`State` carries both accumulators (`acc[2][64]`) and `apply()` updates them eagerly.

## Quantization and embedding

- First layer: int8 at scale `QA = 255` (training clips the float weights to ±127/255).
  Biases, output weights (`QB = 64`) and output biases stay int16 / int32.
- `v = clamp(acc, 0, 255); sum += v * o * v; eval = (sum / 255 + bias) * 800 / (255 * 64)`.
- CodinGame counts characters, not bytes. `tools/pack.py` writes the weights as a bit
  stream, **15 bits per UTF-16 character** (code points 0x2100–0xA0FF: no controls,
  quotes, line separators or surrogates). 64 hidden: 122k int8 weights → 65k characters;
  the whole v2.3 file is 97.3k of the 100k allowed.
- The trained weights use the int8 range fully (7.5 bits of entropy, 6.5% at the clip
  limit): generic compression gains nothing.
- `pack.py --keep-local` keeps the local-only code, so an embedded net can be played at
  fixed nodes; the embedded and file-loaded nets give identical searches.
- Check after any change to the inputs: `CW_EVALCHECK=data/x.bin CW_NET=net.bin build/bot`
  prints the C++ evaluation of the first records; compare with the PyTorch model
  (correlation 0.9999, differences are quantization only).

## Training data

`CW_GEN=games:nodes:seed:file` (in `bot.cpp`, local builds): self-play on random maps,
0–8 random opening plies, then both sides search a fixed number of nodes. One 48-byte
record per searched position: obstacles, 14 units (cell, hp, owner), turn, search score,
game result and final unit margin for the side to move, flags.

| Generation | Player | Nodes per move | Positions |
|---|---|---|---|
| 0 | v1.1 (handcrafted eval) | 8k | 25.6M |
| 1 | first net (32 hidden) | 8k | 11.7M |
| 1x | 64-hidden gen-0 net | 20k | 10.1M |
| 2 | v2.1 net | 20k | 11M |
| 3 | v2.2 net | 20k | 12M |
| 4 | gen-2 net | 20k | 11M |
| 5 | v2.3 (gen-3 net, new search) | 20k | running |

About 100k positions per minute per Kaggle kernel at 8k nodes, 40k at 20k nodes.

## Training

`tools/train.py` (PyTorch). The data set lives on the GPU as raw records; inputs are built
there per batch.

```sh
python3 tools/train.py -o tools/nets/n.bin 'data/*.bin' --hidden 64 --epochs 40 --lam 0.6 --k 800
```

- Target: `0.6 · result (1 / ½ / 0) + 0.4 · sigmoid(search score / 800)`. The scale 800
  was fitted on generation 0 (it minimises the loss of the score alone as a predictor).
- Loss: binary cross-entropy on the logit. AdamW, lr 2e-3, cosine decay, batch 16384.
- Up-down mirror as augmentation (not exact for bullet lines, close enough).
- 70M positions × 40 epochs: 25 minutes on a Kaggle GPU.

## What was measured

| Change | Result |
|---|---|
| Handcrafted eval → first net (8.4M positions, 32 hidden) | +242 Elo at equal nodes, +206 at 50 ms; arena 21.6 → 26.9 |
| Result weight 0.3 instead of 0.6 | −73 |
| 64 hidden at 8.4M positions | −39 (equal at 50 ms) |
| 64 hidden at 25.6M positions | +96 over 32 hidden at 8.4M; +23 over 32 hidden at the same data |
| Generation 1 (37M positions) | +144; arena → 28.9 |
| + 10M positions searched at 20k nodes | +46; arena → 29.75 |
| Generations 2, 3, 4 (58M, 70M, 80M) | +27, +32, +15: saturating |
| 128 hidden at 58M | +24 at equal nodes, 14% slower: not worth the characters |
| Relational inputs: units under fire (best and second best enemy shot), units next to a leader that can convert them | better validation loss (0.3654 vs 0.3664), −5 / −16 Elo at equal nodes, 27% slower; gauntlet tie. Kept on branch `relational` |

| Generation 5: all 90M positions vs the 55M searched at 20k nodes only | +33 each: the 8k-node generations add nothing (v2.4 uses the 55M) |
| + 3.8M positions searched at 60k nodes | −6: too few yet |
| Result weight 0.2 / 0.3 / 0.4 / 0.6 / 0.8 | −2 / −2 / +21 / 0 / −18: flat from 0.2 to 0.6 |
| Result target softened by the final unit margin, `sigmoid(0.7 · margin)` (`--margin-w 1`) | +24 (half weight: +15) |

### A second opinion: real battles

Our own arena battles, rebuilt from seed and moves (`arena_data.py export`), give 80k
positions from 567 games against the eight players above us. How well a net ranks the
eventual winner there (AUC over decided games) follows the arena history and does not
depend on self-play:

| Net | n0c (v2.0) | n1a (v2.1) | n1x (v2.2) | n3a (v2.3) | n5d (v2.4) | n5a | n6d | n7b | n7a (v2.5) |
|---|---|---|---|---|---|---|---|---|---|
| AUC | 0.9253 | 0.9386 | 0.9412 | 0.9448 | 0.9448 | 0.9466 | 0.9477 | 0.9467 | 0.9460 |

By phase (n7a): 0.80 before turn 40, 0.96 for turns 40–99, 0.99 from turn 100. The first
forty turns are where the result is still open, and where the nets have gained least.
Since generation 5 the nets are indistinguishable on this measure too.

Lessons: a stronger or deeper teacher beats more of the same data; width needs data;
validation loss does not predict playing strength at this level.

### After v2.5: the arena as judge

| Net | Data and recipe | Self-play vs n7a (20k nodes) | Held-out battles AUC / log-loss | Arena |
|---|---|---|---|---|
| n7e80 (v2.6) | n7a's data and recipe, 80 epochs | +17 | 0.9380 / 0.385 | 29.54 (with QTT) |
| n9e80 | + generations 9–11 (74M) | −11 vs n7e80 | | |
| n10a | generations 3–12 (65.6M) | | 0.9399 / 0.383 | |
| n10x | n10a + 101k arena positions ×20, game result as target | | 0.9279 (0.965 on its own games: overfit) | |
| n11d | generations 3–12, result weight 0.6, no margin | −7 ± 14 | **0.9421 / 0.360** | 29.55 (v2.7c) |
| n11s | generations 3–12, n7a recipe | | 0.9394 / 0.384 | |
| **n12a (v2.8a)** | n7a's data and recipe + 224k positions of our 1,622 arena games, searched again at 300k nodes (`arena_data.py export --label 300000`), repeated ×10 | +4 ± 17 | (trained on them) | **31.82** |

| n13a (v2.9a) | n12a + 447k endgame positions (100k nodes, every move from turn 80 at 1M nodes) ×4 + 50k newer arena positions | +3 ± 17 vs n12a | 0.9628 / 0.376 † | 30.45 (reverted) |
| n14a | n12a + 1.77M positions played out from 20,914 real mid-game positions (`CW_STARTS`), ×2 | −18 ± 17 vs n12a | 0.9625 / 0.378 † | |
| n14b | same, play-outs ×5 | +6 ± 17 vs n12a | 0.9622 / 0.378 † | not submitted; paired test-game replays of 74 of v2.8a's arena games against the top three: −0.05 ± 0.06 per game against n12a (`tools/pairs.py`) |

AUC columns: 34k positions from 247 battles of v2.6 and v2.5's rerun, not in any training
set at the time. †: 30k positions from 224 later battles (v2.9a and v2.8a's second run),
where n7a scores 0.9635 / 0.373 and n12a 0.9630 / 0.376: no net is separated by it. The best-predicting net (n11d) did no better in the arena, so this
measure does not decide either.

n12a's recipe (Kaggle GPU, `kaggle_train.py push n12a`): generations g1x, g2, g2b, g2c,
g3–g8 plus account-2 datasets p2c–p2i (n7a's data), and dataset p2m = `arena_lab.bin`;
`--hidden 64 --epochs 40 --lam 0.4 --k 800 --margin-w 1.0 --margin-c 0.7 --rep arena_lab:10`.
The arena positions are 0.3% of the data before repetition, 3.4% after.
