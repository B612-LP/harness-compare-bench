import sys
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

    # functional graph: i -> A[i]; condition x_i <= x_{A[i]}
    indeg = [0] * (n + 1)
    for i in range(1, n + 1):
        indeg[A[i]] += 1

    # acc[v][k] = product over already-processed children c of S_c[k]
    # where S_c[k] = sum_{j<=k} dp[c][j]
    acc = [None] * (n + 1)
    done = [False] * (n + 1)

    q = deque(i for i in range(1, n + 1) if indeg[i] == 0)
    ones = None
    while q:
        v = q.popleft()
        d = acc[v]
        if d is None:
            d = [1] * (m + 1)
        p = A[v]
        ap = acc[p]
        if ap is None:
            ap = [1] * (m + 1)
            acc[p] = ap
        s = 0
        for k in range(1, m + 1):
            s += d[k]
            if s >= MOD:
                s -= MOD
            ap[k] = ap[k] * s % MOD
        acc[v] = None
        done[v] = True
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    ans = 1
    seen = [False] * (n + 1)
    for st in range(1, n + 1):
        if done[st] or seen[st]:
            continue
        cyc = []
        v = st
        while not seen[v]:
            seen[v] = True
            cyc.append(v)
            v = A[v]
        # cycle values must all be equal
        arrs = []
        for v in cyc:
            d = acc[v]
            if d is None:
                d = [1] * (m + 1)
            arrs.append(d)
        total = 0
        if len(arrs) == 1:
            d0 = arrs[0]
            total = sum(d0[1:m + 1]) % MOD
        else:
            L = len(arrs)
            for k in range(1, m + 1):
                pr = 1
                for arr in arrs:
                    pr = pr * arr[k] % MOD
                total += pr
            total %= MOD
        ans = ans * total % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
