import sys
from collections import deque

MOD = 998244353

def solve() -> None:
    input = sys.stdin.readline
    N, M = map(int, input().split())
    A = list(map(int, input().split()))
    A = [x - 1 for x in A]

    rev = [[] for _ in range(N)]
    indeg = [0] * N
    for i, p in enumerate(A):
        rev[p].append(i)
        indeg[p] += 1

    q = deque(i for i in range(N) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        v = A[u]
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)

    is_cycle = [False] * N
    for i in range(N):
        if indeg[i] > 0:
            is_cycle[i] = True

    dp = [None] * N

    for u in order:
        arr = [1] * (M + 1)
        for c in rev[u]:
            dpc = dp[c]
            s = 0
            for y in range(1, M + 1):
                s += dpc[y]
                if s >= MOD:
                    s -= MOD
                arr[y] = arr[y] * s % MOD
        dp[u] = arr

    for u in range(N):
        if not is_cycle[u]:
            continue
        arr = [1] * (M + 1)
        for c in rev[u]:
            if is_cycle[c]:
                continue
            dpc = dp[c]
            s = 0
            for y in range(1, M + 1):
                s += dpc[y]
                if s >= MOD:
                    s -= MOD
                arr[y] = arr[y] * s % MOD
        dp[u] = arr

    visited = [False] * N
    ans = 1

    for i in range(N):
        if not is_cycle[i] or visited[i]:
            continue

        cyc = []
        u = i
        while not visited[u]:
            visited[u] = True
            cyc.append(u)
            u = A[u]

        comp = 0
        for y in range(1, M + 1):
            prod = 1
            for u in cyc:
                prod = prod * dp[u][y] % MOD
            comp += prod
            if comp >= MOD:
                comp -= MOD

        ans = ans * comp % MOD

    print(ans)


if __name__ == "__main__":
    solve()
