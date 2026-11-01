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
    for v in A:
        indeg[v] += 1

    q = deque(i for i in range(N) if indeg[i] == 0)
    h = [[1] * (M + 1) for _ in range(N)]

    while q:
        u = q.popleft()
        arr = h[u]
        par = A[u]
        hp = h[par]

        run = 0
        for c in range(1, M + 1):
            run += arr[c]
            if run >= MOD:
                run -= MOD
            hp[c] = hp[c] * run % MOD

        indeg[par] -= 1
        if indeg[par] == 0:
            q.append(par)

    ans = 1
    visited = [False] * N

    for i in range(N):
        if indeg[i] > 0 and not visited[i]:
            cycle = []
            v = i
            while not visited[v]:
                visited[v] = True
                cycle.append(v)
                v = A[v]

            total = 0
            for c in range(1, M + 1):
                prod = 1
                for v in cycle:
                    prod = prod * h[v][c] % MOD
                total += prod
                if total >= MOD:
                    total -= MOD

            ans = ans * total % MOD

    print(ans)


if __name__ == "__main__":
    solve()
