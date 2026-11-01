RANK_MAP = {
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
    return RANK_MAP[card[:-1]], card[-1]


def _straight_high(ranks):
    if len(set(ranks)) != 5:
        return None
    ordered = sorted(set(ranks))
    if ordered == [2, 3, 4, 5, 14]:
        return 5
    for i in range(4):
        if ordered[i + 1] != ordered[i] + 1:
            return None
    return ordered[-1]


def _hand_score(hand):
    cards = hand.split()
    ranks = []
    suits = []

    for card in cards:
        rank, suit = _parse_card(card)
        ranks.append(rank)
        suits.append(suit)

    sorted_ranks = sorted(ranks, reverse=True)
    counts = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1

    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)

    flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)

    if flush and straight_high is not None:
        return (8, straight_high)

    if groups[0][1] == 4:
        quad = groups[0][0]
        kicker = max(rank for rank in ranks if rank != quad)
        return (7, quad, kicker)

    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, groups[0][0], groups[1][0])

    if flush:
        return (5, *sorted_ranks)

    if straight_high is not None:
        return (4, straight_high)

    if groups[0][1] == 3:
        trip = groups[0][0]
        kickers = sorted((rank for rank in ranks if rank != trip), reverse=True)
        return (3, trip, *kickers)

    if groups[0][1] == 2 and groups[1][1] == 2:
        pairs = sorted([groups[0][0], groups[1][0]], reverse=True)
        kicker = max(rank for rank in ranks if rank not in pairs)
        return (2, pairs[0], pairs[1], kicker)

    if groups[0][1] == 2:
        pair = groups[0][0]
        kickers = sorted((rank for rank in ranks if rank != pair), reverse=True)
        return (1, pair, *kickers)

    return (0, *sorted_ranks)


def best_hands(hands):
    scored = [(_hand_score(hand), hand) for hand in hands]
    best = max(score for score, _ in scored)
    return [hand for score, hand in scored if score == best]
