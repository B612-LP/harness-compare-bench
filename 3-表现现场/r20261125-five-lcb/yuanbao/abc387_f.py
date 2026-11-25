import sys
from collections import deque

MOD = 998244353

def solve() -> None:
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    N = int(data[0]); M = int(data[1])
    A = [int(x) - 1 for x in data[2:2 + N]]

    orig_ch = [[] for _ in range(N)]
    for u, p in enumerate(A):
        orig_ch[p].append(u)
    indeg = [len(ch) for ch in orig_ch]
    q = deque(i for i, d in enumerate(indeg) if d == 0)
    on_cycle = [True] * N
    while q:
        u = q.popleft()
        on_cycle[u] = False
        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    children = [[] for _ in range(N)]
    parent = [-1] * N
    for u, p in enumerate(A):
        if on_cycle[u] and on_cycle[p]:
            parent[u] = -1
        else:
            parent[u] = p
            children[p].append(u)

    visited = [False] * N
    cycles = []
    for s in range(N):
        if on_cycle[s] and not visited[s]:
            cyc = []
            cur = s
            while not visited[cur]:
                visited[cur] = True
                cyc.append(cur)
                cur = A[cur]
            cycles.append(cyc)

    prod = [[1] * (M + 1) for _ in range(N)]
    cnt = [len(ch) for ch in children]
    q = deque(i for i, c in enumerate(cnt) if c == 0)
    while q:
        u = q.popleft()
        arr = prod[u]
        pref = [0] * (M + 1)
        run = 0
        for k in range(1, M + 1):
            run += arr[k]
            if run >= MOD:
                run -= MOD
            pref[k] = run
        p = parent[u]
        if p != -1:
            parr = prod[p]
            for k in range(1, M + 1):
                parr[k] = parr[k] * pref[k] % MOD
            cnt[p] -= 1
            if cnt[p] == 0:
                q.append(p)
            prod[u] = None
        else:
            prod[u] = arr

    ans = 1
    for cyc in cycles:
        comp = 0
        for v in range(1, M + 1):
            mul = 1
            for c in cyc:
                mul = mul * prod[c][v] % MOD
            comp += mul
            if comp >= MOD:
                comp -= MOD
        ans = ans * comp % MOD
    print(ans % MOD)

if __name__ == '__main__':
    solve()