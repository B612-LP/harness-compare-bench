def can_chain(dominoes):
    if not dominoes:
        return []

    n = len(dominoes)
    used = [False] * n
    chain = []

    def search():
        if len(chain) == n:
            return chain[0][0] == chain[-1][1]
        last = chain[-1][1] if chain else None
        for i in range(n):
            if used[i]:
                continue
            a, b = dominoes[i]
            if a == b:
                orientations = ((a, b),)
            else:
                orientations = ((a, b), (b, a))
            for x, y in orientations:
                if last is not None and x != last:
                    continue
                used[i] = True
                chain.append((x, y))
                if search():
                    return True
                chain.pop()
                used[i] = False
        return False

    if search():
        return list(chain)
    return None
