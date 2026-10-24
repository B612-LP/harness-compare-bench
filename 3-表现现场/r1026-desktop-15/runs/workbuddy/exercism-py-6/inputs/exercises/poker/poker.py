from collections import Counter

_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
}

STRAIGHT_FLUSH = 8
FOUR_OF_A_KIND = 7
FULL_HOUSE = 6
FLUSH = 5
STRAIGHT = 4
THREE_OF_A_KIND = 3
TWO_PAIR = 2
ONE_PAIR = 1
HIGH_CARD = 0


def _parse(hand):
    """Return a list of (value, suit) tuples for a hand string."""
    return [(_VALUES[card[:-1]], card[-1]) for card in hand.split()]


def _straight_high(values):
    """Return the high card of a straight, or None."""
    ordered = sorted(set(values))
    if len(ordered) != 5:
        return None
    if ordered[-1] - ordered[0] == 4:
        return ordered[-1]
    # Ace may play low: A-2-3-4-5 is a five high straight.
    if ordered == [2, 3, 4, 5, 14]:
        return 5
    return None


def _score(cards):
    """Rank a hand; bigger tuples beat smaller ones."""
    values = [value for value, _ in cards]
    flush = len({suit for _, suit in cards}) == 1
    straight_high = _straight_high(values)
    counts = Counter(values)
    # Sort by count first, then by value: most frequent, highest cards first.
    grouped = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    shape = [count for _, count in grouped]
    ordered = [value for value, _ in grouped]
    desc = sorted(values, reverse=True)

    if straight_high is not None and flush:
        return (STRAIGHT_FLUSH, straight_high)
    if shape == [4, 1]:
        return (FOUR_OF_A_KIND, ordered[0], ordered[1])
    if shape == [3, 2]:
        return (FULL_HOUSE, ordered[0], ordered[1])
    if flush:
        return (FLUSH,) + tuple(desc)
    if straight_high is not None:
        return (STRAIGHT, straight_high)
    if shape == [3, 1, 1]:
        return (THREE_OF_A_KIND, ordered[0], ordered[1], ordered[2])
    if shape == [2, 2, 1]:
        return (TWO_PAIR, ordered[0], ordered[1], ordered[2])
    if shape == [2, 1, 1, 1]:
        return (ONE_PAIR, ordered[0], ordered[1], ordered[2], ordered[3])
    return (HIGH_CARD,) + tuple(desc)


def best_hands(hands):
    if not hands:
        return []
    scored = [(_score(_parse(hand)), hand) for hand in hands]
    best = max(score for score, _ in scored)
    return [hand for score, hand in scored if score == best]
