import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m, a, b = data[:4]
    intervals = []
    at = 4
    for _ in range(m):
        intervals.append((data[at], data[at + 1]))
        at += 2

    if a == b:
        if (n - 1) % a != 0:
            print("No")
            return
        for left, right in intervals:
            k = (left - 2) // a + 1
            if 1 + k * a <= right:
                print("No")
                return
        print("Yes")
        return

    full = (1 << b) - 1
    jump_mask = 0
    for d in range(a, b + 1):
        jump_mask |= 1 << (d - 1)

    # Bit d-1 tells whether the position d steps behind is reachable.
    mask = 1
    pos = 1

    for left, right in intervals:
        gap = left - pos - 1
        while gap > 0 and mask != full:
            new_bit = 1 if mask & jump_mask else 0
            mask = ((mask << 1) & full) | new_bit
            gap -= 1

        length = right - left + 1
        mask = 0 if length >= b else (mask << length) & full
        if mask == 0:
            print("No")
            return
        pos = right

    gap = n - pos
    while gap > 0 and mask != full:
        new_bit = 1 if mask & jump_mask else 0
        mask = ((mask << 1) & full) | new_bit
        gap -= 1

    print("Yes" if mask & 1 else "No")


if __name__ == "__main__":
    main()
