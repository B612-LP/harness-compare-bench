import sys

MOD = 998244353


def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    m = int(data[1])
    A = [int(data[2 + i]) - 1 for i in range(n)]

    rev = [[] for _ in range(n)]
    for i in range(n):
        rev[A[i]].append(i)

    # detect cycles in functional graph
    state = [0] * n  # 0 unvisited, 1 on current path, 2 finished
    incycle = [False] * n
    pre = [-1] * n
    cycles = []
    for start in range(n):
        if state[start] != 0:
            continue
        path = []
        v = start
        while state[v] == 0:
            state[v] = 1
            path.append(v)
            v = A[v]
        if state[v] == 1:
            idx = len(path) - 1
            while path[idx] != v:
                idx -= 1
            cyc = path[idx:]
            cycles.append(cyc)
            k = len(cyc)
            for j in range(k):
                b = cyc[j]
                incycle[b] = True
                pre[b] = cyc[j - 1]
        for u in path:
            state[u] = 2

    children = [[] for _ in range(n)]
    for v in range(n):
        pv = pre[v]
        if pv == -1:
            children[v] = rev[v]
        else:
            children[v] = [u for u in rev[v] if u != pv]

    sys.setrecursionlimit(10000)

    def compute(v):
        # returns pref array (tree node) or dp values (cycle node)
        prod = [1] * (m + 1)
        for u in children[v]:
            pu = compute(u)
            for c in range(1, m + 1):
                prod[c] = prod[c] * pu[c] % MOD
        if incycle[v]:
            return prod
        pref = [0] * (m + 1)
        run = 0
        for c in range(1, m + 1):
            run += prod[c]
            if run >= MOD:
                run -= MOD
            pref[c] = run
        return pref

    ans = 1
    for cyc in cycles:
        prods = [compute(v) for v in cyc]
        total = 0
        for c in range(1, m + 1):
            t = 1
            for pd in prods:
                t = t * pd[c] % MOD
            total += t
        ans = ans * (total % MOD) % MOD

    sys.stdout.write(str(ans % MOD) + "\n")


main()
