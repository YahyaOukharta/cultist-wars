#!/usr/bin/env python3
"""Gauntlet against real arena bots through CodinGame test games (ground truth, unlike self-play).

  gauntlet.py run TAG SRC [-g GAMES_PER_OPPONENT] [-o agent_id,agent_id,...]
  gauntlet.py replay TAG SRC [-g GAMES_PER_OPPONENT]     second-seat suite (replays of our arena battles)
  gauntlet.py show [TAG]
Default opponents: the players above us in Legend. Our bot always has the first seat in a
test game. Limits: about 30 test games per 15 minutes, 600 per day. Results are appended to
arena/gauntlet.jsonl; logs go to arena/logs/.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg

OUT = os.path.join(cg.ROOT, "arena", "gauntlet.jsonl")
TOP = ["aCat", "Noobkins", "MSz", "Zylo", "ziele", "KawattaTaido", "Pduhard-", "jacek"]


def run(tag, src, games, ids):
    fixed = bool(ids)
    for g in range(games):
        if not fixed:   # agent ids change when a player resubmits: look them up every round
            opp = {o["nickname"]: o["agent_id"] for o in cg.call(f"/puzzles/{cg.PUZ}/opponents")["opponents"]}
            ids = [str(opp[n]) for n in TOP if n in opp]
        for i in ids:
            try:
                path = cg.test(src, i)
            except SystemExit as e:
                print("skipped", i, str(e)[:120], flush=True)
                continue
            log = open(path).read()
            name = re.search(r"\n\s+1 (.+?) \(agent_id", log).group(1)
            m = re.search(r"scores: 0=(-?\d+) 1=(-?\d+)", log)
            me, op = int(m.group(1)), int(m.group(2))
            bad = "timeout" if "$0 timeout" in log else "desync" if "DESYNC" in log else ""
            with open(OUT, "a") as f:
                f.write(json.dumps({"tag": tag, "opponent": name, "me": me, "opp": op, "log": os.path.basename(path), "bad": bad, "time": int(time.time())}) + "\n")


def replay(tag, src, n):
    """Second-seat suite: replay our arena battles against the top players in which we moved second
    (same map, same opponent, same seats). The suite is the same for every candidate."""
    bs = [json.loads(l) for l in open(os.path.join(cg.ROOT, "arena", "battles.jsonl"))]
    suite = []
    for b in sorted(bs, key=lambda b: b["game_id"]):
        p = os.path.join(cg.ROOT, "arena", "battle_logs", f"{b['game_id']}.log")
        if b["opponent"] in TOP and b["submission"] >= 41709148 and os.path.exists(p) and re.search(r"\n\s+1 yhyoxx", open(p).read()):
            suite.append(b)
    per = {}
    for b in suite:                      # same number of games per opponent, oldest first
        per.setdefault(b["opponent"], []).append(b)
    picked = [b for k in range(n) for o in TOP if len(per.get(o, [])) > k for b in [per[o][k]]]
    for b in picked:
        try:
            path = cg.test(src, replay=b["game_id"])
        except SystemExit as e:
            print("skipped", b["game_id"], str(e)[:120], flush=True)
            continue
        log = open(path).read()
        m = re.search(r"scores: 0=(-?\d+) 1=(-?\d+)", log)
        me, op = int(m.group(2)), int(m.group(1))
        bad = "timeout" if "$1 timeout" in log else "desync" if "DESYNC" in log else ""
        with open(OUT, "a") as f:
            f.write(json.dumps({"tag": tag, "opponent": b["opponent"], "me": me, "opp": op, "log": os.path.basename(path), "bad": bad,
                                "seat": 1, "replay": b["game_id"], "time": int(time.time())}) + "\n")


def show(tag=None):
    rows = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
    tags = [tag] if tag else sorted(set(r["tag"] for r in rows), key=lambda t: min(r["time"] for r in rows if r["tag"] == t))
    for t in tags:
        rs = [r for r in rows if r["tag"] == t]
        w = sum(r["me"] > r["opp"] for r in rs); l = sum(r["me"] < r["opp"] for r in rs); d = len(rs) - w - l
        per = {}
        for r in rs:
            p = per.setdefault(r["opponent"], [0, 0, 0])
            p[0 if r["me"] > r["opp"] else 1 if r["me"] < r["opp"] else 2] += 1
        bad = sum(1 for r in rs if r["bad"])
        print(f"{t:<14} +{w} -{l} ={d}  ({100 * (w + d / 2) / max(len(rs), 1):.0f}%)  unit diff {sum(r['me'] - r['opp'] for r in rs) / max(len(rs), 1):+.2f}"
              + (f"  BAD {bad}" if bad else "") + "   " + "  ".join(f"{k} {v[0]}-{v[1]}-{v[2]}" for k, v in per.items()))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "replay":
        replay(a[1], a[2], int(a[a.index("-g") + 1]) if "-g" in a else 3)
        show(a[1])
    elif a and a[0] == "run":
        games = int(a[a.index("-g") + 1]) if "-g" in a else 3
        ids = a[a.index("-o") + 1].split(",") if "-o" in a else []
        run(a[1], a[2], games, ids)
        show(a[1])
    else:
        show(a[1] if len(a) > 1 else None)
