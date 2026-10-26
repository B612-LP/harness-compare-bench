#!/usr/bin/env python3
"""小规模独立校验器：对 N ∈ {2,4,6} 直接全枚举所有带标号简单图逐个验证。

不使用任何分层 DP / 生成函数技巧 —— 作为与 solution_abc389_g.py 完全独立的
第二条计算路径，用于交叉验证参考解的正确性（小规模真值）。

判定方式：枚举 K_N 的全部边子集（N=6 时 2^15=32768 个），逐图 BFS：
连通 且 (距离为偶的点数 == 距离为奇的点数) 则按边数 M 计数。
连通图总数可与 OEIS A001187（n=2:1, n=4:38, n=6:26704）锚点核对。

Python ≥3.9，仅标准库。
"""
from itertools import combinations


def enumerate_counts(N):
    """返回 (res, connected_total)：res[M] = 平衡连通图数（未取模的精确整数），
    connected_total = 连通图总数（用于与 A001187 锚点核对）。"""
    edges = list(combinations(range(N), 2))
    E = len(edges)
    full = (1 << N) - 1
    res = [0] * (E + 1)
    connected_total = 0
    for mask in range(1 << E):
        adj = [0] * N
        cnt = 0
        m = mask
        i = 0
        while m:
            if m & 1:
                u, v = edges[i]
                adj[u] |= 1 << v
                adj[v] |= 1 << u
                cnt += 1
            m >>= 1
            i += 1
        # BFS from vertex 0（位运算）
        seen = 1
        frontier = 1
        even = 1  # 顶点 0 自身距离 0
        odd = 0
        d = 0
        while frontier:
            nxt = 0
            f = frontier
            while f:
                b = f & -f
                u = b.bit_length() - 1
                nxt |= adj[u]
                f ^= b
            nxt &= ~seen
            seen |= nxt
            d ^= 1
            c = bin(nxt).count("1")
            if d:
                odd += c
            else:
                even += c
            frontier = nxt
        if seen == full:
            connected_total += 1
            if even == odd:
                res[cnt] += 1
    return res, connected_total


def expected_vector(N, P):
    """与 solution 输出同构：M = N-1 .. C(N,2)，mod P。"""
    res, conn = enumerate_counts(N)
    return [res[M] % P for M in range(N - 1, N * (N - 1) // 2 + 1)], conn


if __name__ == "__main__":
    import json
    import sys

    arg = json.load(sys.stdin)  # [{"N":..,"P":..}, ...]
    out = []
    for case in arg:
        vec, conn = expected_vector(case["N"], case["P"])
        out.append({"N": case["N"], "P": case["P"], "answer": vec,
                    "connected_total": conn})
    json.dump(out, sys.stdout)
