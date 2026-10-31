import sys
from collections import deque

MOD = 998244353


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    a = [int(x) - 1 for x in data[2:2 + n]]

    # functional graph: i -> a[i];  condition x_i <= x_{a[i]}
    # g[u][v] = product over already-processed children c of u of
    #           (sum_{w >= v+1} f[c][w])   (v is 0-based value -> value v+1)
    indeg = [0] * n
    for i in range(n):
        indeg[a[i]] += 1

    g = [[1] * m for _ in range(n)]
    dq = deque(i for i in range(n) if indeg[i] == 0)
    suf = [0] * (m + 1)
    while dq:
        u = dq.popleft()
        f = g[u]
        s = 0
        for v in range(m - 1, -1, -1):
            s += f[v]
            if s >= MOD:
                s -= MOD
            suf[v] = s
        gu = g[a[u]]
        for v in range(m):
            gu[v] = gu[v] * suf[v] % MOD
        indeg[a[u]] -= 1
        if indeg[a[u]] == 0:
            dq.append(a[u])

    visited = [False] * n
    ans = 1
    for st in range(n):
        if indeg[st] > 0 and not visited[st]:
            cyc = []
            u = st
            while not visited[u]:
                visited[u] = True
                cyc.append(u)
                u = a[u]
            # all cycle vertices must share the same value
            tot = 0
            for v in range(m):
                pr = 1
                for c in cyc:
                    pr = pr * g[c][v] % MOD
                tot += pr
            ans = ans * (tot % MOD) % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
