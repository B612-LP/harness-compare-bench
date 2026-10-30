def can_chain(dominoes):
    if not dominoes:
        return []

    dominoes = [tuple(domino) for domino in dominoes]
    used = [False] * len(dominoes)
    chain = []

    def search(current, remaining):
        if remaining == 0:
            return chain[0][0] == current

        for index, domino in enumerate(dominoes):
            if used[index]:
                continue

            for oriented in ((domino[0], domino[1]), (domino[1], domino[0])):
                if oriented[0] != current:
                    continue
                used[index] = True
                chain.append(oriented)
                if search(oriented[1], remaining - 1):
                    return True
                chain.pop()
                used[index] = False
                if domino[0] == domino[1]:
                    break

        return False

    first = dominoes[0]
    orientations = ((first[0], first[1]), (first[1], first[0]))
    for start in orientations:
        used[0] = True
        chain = [start]
        if search(start[1], len(dominoes) - 1):
            return chain
        used[0] = False
        if first[0] == first[1]:
            break

    return None
