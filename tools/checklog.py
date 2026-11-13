#!/usr/bin/env python3
"""Exactness gate: replay CodinGame game logs through our simulator.

  checklog.py LOG [LOG ...]

A log is the text log of a test game played by our bot, whose stderr holds the raw unit
list it received each turn (`#S turn id,hp,x,y,owner ...`) and the RNG state it deduced
(`#R turn seed`). Every action of both players is replayed with the referee's rules
(build/referee --check) and every later unit list must match the simulation exactly.
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0
for path in sys.argv[1:]:
    log = open(path).read()
    frames = re.split(r"\nframe ", log)
    out, grid = [], None
    for f in frames[1:]:
        head = f.split("\n", 1)[0]
        m = re.match(r"(\d+) agent (\d)", head)
        if not m:
            continue
        turn, agent = int(m.group(1)) - 1, int(m.group(2))
        s = re.search(r"#S (\d+)((?: \d+,\d+,\d+,\d+,\d+)+)", f)
        r = re.search(r"#R (\d+) (\d+)( DESYNC)?", f)
        if r and r.group(3):
            print(f"{path}: bot reported DESYNC at turn {turn}")
            bad += 1
        if s and r:
            out.append(f"S {turn} {r.group(2)}{s.group(2)}")
        a = re.search(r"stdout: (.*)", f)
        if a:
            out.append(f"A {turn} {agent} {a.group(1).strip()}")
    rows = re.findall(r"(?:^|\s)([.x]{13})\s*$", log, re.M)
    if len(rows) < 7:
        print(f"{path}: no map in the log")
        bad += 1
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".chk", delete=False) as t:
        t.write("M " + " ".join(rows[:7]) + "\n" + "\n".join(out) + "\n")
    res = subprocess.run([os.path.join(ROOT, "build", "referee"), "--check", t.name], capture_output=True, text=True)
    os.unlink(t.name)
    print(f"{os.path.basename(path)}: {res.stdout.strip()}")
    bad += res.returncode != 0
sys.exit(1 if bad else 0)
