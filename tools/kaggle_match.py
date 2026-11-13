#!/usr/bin/env python3
"""Play gate matches on Kaggle CPU kernels (fixed nodes per move, so hardware speed is irrelevant).

  kaggle_match.py push NAME [--games 300] [--nodes 20000] [--ms 0] A B [A2 B2 ...]
  kaggle_match.py status NAME
  kaggle_match.py fetch NAME
A and B are bot specs: a source file, optionally followed by '@' and compiler flags, e.g.
  bot.cpp@-DNMP=2  league/src/v1.0.cpp
Each pairing is one private kernel cw-match-NAME-i. CW_KP=2 selects the second account
(~/.kaggle/user_2, ~/.kaggle/access_token_2).
"""
import glob, json, math, os, re, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROF = os.environ.get("CW_KP", "1")
_SUF = "" if PROF == "1" else f"_{PROF}"
USER = os.environ.get("KAGGLE_USERNAME") or open(os.path.expanduser(f"~/.kaggle/user{_SUF}")).read().strip()
SFX = "" if PROF == "1" else f"_p{PROF}"
ENV = {**os.environ, "KAGGLE_API_TOKEN": open(os.path.expanduser(f"~/.kaggle/access_token{_SUF}")).read().strip(),
       "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ["PATH"]}
SCRIPT = '''import glob, os, shutil, subprocess
A, FA, B, FB, GAMES, NODES, MS = %r, %r, %r, %r, %d, %d, %d
d = os.path.dirname(glob.glob("/kaggle/input/**/referee.cpp", recursive=True)[0])
os.makedirs("/tmp/src/tools", exist_ok=True)
shutil.copy(d + "/referee.cpp", "/tmp/src/tools/referee.cpp")
shutil.copy(d + "/refbot.cpp", "/tmp/src/bot.cpp")
cc = ["g++", "-O3", "-std=c++17", "-march=native", "-DLOCAL"]
subprocess.check_call(cc + ["-o", "/tmp/referee", "/tmp/src/tools/referee.cpp"])
subprocess.check_call(cc + FA.split() + ["-o", "/tmp/a", d + "/" + A])
subprocess.check_call(cc + FB.split() + ["-o", "/tmp/b", d + "/" + B])
# MS > 0: real time control (2 games at once on 4 vCPUs so every bot has a core to itself)
mode = ["-j", "2", "-n", "0", "-t", str(MS), "-f", str(10 * MS), "-x", "20"] if MS else ["-j", "4", "-n", str(NODES)]
out = subprocess.check_output(["/tmp/referee", "/tmp/a", "/tmp/b", "-g", str(GAMES), "-s", "777"] + mode, text=True)
print("RESULT", A + "@" + FA, B + "@" + FB, out.strip().splitlines()[-1], flush=True)
'''


def kg(*a):
    return subprocess.run(["kaggle", *a], env=ENV, capture_output=True, text=True)


def push(name, specs, games, nodes, ms=0):
    d = os.path.join(ROOT, "kaggle", "matchsrc" + SFX)
    os.makedirs(d, exist_ok=True)
    new = not os.path.exists(os.path.join(d, "dataset-metadata.json"))
    json.dump({"title": "cw-match", "id": f"{USER}/cw-match", "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(d, "dataset-metadata.json"), "w"))
    shutil.copy(os.path.join(ROOT, "tools", "referee.cpp"), d)
    shutil.copy(os.path.join(ROOT, "bot.cpp"), os.path.join(d, "refbot.cpp"))
    bots = []
    for sp in specs:
        f, _, flags = sp.partition("@")
        dst = name + "_" + os.path.basename(f)
        shutil.copy(f, os.path.join(d, dst))
        bots.append((dst, flags))
    r = kg("datasets", "create", "-p", d) if new else kg("datasets", "version", "-p", d, "-m", name)
    print((r.stdout + r.stderr).strip().splitlines()[-1][:120])
    for _ in range(40):
        time.sleep(6)
        if "ready" in (kg("datasets", "status", f"{USER}/cw-match").stdout):
            break
    time.sleep(10)
    for i in range(0, len(bots), 2):
        k = os.path.join(ROOT, "kaggle", f"m{SFX}_{name}_{i // 2 + 1}")
        os.makedirs(k, exist_ok=True)
        open(os.path.join(k, "match.py"), "w").write(SCRIPT % (bots[i][0], bots[i][1], bots[i + 1][0], bots[i + 1][1], games, nodes, ms))
        json.dump({"id": f"{USER}/cw-match-{name}-{i // 2 + 1}", "title": f"cw-match-{name}-{i // 2 + 1}", "code_file": "match.py",
                   "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": False,
                   "enable_internet": False, "dataset_sources": [f"{USER}/cw-match"]}, open(os.path.join(k, "kernel-metadata.json"), "w"))
        r = kg("kernels", "push", "-p", k)
        print(i // 2 + 1, (r.stdout + r.stderr).strip().splitlines()[-1][:110], flush=True)


def kernels(name):
    return sorted(glob.glob(os.path.join(ROOT, "kaggle", f"m{SFX}_{name}_*")), key=lambda k: int(k.rsplit("_", 1)[1]))


def status(name):
    st = []
    for k in kernels(name):
        r = kg("kernels", "status", f"{USER}/cw-match-{name}-{k.rsplit('_', 1)[1]}")
        m = re.search(r"KernelWorkerStatus\.(\w+)", r.stdout + r.stderr)
        st.append(m.group(1) if m else "?")
    print(" ".join(st))
    return st


def fetch(name):
    for k in kernels(name):
        i = k.rsplit("_", 1)[1]
        d = os.path.join(ROOT, "kaggle", "out", f"m{SFX}_{name}_{i}")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        kg("kernels", "output", f"{USER}/cw-match-{name}-{i}", "-p", d)
        for f in glob.glob(os.path.join(d, "*.log")):
            txt = open(f).read().replace('\\"', '"')
            m = re.search(r'RESULT (\S+?)@(.*?) (\S+?)@(.*?) (\{.*?\})', txt)
            if not m:
                print(i, "no result:", txt[-300:]); continue
            s = json.loads(m.group(5))
            w, l, dr = s["wins_a"], s["wins_b"], s["draws"]
            n = w + l + dr
            p = (w + dr / 2 + 0.5) / (n + 1)
            se = math.sqrt(p * (1 - p) / n)
            elo = -400 * math.log10(1 / p - 1)
            err = (-400 * math.log10(1 / min(p + 1.96 * se, .999) - 1) + 400 * math.log10(1 / max(p - 1.96 * se, .001) - 1)) / 2
            print(f"{m.group(1)} [{m.group(2)}] vs {m.group(3)} [{m.group(4)}]: +{w} -{l} ={dr} ({100 * p:.1f}%)  elo {elo:+.0f} +/- {err:.0f}"
                  f"  faults {s['faults_a']}/{s['faults_b']}" + (f"  [{s['ms']} ms/move, max {s['max_ms_a']:.0f}/{s['max_ms_b']:.0f}]" if not s["nodes"] else ""))


if __name__ == "__main__":
    c, name, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    if c == "push":
        games, nodes, ms, files = 300, 20000, 0, []
        i = 0
        while i < len(rest):
            if rest[i] == "--games": games = int(rest[i + 1]); i += 2
            elif rest[i] == "--nodes": nodes = int(rest[i + 1]); i += 2
            elif rest[i] == "--ms": ms = int(rest[i + 1]); i += 2
            else: files.append(rest[i]); i += 1
        push(name, files, games, nodes, ms)
    elif c == "status": status(name)
    elif c == "fetch": fetch(name)
