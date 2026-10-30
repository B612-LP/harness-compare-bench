#!/usr/bin/env python3
"""ABC389G - Odd Even Graph 独立参考解（候选 staging solution）。

输入：一行 `N P`（N 为正偶数，2 ≤ N ≤ 30；P 为素数，10^8 ≤ P ≤ 10^9）。
输出：对 M = N-1 .. N(N-1)/2 依次输出「N 点 M 边连通简单图中，
顶点 1 到各点最短距离的偶/奇侧点数相等（各 = N/2）」的图数，空格分隔，对 P 取模。

算法（editorial-converged，实现为本仓独立代码）：
  按 BFS 距离分层 L_0={1}, L_1, ..., L_k。连通图与「分层 + 边选法」一一对应：
    - 每个 L_i (i≥1) 的点至少与 L_{i-1} 中一点相邻（否则距离更小）；
    - 不存在跨层 |i-j|≥2 的边（否则距离差矛盾）；
    - 同层内边任选。
  固定各层大小 (1, b_1..b_k)，标号方案数 = ∏ C(剩余点数, b_i)；
  边数生成函数（x 计边）：
    相邻层 a→b 之间「b 侧每点至少 1 条边」：容斥
        B_{a,b}(x) = Σ_{j=0..b} (-1)^j C(b,j) (1+x)^{a(b-j)}
    b 层内部： (1+x)^{C(b,2)}
  代换 y = 1+x 后每个因子只剩 b+1 项： y^{C(b,2)} · Σ_j (-1)^j C(b,j) y^{a(b-j)}。
  DP 状态 (上一层大小 a, 偶侧已用 e, 奇侧已用 o)，值 = y 的稀疏多项式；
  终态要求 e = o = N/2。设 Σ_q c_q y^q，则 M 边答案 = Σ_q c_q C(q, M)。

Python ≥3.9，仅标准库。
"""
import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    N, P = int(data[0]), int(data[1])
    max_e = N * (N - 1) // 2
    need = max(N, max_e)

    # 帕斯卡三角 mod P（下标到 need = max(N, C(N,2))）
    comb = [[0] * (need + 1) for _ in range(need + 1)]
    for i in range(need + 1):
        row = comb[i]
        row[0] = 1 % P
        row[i] = 1 % P
        if i:
            prev = comb[i - 1]
            for j in range(1, i):
                row[j] = (prev[j - 1] + prev[j]) % P

    # 预计算相邻层 a→b 的 y-因子（稀疏 (指数, 系数) 列表；系数为 0 的项剔除）
    factor = [[None] * (N + 1) for _ in range(N + 1)]
    for a in range(0, N + 1):
        for b in range(1, N + 1):
            base = b * (b - 1) // 2
            cb = comb[b]
            terms = []
            for j in range(b + 1):
                c = cb[j]
                if c:
                    terms.append((a * (b - j) + base,
                                  c if (j % 2 == 0) else (P - c) % P))
            factor[a][b] = terms

    target = N // 2

    # dp: {(上一层大小 a, 偶侧点数 e, 奇侧点数 o): {q: 系数}}，q 为 y 指数
    dp = {(1, 1, 0): {0: 1}}
    final = {}
    parity = 1  # 下一层奇偶（1 = 奇数距离层）
    while dp:
        ndp = {}
        for (a, e, o), poly in dp.items():
            rem = N - e - o
            items = list(poly.items())
            fa = factor[a]
            for b in range(1, rem + 1):
                if parity:
                    ne, no = e, o + b
                else:
                    ne, no = e + b, o
                if ne > target or no > target:
                    continue
                if e + o + b == N:
                    if ne != target:
                        continue
                    d = final
                else:
                    key = (b, ne, no)
                    d = ndp.get(key)
                    if d is None:
                        d = {}
                        ndp[key] = d
                w = comb[rem][b]
                terms = fa[b]
                dget = d.get
                for q, co in items:
                    cw = co * w
                    for off, ca in terms:
                        qq = q + off
                        d[qq] = dget(qq, 0) + cw * ca
        for d in ndp.values():
            for q in d:
                d[q] %= P
        for q in final:
            final[q] %= P
        parity ^= 1
        dp = ndp

    out = []
    for M in range(N - 1, max_e + 1):
        s = 0
        for q, co in final.items():
            if q >= M:
                s += co * comb[q][M]
        out.append(str(s % P))
    sys.stdout.write(" ".join(out) + "\n")


if __name__ == "__main__":
    main()
