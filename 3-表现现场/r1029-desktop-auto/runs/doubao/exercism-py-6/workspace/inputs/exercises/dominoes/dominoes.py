def can_chain(dominoes):
    if not dominoes:
        return []

    # Fix the first domino (as given); any valid chain can be rotated and
    # reversed so that it starts here.
    first = dominoes[0]
    remaining = dominoes[1:]

    def search(chain, right, pool):
        if not pool:
            return chain if chain[0][0] == right else None
        for i, (a, b) in enumerate(pool):
            if a == right:
                piece = (a, b)
            elif b == right:
                piece = (b, a)
            else:
                continue
            result = search(
                chain + [piece],
                piece[1],
                pool[:i] + pool[i + 1:],
            )
            if result is not None:
                return result
        return None

    return search([first], first[1], remaining)
