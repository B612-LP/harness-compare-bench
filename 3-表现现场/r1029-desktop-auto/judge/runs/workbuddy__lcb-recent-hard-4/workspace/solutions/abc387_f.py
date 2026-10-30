import sys
from itertools import accumulate
from collections import deque

MOD = 998244353


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = [0] * (n + 1)
    for i in range(1, n + 1):
        A[i] = int(data[1 + i])

    # indegree of the functional graph, for Kahn peeling (leaves -> cycle)
    indeg = [0] * (n + 1)
    for i in range(1, n + 1):
        indeg[A[i]] += 1

    q = deque(i for i in range(1, n + 1) if indeg[i] == 0)
    order = []
    while q:
        v = q.popleft()
        order.append(v)
        p = A[v]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    # dp[v][j] = #ways for the tree hanging at v (v included) with x_v = j
    # dp[v] is None while still "all ones", i.e. no child processed yet.
    dp = [None] * (n + 1)
    leaf_pref = list(range(m + 1))  # prefix sums of all-ones = j

    for v in order:
        arr = dp[v]
        if arr is None:
            pref = leaf_pref
        else:
            # prefix sums over j = 1..m  (pref[0] = 0)
            pref = [x % MOD for x in accumulate(arr[1:], initial=0)]
            dp[v] = None
        p = A[v]
        cur = dp[p]
        if cur is None:
            # pref is only read afterwards (products build fresh lists), so aliasing is safe
            dp[p] = pref
        else:
            dp[p] = [(x * y) % MOD for x, y in zip(cur, pref)]

    visited = [False] * (n + 1)
    ans = 1
    for v in range(1, n + 1):
        if indeg[v] > 0 and not visited[v]:
            # collect the cycle containing v
            cyc = []
            u = v
            while not visited[u]:
                visited[u] = True
                cyc.append(u)
                u = A[u]
            total = None
            for c in cyc:
                d = dp[c]
                if d is None:
                    continue
                if total is None:
                    total = d
                else:
                    total = [(x * y) % MOD for x, y in zip(total, d)]
            if total is None:
                s = m % MOD
            else:
                s = sum(total[1:]) % MOD
            ans = ans * s % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
