import sys
from collections import deque


MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n, m = data[0], data[1]
    parent = [x - 1 for x in data[2:2 + n]]

    indeg = [0] * n
    for v in range(n):
        indeg[parent[v]] += 1

    queue = deque(v for v in range(n) if indeg[v] == 0)
    order = []
    while queue:
        v = queue.popleft()
        order.append(v)
        p = parent[v]
        indeg[p] -= 1
        if indeg[p] == 0:
            queue.append(p)

    dp = [[1] * (m + 1) for _ in range(n)]

    for v in order:
        row = dp[v]
        total = 0
        for value in range(1, m + 1):
            total += row[value]
            if total >= MOD:
                total -= MOD
            row[value] = total

        parent_row = dp[parent[v]]
        for value in range(1, m + 1):
            parent_row[value] = parent_row[value] * row[value] % MOD

    visited = [False] * n
    answer = 1

    for start in range(n):
        if indeg[start] == 0 or visited[start]:
            continue

        cycle = []
        v = start
        while not visited[v]:
            visited[v] = True
            cycle.append(v)
            v = parent[v]

        product = [1] * (m + 1)
        for v in cycle:
            row = dp[v]
            for value in range(1, m + 1):
                product[value] = product[value] * row[value] % MOD

        answer = answer * (sum(product[1:]) % MOD) % MOD

    print(answer)


if __name__ == "__main__":
    main()
