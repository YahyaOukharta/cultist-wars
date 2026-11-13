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

Lessons: a stronger or deeper teacher beats more of the same data; width needs data;
validation loss does not predict playing strength at this level.
