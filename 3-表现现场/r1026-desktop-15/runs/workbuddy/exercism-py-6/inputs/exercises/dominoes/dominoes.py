def can_chain(dominoes):
    dominoes = list(dominoes)
    if not dominoes:
        return []

    total = len(dominoes)
    used = [False] * total
    chain = []

    def search(end):
        if len(chain) == total:
            return chain[0][0] == chain[-1][1]
        for index, (left, right) in enumerate(dominoes):
            if used[index]:
                continue
            if left == end:
                fit = (left, right)
            elif right == end:
                fit = (right, left)
            else:
                continue
            used[index] = True
            chain.append(fit)
            if search(fit[1]):
                return True
            chain.pop()
            used[index] = False
        return False

    for index, (left, right) in enumerate(dominoes):
        for start in ((left, right), (right, left)):
            used[index] = True
            chain.append(start)
            if search(start[1]):
                return chain
            chain.pop()
            used[index] = False
    return None
