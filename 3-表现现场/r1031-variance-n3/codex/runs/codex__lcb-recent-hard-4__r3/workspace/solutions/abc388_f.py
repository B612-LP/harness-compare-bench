import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n, m, a, b = data[0], data[1], data[2], data[3]
    intervals = [(data[i], data[i + 1]) for i in range(4, 4 + 2 * m, 2)]

    if a == b:
        if (n - 1) % a != 0:
            print("No")
            return

        want = 1 % a
        for left, right in intervals:
            first = left + (want - left % a) % a
            if first <= right:
                print("No")
                return

        print("Yes")
        return

    full = (1 << b) - 1
    jump_mask = (1 << (b - a + 1)) - 1
    shift = a - 1

    t0 = (a - 1 + (b - a) - 1) // (b - a)
    limit = t0 * a + b

    def advance_good(mask, steps):
        if mask == 0 or steps <= 0:
            return mask
        if mask == full:
            return full

        for _ in range(min(steps, limit)):
            new_bit = 1 if ((mask >> shift) & jump_mask) else 0
            mask = ((mask << 1) & full) | new_bit
            if mask == full:
                return full

        if steps > limit:
            return full
        return mask

    mask = 1
    current = 1

    for left, right in intervals:
        mask = advance_good(mask, left - current - 1)
        if mask == 0:
            print("No")
            return

        bad_length = right - left + 1
        if bad_length >= b:
            print("No")
            return

        mask = (mask << bad_length) & full
        if mask == 0:
            print("No")
            return
        current = right

    mask = advance_good(mask, n - current)
    print("Yes" if (mask & 1) else "No")


if __name__ == "__main__":
    main()
