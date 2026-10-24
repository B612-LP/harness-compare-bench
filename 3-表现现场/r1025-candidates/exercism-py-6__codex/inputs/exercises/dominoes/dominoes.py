def can_chain(dominoes):
    if not dominoes:
        return []

    degree = {}
    adjacency = {}
    for index, (left, right) in enumerate(dominoes):
        degree[left] = degree.get(left, 0) + 1
        degree[right] = degree.get(right, 0) + 1
        adjacency.setdefault(left, []).append((index, right))
        adjacency.setdefault(right, []).append((index, left))

    if any(value % 2 for value in degree.values()):
        return None

    start = dominoes[0][0]
    connected = {start}
    pending = [start]
    while pending:
        vertex = pending.pop()
        for _, neighbor in adjacency[vertex]:
            if neighbor not in connected:
                connected.add(neighbor)
                pending.append(neighbor)

    if len(connected) != len(degree):
        return None

    used = set()
    trail = []

    def visit(vertex):
        while adjacency[vertex]:
            edge_index, neighbor = adjacency[vertex].pop()
            if edge_index in used:
                continue
            used.add(edge_index)
            visit(neighbor)
            trail.append((vertex, neighbor))

    visit(start)
    if len(used) != len(dominoes):
        return None

    trail.reverse()
    return trail
