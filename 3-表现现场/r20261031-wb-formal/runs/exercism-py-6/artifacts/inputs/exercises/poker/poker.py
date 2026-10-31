RANKS = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}


def _parse(hand):
    cards = hand.split()
    ranks = [RANKS[card[:-1]] for card in cards]
    suits = [card[-1] for card in cards]
    return ranks, suits


def _straight_high(ranks):
    unique = sorted(set(ranks))
    if len(unique) != 5:
        return None
    if unique[-1] - unique[0] == 4:
        return unique[-1]
    if unique == [2, 3, 4, 5, 14]:
        return 5
    return None


def _hand_key(hand):
    ranks, suits = _parse(hand)
    counts = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], -item[0]))
    values = sorted(ranks, reverse=True)
    flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)
    shape = [count for _, count in ordered]

    if flush and straight_high is not None:
        return (8, straight_high)
    if shape == [4, 1]:
        return (7, ordered[0][0], ordered[1][0])
    if shape == [3, 2]:
        return (6, ordered[0][0], ordered[1][0])
    if flush:
        return (5,) + tuple(values)
    if straight_high is not None:
        return (4, straight_high)
    if shape == [3, 1, 1]:
        return (3, ordered[0][0]) + tuple(sorted((ordered[1][0], ordered[2][0]), reverse=True))
    if shape == [2, 2, 1]:
        high_pair = max(ordered[0][0], ordered[1][0])
        low_pair = min(ordered[0][0], ordered[1][0])
        return (2, high_pair, low_pair, ordered[2][0])
    if shape == [2, 1, 1, 1]:
        return (1, ordered[0][0]) + tuple(sorted((ordered[1][0], ordered[2][0], ordered[3][0]), reverse=True))
    return (0,) + tuple(values)


def best_hands(hands):
    keys = [_hand_key(hand) for hand in hands]
    best = max(keys)
    return [hand for hand, key in zip(hands, keys) if key == best]
