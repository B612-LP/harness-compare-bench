from collections import Counter


_RANKS = {
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


def _hand_key(hand):
    cards = hand.split()
    values = sorted((_RANKS[card[:-1]] for card in cards), reverse=True)
    suits = [card[-1] for card in cards]
    counts = Counter(values)
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)

    is_flush = len(set(suits)) == 1
    unique = sorted(set(values))

    straight_high = None
    if unique == [2, 3, 4, 5, 14]:
        straight_high = 5
    elif len(unique) == 5 and unique[-1] - unique[0] == 4:
        straight_high = unique[-1]

    if is_flush and straight_high is not None:
        return (8, (straight_high,))

    if groups[0][1] == 4:
        quad = groups[0][0]
        kicker = groups[1][0]
        return (7, (quad, kicker))

    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, (groups[0][0], groups[1][0]))

    if is_flush:
        return (5, tuple(values))

    if straight_high is not None:
        return (4, (straight_high,))

    if groups[0][1] == 3:
        trip = groups[0][0]
        kickers = tuple(sorted((value for value, count in groups[1:]), reverse=True))
        return (3, (trip,) + kickers)

    if groups[0][1] == 2 and groups[1][1] == 2:
        pairs = tuple(sorted((groups[0][0], groups[1][0]), reverse=True))
        kicker = max(value for value, count in groups[2:])
        return (2, pairs + (kicker,))

    if groups[0][1] == 2:
        pair = groups[0][0]
        kickers = tuple(sorted((value for value, count in groups[1:]), reverse=True))
        return (1, (pair,) + kickers)

    return (0, tuple(values))


def best_hands(hands):
    keys = [_hand_key(hand) for hand in hands]
    best = max(keys)
    return [hand for hand, key in zip(hands, keys) if key == best]
