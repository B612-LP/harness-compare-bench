"""dominoes 参考解：回溯搜索把骨牌排成首尾相接的闭环；无解返回 None。"""


def can_chain(dominoes):
    stones = [tuple(stone) for stone in dominoes]
    if not stones:
        return []

    count = len(stones)
    used = [False] * count
    chain = []

    def place(end):
        if len(chain) == count:
            return chain[0][0] == chain[-1][1]
        for index, (left, right) in enumerate(stones):
            if used[index]:
                continue
            if end is None:
                options = [(left, right)] if left == right else [(left, right), (right, left)]
            elif left == end:
                options = [(left, right)]
            elif right == end:
                options = [(right, left)]
            else:
                continue
            for oriented in options:
                used[index] = True
                chain.append(oriented)
                if place(oriented[1]):
                    return True
                chain.pop()
                used[index] = False
        return False

    return chain if place(None) else None