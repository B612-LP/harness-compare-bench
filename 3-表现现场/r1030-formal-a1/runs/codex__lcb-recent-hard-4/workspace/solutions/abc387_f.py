import sys
from collections import deque


MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m = data[0], data[1]
    parent = [x - 1 for x in data[2:2 + n]]

    indeg = [0] * n
    children = [[] for _ in range(n)]
    for v, p in enumerate(parent):
        indeg[p] += 1
        children[p].append(v)

    queue = deque(v for v in range(n) if indeg[v] == 0)
    order = []
    while queue:
        v = queue.popleft()
        order.append(v)
        p = parent[v]
        indeg[p] -= 1
        if indeg[p] == 0:
            queue.append(p)

    # f[v][t] = number of assignments in v's subtree with x_v <= t.
    f = [None] * n
    for v in order:
        ch = children[v]
        if not ch:
            f[v] = list(range(m + 1))
            continue

        arr = [0] * (m + 1)
        cumulative = 0
        for t in range(1, m + 1):
            product = 1
            for c in ch:
                product = product * f[c][t] % MOD
            cumulative += product
            if cumulative >= MOD:
                cumulative -= MOD
            arr[t] = cumulative
        f[v] = arr

    # For a cycle vertex v, g[v][t] counts the attached trees when x_v = t.
    g = [None] * n
    for v in range(n):
        if indeg[v] == 0:
            continue
        arr = [1] * (m + 1)
        for c in children[v]:
            if f[c] is not None:
                fc = f[c]
                for t in range(1, m + 1):
                    arr[t] = arr[t] * fc[t] % MOD
        g[v] = arr

    seen = [False] * n
    answer = 1
    for start in range(n):
        if indeg[start] == 0 or seen[start]:
            continue

        cycle = []
        v = start
        while not seen[v]:
            seen[v] = True
            cycle.append(v)
            v = parent[v]

        component = 0
        for t in range(1, m + 1):
            ways = 1
            for v in cycle:
                ways = ways * g[v][t] % MOD
            component += ways
        answer = answer * (component % MOD) % MOD

    print(answer)


if __name__ == "__main__":
    main()
