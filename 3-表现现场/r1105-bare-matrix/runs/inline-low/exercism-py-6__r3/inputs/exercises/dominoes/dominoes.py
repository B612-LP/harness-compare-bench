def can_chain(dominoes):
    if not dominoes:
        return []

    n = len(dominoes)
    used = [False] * n
    chain = []

    def search(start, end, count):
        if count == n:
            return start == end
        for i, (a, b) in enumerate(dominoes):
            if used[i]:
                continue
            for x, y in ((a, b), (b, a)):
                if x == end:
                    used[i] = True
                    chain.append((x, y))
                    if search(start, y, count + 1):
                        return True
                    chain.pop()
                    used[i] = False
        return False

    for i, (a, b) in enumerate(dominoes):
        for x, y in ((a, b), (b, a)):
            used[i] = True
            chain = [(x, y)]
            if search(x, y, 1):
                return chain
            used[i] = False
    return None
