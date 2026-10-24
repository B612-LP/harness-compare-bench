import sys
from collections import deque


MOD = 998244353


def main() -> None:
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m = data[0], data[1]
    a = [x - 1 for x in data[2:2 + n]]

    indeg = [0] * n
    for v in a:
        indeg[v] += 1

    # dp[v][x] is the product of prefix sums from v's already removed
    # (non-cycle) children.  For a removed vertex it becomes its prefix sum.
    dp = [[1] * (m + 1) for _ in range(n)]
    queue = deque(i for i in range(n) if indeg[i] == 0)

    while queue:
        v = queue.popleft()
        row = dp[v]
        acc = 0
        for x in range(1, m + 1):
            acc += row[x]
            if acc >= MOD:
                acc -= MOD
            row[x] = acc

        p = a[v]
        parent_row = dp[p]
        for x in range(1, m + 1):
            parent_row[x] = parent_row[x] * row[x] % MOD

        indeg[p] -= 1
        if indeg[p] == 0:
            queue.append(p)

    visited = [False] * n
    answer = 1

    for start in range(n):
        if indeg[start] == 0 or visited[start]:
            continue

        product = [1] * (m + 1)
        v = start
        while not visited[v]:
            visited[v] = True
            row = dp[v]
            for x in range(1, m + 1):
                product[x] = product[x] * row[x] % MOD
            v = a[v]

        component = sum(product[1:]) % MOD
        answer = answer * component % MOD

    print(answer)


if __name__ == "__main__":
    main()
