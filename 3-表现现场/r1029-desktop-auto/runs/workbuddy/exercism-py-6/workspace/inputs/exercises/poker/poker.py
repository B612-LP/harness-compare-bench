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

CATEGORY_NAMES = {
    8: "straight flush",
    7: "four of a kind",
    6: "full house",
    5: "flush",
    4: "straight",
    3: "three of a kind",
    2: "two pair",
    1: "one pair",
    0: "high card",
}


def _score(hand):
    """Return a sortable key describing the strength of a hand."""
    cards = hand.split()
    ranks = sorted((RANKS[card[:-1]] for card in cards), reverse=True)
    suits = {card[-1] for card in cards}
    flush = len(suits) == 1

    counts = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1

    # Group ranks by how often they appear, ordered by count then rank.
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    shape = [count for _, count in groups]
    ordered = [rank for rank, _ in groups]

    straight_high = None
    if len(counts) == 5:
        if ranks[0] - ranks[4] == 4:
            straight_high = ranks[0]
        elif ranks == [14, 5, 4, 3, 2]:
            straight_high = 5

    if flush and straight_high is not None:
        return (8, [straight_high])
    if shape == [4, 1]:
        return (7, ordered)
    if shape == [3, 2]:
        return (6, ordered)
    if flush:
        return (5, ranks)
    if straight_high is not None:
        return (4, [straight_high])
    if shape == [3, 1, 1]:
        return (3, ordered)
    if shape == [2, 2, 1]:
        return (2, ordered)
    if shape == [2, 1, 1, 1]:
        return (1, ordered)
    return (0, ranks)


def best_hands(hands):
    scored = [(hand, _score(hand)) for hand in hands]
    best = max(score for _, score in scored)
    return [hand for hand, score in scored if score == best]
