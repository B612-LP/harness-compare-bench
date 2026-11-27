"""Arithmetic for legal functional-graph shapes and named table-count formulas.

This does not load, run, compile, benchmark, or grade any archived program.
"""
import json
from collections import deque


def shapes(n):
    return {
        'chain': [*range(1, n), n - 1],
        'star': [n - 1] * n,
        'cycle': [*range(1, n), 0],
        'pairs': [u + 1 if u % 2 == 0 and u + 1 < n else u for u in range(n)],
    }


def invariant(parents):
    n = len(parents)
    count = [0] * n
    for p in parents:
        if not 0 <= p < n:
            raise ValueError('not a function on the vertex set')
        count[p] += 1
    q = deque(u for u, d in enumerate(count) if d == 0)
    depth = [1] * n
    removed = 0
    while q:
        u = q.popleft()
        removed += 1
        p = parents[u]
        depth[p] = max(depth[p], depth[u] + 1)
        count[p] -= 1
        if count[p] == 0:
            q.append(p)
    return {'peeled': removed, 'cycle_vertices': n - removed, 'max_tree_depth_inclusive': max(depth)}


def main():
    n = m = 2025
    graphs = {key: invariant(g) for key, g in shapes(n).items()}
    expected = {
        'chain': (n - 1, 1, n), 'star': (n - 1, 1, 2),
        'cycle': (0, n, 1), 'pairs': (n // 2, n - n // 2, 2),
    }
    for key, inf in graphs.items():
        got = tuple(inf[k] for k in ('peeled', 'cycle_vertices', 'max_tree_depth_inclusive'))
        if got != expected[key]:
            raise ValueError((key, got, expected[key]))
    rows = {
        'codex_container_point': (m + 1, [2, 2, 0, n // 2 + 1]),
        'dsh_build': (m, [g['peeled'] + 1 if g['peeled'] else 0 for g in graphs.values()]),
        'doubao_component_stage': (m + 1, [n + 1, 4, n, 4]),
        'yuanbao_allocate_and_peel': (m + 1, [n + 1, n + 1, n + 2, n + 1]),
    }
    out = {'n': n, 'm': m, 'shapes': graphs, 'accounting': {
        name: {'table_length': length, 'objects': dict(zip(graphs, owners)),
               'slots': {key: length * count for key, count in zip(graphs, owners)}}
        for name, (length, owners) in rows.items()},
        'warning': 'Arithmetic for proof-defined counts, not measured candidate memory.'}
    print(json.dumps(out, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
