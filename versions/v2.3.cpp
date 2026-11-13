// Cultist Wars bot (CodinGame). One file: exact simulator, alpha-beta search, evaluation.
// Local-only code sits in `#ifdef LOCAL` blocks and is stripped by tools/pack.py.
// Environment knobs for local runs: CW_NODES (fixed nodes per move), CW_MS, CW_FIRST_MS.
#if defined(__x86_64__)
#pragma GCC optimize("O3,inline,omit-frame-pointer,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,popcnt,lzcnt")
#endif
#define NN_H 64
#define THREAT 1
#define RFP 150
#define QDMG 1
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
using namespace std;

typedef unsigned long long U64;
typedef __uint128_t U128;
typedef uint16_t Move;

enum { W = 13, H = 7, NC = 91, NU = 14, MAXTURN = 150, RANGE = 6 };
enum { WAIT = 0, MOVE = 1, SHOOT = 2, CONVERT = 3 };
static const Move NOMOVE = 0xFFFF;

// ---- search / eval parameters (override with -D) --------------------------------------
#ifndef MS_TURN
#define MS_TURN 44
#endif
#ifndef MS_FIRST
#define MS_FIRST 850
#endif
#ifndef TT_BITS
#define TT_BITS 21
#endif
#ifndef LMR
#define LMR 1
#endif
#ifndef LMR_DIV
#define LMR_DIV 1.1
#endif
#ifndef QMAX
#define QMAX 6
#endif
#ifndef ASP          // aspiration window half-width (0 = off)
#define ASP 60
#endif
#ifndef NMP          // null move (a real WAIT) reduction base (0 = off)
#define NMP 2
#endif
#ifndef RFP          // reverse futility margin per depth (0 = off)
#define RFP 0
#endif
#ifndef RFP_MAXD
#define RFP_MAXD 4
#endif
#ifndef FUT          // futility margin per depth, depth <= 2 (0 = off)
#define FUT 450
#endif
#ifndef LMP          // late move pruning base count (0 = off)
#define LMP 2
#endif
#ifndef LMP_D
#define LMP_D 3
#endif
#ifndef FUT_D        // futility up to this depth
#define FUT_D 2
#endif
#ifndef NOWAIT       // 1: WAIT is only generated when there is no other move
#define NOWAIT 0
#endif
#ifndef NEUSHOT      // 0: all shots at neutrals, 1: only killing ones, 2: none
#define NEUSHOT 0
#endif
#ifndef QDMG         // quiescence also searches shots on enemy units doing at least QDMG damage (0 = killing shots only)
#define QDMG 0
#endif
#ifndef LMP_LIN      // late move pruning threshold LMP + LMP_LIN * depth instead of LMP + depth^2 (0 = off)
#define LMP_LIN 0
#endif
#ifndef HPRUNE       // history pruning: skip quiet moves with history below -HPRUNE*depth at depth <= 4 (0 = off)
#define HPRUNE 0
#endif
#ifndef THREAT       // leader steps that threaten a conversion are never pruned and reduced less (0 = off)
#define THREAT 1
#endif
#ifndef IIR          // internal iterative reduction from this depth (0 = off)
#define IIR 0
#endif
#ifndef UNITV
#define UNITV 1000
#endif
#ifndef HPV
#define HPV 40
#endif
#ifndef LEADV
#define LEADV 150
#endif
#ifndef LHPV
#define LHPV 30
#endif
#ifndef NEUV
#define NEUV 300
#endif
#ifndef NEUD
#define NEUD 25
#endif

#ifndef NN_H         // hidden size of the neural evaluation (0 = handcrafted evaluation)
#define NN_H 0
#endif
#ifndef NN_SCALE     // search units per logit; equals the training score scale (train.py --k)
#define NN_SCALE 800
#endif
#define NN_EMBED 1
#define NN_OFF 8448
static const char16_t NN_DATA[] = u"<weights removed: tools/nets/n3a.bin, embed with tools/pack.py>";

static const int MATE = 30000, INF = 32000;

// ---- static tables ---------------------------------------------------------------------
static bool wallAt[NC];
static int8_t nbr[NC][4];            // referee order: up, right, down, left; -1 = off board / obstacle
static uint8_t mdist[NC][NC];        // manhattan
static uint8_t bfsD[NC][NC];         // walking distance around obstacles (units ignored)
static int8_t pathLen[NC][NC];       // bullet line from shooter to target, cells strictly between,
static int8_t pathCell[NC][NC][6];   //   ordered from the shooter, cut at the first obstacle
static bool pathWall[NC][NC];        // an obstacle is on the line: the target itself is never hit
static U128 pathMask[NC][NC];
static U128 rangeMask[NC];           // cells within manhattan distance 1..6
static U64 zPos[NU][NC], zHp[NU][11], zOwn[NU][3], zTurn[MAXTURN + 2];

static inline U128 bit(int c) { return (U128)1 << c; }

#if NN_H
// ---- neural evaluation: weights and feature indexing (see tools/train.py) -----------------
enum { NN_B = 4, NUF = 5 * 4 * NC, NF = NUF + NC, QA = 255, QB = 64 };
static int16_t nnW[NF][NN_H], nnBias[NN_H], nnO[NN_B][2][NN_H];
static int32_t nnOB[NN_B];
static int16_t nnBase[2][NN_H];   // bias + obstacle features of this map, per perspective
static const int8_t HPB[11] = {0, 0, 0, 1, 1, 2, 2, 3, 3, 3, 3};
static inline int feat(int p, int u, int own, int hp, int pos) {
    int typ = u < 2 ? (u != p) : own == p ? 2 : own == 2 ? 4 : 3;
    int sq = p ? pos / W * W + (W - 1 - pos % W) : pos;
    return (typ * 4 + HPB[hp]) * NC + sq;
}
static bool nnLoaded;
static void nnRead(const int16_t* v) {   // v: the int16 stream of the .bin file, biases split in two
    memcpy(nnW, v, sizeof nnW); v += NF * NN_H;
    memcpy(nnBias, v, sizeof nnBias); v += NN_H;
    memcpy(nnO, v, sizeof nnO); v += NN_B * 2 * NN_H;
    for (int b = 0; b < NN_B; b++) nnOB[b] = (int32_t)v[2 * b] * 16384 + v[2 * b + 1];
    nnLoaded = true;
}
#endif

// Bullet line exactly as Board.checkBulletPath: Bresenham drawn from the lower-y end
// (from the target when y is equal). Returns the cells strictly between, shooter side first.
static int lineCells(int from, int to, int8_t* out) {
    int fx = from % W, fy = from / W, tx = to % W, ty = to / W;
    bool fwd = fy < ty;
    int x0 = fwd ? fx : tx, y0 = fwd ? fy : ty, x1 = fwd ? tx : fx, y1 = fwd ? ty : fy;
    int dx = abs(x1 - x0), dy = abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = dx - dy, cx = x0, cy = y0, n = 0;
    int8_t tmp[32];
    for (;;) {
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; cx += sx; }
        if (e2 < dx) { err += dx; cy += sy; }
        if (cx == x1 && cy == y1) break;
        tmp[n++] = (int8_t)(cy * W + cx);
    }
    for (int i = 0; i < n; i++) out[i] = fwd ? tmp[i] : tmp[n - 1 - i];
    return n;
}

static void initTables(const char grid[H][W + 2]) {
    static const int DX[4] = {0, 1, 0, -1}, DY[4] = {-1, 0, 1, 0};
    for (int c = 0; c < NC; c++) wallAt[c] = grid[c / W][c % W] == 'x';
    for (int c = 0; c < NC; c++)
        for (int d = 0; d < 4; d++) {
            int x = c % W + DX[d], y = c / W + DY[d];
            nbr[c][d] = (x < 0 || x >= W || y < 0 || y >= H || wallAt[y * W + x]) ? -1 : (int8_t)(y * W + x);
        }
    for (int a = 0; a < NC; a++) {
        rangeMask[a] = 0;
        for (int b = 0; b < NC; b++) {
            mdist[a][b] = (uint8_t)(abs(a % W - b % W) + abs(a / W - b / W));
            if (a != b && mdist[a][b] <= RANGE) rangeMask[a] |= bit(b);
            bfsD[a][b] = 99;
            pathLen[a][b] = 0; pathWall[a][b] = false; pathMask[a][b] = 0;
        }
    }
    for (int a = 0; a < NC; a++) {
        if (wallAt[a]) continue;
        int q[NC], qh = 0, qt = 0;
        q[qt++] = a; bfsD[a][a] = 0;
        while (qh < qt) {
            int c = q[qh++];
            for (int d = 0; d < 4; d++) {
                int n = nbr[c][d];
                if (n >= 0 && bfsD[a][n] == 99) { bfsD[a][n] = bfsD[a][c] + 1; q[qt++] = n; }
            }
        }
        for (int b = 0; b < NC; b++) {
            if (a == b || mdist[a][b] > RANGE) continue;
            int8_t cells[32];
            int n = lineCells(a, b, cells), k = 0;
            for (int i = 0; i < n; i++) {
                if (wallAt[cells[i]]) { pathWall[a][b] = true; break; }
                pathCell[a][b][k++] = cells[i];
                pathMask[a][b] |= bit(cells[i]);
            }
            pathLen[a][b] = (int8_t)k;
        }
    }
#if NN_H
    for (int p = 0; p < 2; p++) {
        memcpy(nnBase[p], nnBias, sizeof nnBias);
        for (int c = 0; c < NC; c++)
            if (wallAt[c]) {
                const int16_t* w = nnW[NUF + (p ? c / W * W + (W - 1 - c % W) : c)];
                for (int i = 0; i < NN_H; i++) nnBase[p][i] += w[i];
            }
    }
#endif
    U64 x = 0x9E3779B97F4A7C15ULL;
    auto r64 = [&]() { x ^= x << 13; x ^= x >> 7; x ^= x << 17; return x; };
    for (int u = 0; u < NU; u++) {
        for (int c = 0; c < NC; c++) zPos[u][c] = r64();
        for (int h = 0; h < 11; h++) zHp[u][h] = r64();
        for (int o = 0; o < 3; o++) zOwn[u][o] = r64();
    }
    for (int t = 0; t < MAXTURN + 2; t++) zTurn[t] = r64();
}

// ---- state -------------------------------------------------------------------------------
// Unit ids as in the referee: 0 and 1 are the cult leaders of player 0 and 1, 2..13 cultists.
// A dead unit keeps its owner (a dead neutral still takes a slot in the referee's neutral list).
struct State {
    U128 occ;
    U64 hash;          // units only; see key()
    uint32_t seed;     // referee LCG state (model.Random), starts at 42
    int16_t turn;      // plies played; player turn % 2 is to move
    int8_t cnt[2];
    int8_t pos[NU], hp[NU], own[NU];
    int8_t at[NC];     // unit id on the cell, -1 if none
#if NN_H
    int16_t acc[2][NN_H];   // first-layer sums, perspective of player 0 and 1
#endif
};
#if NN_H
static inline void accAdd(State& s, int u, int own, int hp, int pos, int sign) {
    for (int p = 0; p < 2; p++) {
        const int16_t* w = nnW[feat(p, u, own, hp, pos)];
        int16_t* a = s.acc[p];
        if (sign > 0) for (int i = 0; i < NN_H; i++) a[i] += w[i];
        else for (int i = 0; i < NN_H; i++) a[i] -= w[i];
    }
}
#else
static inline void accAdd(State&, int, int, int, int, int) {}
#endif

static inline U64 key(const State& s) {
    return s.hash ^ ((U64)s.seed * 0xD6E8FEB86659FD93ULL) ^ zTurn[s.turn];
}
static inline int rnd(State& s, int bound) {
    s.seed = (s.seed * 1103515245u + 12345u) & 0x7fffffffu;
    return (int)(s.seed % (uint32_t)bound);
}
static inline bool over(const State& s) { return s.turn >= MAXTURN || s.cnt[0] < 1 || s.cnt[1] < 1; }

static void rehash(State& s) {
    s.hash = 0; s.occ = 0;
    memset(s.at, -1, sizeof s.at);
    for (int u = 0; u < NU; u++) {
        s.hash ^= zHp[u][s.hp[u]] ^ zOwn[u][s.own[u]];
        if (s.hp[u] > 0) { s.hash ^= zPos[u][s.pos[u]]; s.occ |= bit(s.pos[u]); s.at[s.pos[u]] = (int8_t)u; }
    }
#if NN_H
    memcpy(s.acc, nnBase, sizeof nnBase);
    for (int u = 0; u < NU; u++) if (s.hp[u] > 0) accAdd(s, u, s.own[u], s.hp[u], s.pos[u], 1);
#endif
}
static inline void moveUnit(State& s, int u, int to) {
    int from = s.pos[u];
    accAdd(s, u, s.own[u], s.hp[u], from, -1);
    accAdd(s, u, s.own[u], s.hp[u], to, 1);
    s.hash ^= zPos[u][from] ^ zPos[u][to];
    s.occ ^= bit(from) | bit(to);
    s.at[from] = -1; s.at[to] = (int8_t)u; s.pos[u] = (int8_t)to;
}
// Unit hit by a bullet fired from cell `from` at the unit on cell `to`; -1 = obstacle.
static inline int resolveHit(const State& s, int from, int to) {
    if (!(pathMask[from][to] & s.occ)) return pathWall[from][to] ? -1 : s.at[to];
    for (int i = 0;; i++) {
        int u = s.at[pathCell[from][to][i]];
        if (u >= 0) return u;
    }
}

static inline Move mk(int type, int unit, int arg) { return (Move)(type | unit << 2 | arg << 6); }
static inline int mType(Move m) { return m & 3; }
static inline int mUnit(Move m) { return (m >> 2) & 15; }
static inline int mArg(Move m) { return m >> 6; }   // MOVE: cell, SHOOT/CONVERT: target id

// One referee turn: the player's action, then the neutral move. Actions are already
// resolved (adjacent moves, targets in range): the bot never relies on referee pathfinding.
static void apply(State& s, Move m) {
    int deadCell = -1, u = mUnit(m), a = mArg(m);
    switch (mType(m)) {
    case MOVE: moveUnit(s, u, a); break;
    case SHOOT: {
        int h = resolveHit(s, s.pos[u], s.pos[a]);
        if (h >= 0) {
            int nh = max(0, s.hp[h] - (7 - mdist[s.pos[u]][s.pos[h]]));
            s.hash ^= zHp[h][s.hp[h]] ^ zHp[h][nh];
            accAdd(s, h, s.own[h], s.hp[h], s.pos[h], -1);
            if (nh) accAdd(s, h, s.own[h], nh, s.pos[h], 1);
            s.hp[h] = (int8_t)nh;
            if (!nh) {
                deadCell = s.pos[h];   // the body blocks its tile until the end of the turn
                s.hash ^= zPos[h][deadCell];
                s.occ ^= bit(deadCell); s.at[deadCell] = -1;
                if (s.own[h] != 2) s.cnt[s.own[h]]--;
            }
        }
        break;
    }
    case CONVERT: {
        int me = s.own[u];
        if (s.own[a] != 2) s.cnt[s.own[a]]--;
        s.hash ^= zOwn[a][s.own[a]] ^ zOwn[a][me];
        accAdd(s, a, s.own[a], s.hp[a], s.pos[a], -1);
        accAdd(s, a, me, s.hp[a], s.pos[a], 1);
        s.own[a] = (int8_t)me; s.cnt[me]++;
        break;
    }
    }
    // Referee.moveNeutralUnit: index = rand(12) into the list of neutral-owned units (dead ones
    // included); out of range or dead: nobody moves and the direction is not drawn.
    int8_t list[12]; int n = 0;
    for (int i = 2; i < NU; i++) if (s.own[i] == 2) list[n++] = (int8_t)i;
    if (n) {
        int idx = rnd(s, 12);
        if (idx < n && s.hp[list[idx]] > 0) {
            int v = list[idx], p = s.pos[v], k = 0; int8_t opt[4];
            for (int d = 0; d < 4; d++) {
                int c = nbr[p][d];
                if (c >= 0 && s.at[c] < 0 && c != deadCell) opt[k++] = (int8_t)c;
            }
            if (!k) rnd(s, 1); else moveUnit(s, v, opt[rnd(s, k)]);
        }
    }
    s.turn++;
}

// ---- move generation ---------------------------------------------------------------------
// mode 0: search (drops shots that hit nothing or hit an own unit, except a killing shot on
//         an own cultist standing next to the enemy leader, which denies a conversion)
// mode 1: every distinct legal effect (to recognise the opponent's action)
// mode 2: tactical only (conversions, killing shots on enemy units)
static int gen(const State& s, Move* mv, int* sc, int mode) {
    int me = s.turn & 1, opp = me ^ 1, n = 0;
    for (int u = 0; u < NU; u++) {
        if (s.hp[u] <= 0 || s.own[u] != me) continue;
        int p = s.pos[u];
        if (mode != 2) {
            int best0 = 99;   // leader: walking distance to the nearest unit it could convert
            if (THREAT && u < 2 && mode == 0)
                for (int t = 2; t < NU; t++)
                    if (s.hp[t] > 0 && s.own[t] != me) best0 = min(best0, (int)bfsD[p][s.pos[t]]);
            for (int d = 0; d < 4; d++) {
                int c = nbr[p][d];
                if (c < 0 || s.at[c] >= 0) continue;
                int v = 0;
                if (best0 < 99) {
                    int b1 = 99;
                    for (int t = 2; t < NU; t++)
                        if (s.hp[t] > 0 && s.own[t] != me) b1 = min(b1, (int)bfsD[c][s.pos[t]]);
                    if (b1 == 1) v = 430000;            // next to a convertible unit: a threat
                    else if (b1 < best0) v = 50000;     // approaching one
                }
                mv[n] = mk(MOVE, u, c); sc[n++] = v;
            }
        }
        if (u < 2) {
            for (int d = 0; d < 4; d++) {
                int c = nbr[p][d], t = c >= 0 ? s.at[c] : -1;
                if (t >= 2 && s.own[t] != me) { mv[n] = mk(CONVERT, u, t); sc[n++] = (s.own[t] == opp ? 900000 : 800000) + s.hp[t]; }
            }
            continue;
        }
        U128 cand = s.occ & rangeMask[p];
        unsigned seen = 0;
        for (int half = 0; half < 2; half++) {
            U64 b = half ? (U64)(cand >> 64) : (U64)cand;
            while (b) {
                int c = __builtin_ctzll(b) + half * 64; b &= b - 1;
                int h = resolveHit(s, p, c);
                if (h < 0 || (seen >> h & 1)) continue;
                seen |= 1u << h;
                int dmg = 7 - mdist[p][s.pos[h]];
                bool kill = dmg >= s.hp[h];
                int o = s.own[h], v;
                if (o == me) {
                    if (mode == 2) continue;
                    if (mode == 0 && !(kill && h >= 2 && s.hp[opp] > 0 && mdist[s.pos[h]][s.pos[opp]] == 1)) continue;
                    v = -500000;
                } else if (o == 2) {
                    if (mode == 2) continue;
                    if (mode == 0 && NEUSHOT && (NEUSHOT == 2 || !kill)) continue;
                    v = kill ? -1000 : -2000 + dmg;
                } else {
                    if (mode == 2 && !kill && !(QDMG && dmg >= QDMG)) continue;
                    v = (kill ? 850000 : 500000) + dmg * 1000 + (h < 2 ? 500 : 0) - s.hp[h];
                }
                mv[n] = mk(SHOOT, u, s.at[c]); sc[n++] = v;
            }
        }
    }
    if (mode != 2 && !(NOWAIT && mode == 0 && n)) { mv[n] = mk(WAIT, 0, 0); sc[n++] = -900000; }
    return n;
}

static string moveStr(const State& s, Move m) {
    char buf[40];
    int u = mUnit(m), a = mArg(m);
    switch (mType(m)) {
    case MOVE: snprintf(buf, sizeof buf, "%d MOVE %d %d", u, a % W, a / W); break;
    case SHOOT: snprintf(buf, sizeof buf, "%d SHOOT %d", u, a); break;
    case CONVERT: snprintf(buf, sizeof buf, "%d CONVERT %d", u, a); break;
    default: snprintf(buf, sizeof buf, "WAIT");
    }
    (void)s;
    return buf;
}

// ---- evaluation --------------------------------------------------------------------------
// Score for player 0. Material (unit count decides the game), hit points, and how close each
// living leader is to the neutrals it could still convert.
static int evalP0(const State& s) {
    int sc = UNITV * (s.cnt[0] - s.cnt[1]);
    int8_t neu[12]; int nn = 0;
    for (int u = 2; u < NU; u++) {
        if (s.hp[u] <= 0) continue;
        if (s.own[u] == 2) neu[nn++] = s.pos[u];
        else sc += (s.own[u] == 0 ? HPV : -HPV) * s.hp[u];
    }
    for (int p = 0; p < 2; p++) {
        if (s.hp[p] <= 0) continue;
        int v = LEADV + LHPV * s.hp[p];
        for (int i = 0; i < nn; i++) v += max(0, NEUV - NEUD * (int)bfsD[s.pos[p]][neu[i]]);
        sc += p == 0 ? v : -v;
    }
    return sc;
}
#if NN_H
static inline int nnEval(const State& s) {
    int stm = s.turn & 1, left = MAXTURN - s.turn, b = (left <= 70) + (left <= 30) + (left <= 10);
    const int16_t *a0 = s.acc[stm], *a1 = s.acc[stm ^ 1], *o0 = nnO[b][0], *o1 = nnO[b][1];
    int sum = 0;
    for (int i = 0; i < NN_H; i++) {
        int v = min(max((int)a0[i], 0), (int)QA), w = min(max((int)a1[i], 0), (int)QA);
        sum += v * o0[i] * v + w * o1[i] * w;
    }
    return (int)((long long)(sum / QA + nnOB[b]) * NN_SCALE / (QA * QB));
}
static inline int evalStm(const State& s) {
    if (!nnLoaded) return (s.turn & 1) ? -evalP0(s) : evalP0(s);
    return nnEval(s);
}
#else
static inline int evalStm(const State& s) { return (s.turn & 1) ? -evalP0(s) : evalP0(s); }
#endif
static inline int terminal(const State& s, int ply) {
    int d = s.cnt[0] - s.cnt[1];
    if (s.turn & 1) d = -d;
    return d > 0 ? MATE - ply : d < 0 ? -MATE + ply : 0;
}

// ---- search ------------------------------------------------------------------------------
struct TTE { uint32_t key; Move move; int16_t score; int8_t depth; uint8_t flag; };
enum { TT_EXACT = 1, TT_LOWER = 2, TT_UPPER = 3 };
static TTE* tt;
static const U64 TT_MASK = (1ULL << TT_BITS) - 1;
static int hist[2][1 << 13];
static Move killer[MAXTURN + 8][2];
static long long nodes, nodeLimit;
static bool stopped;
static chrono::steady_clock::time_point deadline;
static int lmrTab[64][64];

static inline bool timeUp() {
    if (nodeLimit) return nodes >= nodeLimit;
    return (nodes & 255) == 0 && chrono::steady_clock::now() >= deadline;
}
static inline int pick(Move* mv, int* sc, int i, int n) {
    int b = i;
    for (int j = i + 1; j < n; j++) if (sc[j] > sc[b]) b = j;
    swap(mv[i], mv[b]); swap(sc[i], sc[b]);
    return i;
}

static int qsearch(const State& s, int alpha, int beta, int ply, int qd) {
    if (over(s)) return terminal(s, ply);
    nodes++;
    int stand = evalStm(s);
    if (stand >= beta || qd >= QMAX) return stand;
    if (stand > alpha) alpha = stand;
    Move mv[64]; int sc[64];
    int n = gen(s, mv, sc, 2);
    for (int i = 0; i < n; i++) {
        pick(mv, sc, i, n);
        State c = s;
        apply(c, mv[i]);
        int v = -qsearch(c, -beta, -alpha, ply + 1, qd + 1);
        if (v > stand) { stand = v; if (v > alpha) { alpha = v; if (v >= beta) break; } }
    }
    return stand;
}

static int search(const State& s, int depth, int alpha, int beta, int ply, bool allowNull = true) {
    if (over(s)) return terminal(s, ply);
    if (depth <= 0) return qsearch(s, alpha, beta, ply, 0);
    nodes++;
    if (timeUp()) { stopped = true; return 0; }
    bool pv = beta - alpha > 1;
    U64 k = key(s);
    TTE* e = &tt[k & TT_MASK];
    Move ttm = NOMOVE;
    if (e->key == (uint32_t)(k >> 32)) {
        ttm = e->move;
        if (e->depth >= depth && !pv) {
            int v = e->score;
            if (v > MATE - 400) v -= ply; else if (v < -MATE + 400) v += ply;
            if (e->flag == TT_EXACT || (e->flag == TT_LOWER && v >= beta) || (e->flag == TT_UPPER && v <= alpha)) return v;
        }
    }
    int ev = evalStm(s);
    if (!pv && abs(beta) < MATE - 400) {
        if (RFP && depth <= RFP_MAXD && ev - RFP * depth >= beta) return ev;
        if (NMP && allowNull && depth >= 3 && ev >= beta) {
            State c = s;
            apply(c, mk(WAIT, 0, 0));
            int v = -search(c, depth - 1 - NMP - depth / 4, -beta, -beta + 1, ply + 1, false);
            if (stopped) return 0;
            if (v >= beta && v < MATE - 400) return v;
        }
    }
    if (IIR && depth >= IIR && ttm == NOMOVE) depth--;
    Move mv[256]; int sc[256];
    int n = gen(s, mv, sc, 0), me = s.turn & 1;
    for (int i = 0; i < n; i++) {
        Move m = mv[i];
        if (m == ttm) sc[i] = 2000000;
        else if (sc[i] > -100000 && sc[i] < 100000) {   // quiet steps and shots at neutrals
            if (m == killer[ply][0]) sc[i] = 400000;
            else if (m == killer[ply][1]) sc[i] = 399000;
            else sc[i] += hist[me][m & 8191];
        }
    }
    int best = -INF, a0 = alpha;
    Move bm = NOMOVE;
    for (int i = 0; i < n; i++) {
        pick(mv, sc, i, n);
        Move m = mv[i];
        bool quiet = sc[i] < 450000, threat = quiet && sc[i] >= 420000;
        if (i > 0 && quiet && !threat && !pv && best > -MATE + 400) {
            if (LMP && depth <= LMP_D && i >= LMP + (LMP_LIN ? LMP_LIN * depth : depth * depth)) continue;
            if (FUT && depth <= FUT_D && ev + FUT * depth <= alpha) continue;
            if (HPRUNE && depth <= 4 && sc[i] < -HPRUNE * depth) continue;
        }
        State c = s;
        apply(c, m);
        int v;
        if (i == 0) v = -search(c, depth - 1, -beta, -alpha, ply + 1);
        else {
            int r = 0;
            if (LMR && quiet && depth >= 3 && i >= 3) {
                r = lmrTab[min(depth, 63)][min(i, 63)];
                if (threat) r = r / 2;
                if (r > depth - 2) r = depth - 2;
            }
            v = -search(c, depth - 1 - r, -alpha - 1, -alpha, ply + 1);
            if (v > alpha && r && !stopped) v = -search(c, depth - 1, -alpha - 1, -alpha, ply + 1);
            if (v > alpha && v < beta && !stopped) v = -search(c, depth - 1, -beta, -alpha, ply + 1);
        }
        if (stopped) return 0;
        if (v > best) {
            best = v; bm = m;
            if (v > alpha) {
                alpha = v;
                if (v >= beta) {
                    if (quiet) {
                        if (killer[ply][0] != m) { killer[ply][1] = killer[ply][0]; killer[ply][0] = m; }
                        int& h = hist[me][m & 8191];
                        h += depth * depth - h * depth * depth / 16384;
                    }
                    break;
                }
            }
        }
    }
    int st = best;
    if (st > MATE - 400) st += ply; else if (st < -MATE + 400) st -= ply;
    e->key = (uint32_t)(k >> 32); e->move = bm; e->score = (int16_t)st; e->depth = (int8_t)depth;
    e->flag = best >= beta ? TT_LOWER : best > a0 ? TT_EXACT : TT_UPPER;
    return best;
}

struct Info { int depth, score; long long nodes; double ms; };
static Info info;

static Move think(const State& root, double budgetMs) {
    auto t0 = chrono::steady_clock::now();
    deadline = t0 + chrono::microseconds((long long)(budgetMs * 1000));
    nodes = 0; stopped = false;
    memset(killer, 0xFF, sizeof killer);
    for (auto& side : hist) for (int& h : side) h /= 2;
    Move mv[256]; int sc[256];
    int n = gen(root, mv, sc, 0);
    Move best = mv[pick(mv, sc, 0, n)];
    info = {0, 0, 0, 0};
    int maxDepth = MAXTURN - root.turn, prev = 0;
    for (int depth = 1; depth <= maxDepth; depth++) {
        int lo = -INF, hi = INF, delta = ASP;
        if (ASP && depth >= 4) { lo = prev - delta; hi = prev + delta; }
        for (;;) {
            int alpha = lo, itScore = -INF;
            Move itBest = NOMOVE;
            for (int i = 0; i < n; i++) if (mv[i] == best) { swap(mv[0], mv[i]); swap(sc[0], sc[i]); }
            for (int i = 0; i < n; i++) {
                if (i) pick(mv, sc, i, n);
                State c = root;
                apply(c, mv[i]);
                int v;
                if (i == 0) v = -search(c, depth - 1, -hi, -alpha, 1);
                else {
                    v = -search(c, depth - 1, -alpha - 1, -alpha, 1);
                    if (v > alpha && !stopped) v = -search(c, depth - 1, -hi, -alpha, 1);
                }
                if (stopped) break;
                if (v > itScore) { itScore = v; if (v > alpha) { alpha = v; itBest = mv[i]; if (v >= hi) break; } }
            }
            // An interrupted iteration still counts once a move has beaten the window's lower bound.
            if (itBest != NOMOVE) { best = itBest; info.score = itScore; }
            if (stopped) break;
            if (itScore <= lo) { lo = max(-INF, lo - delta * 2); delta *= 3; }
            else if (itScore >= hi) { hi = min(INF, hi + delta * 2); delta *= 3; }
            else { prev = itScore; info.depth = depth; break; }
        }
        if (stopped) break;
        if (abs(prev) > MATE - 400) break;
        if (!nodeLimit && chrono::steady_clock::now() - t0 > (deadline - t0) * 6 / 10) break;
    }
    info.nodes = nodes;
    info.ms = chrono::duration<double, milli>(chrono::steady_clock::now() - t0).count();
    return best;
}

static void initNet() {
#if NN_H
#ifdef NN_EMBED
    // Embedded net: a bit stream, 15 bits per character. First-layer weights are int8,
    // everything else int16 (see tools/pack.py).
    static int16_t buf[NF * NN_H + NN_H + NN_B * 2 * NN_H + 2 * NN_B];
    const char16_t* p = NN_DATA;
    U64 acc = 0;
    int nb = 0, k = 0;
    auto byte = [&]() {
        while (nb < 8) { acc |= (U64)(*p++ - NN_OFF) << nb; nb += 15; }
        int v = (int)(acc & 255);
        acc >>= 8; nb -= 8;
        return v;
    };
    for (int i = 0; i < NF * NN_H; i++) buf[k++] = (int8_t)byte();
    for (int i = 0; i < NN_H + NN_B * 2 * NN_H + 2 * NN_B; i++) { int lo = byte(); buf[k++] = (int16_t)(lo | byte() << 8); }
    nnRead(buf);
#endif
#endif
}
static void initSearch() {
    tt = (TTE*)calloc(1ULL << TT_BITS, sizeof(TTE));
    memset(tt, 0, sizeof(TTE) << TT_BITS);   // touch every page before the first timed turn
    for (int d = 1; d < 64; d++)
        for (int i = 1; i < 64; i++) lmrTab[d][i] = (int)(log(d) * log(i) / LMR_DIV);
}

// ---- protocol: rebuild the exact state (with the referee's RNG) from the inputs --------------
struct Obs { int8_t pos[NU], hp[NU], own[NU]; };   // hp 0 = not listed (dead)

static bool matches(const State& s, const Obs& o) {
    for (int u = 0; u < NU; u++) {
        if ((s.hp[u] > 0) != (o.hp[u] > 0)) return false;
        if (s.hp[u] > 0 && (s.hp[u] != o.hp[u] || s.pos[u] != o.pos[u] || s.own[u] != o.own[u])) return false;
    }
    return true;
}
// Find the opponent action that leads from `prev` to the observed units.
static bool syncFrom(const State& prev, const Obs& o, State& out) {
    Move mv[256]; int sc[256];
    int n = gen(prev, mv, sc, 1);
    for (int i = 0; i < n; i++) {
        State c = prev;
        apply(c, mv[i]);
        if (matches(c, o)) { out = c; return true; }
    }
    return false;
}
static State fromObs(const Obs& o, uint32_t seed, int turn, const State* prev) {
    State s;
    memset(&s, 0, sizeof s);
    s.seed = seed; s.turn = (int16_t)turn;
    for (int u = 0; u < NU; u++) {
        s.hp[u] = o.hp[u]; s.pos[u] = o.pos[u];
        s.own[u] = o.hp[u] > 0 ? o.own[u] : prev ? prev->own[u] : (u < 2 ? u : 2);
        if (o.hp[u] > 0 && s.own[u] < 2) s.cnt[s.own[u]]++;
    }
    rehash(s);
    return s;
}
// Second player: the first input is already one action and one neutral move old. The start
// position is mirror symmetric (unit 2+i mirrors unit 8+i), which gives the candidates.
static bool syncSecond(const Obs& o, State& out) {
    Obs base = o;
    base.pos[0] = 3 * W;
    for (int u = 2; u < NU; u++) base.own[u] = 2;
    auto mir = [](int c) { return c / W * W + (W - 1 - c % W); };
    for (int v = -1; v < 12; v++) {
        Obs cand = base;
        if (v >= 0) {
            int u = 2 + v, twin = u < 8 ? u + 6 : u - 6;
            if (mir(cand.pos[twin]) == cand.pos[u]) continue;
            cand.pos[u] = (int8_t)mir(cand.pos[twin]);
        }
        State s0 = fromObs(cand, 42, 0, nullptr);
        if (syncFrom(s0, o, out)) return true;
    }
    return false;
}


#ifndef CW_LIB
int main() {
    int myId, w, h;
    char grid[H][W + 2];
    if (scanf("%d", &myId) != 1) return 0;
    auto t0 = chrono::steady_clock::now();
    if (scanf("%d %d", &w, &h) != 2) return 0;
    for (int y = 0; y < H; y++) if (scanf("%14s", grid[y]) != 1) return 0;
    for (int y = 0; y < H; y++) fprintf(stderr, "%s\n", grid[y]);
    initNet();
    initTables(grid);
    initSearch();
    double msTurn = MS_TURN, msFirst = MS_FIRST;
    State cur;
    bool have = false, first = true;
    int myTurns = 0;
    for (;;) {
        int n;
        if (scanf("%d", &n) != 1) break;
        if (!first) t0 = chrono::steady_clock::now();
        Obs o;
        memset(&o, 0, sizeof o);
        fprintf(stderr, "#S %d", myTurns * 2 + myId);
        for (int i = 0; i < n; i++) {
            int id, type, hp, x, y, owner;
            if (scanf("%d %d %d %d %d %d", &id, &type, &hp, &x, &y, &owner) != 6) return 0;
            o.hp[id] = (int8_t)hp; o.pos[id] = (int8_t)(y * W + x); o.own[id] = (int8_t)owner;
            fprintf(stderr, " %d,%d,%d,%d,%d", id, hp, x, y, owner);
        }
        int turn = myTurns * 2 + myId;
        bool ok = true;
        State nxt;
        if (!have) {
            if (myId == 0) nxt = fromObs(o, 42, 0, nullptr);
            else ok = syncSecond(o, nxt);
        } else ok = syncFrom(cur, o, nxt);
        if (!ok) nxt = fromObs(o, have ? cur.seed : 42, turn, have ? &cur : nullptr);   // should not happen
        cur = nxt;
        have = true;
        fprintf(stderr, "\n#R %d %u%s\n", turn, cur.seed, ok ? "" : " DESYNC");
        double used = chrono::duration<double, milli>(chrono::steady_clock::now() - t0).count();
        Move m = think(cur, (first ? msFirst : msTurn) - used);
        puts(moveStr(cur, m).c_str());
        fflush(stdout);
        fprintf(stderr, "d%d s%d n%lld %.1fms %.0fknps\n", info.depth, info.score, info.nodes, info.ms,
                info.ms > 0 ? info.nodes / info.ms : 0.0);
        apply(cur, m);
        first = false;
        myTurns++;
    }
    return 0;
}
#endif
