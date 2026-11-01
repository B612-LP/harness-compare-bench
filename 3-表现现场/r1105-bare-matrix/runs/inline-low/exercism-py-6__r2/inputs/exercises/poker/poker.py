from collections import Counter


RANKS = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}


def _check_straight(ranks):
    unique = sorted(set(ranks))
    if len(unique) != 5:
        return False, None
    if unique[-1] - unique[0] == 4:
        return True, unique[-1]
    if unique == [2, 3, 4, 5, 14]:
        return True, 5
    return False, None


def _rank_key(hand):
    cards = hand.split()
    ranks = [RANKS[c[:-1]] for c in cards]
    suits = [c[-1] for c in cards]
    counts = Counter(ranks)
    ordered = sorted(ranks, key=lambda r: (-counts[r], -r))
    values = sorted(counts.values(), reverse=True)
    flush = len(set(suits)) == 1
    straight, straight_high = _check_straight(ranks)

    if straight and flush:
        return (8, straight_high)
    if values[0] == 4:
        return (7, ordered[0], ordered[-1])
    if values == [3, 2]:
        return (6, ordered[0], ordered[-1])
    if flush:
        return (5,) + tuple(sorted(ranks, reverse=True))
    if straight:
        return (4, straight_high)
    if values[0] == 3:
        trip = [r for r in counts if counts[r] == 3][0]
        kickers = sorted([r for r in ranks if r != trip], reverse=True)
        return (3, trip) + tuple(kickers)
    if values == [2, 2, 1]:
        pairs = sorted([r for r in counts if counts[r] == 2], reverse=True)
        kicker = [r for r in counts if counts[r] == 1]
        return (2,) + tuple(pairs) + tuple(kicker)
    if values[0] == 2:
        pair = [r for r in counts if counts[r] == 2][0]
        kickers = sorted([r for r in ranks if r != pair], reverse=True)
        return (1, pair) + tuple(kickers)
    return (0,) + tuple(sorted(ranks, reverse=True))


def best_hands(hands):
    if not hands:
        return []
    keys = [_rank_key(h) for h in hands]
    best = max(keys)
    return [h for h, k in zip(hands, keys) if k == best]
