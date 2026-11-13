#!/usr/bin/env python3
"""The referee's map generator: java.util.SplittableRandom(seed) driving Board.initLaymen and
Board.initExtraObstacles. A game log's `options: seed=N` gives back the start position.

  mapgen.py SEED            print the grid and the neutral units
  mapgen.py --verify LOG..  check against test-game logs that contain the map and units
"""
import re, sys

M64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15


class SplittableRandom:
    def __init__(self, seed):
        self.seed = seed & M64

    def _next(self):
        self.seed = (self.seed + GAMMA) & M64
        return self.seed

    def _mix64(self):
        z = self._next()
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def _mix32(self):
        z = self._next()
        z = ((z ^ (z >> 33)) * 0x62A9D9ED799705F5) & M64
        return (((z ^ (z >> 28)) * 0xCB24D0A5C88C35B3) & M64) >> 32      # unsigned 32 bits

    def next_int(self, bound):
        r, m = self._mix32(), bound - 1
        if bound & m == 0:
            return r & m
        u = r >> 1                      # r is unsigned here, so r >>> 1 is the same
        while True:
            r = u % bound
            if u + m - r < (1 << 31):   # no int overflow
                return r
            u = self._mix32() >> 1

    def next_double(self):
        return (self._mix64() >> 11) * (1.0 / (1 << 53))


W, H = 13, 7


def make_map(seed):
    rnd = SplittableRandom(seed)
    units = {0: (0, 3), 1: (12, 3)}
    used = set()
    for i in range(6):
        while True:
            x = rnd.next_int(5) + 1
            y = rnd.next_int(H)
            if (x, y) not in used:
                break
        used.add((x, y))
        units[2 + i] = (x, y)
    for i in range(6):
        x, y = units[2 + i]
        units[8 + i] = (W - 1 - x, y)
    blocked = used | {(0, 3)}
    while True:
        walls = set()
        for col in range((W - 1) // 2):
            for row in range(H):
                if (col, row) not in blocked and rnd.next_double() < 0.2:
                    walls.add((col, row)); walls.add((W - 1 - col, row))
        seen, todo = {(0, 3)}, [(0, 3)]
        while todo:
            x, y = todo.pop()
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < W and 0 <= n[1] < H and n not in walls and n not in seen:
                    seen.add(n); todo.append(n)
        if len(seen) == W * H - len(walls):
            break
    grid = ["".join("x" if (x, y) in walls else "." for x in range(W)) for y in range(H)]
    return grid, units


if __name__ == "__main__":
    if sys.argv[1] == "--verify":
        ok = bad = 0
        for p in sys.argv[2:]:
            log = open(p).read()
            seed = re.search(r"options: seed=(-?\d+)", log)
            rows = re.findall(r"(?:^|\s)([.x]{13})\s*$", log, re.M)[:7]
            s0 = re.search(r"#S 0((?: \d+,\d+,\d+,\d+,\d+)+)", log)
            if not seed or len(rows) < 7 or not s0:
                continue
            grid, units = make_map(int(seed.group(1)))
            real = {int(a): (int(x), int(y)) for a, hp, x, y, o in (u.split(",") for u in s0.group(1).split())}
            if grid == rows and units == real:
                ok += 1
            else:
                bad += 1
                print("MISMATCH", p)
        print(f"{ok} maps reproduced, {bad} mismatches")
    else:
        grid, units = make_map(int(sys.argv[1]))
        print("\n".join(grid)); print(units)
