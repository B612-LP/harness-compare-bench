def can_chain(dominoes):
    dominoes = [tuple(domino) for domino in dominoes]
    if not dominoes:
        return []

    used = [False] * len(dominoes)
    chain = []

    def build(start):
        used[0] = True
        chain.append((start[0], start[1]))
        if walk(start[1]):
            return True
        chain.pop()
        used[0] = False
        return False

    def walk(end):
        if len(chain) == len(dominoes):
            return chain[0][0] == end
        for index, (left, right) in enumerate(dominoes):
            if used[index]:
                continue
            if left == end:
                used[index] = True
                chain.append((left, right))
                if walk(right):
                    return True
                chain.pop()
                used[index] = False
            if right == end and right != left:
                used[index] = True
                chain.append((right, left))
                if walk(left):
                    return True
                chain.pop()
                used[index] = False
        return False

    # Every domino can serve as the starting point of the loop.
    for index in range(len(dominoes)):
        dominoes[0], dominoes[index] = dominoes[index], dominoes[0]
        chain.clear()
        used = [False] * len(dominoes)
        if build(dominoes[0]):
            return list(chain)

    return None
