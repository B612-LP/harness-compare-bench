import sys
from collections import deque


MOD = 998244353


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m = data[0], data[1]
    parent = [x - 1 for x in data[2:2 + n]]

    indegree = [0] * n
    for v in parent:
        indegree[v] += 1

    queue = deque(i for i in range(n) if indegree[i] == 0)
    order = []
    while queue:
        v = queue.popleft()
        order.append(v)
        to = parent[v]
        indegree[to] -= 1
        if indegree[to] == 0:
            queue.append(to)

    products = [None] * n

    for v in order:
        poly = products[v]
        if poly is None:
            poly = list(range(1, m + 1))
        else:
            products[v] = None
            total = 0
            for i in range(m):
                total += poly[i]
                if total >= MOD:
                    total -= MOD
                poly[i] = total

        to = parent[v]
        current = products[to]
        if current is None:
            products[to] = poly
        else:
            for i in range(m):
                current[i] = current[i] * poly[i] % MOD

    answer = 1
    visited = [False] * n

    for start in range(n):
        if indegree[start] == 0 or visited[start]:
            continue

        component = None
        v = start
        while not visited[v]:
            visited[v] = True
            poly = products[v]
            if poly is None:
                if component is None:
                    component = [1] * m
            elif component is None:
                component = poly
            else:
                for i in range(m):
                    component[i] = component[i] * poly[i] % MOD
            v = parent[v]

        answer = answer * (sum(component) % MOD) % MOD

    print(answer)


if __name__ == "__main__":
    main()
