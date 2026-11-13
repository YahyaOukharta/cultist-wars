#!/usr/bin/env python3
"""Turn our arena battles into training / validation records.

  arena_data.py fetch            download the text log of every archived battle -> arena/battle_logs/
  arena_data.py export OUT.bin [--top] [--sub ID]
                                 rebuild every position (map from the game seed, tools/mapgen.py;
                                 moves from the log) -> 48-byte records, result as label
  arena_data.py games OUT.txt [--top] [--sub ID] [--only loss] [--who NAME] [--opp-side]
                                 (--opp-side: analyse the opponent's positions instead of ours)
                                 the same games as text, for `referee --analyze` (needs a net: CW_NET)
A battle log has no board, only the seed and both players' outputs; the game is deterministic.
--top keeps only games against the eight players above us.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapgen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "arena", "battle_logs")
TOKEN = open(os.path.expanduser("~/.config/codingame/token")).read().strip()
TOP = {"aCat", "Noobkins", "MSz", "Zylo", "ziele", "KawattaTaido", "Pduhard-", "jacek"}


def battles():
    return [json.loads(l) for l in open(os.path.join(ROOT, "arena", "battles.jsonl")) if l.strip()]


def fetch():
    os.makedirs(LOGS, exist_ok=True)
    todo = [b for b in battles() if not os.path.exists(os.path.join(LOGS, f"{b['game_id']}.log"))]
    print(len(todo), "logs to download", flush=True)
    for i, b in enumerate(todo):
        req = urllib.request.Request(f"https://www.codingame.com/api/v1/games/{b['game_id']}", headers={"Authorization": "Bearer " + TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                t = r.read().decode("utf-8")
        except Exception as e:
            print("skip", b["game_id"], e, flush=True)
            time.sleep(5)
            continue
        if t.lstrip().startswith("{"):
            t = json.loads(t).get("log", "")
        open(os.path.join(LOGS, f"{b['game_id']}.log"), "w").write(t)
        time.sleep(0.6)
        if i % 100 == 0:
            print(i, flush=True)


def export(out, top, sub, only=None, seats=False, opp_side=False, who=None):
    lines, n = [], 0
    for b in battles():
        if (top and b["opponent"] not in TOP) or (sub and b["submission"] != sub) or (only and b["result"] != only) or (who and b["opponent"] != who):
            continue
        p = os.path.join(LOGS, f"{b['game_id']}.log")
        if not os.path.exists(p):
            continue
        log = open(p).read()
        seed = re.search(r"options: seed=(-?\d+)", log)
        sc = re.search(r"scores: 0=(-?\d+) 1=(-?\d+)", log)
        if not seed or not sc:
            continue
        grid, units = mapgen.make_map(int(seed.group(1)))
        if seats:
            seat = int(re.search(r'(\d) yhyoxx', log).group(1))
            lines.append(f"P {1 - seat if opp_side else seat} {b['game_id']}")
        lines.append("M " + " ".join(grid))
        lines.append("S 0 42 " + " ".join(f"{u},10,{x},{y},{u if u < 2 else 2}" for u, (x, y) in sorted(units.items())))
        for f in re.split(r"\nframe ", log)[1:]:
            m = re.match(r"(\d+) agent (\d)", f)
            a = re.search(r"stdout: (.*)", f)
            if m and a:
                lines.append(f"A {int(m.group(1)) - 1} {m.group(2)} {a.group(1).strip()}")
        d = int(sc.group(1)) - int(sc.group(2))
        lines.append(f"R {(d > 0) - (d < 0)}")
        n += 1
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
        t.write("\n".join(lines) + "\n")
    if seats:          # analysis input: keep the file, the caller runs build/referee --analyze on it
        os.replace(t.name, out)
        print(n, "games ->", out)
        return
    print(n, "games;", subprocess.run([os.path.join(ROOT, "build", "referee"), "--export", t.name, out], capture_output=True, text=True).stdout.strip())
    os.unlink(t.name)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "fetch":
        fetch()
    else:
        export(a[1], "--top" in a, int(a[a.index("--sub") + 1]) if "--sub" in a else 0,
               a[a.index("--only") + 1] if "--only" in a else None, a[0] == "games", "--opp-side" in a,
               a[a.index("--who") + 1] if "--who" in a else None)
