import sys
from collections import deque
from array import array

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M = data[0], data[1]
    A = [0] + data[2:2 + N]

    indeg = [0] * (N + 1)
    for i in range(1, N + 1):
        indeg[A[i]] += 1

    q = deque(i for i in range(1, N + 1) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        v = A[u]
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)

    h = [None] * (N + 1)
    base = array('I', [1]) * (M + 1)
    for i in range(1, N + 1):
        h[i] = array('I', base)

    for u in order:
        hu = h[u]
        f = [0] * (M + 1)
        s = 0
        for c in range(1, M + 1):
            s += hu[c]
            if s >= MOD:
                s -= MOD
            f[c] = s
        p = A[u]
        hp = h[p]
        for c in range(1, M + 1):
            hp[c] = (hp[c] * f[c]) % MOD
        h[u] = None

    ans = 1
    visited = [False] * (N + 1)
    for i in range(1, N + 1):
        if indeg[i] > 0 and not visited[i]:
            cyc = []
            u = i
            while not visited[u]:
                visited[u] = True
                cyc.append(u)
                u = A[u]
            total = 0
            for c in range(1, M + 1):
                prod = 1
                for u in cyc:
                    prod = (prod * h[u][c]) % MOD
                total += prod
            ans = (ans * (total % MOD)) % MOD

    print(ans % MOD)

if __name__ == '__main__':
    main()
