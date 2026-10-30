import sys
from collections import deque

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M = data[0], data[1]
    A = [x - 1 for x in data[2:2 + N]]

    f = [[1] * (M + 1) for _ in range(N)]
    indeg = [0] * N
    for i in range(N):
        indeg[A[i]] += 1

    q = deque(i for i in range(N) if indeg[i] == 0)
    while q:
        u = q.popleft()
        fu = f[u]
        g = [0] * (M + 1)
        s = 0
        for v in range(1, M + 1):
            s += fu[v]
            if s >= MOD:
                s -= MOD
            g[v] = s
        p = A[u]
        fp = f[p]
        for v in range(1, M + 1):
            fp[v] = fp[v] * g[v] % MOD
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    visited = [False] * N
    ans = 1
    for i in range(N):
        if indeg[i] > 0 and not visited[i]:
            cyc = []
            u = i
            while not visited[u]:
                visited[u] = True
                cyc.append(u)
                u = A[u]
            total = 0
            for v in range(1, M + 1):
                prod = 1
                for u in cyc:
                    prod = prod * f[u][v] % MOD
                total += prod
                if total >= MOD:
                    total -= MOD
            ans = ans * total % MOD
    print(ans)

if __name__ == "__main__":
    main()
