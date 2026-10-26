import sys
from collections import deque

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m = data[0], data[1]
    a = [x - 1 for x in data[2:2+n]]
    children = [[] for _ in range(n)]
    indeg = [0] * n
    for i, p in enumerate(a):
        children[p].append(i)
        indeg[p] += 1

    # acc[v][k] = product over already processed in-tree children c of v
    #             of (sum_{j<=k} g_c(j)), for k=1..m.
    # None means the all-ones vector.
    acc = [None] * n

    q = deque(i for i in range(n) if indeg[i] == 0)
    while q:
        v = q.popleft()
        gv = acc[v]
        # prefix sums of gv (or of the all-ones vector)
        if gv is None:
            pref = list(range(m + 1))
        else:
            pref = [0] * (m + 1)
            s = 0
            for k in range(1, m + 1):
                s += gv[k]
                if s >= MOD:
                    s -= MOD
                pref[k] = s
            acc[v] = None
        p = a[v]
        ap = acc[p]
        if ap is None:
            acc[p] = pref
        else:
            for k in range(1, m + 1):
                ap[k] = ap[k] * pref[k] % MOD
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    on_cycle = [indeg[i] > 0 for i in range(n)]
    visited = [False] * n
    ans = 1
    for s in range(n):
        if on_cycle[s] and not visited[s]:
            cyc = []
            v = s
            while not visited[v]:
                visited[v] = True
                cyc.append(v)
                v = a[v]
            # acc[v] is g_v (only non-cycle children were accumulated)
            prod = None
            for v in cyc:
                gv = acc[v]
                if gv is None:
                    continue
                if prod is None:
                    prod = gv[:]
                else:
                    for k in range(1, m + 1):
                        prod[k] = prod[k] * gv[k] % MOD
            if prod is None:
                total = m % MOD
            else:
                total = sum(prod[1:]) % MOD
            ans = ans * total % MOD
    print(ans)

if __name__ == "__main__":
    main()
