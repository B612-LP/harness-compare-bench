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


def _parse_card(card):
    return _RANKS[card[:-1].upper()], card[-1].upper()


def _straight_high(ranks):
    unique = sorted(set(ranks))
    if len(unique) != 5:
        return None
    if unique == [2, 3, 4, 5, 14]:
        return 5
    if unique[-1] - unique[0] == 4:
        return unique[-1]
    return None


def _score(hand):
    cards = [_parse_card(card) for card in hand.split()]
    ranks = [rank for rank, _ in cards]
    suits = [suit for _, suit in cards]

    counts = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1

    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    flush = len(set(suits)) == 1
    straight = _straight_high(ranks)
    ranks_desc = sorted(ranks, reverse=True)

    if flush and straight is not None:
        return (8, straight)
    if groups[0][1] == 4:
        quad = groups[0][0]
        kicker = max(rank for rank in ranks if rank != quad)
        return (7, quad, kicker)
    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, groups[0][0], groups[1][0])
    if flush:
        return (5, *ranks_desc)
    if straight is not None:
        return (4, straight)
    if groups[0][1] == 3:
        trip = groups[0][0]
        kickers = sorted((rank for rank in ranks if rank != trip), reverse=True)
        return (3, trip, *kickers)
    if groups[0][1] == 2 and groups[1][1] == 2:
        high_pair = max(groups[0][0], groups[1][0])
        low_pair = min(groups[0][0], groups[1][0])
        kicker = max(rank for rank in ranks if rank not in (high_pair, low_pair))
        return (2, high_pair, low_pair, kicker)
    if groups[0][1] == 2:
        pair = groups[0][0]
        kickers = sorted((rank for rank in ranks if rank != pair), reverse=True)
        return (1, pair, *kickers)
    return (0, *ranks_desc)


def best_hands(hands):
    if not hands:
        return []
    scored = [(_score(hand), hand) for hand in hands]
    best = max(score for score, _ in scored)
    return [hand for score, hand in scored if score == best]
