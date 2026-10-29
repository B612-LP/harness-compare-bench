import sys
from collections import deque

MOD = 998244353


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = [int(x) - 1 for x in data[2:2 + n]]

    indeg = [0] * n
    for v in A:
        indeg[v] += 1

    # Kahn peeling: remove non-cycle vertices (leaves of the in-trees first)
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    # acc[u] : array over c=1..m holding prod over processed children v of S_v[c]
    # (S_v[c] = sum_{k<=c} f_v[k]); None means no children processed yet.
    acc = [None] * n
    leaf = list(range(m + 1))  # S of a childless node: S[c] = c

    for u in order:
        a = acc[u]
        if a is None:
            S = leaf
        else:
            run = 0
            for c in range(1, m + 1):
                run += a[c]
                a[c] = run % MOD
            S = a
        p = A[u]
        ap = acc[p]
        if ap is None:
            ap = [0] + [1] * m
            acc[p] = ap
        for c in range(1, m + 1):
            ap[c] = ap[c] * S[c] % MOD
        acc[u] = None

    # remaining vertices with indeg>0 form disjoint cycles
    visited = [False] * n
    ans = 1
    for i in range(n):
        if indeg[i] > 0 and not visited[i]:
            cyc = []
            u = i
            while not visited[u]:
                visited[u] = True
                cyc.append(u)
                u = A[u]
            arrays = [acc[u] for u in cyc]
            total = 0
            for c in range(1, m + 1):
                pr = 1
                for f in arrays:
                    if f is not None:
                        pr = pr * f[c] % MOD
                total += pr
            ans = ans * (total % MOD) % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
