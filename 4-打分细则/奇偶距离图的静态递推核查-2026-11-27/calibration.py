"""Pure math calibration: no program or archived output is read or executed."""
from collections import Counter
from itertools import combinations
from math import comb


def exhaustive_graphs(n):
    """Literally build simple graphs, then use BFS distances from vertex 0."""
    edge_universe = list(combinations(range(n), 2))
    counts = Counter()
    for m in range(n - 1, len(edge_universe) + 1):
        for edges in combinations(edge_universe, m):
            neighbors = [[] for _ in range(n)]
            for u, v in edges:
                neighbors[u].append(v)
                neighbors[v].append(u)
            queue = [0]
            dist = {0: 0}
            for u in queue:
                for v in neighbors[u]:
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        queue.append(v)
            if len(dist) == n and sum(x % 2 == 0 for x in dist.values()) == n // 2:
                counts[m] += 1
    return [counts[m] for m in range(n - 1, len(edge_universe) + 1)]


def multiply(a, b):
    out = Counter()
    for i, x in a.items():
        for j, y in b.items():
            out[i + j] += x * y
    return out


def layer_compositions(n):
    """Distinct mathematical derivation: explicitly sum ordered layers, no DP."""
    total = Counter()

    def visit(sizes, remaining, even, labels, poly):
        if not remaining:
            if even == n // 2:
                for m, count in poly.items():
                    total[m] += labels * count
            return
        prev = sizes[-1]
        for nxt in range(1, remaining + 1):
            internal = comb(nxt, 2)
            transition = Counter({m: comb(internal, m) for m in range(internal + 1)})
            for _ in range(nxt):
                transition = multiply(transition, {m: comb(prev, m) for m in range(1, prev + 1)})
            visit(sizes + [nxt], remaining - nxt, even + nxt * (len(sizes) % 2 == 0),
                  labels * comb(remaining, nxt), multiply(poly, transition))

    visit([1], n - 1, 1, 1, {0: 1})
    return [total[m] for m in range(n - 1, comb(n, 2) + 1)]


def main():
    for n in (2, 4, 6):
        direct = exhaustive_graphs(n)
        layer = layer_compositions(n)
        if direct != layer:
            raise RuntimeError(f'abstract graph identity mismatch at n={n}')
        print(f'n={n} nonnegative BFS versus layer counts: {direct}')
    p = 10**9
    lane = 2**72
    bounds = [407*(p-1)**2, 29*(p-1), 30*29*(p-1)]
    if not all(0 < bound < lane for bound in bounds) or not 1340 < 10**8:
        raise RuntimeError('lane or inversion bound violation')
    print('lane, convolution, target sum, final sum:', lane, *bounds)
    print('max factorial index:', 1340)


if __name__ == '__main__':
    main()
