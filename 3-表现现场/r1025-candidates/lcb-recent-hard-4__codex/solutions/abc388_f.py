import sys


def main() -> None:
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m, a, b = data[:4]
    intervals = [(data[4 + 2 * i], data[5 + 2 * i]) for i in range(m)]

    window = (1 << b) - 1

    # A state stores, in bit j, whether position (current - j) is reachable.
    # The matrix of one good-position transition, over the Boolean semiring.
    source_mask = ((1 << b) - 1) ^ ((1 << (a - 1)) - 1)
    good_rows = [source_mask]
    for i in range(1, b):
        good_rows.append(1 << (i - 1))

    powers = [good_rows]
    for _ in range(1, max(1, n.bit_length())):
        prev = powers[-1]
        cur = []
        for mask in prev:
            out = 0
            bits = mask
            while bits:
                low = bits & -bits
                out |= prev[low.bit_length() - 1]
                bits ^= low
            cur.append(out)
        powers.append(cur)

    def advance_good(state: int, length: int) -> int:
        bit = 0
        while length:
            if length & 1:
                mat = powers[bit]
                nxt = 0
                for i, row in enumerate(mat):
                    if row & state:
                        nxt |= 1 << i
                state = nxt
            length >>= 1
            bit += 1
        return state

    state = 1  # Position 1 is reachable.
    pos = 1

    for left, right in intervals:
        good_length = left - pos - 1
        if good_length:
            state = advance_good(state, good_length)

        bad_length = right - left + 1
        if bad_length >= b:
            state = 0
        else:
            state = (state << bad_length) & window

        pos = right

    good_length = n - pos
    if good_length:
        state = advance_good(state, good_length)

    print("Yes" if state & 1 else "No")


if __name__ == "__main__":
    main()
