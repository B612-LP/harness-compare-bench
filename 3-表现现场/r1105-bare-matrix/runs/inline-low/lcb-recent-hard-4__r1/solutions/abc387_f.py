import sys
from collections import deque

MOD = 998244353

def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M = data[0], data[1]
    A = [x - 1 for x in data[2:2 + N]]

    indeg = [0] * N
    rev = [[] for _ in range(N)]
    for i, p in enumerate(A):
        indeg[p] += 1
        rev[p].append(i)

    q = deque(i for i in range(N) if indeg[i] == 0)
    pref = [None] * N

    while q:
        u = q.popleft()
        f = [1] * (M + 1)
        for v in rev[u]:
            pv = pref[v]
            for k in range(1, M + 1):
                f[k] = f[k] * pv[k] % MOD

        pu = [0] * (M + 1)
        s = 0
        for k in range(1, M + 1):
            s += f[k]
            if s >= MOD:
                s -= MOD
            pu[k] = s
        pref[u] = pu

        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    cycle = [indeg[i] > 0 for i in range(N)]
    visited = [False] * N
    ans = 1

    for start in range(N):
        if not cycle[start] or visited[start]:
            continue

        comp = []
        cur = start
        while not visited[cur]:
            visited[cur] = True
            comp.append(cur)
            cur = A[cur]

        prod = [1] * (M + 1)

        for u in comp:
            w = [1] * (M + 1)
            for v in rev[u]:
                if cycle[v]:
                    continue
                pv = pref[v]
                for k in range(1, M + 1):
                    w[k] = w[k] * pv[k] % MOD

            for k in range(1, M + 1):
                prod[k] = prod[k] * w[k] % MOD

        contrib = sum(prod[1:]) % MOD
        ans = ans * contrib % MOD

    print(ans)


if __name__ == "__main__":
    solve()
