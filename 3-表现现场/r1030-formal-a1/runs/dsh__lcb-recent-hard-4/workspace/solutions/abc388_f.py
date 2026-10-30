import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m, A, B = data[0:4]
    intervals = []
    idx = 4
    for _ in range(m):
        L, R = data[idx], data[idx + 1]
        idx += 2
        intervals.append((L, R))

    if A == B:
        # The only possible move is +A.
        if (n - 1) % A != 0:
            print("No")
            return
        # Every cell of the progression 1, 1+A, ... must be good.
        for L, R in intervals:
            # First number >= L congruent to 1 modulo A.
            first = L + ((1 - L) % A)
            if first <= R and first < n:
                print("No")
                return
        print("Yes")
        return

    full = (1 << B) - 1
    # Bits d-1 for A <= d <= B.
    allowed = ((1 << (B - A + 1)) - 1) << (A - 1)

    # mask bit j means: position (cur - j) is reachable.
    # Initially cur = 1 and position 1 is reachable.
    mask = 1
    cur = 1
    LIMIT = B * B + 5

    def advance_good(length):
        nonlocal mask
        if length <= 0:
            return
        if mask == full:
            return
        if mask == 0:
            return
        steps = length if length < LIMIT else LIMIT
        for _ in range(steps):
            if mask == full:
                return
            nb = 1 if (mask & allowed) else 0
            mask = ((mask << 1) | nb) & full
        # For A < B a non-empty mask becomes full within fewer than B^2 steps.
        # The loop above therefore normally exits through the 'full' check;
        # leaving it untouched here is still correct for any remaining steps
        # because a full mask stays full.

    def advance_bad(length):
        nonlocal mask
        if length <= 0 or mask == 0:
            return
        steps = length if length < B else B
        for _ in range(steps):
            mask = (mask << 1) & full
        # After B shifts the mask is zero; any remaining bad cells keep it zero.

    for L, R in intervals:
        advance_good(L - cur - 1)
        advance_bad(R - L + 1)
        cur = R

    advance_good(n - cur)
    print("Yes" if (mask & 1) else "No")


if __name__ == "__main__":
    main()
