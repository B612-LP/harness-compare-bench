import sys


def main():
    input = sys.stdin.buffer.readline
    n, m, A, B = map(int, input().split())
    intervals = [tuple(map(int, input().split())) for _ in range(m)]

    full = (1 << B) - 1
    select = ((1 << (B - A + 1)) - 1) << (A - 1)

    def step_good(mask):
        return ((mask << 1) & full) | (1 if (mask & select) else 0)

    def advance_good(mask, length):
        if length <= 600:
            for _ in range(length):
                mask = ((mask << 1) & full) | (1 if (mask & select) else 0)
            return mask

        seen = {}
        states = []
        i = 0
        while i < length and mask not in seen:
            seen[mask] = i
            states.append(mask)
            mask = step_good(mask)
            i += 1
        if i == length:
            return mask

        start = seen[mask]
        cycle_len = i - start
        return states[start + (length - start) % cycle_len]

    pos = 1
    mask = 1

    for left, right in intervals:
        mask = advance_good(mask, (left - 1) - pos)

        bad_len = right - left + 1
        mask = 0 if bad_len >= B else (mask << bad_len) & full
        pos = right

    mask = advance_good(mask, n - pos)
    print("Yes" if (mask & 1) else "No")


if __name__ == "__main__":
    main()
