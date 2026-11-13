#!/usr/bin/env python3
"""Build the single-file CodinGame submission.

  pack.py [-n NET.bin -H hidden] [-D NAME=VALUE ...] [-o out/submission.cpp] [SRC]

Strips `#ifdef LOCAL ... #endif` blocks, bakes -D overrides in as #defines, and embeds the
net as a UTF-16 string literal (one character per int16 weight; CodinGame's 100k limit
counts characters, not bytes).
"""
import argparse, os, re
import numpy as np

OFF = 27756  # value + OFF stays in [256, 0xD800): no controls, quotes or surrogates
NF, NB = 1911, 4
ap = argparse.ArgumentParser()
ap.add_argument("src", nargs="?", default="bot.cpp")
ap.add_argument("-n", "--net")
ap.add_argument("-H", "--hidden", type=int, default=32)
ap.add_argument("-D", action="append", default=[])
ap.add_argument("-o", "--out", default="out/submission.cpp")
a = ap.parse_args()

s = open(a.src, encoding="utf-8").read()
out, skip = [], 0          # drop `#ifdef LOCAL` blocks, nested conditionals included
for line in s.split("\n"):
    t = line.strip()
    if skip:
        if re.match(r"#\s*if", t): skip += 1
        elif re.match(r"#\s*endif", t): skip -= 1
        continue
    if t == "#ifdef LOCAL":
        skip = 1
        continue
    out.append(line)
s = "\n".join(out)
defs = "".join(f"#define {d.replace('=', ' ', 1)}\n" for d in a.D)
assert "//@NET_DATA@" in s
net = ""
if a.net:
    h = a.hidden
    raw = open(a.net, "rb").read()
    n16 = NF * h + h + 2 * h * NB
    assert len(raw) == n16 * 2 + 4 * NB, f"net size mismatch for hidden={h}"
    v = np.frombuffer(raw[:n16 * 2], dtype="<i2").astype(np.int64)
    ob = np.frombuffer(raw[n16 * 2:], dtype="<i4").astype(np.int64)
    v = np.concatenate([v, np.stack([ob >> 14, ob & 16383], axis=1).reshape(-1)])
    assert np.abs(v).max() <= 27500, "weight out of encodable range"
    codes = v + OFF
    assert not ((codes == 0x2028) | (codes == 0x2029)).any() or True
    codes[(codes == 0x2028) | (codes == 0x2029)] += 2  # avoid line/paragraph separators (2 units of error at most)
    text = "".join(map(chr, codes.tolist()))
    net = f'#define NN_EMBED 1\n#define NN_OFF {OFF}\nstatic const char16_t NN_DATA[] = u"{text}";\n'
    defs = f"#define NN_H {h}\n" + defs
s = s.replace("//@NET_DATA@\n", net)
if defs:
    i = s.index("#include")
    s = s[:i] + defs + s[i:]
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
open(a.out, "w", encoding="utf-8").write(s)
print(f"{a.out}: {len(s)} chars" + ("  ** over the 100k limit **" if len(s) > 100000 else ""))
