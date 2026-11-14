#!/usr/bin/env python3
"""Arena runs compared on the same game mix.

  strata.py BASE_SUBS SUBS [SUBS ...]        (comma-separated submission ids)

Each run is split by opponent group (top 3 / rest) and our seat. The last column is the
score the run would have had on the first argument's mix of games: one raw arena score
depends on how many second-seat games against the top 3 the run happened to draw.
"""
import collections, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = [json.loads(l) for l in open(os.path.join(ROOT, "arena", "battles.jsonl")) if l.strip()]
TOP3 = {"aCat", "Noobkins", "MSz"}
KEYS = [("top3", 0), ("top3", 1), ("rest", 0), ("rest", 1)]


def strata(subs):
    st = collections.defaultdict(lambda: [0, 0.0])
    for b in B:
        if b["submission"] not in subs:
            continue
        p = os.path.join(ROOT, "arena", "battle_logs", f"{b['game_id']}.log")
        if not os.path.exists(p):
            continue
        seat = int(re.search(r"(\d) yhyoxx", open(p).read()).group(1))
        k = ("top3" if b["opponent"] in TOP3 else "rest", seat)
        st[k][0] += 1
        st[k][1] += {"win": 1, "loss": 0, "draw": .5}[b["result"]]
    return st


groups = [[int(x) for x in a.split(",")] for a in sys.argv[1:]]
base = strata(groups[0])
total = sum(base[k][0] for k in KEYS)
for g in groups:
    s = strata(g)
    adj = sum(base[k][0] * (s[k][1] / s[k][0] if s[k][0] else 0) for k in KEYS) / total
    cells = "  ".join(f"{k[0]}-s{k[1] + 1}: {s[k][1]:.1f}/{s[k][0]} ({100 * s[k][1] / max(s[k][0], 1):.0f}%)" for k in KEYS)
    print(g, cells, f" | on baseline mix: {100 * adj:.1f}%")
