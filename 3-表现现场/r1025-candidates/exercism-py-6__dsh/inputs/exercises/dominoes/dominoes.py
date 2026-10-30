def can_chain(dominoes):
    dominoes = list(dominoes)
    if not dominoes:
        return []

    count = len(dominoes)

    def search(chain, right, used):
        if len(chain) == count:
            return chain if chain[0][0] == chain[-1][1] else None
        for index, (a, b) in enumerate(dominoes):
            if used[index]:
                continue
            if a == right:
                used[index] = True
                result = search(chain + [(a, b)], b, used)
                if result is not None:
                    return result
                used[index] = False
            if b == right and b != a:
                used[index] = True
                result = search(chain + [(b, a)], a, used)
                if result is not None:
                    return result
                used[index] = False
        return None

    first = dominoes[0]
    orientations = [(first[0], first[1])]
    if first[1] != first[0]:
        orientations.append((first[1], first[0]))
    for orientation in orientations:
        used = [False] * count
        used[0] = True
        result = search([orientation], orientation[1], used)
        if result is not None:
            return result
    return None
