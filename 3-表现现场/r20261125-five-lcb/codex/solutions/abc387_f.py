import sys
from collections import deque


def main():
    input = sys.stdin.buffer.readline
    n, m = map(int, input().split())
    a = list(map(int, input().split()))
    a = [x - 1 for x in a]
    mod = 998244353

    indeg = [0] * n
    for v in a:
        indeg[v] += 1

    q = deque(i for i in range(n) if indeg[i] == 0)

    agg = [None] * n
    leaf_pref_cache = None

    while q:
        u = q.popleft()
        arr = agg[u]
        if arr is None:
            if leaf_pref_cache is None:
                leaf_pref_cache = [0] + list(range(1, m + 1))
            pref = leaf_pref_cache.copy()
        else:
            pref = arr
            s = 0
            for k in range(1, m + 1):
                s += pref[k]
                if s >= mod:
                    s -= mod
                pref[k] = s
            pref[0] = 0

        p = a[u]
        if agg[p] is None:
            agg[p] = pref
        else:
            cur = agg[p]
            for k in range(1, m + 1):
                cur[k] = cur[k] * pref[k] % mod

        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    visited = [False] * n
    answer = 1

    for s in range(n):
        if indeg[s] == 0 or visited[s]:
            continue

        cycle = []
        v = s
        while not visited[v]:
            visited[v] = True
            cycle.append(v)
            v = a[v]

        prod = [1] * (m + 1)
        for v in cycle:
            arr = agg[v]
            if arr is not None:
                for k in range(1, m + 1):
                    prod[k] = prod[k] * arr[k] % mod

        answer = answer * (sum(prod[1:]) % mod) % mod

    print(answer)


if __name__ == "__main__":
    main()
