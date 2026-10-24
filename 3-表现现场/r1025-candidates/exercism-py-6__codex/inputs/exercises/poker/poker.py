def best_hands(hands):
    def hand_key(hand):
        ranks = []
        suits = []
        face_values = {"J": 11, "Q": 12, "K": 13, "A": 14}

        for card in hand.split():
            rank = card[:-1]
            ranks.append(face_values.get(rank, int(rank) if rank.isdigit() else None))
            suits.append(card[-1])

        ranks.sort(reverse=True)
        counts = {}
        for rank in ranks:
            counts[rank] = counts.get(rank, 0) + 1

        groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
        group_ranks = [rank for rank, _ in groups]
        group_sizes = [size for _, size in groups]

        unique_ranks = sorted(counts)
        straight_high = None
        if len(unique_ranks) == 5:
            if unique_ranks == list(range(unique_ranks[0], unique_ranks[0] + 5)):
                straight_high = unique_ranks[-1]
            elif unique_ranks == [2, 3, 4, 5, 14]:
                straight_high = 5

        flush = len(set(suits)) == 1

        if straight_high is not None and flush:
            return (8, straight_high)
        if group_sizes == [4, 1]:
            return (7, *group_ranks)
        if group_sizes == [3, 2]:
            return (6, *group_ranks)
        if flush:
            return (5, *ranks)
        if straight_high is not None:
            return (4, straight_high)
        if group_sizes == [3, 1, 1]:
            return (3, *group_ranks)
        if group_sizes == [2, 2, 1]:
            return (2, *group_ranks)
        if group_sizes == [2, 1, 1, 1]:
            return (1, *group_ranks)
        return (0, *ranks)

    best_key = max(hand_key(hand) for hand in hands)
    return [hand for hand in hands if hand_key(hand) == best_key]
