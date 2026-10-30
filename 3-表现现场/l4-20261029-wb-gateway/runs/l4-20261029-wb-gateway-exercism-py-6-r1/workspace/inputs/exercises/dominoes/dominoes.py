def can_chain(dominoes):
    dominoes = [tuple(domino) for domino in dominoes]
    if not dominoes:
        return []

    count = len(dominoes)
    used = [False] * count
    chain = []

    def orient(domino):
        if domino[0] == domino[1]:
            return [domino]
        return [domino, (domino[1], domino[0])]

    def backtrack(end):
        if len(chain) == count:
            return chain[0][0] == end
        for index, domino in enumerate(dominoes):
            if used[index]:
                continue
            for piece in orient(domino):
                if piece[0] != end:
                    continue
                used[index] = True
                chain.append(piece)
                if backtrack(piece[1]):
                    return True
                chain.pop()
                used[index] = False
        return False

    for index, domino in enumerate(dominoes):
        for piece in orient(domino):
            used[index] = True
            chain.append(piece)
            if backtrack(piece[1]):
                return chain
            chain.pop()
            used[index] = False

    return None
