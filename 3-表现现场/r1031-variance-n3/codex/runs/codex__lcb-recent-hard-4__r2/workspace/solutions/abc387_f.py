import sys
from array import array
from collections import deque


MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m = data[0], data[1]
    parent = [x - 1 for x in data[2:2 + n]]

    children = [[] for _ in range(n)]
    indeg = [0] * n
    for u, p in enumerate(parent):
        children[p].append(u)
        indeg[p] += 1

    queue = deque(u for u in range(n) if indeg[u] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        p = parent[u]
        indeg[p] -= 1
        if indeg[p] == 0:
            queue.append(p)

    in_cycle = [d > 0 for d in indeg]
    prefix = [None] * n

    # prefix[u][v] = sum_{w=1..v} (ways in u's subtree when x_u = w)
    for u in order:
        ch = children[u]
        if not ch:
            prefix[u] = array('I', range(m + 1))
            continue

        prod = array('I', prefix[ch[0]])
        for c in ch[1:]:
            pc = prefix[c]
            for v in range(1, m + 1):
                prod[v] = prod[v] * pc[v] % MOD

        cur = array('I', [0]) * (m + 1)
        total = 0
        for v in range(1, m + 1):
            total += prod[v]
            if total >= MOD:
                total -= MOD
            cur[v] = total
        prefix[u] = cur

    answer = 1
    visited = [False] * n
    for start in range(n):
        if not in_cycle[start] or visited[start]:
            continue

        cycle = []
        u = start
        while not visited[u]:
            visited[u] = True
            cycle.append(u)
            u = parent[u]

        ways = [1] * (m + 1)
        for c in cycle:
            for ch in children[c]:
                if in_cycle[ch]:
                    continue
                pc = prefix[ch]
                for v in range(1, m + 1):
                    ways[v] = ways[v] * pc[v] % MOD

        component = sum(ways[1:]) % MOD
        answer = answer * component % MOD

    print(answer)


if __name__ == "__main__":
    main()
