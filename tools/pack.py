#!/usr/bin/env python3
"""Build the single-file CodinGame submission.

  pack.py [-D NAME=VALUE ...] [-o out/submission.cpp] [SRC]

Strips `#ifdef LOCAL ... #endif` blocks and bakes -D overrides in as #defines.
CodinGame's limit is 100k characters.
"""
import argparse, os, re

ap = argparse.ArgumentParser()
ap.add_argument("src", nargs="?", default="bot.cpp")
ap.add_argument("-D", action="append", default=[])
ap.add_argument("-o", "--out", default="out/submission.cpp")
a = ap.parse_args()

s = open(a.src, encoding="utf-8").read()
s = re.sub(r"#ifdef LOCAL\n.*?\n#endif\n", "", s, flags=re.S)
defs = "".join(f"#define {d.replace('=', ' ', 1)}\n" for d in a.D)
if defs:
    i = s.index("#include")
    s = s[:i] + defs + s[i:]
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
open(a.out, "w", encoding="utf-8").write(s)
print(f"{a.out}: {len(s)} chars")
