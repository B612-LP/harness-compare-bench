import sys
from collections import deque

MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m = data[0], data[1]
    a = [x - 1 for x in data[2:2 + n]]

    # f[v][k] = number of ways in the subtree rooted at v (tree edges only)
    # when x_v = k.  Index k runs from 0..m (0 is unused).
    f = [[1] * (m + 1) for _ in range(n)]
    indeg = [0] * n
    for v in a:
        indeg[v] += 1

    q = deque(i for i in range(n) if indeg[i] == 0)
    while q:
        v = q.popleft()
        fv = f[v]
        pref = [0] * (m + 1)
        s = 0
        for k in range(1, m + 1):
            s += fv[k]
            if s >= MOD:
                s -= MOD
            pref[k] = s
        p = a[v]
        fp = f[p]
        for k in range(1, m + 1):
            fp[k] = fp[k] * pref[k] % MOD
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    # Remaining vertices form directed cycles.
    visited = [False] * n
    ans = 1
    for start in range(n):
        if indeg[start] == 0 or visited[start]:
            continue
        cyc = []
        v = start
        while not visited[v]:
            visited[v] = True
            cyc.append(v)
            v = a[v]
        total = [0] * (m + 1)
        for k in range(1, m + 1):
            prod = 1
            for u in cyc:
                prod = prod * f[u][k] % MOD
            total[k] = prod
        s = 0
        for k in range(1, m + 1):
            s += total[k]
            if s >= MOD:
                s -= MOD
        ans = ans * (s % MOD) % MOD

    print(ans % MOD)


if __name__ == "__main__":
    main()
