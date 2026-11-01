from collections import defaultdict


def can_chain(dominoes):
    if not dominoes:
        return []

    edges = [tuple(d) for d in dominoes]
    adj = defaultdict(list)
    degree = defaultdict(int)

    for idx, (a, b) in enumerate(edges):
        adj[a].append((b, idx))
        adj[b].append((a, idx))
        degree[a] += 1
        degree[b] += 1

    for d in degree.values():
        if d % 2 == 1:
            return None

    start = next(iter(degree))
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for w, _ in adj[v]:
            if w not in seen:
                seen.add(w)
                stack.append(w)

    if set(degree) - seen:
        return None

    adj2 = {v: list(edges_list) for v, edges_list in adj.items()}
    used = set()
    circuit = []

    def dfs(v):
        while adj2[v]:
            w, edge_id = adj2[v].pop()
            if edge_id not in used:
                used.add(edge_id)
                dfs(w)
                circuit.append(edge_id)

    dfs(start)
    circuit.reverse()

    result = []
    current = start
    for edge_id in circuit:
        a, b = edges[edge_id]
        if a == current:
            result.append((a, b))
            current = b
        elif b == current:
            result.append((b, a))
            current = a
        else:
            return None

    if current != start:
        return None
    return result
