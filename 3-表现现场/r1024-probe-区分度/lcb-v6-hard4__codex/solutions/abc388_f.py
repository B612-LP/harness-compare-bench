import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, m, a, b = data[:4]
    intervals = [(data[i], data[i + 1]) for i in range(4, 4 + 2 * m, 2)]

    full = (1 << b) - 1
    relevant = 0
    for i in range(a - 1, b):
        relevant |= 1 << i

    def valid_step(mask):
        return ((mask << 1) & full) | (1 if mask & relevant else 0)

    def advance_valid(mask, length):
        if length <= 0 or mask == 0:
            return mask

        if a == b:
            shift = length % b
            if shift == 0:
                return mask
            return ((mask << shift) & full) | (mask >> (b - shift))

        if mask == full:
            return full

        seen = {}
        done = 0
        while length > 0:
            if mask == 0 or mask == full:
                return mask
            if mask in seen:
                cycle = done - seen[mask]
                length %= cycle
                for _ in range(length):
                    mask = valid_step(mask)
                return mask
            seen[mask] = done
            mask = valid_step(mask)
            done += 1
            length -= 1
        return mask

    def advance_bad(mask, length):
        if length >= b:
            return 0
        return (mask << length) & full

    mask = 1
    current = 1

    for left, right in intervals:
        mask = advance_valid(mask, left - current - 1)
        mask = advance_bad(mask, right - left + 1)
        current = right
        if mask == 0:
            break

    if mask:
        mask = advance_valid(mask, n - current)

    print("Yes" if mask & 1 else "No")


if __name__ == "__main__":
    main()
