import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M, A, B = data[0], data[1], data[2], data[3]
    bad = []
    idx = 4
    for _ in range(M):
        L, R = data[idx], data[idx+1]
        idx += 2
        bad.append((L, R))

    if A == B:
        if (N - 1) % A != 0:
            print("No")
            return
        pos = 1
        for L, R in bad:
            # first multiple of A reached from 1 inside [L, R]
            if pos <= R:
                # positions are 1 + k*A
                k = (L - 1 + A - 1) // A
                if k <= 0:
                    k = 1
                first = 1 + k * A
                if first <= R and first <= N:
                    print("No")
                    return
        print("Yes")
        return

    # For B > A saturation threshold.
    j0 = (B - 1 + (B - A) - 1) // (B - A)
    P = j0 * A + 2 * B + 5
    FULL = (1 << B) - 1
    range_mask = (1 << (B - A + 1)) - 1

    cur = 1
    mask = 1  # position 1 is reachable, bit 0 = current position

    def process_good(start, end):
        nonlocal cur, mask
        if start > end:
            return
        length = end - start + 1
        take = length if length <= P else P
        for _ in range(take):
            cur += 1
            b = ((mask >> (A - 1)) & range_mask) != 0
            mask = ((mask << 1) | (1 if b else 0)) & FULL
        if length > P:
            if mask:
                # eventually every position in this whole good interval is reachable
                cur = end
                mask = FULL
            else:
                cur = end
                mask = 0

    for L, R in bad:
        # good part between current position and L
        process_good(cur + 1, L - 1)
        # skip the bad interval
        gap = R - cur
        if gap >= B:
            mask = 0
        elif gap > 0:
            mask = (mask << gap) & FULL
        cur = R

    process_good(cur + 1, N)
    print("Yes" if (mask & 1) else "No")

if __name__ == "__main__":
    main()
