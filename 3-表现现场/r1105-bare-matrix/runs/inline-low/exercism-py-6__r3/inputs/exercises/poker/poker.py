from collections import Counter


def _rank_value(rank_str):
    if rank_str == "A":
        return 14
    if rank_str == "K":
        return 13
    if rank_str == "Q":
        return 12
    if rank_str == "J":
        return 11
    return int(rank_str)


def _score_hand(hand):
    cards = hand.split()
    ranks = []
    suits = []
    for card in cards:
        ranks.append(_rank_value(card[:-1]))
        suits.append(card[-1])

    ranks_sorted = sorted(ranks, reverse=True)
    counts = Counter(ranks)

    is_flush = len(set(suits)) == 1

    unique = sorted(set(ranks))
    straight_high = None
    if len(unique) == 5:
        if unique[-1] - unique[0] == 4:
            straight_high = unique[-1]
        elif unique == [2, 3, 4, 5, 14]:
            straight_high = 5

    if is_flush and straight_high is not None:
        return (8, straight_high)

    for rank, count in counts.items():
        if count == 4:
            kicker = max(r for r in ranks if r != rank)
            return (7, rank, kicker)

    threes = [r for r, c in counts.items() if c == 3]
    pairs = [r for r, c in counts.items() if c == 2]

    if threes and pairs:
        return (6, max(threes), max(pairs))

    if is_flush:
        return (5, *ranks_sorted)

    if straight_high is not None:
        return (4, straight_high)

    if threes:
        trip = max(threes)
        kickers = sorted((r for r in ranks if r != trip), reverse=True)
        return (3, trip, *kickers)

    pairs = sorted(pairs, reverse=True)
    if len(pairs) == 2:
        kicker = max(r for r in ranks if r != pairs[0] and r != pairs[1])
        return (2, pairs[0], pairs[1], kicker)

    if len(pairs) == 1:
        pair_rank = pairs[0]
        kickers = sorted((r for r in ranks if r != pair_rank), reverse=True)
        return (1, pair_rank, *kickers)

    return (0, *ranks_sorted)


def best_hands(hands):
    scored = [(hand, _score_hand(hand)) for hand in hands]
    best = max(score for _, score in scored)
    return [hand for hand, score in scored if score == best]
