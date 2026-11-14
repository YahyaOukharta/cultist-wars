#!/usr/bin/env python3
"""netscore.py DATA.bin NET.pt [NET.pt ...]: AUC of each net's static eval for the eventual winner (decided games),
overall and by phase, plus log-loss against the result."""
import sys
import numpy as np
import torch
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import train as T


def auc(score, y):
    o = np.argsort(score)
    r = np.empty(len(score)); r[o] = np.arange(1, len(score) + 1)
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    return (r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


data = np.fromfile(sys.argv[1], dtype=T.REC)
dev = torch.device("cpu")
U = torch.from_numpy(data["unit"].astype(np.int16))
WL = torch.from_numpy(np.ascontiguousarray(data["walls"]))
TT = torch.from_numpy(data["turn"].astype(np.uint8))
feats = T.make_feats(dev, U, WL, TT)
res = data["result"]
turn = data["turn"]
dec = res != 0
y = (res > 0).astype(int)
print(f"{len(data)} positions, {dec.sum()} decided")
for path in sys.argv[2:]:
    sd = torch.load(path, map_location=dev)
    h = sd["emb.weight"].shape[1]
    m = T.Net(h); m.load_state_dict(sd); m.eval()
    z = []
    with torch.no_grad():
        for i in range(0, len(data), 65536):
            idx = torch.arange(i, min(i + 65536, len(data)))
            z.append(m(*feats(idx, None)).numpy())
    z = np.concatenate(z)
    p = 1 / (1 + np.exp(-z))
    r01 = (res + 1) / 2
    ll = -np.mean(r01 * np.log(p + 1e-9) + (1 - r01) * np.log(1 - p + 1e-9))
    ph = [(0, 40), (40, 100), (100, 151)]
    parts = " ".join(f"{a}-{b}:{auc(z[dec & (turn >= a) & (turn < b)], y[dec & (turn >= a) & (turn < b)]):.4f}" for a, b in ph)
    print(f"{path.split('/')[-1]:16s} AUC {auc(z[dec], y[dec]):.4f}  {parts}  logloss {ll:.4f}")
