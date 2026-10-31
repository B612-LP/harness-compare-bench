from collections import defaultdict


def _is_connected(dominoes):
    graph = defaultdict(set)
    for a, b in dominoes:
        graph[a].add(b)
        graph[b].add(a)
    start = dominoes[0][0]
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbour in graph[node]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return all(a in seen and b in seen for a, b in dominoes)


def can_chain(dominoes):
    if not dominoes:
        return []
    if not _is_connected(dominoes):
        return None

    degree = defaultdict(int)
    for a, b in dominoes:
        degree[a] += 1
        degree[b] += 1
    if any(value % 2 for value in degree.values()):
        return None

    adjacency = defaultdict(list)
    for index, (a, b) in enumerate(dominoes):
        adjacency[a].append((b, index))
        adjacency[b].append((a, index))

    used = [False] * len(dominoes)
    stack = [dominoes[0][0]]
    path = []
    while stack:
        node = stack[-1]
        while adjacency[node] and used[adjacency[node][-1][1]]:
            adjacency[node].pop()
        if adjacency[node]:
            neighbour, index = adjacency[node].pop()
            used[index] = True
            stack.append(neighbour)
        else:
            path.append(stack.pop())
    path.reverse()

    remaining = list(dominoes)
    chain = []
    for left, right in zip(path, path[1:]):
        for index, (a, b) in enumerate(remaining):
            if (a, b) == (left, right):
                chain.append((a, b))
                remaining.pop(index)
                break
            if (a, b) == (right, left):
                chain.append((b, a))
                remaining.pop(index)
                break
        else:
            return None
    return chain
