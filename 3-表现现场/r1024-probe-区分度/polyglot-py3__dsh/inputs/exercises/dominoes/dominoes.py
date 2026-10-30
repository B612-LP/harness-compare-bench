def can_chain(dominoes):
    dominoes = list(dominoes)
    if not dominoes:
        return []

    n = len(dominoes)
    used = [False] * n

    def search(chain, end):
        if len(chain) == n:
            return chain if chain[0][0] == chain[-1][1] else None

        for index, (left, right) in enumerate(dominoes):
            if used[index]:
                continue
            if left == end:
                used[index] = True
                result = search(chain + [(left, right)], right)
                used[index] = False
                if result is not None:
                    return result
            elif right == end:
                used[index] = True
                result = search(chain + [(right, left)], left)
                used[index] = False
                if result is not None:
                    return result
        return None

    for index, (left, right) in enumerate(dominoes):
        for start in ((left, right), (right, left)):
            used[index] = True
            result = search([start], start[1])
            used[index] = False
            if result is not None:
                return result
    return None
