def can_chain(dominoes):
    if not dominoes:
        return []

    def search(remaining, chain):
        if not remaining:
            if chain[0][0] == chain[-1][1]:
                return chain
            return None
        end = chain[-1][1]
        for i, (a, b) in enumerate(remaining):
            rest = remaining[:i] + remaining[i + 1:]
            if a == end:
                result = search(rest, chain + [(a, b)])
                if result is not None:
                    return result
            if b == end and a != b:
                result = search(rest, chain + [(b, a)])
                if result is not None:
                    return result
        return None

    first = dominoes[0]
    return search(dominoes[1:], [first])
