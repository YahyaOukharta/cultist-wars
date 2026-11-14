#!/usr/bin/env python3
"""Paired replays of arena battles in CodinGame test games (they do not touch the leaderboard).

  pairs.py run TAG_A SRC_A TAG_B SRC_B --sub SUB[,SUB] [--who aCat,Noobkins,MSz] [--limit N]
  pairs.py show TAG_A TAG_B

Each listed battle is replayed with SRC_A, then with SRC_B, in our seat of that battle and
against the same opponent agent on the same map (replay_game_id). Same map and seat for both
sides of a pair; what is left is the timing noise of the test machines. Results go to
arena/gauntlet.jsonl with the battle id in "replay"; `show` scores the pairs both versions
completed, by seat.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg

OUT = os.path.join(cg.ROOT, "arena", "gauntlet.jsonl")


def play(tag, src, gid):
    try:
        path = cg.test(src, replay=int(gid))
    except SystemExit as e:
        print("skipped", tag, gid, str(e)[:120], flush=True)
        return
    log = open(path).read()
    seat = int(re.search(r"\n\s+(\d) yhyoxx", log).group(1))
    opp = re.search(r"\n\s+%d (.+?) \(agent_id" % (1 - seat), log).group(1)
    m = re.search(r"scores: 0=(-?\d+) 1=(-?\d+)", log)
    sc = [int(m.group(1)), int(m.group(2))]
    bad = "timeout" if f"${seat} timeout" in log else "desync" if "DESYNC" in log else ""
    rec = {"tag": tag, "opponent": opp, "me": sc[seat], "opp": sc[1 - seat], "log": os.path.basename(path), "bad": bad,
           "seat": seat, "replay": int(gid), "time": int(time.time())}
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(tag, gid, opp, "seat", seat, "me", sc[seat], "opp", sc[1 - seat], bad, flush=True)


def run(ta, sa, tb, sb, subs, who, limit):
    bs = [json.loads(l) for l in open(os.path.join(cg.ROOT, "arena", "battles.jsonl")) if l.strip()]
    ids = [b["game_id"] for b in bs if b["submission"] in subs and (not who or b["opponent"] in who)][:limit]
    print(len(ids), "battles", flush=True)
    for gid in ids:
        play(ta, sa, gid)
        play(tb, sb, gid)


def score(r):
    return 1.0 if r["me"] > r["opp"] else 0.0 if r["me"] < r["opp"] else 0.5


def show(ta, tb):
    rs = [json.loads(l) for l in open(OUT) if l.strip()]
    a = {r["replay"]: r for r in rs if r["tag"] == ta and "replay" in r}
    b = {r["replay"]: r for r in rs if r["tag"] == tb and "replay" in r}
    both = sorted(set(a) & set(b))
    for seat in (0, 1, None):
        ks = [k for k in both if seat is None or a[k]["seat"] == seat]
        if not ks:
            continue
        sa, sb = sum(score(a[k]) for k in ks), sum(score(b[k]) for k in ks)
        d = [score(b[k]) - score(a[k]) for k in ks]
        mean = sum(d) / len(d)
        se = (sum((x - mean) ** 2 for x in d) / max(len(d) - 1, 1) / len(d)) ** .5
        name = "all" if seat is None else f"seat {seat + 1}"
        print(f"{name:7s} {len(ks):3d} pairs  {ta} {sa:.1f}  {tb} {sb:.1f}  diff {mean:+.3f} ± {se:.3f} per game")


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    if c == "run":
        subs = [int(x) for x in a[a.index("--sub") + 1].split(",")]
        who = a[a.index("--who") + 1].split(",") if "--who" in a else None
        limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
        run(a[0], a[1], a[2], a[3], subs, who, limit)
    elif c == "show":
        show(a[0], a[1])
