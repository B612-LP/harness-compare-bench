import sys
from array import array
from collections import deque

MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    N, M = data[0], data[1]
    A = [v - 1 for v in data[2:2 + N]]

    children = [[] for _ in range(N)]
    indeg = [0] * N
    for i in range(N):
        p = A[i]
        children[p].append(i)
        indeg[p] += 1

    # pref[u][v] = number of assignments in subtree of u (u fixed at a value
    # <= v); prefix sums of g(u, v) over v = 1..M.
    pref = [None] * N
    leaf_pref = array('I', [0])
    leaf_pref.extend(range(1, M + 1))

    dq = deque(i for i in range(N) if indeg[i] == 0)
    order = []
    while dq:
        u = dq.popleft()
        order.append(u)
        p = A[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            dq.append(p)

    is_cycle = [indeg[i] > 0 for i in range(N)]

    for u in order:
        ch = children[u]
        if not ch:
            pref[u] = array('I', leaf_pref)
        else:
            cur = array('I', [0]) * (M + 1)
            s = 0
            for v in range(1, M + 1):
                val = 1
                for c in ch:
                    val = val * pref[c][v] % MOD
                s = (s + val) % MOD
                cur[v] = s
            pref[u] = cur
            for c in ch:
                pref[c] = None

    # cycle nodes: hanging (non-cycle) children
    for u in range(N):
        if is_cycle[u]:
            hc = [c for c in children[u] if not is_cycle[c]]
            if not hc:
                pref[u] = array('I', leaf_pref)
            else:
                cur = array('I', [0]) * (M + 1)
                s = 0
                for v in range(1, M + 1):
                    val = 1
                    for c in hc:
                        val = val * pref[c][v] % MOD
                    s = (s + val) % MOD
                    cur[v] = s
                pref[u] = cur
                for c in hc:
                    pref[c] = None

    ans = 1
    seen = [False] * N
    for start in range(N):
        if is_cycle[start] and not seen[start]:
            cyc = []
            u = start
            while not seen[u]:
                seen[u] = True
                cyc.append(u)
                u = A[u]
            total = 0
            prev = 0
            for v in range(1, M + 1):
                val = 1
                for c in cyc:
                    gv = pref[c][v] - pref[c][v - 1]
                    if gv < 0:
                        gv += MOD
                    val = val * gv % MOD
                total = (total + val) % MOD
            ans = ans * total % MOD

    print(ans)


if __name__ == '__main__':
    main()
