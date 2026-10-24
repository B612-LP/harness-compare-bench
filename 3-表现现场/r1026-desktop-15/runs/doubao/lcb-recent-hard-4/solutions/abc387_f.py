import sys
from collections import deque


def main():
    MOD = 998244353
    data = list(map(int, sys.stdin.buffer.read().split()))
    N, M = data[0], data[1]
    A = [v - 1 for v in data[2:2 + N]]

    children = [[] for _ in range(N)]
    indeg = [0] * N
    for i, p in enumerate(A):
        children[p].append(i)
        indeg[p] += 1

    # prod[v][t] = product of g_child(t) over already-processed tree children
    prod = [None] * N
    ones = [1] * (M + 1)

    q = deque(i for i in range(N) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    # Peeling order is leaves-first, so children are processed before parent.
    for u in order:
        f = prod[u]
        if f is None:
            f = ones
        g = [0] * (M + 1)
        acc = 0
        for t in range(1, M + 1):
            acc += f[t]
            if acc >= MOD:
                acc -= MOD
            g[t] = acc
        p = A[u]
        gp = prod[p]
        if gp is None:
            prod[p] = g
        else:
            for t in range(1, M + 1):
                gp[t] = gp[t] * g[t] % MOD

    incycle = [indeg[i] > 0 for i in range(N)]

    ans = 1
    seen = [False] * N
    for start in range(N):
        if not incycle[start] or seen[start]:
            continue
        cyc = []
        v = start
        while not seen[v]:
            seen[v] = True
            cyc.append(v)
            v = A[v]
        acc = 0
        for t in range(1, M + 1):
            val = 1
            for c in cyc:
                h = prod[c]
                if h is not None:
                    val = val * h[t] % MOD
            acc += val
            if acc >= MOD:
                acc -= MOD
        ans = ans * acc % MOD

    print(ans)


if __name__ == "__main__":
    main()
