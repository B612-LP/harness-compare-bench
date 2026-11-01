import sys


def solve() -> None:
    input = sys.stdin.readline
    N, M, A, B = map(int, input().split())
    intervals = [tuple(map(int, input().split())) for _ in range(M)]

    mask = (1 << B) - 1

    def advance_bad(state: int, length: int) -> int:
        if length <= 0:
            return state
        if length >= B:
            return 0
        return (state << length) & mask

    if A == B:
        def advance_good(state: int, length: int) -> int:
            if length <= 0:
                return state
            length %= A
            for _ in range(length):
                bit = (state >> (A - 1)) & 1
                state = ((state << 1) | bit) & mask
            return state
    else:
        seg_mask = ((1 << B) - 1) ^ ((1 << (A - 1)) - 1)

        def advance_good(state: int, length: int) -> int:
            if length <= 0:
                return state

            steps = length if length < 1000 else 1000
            for _ in range(steps):
                new_bit = 1 if (state & seg_mask) else 0
                state = ((state << 1) | new_bit) & mask

            if length > 1000:
                state = mask if state != 0 else 0
            return state

    cur = 1
    state = 1

    for L, R in intervals:
        if L - 1 > cur:
            length = (L - 1) - cur
            state = advance_good(state, length)
            cur = L - 1

        length_bad = R - L + 1
        state = advance_bad(state, length_bad)
        cur = R

    if N > cur:
        state = advance_good(state, N - cur)

    print("Yes" if (state & 1) else "No")


if __name__ == "__main__":
    solve()
