# Self-play data generation for the Cultist Wars bot. Compiles the engine from the
# attached private dataset and runs one generator process per CPU core.
import glob, os, subprocess, time
GAMES, NODES, SEED, NET, FLAGS = 300, 5000, 9000, "", ""   # templated by tools/kaggle_gen.py
src = glob.glob("/kaggle/input/**/bot.cpp", recursive=True)[0]
d = os.path.dirname(src)
t0 = time.time()
subprocess.check_call(["g++", "-O3", "-std=c++17", "-march=native", "-DLOCAL"] + FLAGS.split() + ["-o", "/kaggle/working/bot", src])
n = os.cpu_count()
print("cpus", n, "compile s", round(time.time() - t0, 1), flush=True)
t0 = time.time()
env = {**os.environ}
if NET:
    env["CW_NET"] = f"{d}/{NET}"
procs = [subprocess.Popen(["/kaggle/working/bot"], env={**env, "CW_GEN": f"{GAMES}:{NODES}:{SEED + i}:/kaggle/working/k_{SEED + i}.bin"}) for i in range(n)]
for p in procs:
    p.wait()
os.remove("/kaggle/working/bot")
el = time.time() - t0
pos = sum(os.path.getsize(f) for f in glob.glob("/kaggle/working/k_*.bin")) // 48
print(f"positions {pos} in {el:.0f}s = {pos / el * 60:.0f} per minute", flush=True)
