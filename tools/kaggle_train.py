#!/usr/bin/env python3
"""Train a net on a Kaggle GPU kernel.

  kaggle_train.py push NAME [--gen TAG:N ...] [--ds DATASET ...] -- <train.py args, data as /kaggle/input globs>
  kaggle_train.py status NAME
  kaggle_train.py fetch NAME          -> tools/nets/NAME.bin (+ log printed)
Data sources mounted: the outputs of generation kernels cw-TAG-1..N (of this account) and
any datasets given with --ds (user/name, or name for this account).
"""
import glob, json, os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROF = os.environ.get("CW_KP", "1")
_SUF = "" if PROF == "1" else f"_{PROF}"
USER = os.environ.get("KAGGLE_USERNAME") or open(os.path.expanduser(f"~/.kaggle/user{_SUF}")).read().strip()
SFX = "" if PROF == "1" else f"_p{PROF}"
ENV = {**os.environ, "KAGGLE_API_TOKEN": open(os.path.expanduser(f"~/.kaggle/access_token{_SUF}")).read().strip(),
       "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ["PATH"]}


def kg(*a):
    return subprocess.run(["kaggle", *a], env=ENV, capture_output=True, text=True)


def push(name, gens, targs, extra=()):
    d = os.path.join(ROOT, "kaggle", f"t{SFX}_{name}")
    os.makedirs(d, exist_ok=True)
    argv = ["train.py", "-o", f"/kaggle/working/{name}.bin"] + targs
    src = open(os.path.join(ROOT, "tools", "train.py")).read()
    open(os.path.join(d, "train.py"), "w").write(f"import sys\nsys.argv = {argv!r}\n" + src)
    ks = [f"{USER}/cw-{t}-{i}" for t, n in gens for i in range(1, n + 1)]
    json.dump({"id": f"{USER}/cw-train-{name}", "title": f"cw-train-{name}", "code_file": "train.py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": False,
               "dataset_sources": [x if "/" in x else f"{USER}/{x}" for x in extra], "kernel_sources": ks},
              open(os.path.join(d, "kernel-metadata.json"), "w"))
    r = kg("kernels", "push", "-p", d)
    print((r.stdout + r.stderr).strip().splitlines()[-1][:150])


def status(name):
    r = kg("kernels", "status", f"{USER}/cw-train-{name}")
    m = re.search(r"KernelWorkerStatus\.(\w+)", r.stdout + r.stderr)
    print(m.group(1) if m else (r.stdout + r.stderr).strip()[-200:])
    return m.group(1) if m else "?"


def fetch(name):
    d = os.path.join(ROOT, "kaggle", "out", f"t{SFX}_{name}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    kg("kernels", "output", f"{USER}/cw-train-{name}", "-p", d)
    for f in glob.glob(os.path.join(d, "*.log")):
        try:
            for e in json.load(open(f)):
                t = e.get("data", "").rstrip()
                if t and "Warning" not in t and "NbConvert" not in t and "re.sub" not in t:
                    print(t)
        except Exception:
            print(open(f).read()[-3000:])
    os.makedirs(os.path.join(ROOT, "tools", "nets"), exist_ok=True)
    for f in glob.glob(os.path.join(d, f"{name}.bin*")):
        shutil.copy(f, os.path.join(ROOT, "tools", "nets"))
        print("saved tools/nets/" + os.path.basename(f))


if __name__ == "__main__":
    c, name, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    if c == "push":
        gens, extra, i = [], [], 0
        while i < len(rest) and rest[i] != "--":
            if rest[i] == "--gen":
                t, n = rest[i + 1].split(":"); gens.append((t, int(n))); i += 2
            elif rest[i] == "--ds":
                extra.append(rest[i + 1]); i += 2
            else:
                i += 1
        push(name, gens, rest[i + 1:], extra)
    elif c == "status": status(name)
    elif c == "fetch": fetch(name)
