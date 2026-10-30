import sys
from collections import deque


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = [int(x) - 1 for x in data[2:2 + n]]
    MOD = 998244353

    indeg = [0] * n
    for i in range(n):
        indeg[A[i]] += 1

    # Kahn peeling: nodes left with indeg > 0 are exactly the cycle nodes.
    dq = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while dq:
        u = dq.popleft()
        order.append(u)
        v = A[u]
        indeg[v] -= 1
        if indeg[v] == 0:
            dq.append(v)

    in_cycle = [indeg[i] > 0 for i in range(n)]

    # non-cycle children of each node (reverse edges)
    child = [[] for _ in range(n)]
    for i in range(n):
        if not in_cycle[i]:
            child[A[i]].append(i)

    # f[u][j] = ways for the (non-cycle) subtree hanging at u, with x_u = j
    f = [None] * n

    def build(u):
        arr = [1] * (m + 1)
        for c in child[u]:
            fc = f[c]
            f[c] = None
            s = 0
            for j in range(1, m + 1):
                s += fc[j]
                if s >= MOD:
                    s -= MOD
                if s != 1:
                    arr[j] = arr[j] * s % MOD
        f[u] = arr

    for u in order:
        build(u)
    for u in range(n):
        if in_cycle[u]:
            build(u)

    ans = 1
    seen = [False] * n
    for s in range(n):
        if in_cycle[s] and not seen[s]:
            cyc = []
            u = s
            while not seen[u]:
                seen[u] = True
                cyc.append(u)
                u = A[u]
            # on a cycle all x values must be equal (x_1 <= x_2 <= ... <= x_1)
            total = 0
            first = cyc[0]
            prod = f[first][:]
            for v in cyc[1:]:
                fv = f[v]
                for j in range(1, m + 1):
                    prod[j] = prod[j] * fv[j] % MOD
            for j in range(1, m + 1):
                total += prod[j]
            ans = ans * (total % MOD) % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
