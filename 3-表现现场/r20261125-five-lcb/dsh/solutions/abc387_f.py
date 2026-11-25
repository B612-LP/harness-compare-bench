import sys

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m = data[0], data[1]
    a = [x - 1 for x in data[2:2+n]]

    rev = [[] for _ in range(n)]
    indeg = [0] * n
    for i, p in enumerate(a):
        rev[p].append(i)
        indeg[p] += 1

    # Kahn removal: leaves first.  The nodes left are exactly cycle nodes.
    from collections import deque
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    in_cycle = [True] * n
    while q:
        v = q.popleft()
        in_cycle[v] = False
        order.append(v)
        p = a[v]
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)

    # pref[v][k] = sum_{t=0..k} f_v(t), where f_v(t) is the number of
    # assignments of v's subtree when x_v = t+1.
    pref = [None] * n
    for v in order:
        arr = [1] * m
        for c in rev[v]:
            pc = pref[c]
            for k in range(m):
                arr[k] = arr[k] * pc[k] % MOD
        p = [0] * m
        s = 0
        for k in range(m):
            s += arr[k]
            if s >= MOD:
                s -= MOD
            p[k] = s
        pref[v] = p

    ans = 1
    seen_cycle = [False] * n
    for start in range(n):
        if in_cycle[start] and not seen_cycle[start]:
            cyc = []
            v = start
            while not seen_cycle[v]:
                seen_cycle[v] = True
                cyc.append(v)
                v = a[v]
            # All cycle values must be equal.
            total = 0
            for k in range(m):
                prod = 1
                for c in cyc:
                    g = 1
                    for ch in rev[c]:
                        if not in_cycle[ch]:
                            g = g * pref[ch][k] % MOD
                    prod = prod * g % MOD
                total += prod
            ans = ans * (total % MOD) % MOD

    print(ans % MOD)

if __name__ == "__main__":
    main()
