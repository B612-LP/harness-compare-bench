def best_hands(hands):
    ranked = [(hand_rank(hand), hand) for hand in hands]
    best = max(rank for rank, _ in ranked)
    return [hand for rank, hand in ranked if rank == best]


def hand_rank(hand):
    cards = hand.split()
    values = []
    suits = []
    rank_names = {
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }

    for card in cards:
        value = card[:-1]
        values.append(int(value) if value.isdigit() else rank_names[value])
        suits.append(card[-1])

    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1

    groups = sorted(
        counts.items(), key=lambda item: (item[1], item[0]), reverse=True
    )
    ordered_values = sorted(values, reverse=True)
    flush = len(set(suits)) == 1
    straight_high = get_straight_high(values)

    if flush and straight_high:
        return (8, straight_high)
    if groups[0][1] == 4:
        return (7, groups[0][0], groups[1][0])
    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, groups[0][0], groups[1][0])
    if flush:
        return (5, *ordered_values)
    if straight_high:
        return (4, straight_high)
    if groups[0][1] == 3:
        kickers = sorted(
            (value for value in values if value != groups[0][0]), reverse=True
        )
        return (3, groups[0][0], *kickers)
    if groups[0][1] == 2 and groups[1][1] == 2:
        pairs = sorted((groups[0][0], groups[1][0]), reverse=True)
        kicker = next(value for value in values if value not in pairs)
        return (2, pairs[0], pairs[1], kicker)
    if groups[0][1] == 2:
        kickers = sorted(
            (value for value in values if value != groups[0][0]), reverse=True
        )
        return (1, groups[0][0], *kickers)
    return (0, *ordered_values)


def get_straight_high(values):
    unique = sorted(set(values))
    if unique == [2, 3, 4, 5, 14]:
        return 5
    if len(unique) == 5 and unique[-1] - unique[0] == 4:
        return unique[-1]
    return None
