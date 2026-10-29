RANKS = {rank: index for index, rank in enumerate("23456789TJQKA", start=2)}


def _parse(card):
    rank = card[:-1].upper()
    suit = card[-1].upper()
    if rank == "10":
        rank = "T"
    return RANKS[rank], suit


def _straight_high(ranks):
    """Return the high card of a straight, or None if not a straight."""
    unique = sorted(set(ranks))
    if len(unique) != 5:
        return None
    if unique == [2, 3, 4, 5, 14]:
        return 5  # ace-low wheel
    if unique[-1] - unique[0] == 4:
        return unique[-1]
    return None


def _hand_key(cards):
    values = [_parse(card)[0] for card in cards]
    suits = [_parse(card)[1] for card in cards]
    flush = len(set(suits)) == 1

    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1

    groups = sorted(counts.items(), key=lambda item: (-item[1], -item[0]))
    grouped = tuple(rank for rank, count in groups for _ in range(count))
    descending = tuple(sorted(values, reverse=True))
    high = _straight_high(values)

    if flush and high is not None:
        return (8, (high,))
    if groups[0][1] == 4:
        return (7, grouped)
    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, grouped)
    if flush:
        return (5, descending)
    if high is not None:
        return (4, (high,))
    if groups[0][1] == 3:
        return (3, grouped)
    if groups[0][1] == 2 and groups[1][1] == 2:
        return (2, grouped)
    if groups[0][1] == 2:
        return (1, grouped)
    return (0, descending)


def best_hands(hands):
    scored = [(hand, _hand_key(hand.split())) for hand in hands]
    best = max(key for _, key in scored)
    return [hand for hand, key in scored if key == best]
