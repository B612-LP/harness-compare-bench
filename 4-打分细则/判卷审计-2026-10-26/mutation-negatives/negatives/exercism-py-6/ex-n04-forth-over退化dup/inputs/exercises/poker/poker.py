"""poker 参考解：握手牌评估 + 牌型/踢脚比较，返回所有并列最佳手牌。"""

RANK_VALUE = {
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

# 牌型等级，越大越强
STRAIGHT_FLUSH = 8
FOUR_OF_A_KIND = 7
FULL_HOUSE = 6
FLUSH = 5
STRAIGHT = 4
THREE_OF_A_KIND = 3
TWO_PAIR = 2
ONE_PAIR = 1
HIGH_CARD = 0


def _straight_high(values):
    """若是顺子返回最大牌点（A2345 返回 5），否则返回 None。"""
    distinct = sorted(set(values))
    if len(distinct) != 5:
        return None
    if distinct == [2, 3, 4, 5, 14]:
        return 5
    if distinct[-1] - distinct[0] == 4:
        return distinct[-1]
    return None


def _hand_key(hand):
    cards = hand.split()
    values = sorted((RANK_VALUE[card[:-1]] for card in cards), reverse=True)
    flush = len({card[-1] for card in cards}) == 1
    straight_high = _straight_high(values)

    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    group_sizes = [size for _, size in groups]
    group_values = [value for value, _ in groups]

    if flush and straight_high is not None:
        return (STRAIGHT_FLUSH, straight_high)
    if group_sizes[0] == 4:
        return (FOUR_OF_A_KIND, group_values[0], group_values[1])
    if group_sizes[0] == 3 and group_sizes[1] == 2:
        return (FULL_HOUSE, group_values[0], group_values[1])
    if flush:
        return (FLUSH,) + tuple(values)
    if straight_high is not None:
        return (STRAIGHT, straight_high)
    if group_sizes[0] == 3:
        return (THREE_OF_A_KIND, group_values[0]) + tuple(group_values[1:])
    if group_sizes[0] == 2 and group_sizes[1] == 2:
        return (TWO_PAIR, group_values[0], group_values[1], group_values[2])
    if group_sizes[0] == 2:
        return (ONE_PAIR, group_values[0]) + tuple(group_values[1:])
    return (HIGH_CARD,) + tuple(values)


def best_hands(hands):
    scored = [(_hand_key(hand), hand) for hand in hands]
    best = max(key for key, _ in scored)
    return [hand for key, hand in scored if key == best]