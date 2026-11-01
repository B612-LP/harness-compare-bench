# FILE: solutions/abc387_f.py
import sys
from collections import deque

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M = data[0], data[1]
    A = [0] + data[2:2 + N]

    rev = [[] for _ in range(N + 1)]
    indeg = [0] * (N + 1)
    for i in range(1, N + 1):
        p = A[i]
        rev[p].append(i)
        indeg[p] += 1

    q = deque()
    for i in range(1, N + 1):
        if indeg[i] == 0:
            q.append(i)

    removed = [False] * (N + 1)
    f = [None] * (N + 1)

    while q:
        u = q.popleft()
        removed[u] = True

        cur = [1] * (M + 1)
        for v in rev[u]:
            fv = f[v]
            s = 0
            for y in range(1, M + 1):
                s += fv[y]
                if s >= MOD:
                    s -= MOD
                cur[y] = cur[y] * s % MOD
        f[u] = cur

        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    visited = [False] * (N + 1)
    ans = 1

    for start in range(1, N + 1):
        if removed[start] or visited[start]:
            continue

        cycle = []
        u = start
        while not visited[u]:
            visited[u] = True
            cycle.append(u)
            u = A[u]

        prod = [1] * (M + 1)

        for u in cycle:
            g = [1] * (M + 1)

            for v in rev[u]:
                if removed[v]:
                    fv = f[v]
                    s = 0
                    for y in range(1, M + 1):
                        s += fv[y]
                        if s >= MOD:
                            s -= MOD
                        g[y] = g[y] * s % MOD

            for y in range(1, M + 1):
                prod[y] = prod[y] * g[y] % MOD

        comp = 0
        for y in range(1, M + 1):
            comp += prod[y]
            if comp >= MOD:
                comp -= MOD

        ans = ans * comp % MOD

    print(ans)

if __name__ == "__main__":
    main()
