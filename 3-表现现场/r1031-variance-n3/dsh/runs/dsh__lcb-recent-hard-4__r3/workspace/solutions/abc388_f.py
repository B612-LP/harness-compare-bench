import sys

def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M, A, B = data[0], data[1], data[2], data[3]
    intervals = []
    idx = 4
    for _ in range(M):
        intervals.append((data[idx], data[idx + 1]))
        idx += 2

    if A == B:
        if (N - 1) % A != 0:
            print("No")
            return
        for L, R in intervals:
            # smallest reachable position 1 + k*A that is >= L
            k = (L - 1 + A - 1) // A
            p = 1 + k * A
            if p <= R:
                print("No")
                return
        print("Yes")
        return

    full = (1 << B) - 1
    need_mask = full ^ ((1 << (A - 1)) - 1)
    LIMIT = B * B + 5

    def step(mask):
        nb = 1 if (mask & need_mask) else 0
        return ((mask << 1) | nb) & full

    def advance_good(mask, length):
        if length <= 0:
            return mask
        if length <= LIMIT:
            for _ in range(length):
                mask = step(mask)
            return mask
        if mask == 0:
            return 0
        for _ in range(LIMIT):
            mask = step(mask)
            if mask == full:
                break
        # For A < B, any non-zero state becomes full within (B-1)^2+1
        # consecutive good cells; hence it stays full afterwards.
        return mask

    mask = 1  # position 1 is reachable
    cur = 1
    for L, R in intervals:
        gap = L - cur - 1
        mask = advance_good(mask, gap)
        cur = L - 1
        length = R - L + 1
        if length >= B:
            mask = 0
        else:
            mask = (mask << length) & full
        cur = R

    mask = advance_good(mask, N - cur)
    print("Yes" if (mask & 1) else "No")

if __name__ == "__main__":
    solve()
