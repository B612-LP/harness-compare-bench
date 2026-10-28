import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m, a, b = data[:4]

    intervals = []
    pos = 4
    for _ in range(m):
        left, right = data[pos], data[pos + 1]
        pos += 2
        if intervals and left <= intervals[-1][1] + 1:
            if right > intervals[-1][1]:
                intervals[-1] = (intervals[-1][0], right)
        else:
            intervals.append((left, right))

    mask = (1 << b) - 1
    step_mask = ((1 << b) - 1) ^ ((1 << (a - 1)) - 1)

    # A set bit i means that the position i steps behind is reachable.
    def one_good_step(state):
        return ((state << 1) & mask) | (1 if state & step_mask else 0)

    # powers[k] maps a state through 2^k consecutive good positions.
    powers = [[one_good_step(1 << i) for i in range(b)]]
    for _ in range(1, n.bit_length()):
        previous = powers[-1]
        current = []
        for j in range(b):
            state = previous[j]
            mapped = 0
            while state:
                lowest = state & -state
                mapped |= previous[lowest.bit_length() - 1]
                state ^= lowest
            current.append(mapped)
        powers.append(current)

    def advance(state, length):
        level = 0
        while length:
            if length & 1:
                columns = powers[level]
                mapped = 0
                while state:
                    lowest = state & -state
                    mapped |= columns[lowest.bit_length() - 1]
                    state ^= lowest
                state = mapped
            length >>= 1
            level += 1
        return state

    state = 1  # Position 1 is reachable.
    current = 1

    for left, right in intervals:
        state = advance(state, left - current - 1)
        current = left - 1

        length = right - left + 1
        if length >= b:
            print("No")
            return

        state = (state << length) & mask
        current = right
        if state == 0:
            print("No")
            return

    state = advance(state, n - current)
    print("Yes" if state & 1 else "No")


if __name__ == "__main__":
    main()
