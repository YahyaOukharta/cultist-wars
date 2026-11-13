#!/usr/bin/env python3
"""Local league for Cultist Wars bot versions (in the spirit of psyleague).

Every version is frozen (source + binary) under league/ and plays through the native
referee (build/referee). Results are appended to league/results.jsonl; ratings are a
Bradley-Terry fit over the whole history (a draw counts as half a win for each side).

  league.py add NAME [SRC]         freeze SRC (default bot.cpp) as version NAME
  league.py run [-b NAME] [-g N]   play N games per pairing (NAME vs all, or all pairs)
  league.py match A B [-g N]       head-to-head only (A/B may be league names or binaries)
  league.py show                   rating table
Common options: -n NODES (fixed nodes per move, default 20000; 0 = use time),
                -t MS (time per move when -n 0), -j PROCS, -s SEED, --nb NODES_FOR_B
"""
import argparse, json, math, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAGUE = os.path.join(ROOT, "league")
BOTS = os.path.join(LEAGUE, "bots")
SRCS = os.path.join(LEAGUE, "src")
RESULTS = os.path.join(LEAGUE, "results.jsonl")
REFEREE = os.path.join(ROOT, "build", "referee")
CXX = [os.environ.get("CXX", "c++"), "-O3", "-std=c++17", "-march=native", "-DLOCAL"]


def build_referee():
    srcs = [os.path.join(ROOT, "tools", "referee.cpp"), os.path.join(ROOT, "bot.cpp")]
    if not os.path.exists(REFEREE) or os.path.getmtime(REFEREE) < max(map(os.path.getmtime, srcs)):
        os.makedirs(os.path.dirname(REFEREE), exist_ok=True)
        subprocess.check_call(CXX + ["-o", REFEREE, srcs[0]])


def bot_names():
    if not os.path.isdir(SRCS):
        return []
    return [n[:-4] for n in sorted(os.listdir(SRCS), key=lambda n: os.path.getmtime(os.path.join(SRCS, n))) if n.endswith(".cpp")]


def resolve(name):
    p = os.path.join(BOTS, name)
    src = os.path.join(SRCS, name + ".cpp")
    if not os.path.exists(p) and os.path.exists(src):   # fresh clone: binaries are not tracked
        os.makedirs(BOTS, exist_ok=True)
        subprocess.check_call(CXX + ["-o", p, src])
    if os.path.exists(p):
        return p
    if os.path.exists(name):
        return os.path.abspath(name)
    sys.exit(f"unknown bot: {name}")


def cmd_add(a):
    os.makedirs(BOTS, exist_ok=True)
    os.makedirs(SRCS, exist_ok=True)
    dst = os.path.join(BOTS, a.name)
    if os.path.exists(dst) or os.path.exists(os.path.join(SRCS, a.name + ".cpp")):
        sys.exit(f"{a.name} already exists (versions are immutable)")
    src = a.src or os.path.join(ROOT, "bot.cpp")
    subprocess.check_call(CXX + ["-o", dst, src])
    shutil.copy(src, os.path.join(SRCS, a.name + ".cpp"))
    print(f"added {a.name}")


def play(a, na, nb, record=True):
    build_referee()
    cmd = [REFEREE, resolve(na), resolve(nb), "-g", str(a.games), "-j", str(a.threads),
           "-s", str(a.seed if a.seed else int(time.time() * 1000) % 2**31)]
    cmd += ["-n", str(a.nodes)] if a.nodes else ["-t", str(a.ms)]
    if a.nb: cmd += ["-nb", str(a.nb)]
    out = subprocess.check_output(cmd, text=True)
    s = json.loads(out.strip().splitlines()[-1])
    rec = {k: s[k] for k in ("wins_a", "wins_b", "draws", "faults_a", "faults_b", "first_wins", "games", "nodes", "ms", "avg_plies", "max_ms_a", "max_ms_b")}
    rec.update({"a": na, "b": nb, "time": int(time.time())})
    if record:
        with open(RESULTS, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def elo_diff(w, l, d=0):
    n = w + l + d
    if n == 0:
        return 0.0, 0.0
    p = min(max((w + d / 2 + 0.5) / (n + 1), 1e-6), 1 - 1e-6)
    elo = -400 * math.log10(1 / p - 1)
    se = math.sqrt(p * (1 - p) / n)
    lo, hi = max(p - 1.96 * se, 1e-6), min(p + 1.96 * se, 1 - 1e-6)
    err = (-400 * math.log10(1 / hi - 1) + 400 * math.log10(1 / lo - 1)) / 2
    return elo, err


def report(r):
    n = r["wins_a"] + r["wins_b"] + r["draws"]
    elo, err = elo_diff(r["wins_a"], r["wins_b"], r["draws"])
    pct = 100.0 * (r["wins_a"] + r["draws"] / 2) / n if n else 0
    f = f"  faults {r['faults_a']}/{r['faults_b']}" if r["faults_a"] or r["faults_b"] else ""
    t = "" if r["nodes"] else f"  max ms {r['max_ms_a']:.0f}/{r['max_ms_b']:.0f}"
    print(f"{r['a']} vs {r['b']}: +{r['wins_a']} -{r['wins_b']} ={r['draws']} ({pct:.1f}%)  elo {elo:+.0f} +/- {err:.0f}"
          f"  first-seat wins {100.0 * r['first_wins'] / max(n, 1):.0f}%  plies {r['avg_plies']}{f}{t}", flush=True)


def cmd_match(a):
    rec = os.path.exists(os.path.join(SRCS, a.a + ".cpp")) and os.path.exists(os.path.join(SRCS, a.b + ".cpp")) and not a.nb
    report(play(a, a.a, a.b, record=rec))


def cmd_run(a):
    names = bot_names()
    if a.bot:
        opp = [n for n in names if n != a.bot]
        if a.last:
            opp = opp[-a.last:]
        pairs = [(a.bot, n) for n in opp]
    else:
        pairs = [(x, y) for i, x in enumerate(names) for y in names[i + 1:]]
    for x, y in pairs:
        report(play(a, x, y))
    cmd_show(a)


def cmd_show(a):
    res = [json.loads(l) for l in open(RESULTS) if l.strip()] if os.path.exists(RESULTS) else []
    names = bot_names()
    idx = {n: i for i, n in enumerate(names)}
    k = len(names)
    w = [[0.0] * k for _ in range(k)]
    faults = [0] * k
    for r in res:
        if r["a"] in idx and r["b"] in idx:
            i, j = idx[r["a"]], idx[r["b"]]
            w[i][j] += r["wins_a"] + r["draws"] / 2
            w[j][i] += r["wins_b"] + r["draws"] / 2
            faults[i] += r["faults_a"]
            faults[j] += r["faults_b"]
    # Bradley-Terry (MM algorithm) with a weak prior: one win and one loss against a
    # virtual average player, which keeps unbeaten/winless bots finite.
    p = [1.0] * k
    for _ in range(500):
        np_ = []
        for i in range(k):
            wins = 1.0 + sum(w[i])
            den = 2.0 / (p[i] + 1.0)
            for j in range(k):
                n = w[i][j] + w[j][i]
                if n:
                    den += n / (p[i] + p[j])
            np_.append(wins / den)
        g = math.exp(sum(math.log(x) for x in np_) / k) if k else 1
        p = [x / g for x in np_]
    rows = []
    for n in names:
        i = idx[n]
        won, lost = sum(w[i]), sum(w[j][i] for j in range(k))
        rows.append((400 * math.log10(p[i]), n, int(won + lost), 100 * won / (won + lost) if won + lost else 0, faults[i]))
    base = rows[0][0] if rows else 0  # oldest version anchored at 0
    print(f"\n{'bot':<16}{'elo':>7}{'games':>8}{'score%':>8}{'faults':>8}")
    for elo, n, g, pct, f in sorted(rows, reverse=True):
        print(f"{n:<16}{elo - base:>7.0f}{g:>8}{pct:>8.1f}{f:>8}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("-g", "--games", type=int, default=200)
        p.add_argument("-n", "--nodes", type=int, default=20000)
        p.add_argument("-t", "--ms", type=int, default=50)
        p.add_argument("-j", "--threads", type=int, default=8)
        p.add_argument("-s", "--seed", type=int, default=0)
        p.add_argument("--nb", type=int)

    p = sub.add_parser("add"); p.add_argument("name"); p.add_argument("src", nargs="?"); p.set_defaults(f=cmd_add)
    p = sub.add_parser("run"); p.add_argument("-b", "--bot"); p.add_argument("--last", type=int, default=0)
    common(p); p.set_defaults(f=cmd_run)
    p = sub.add_parser("match"); p.add_argument("a"); p.add_argument("b"); common(p); p.set_defaults(f=cmd_match)
    p = sub.add_parser("show"); p.set_defaults(f=cmd_show)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
