# FILE: solutions/abc388_f.py
import sys
from array import array

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N, M, A, B = data[0], data[1], data[2], data[3]
    intervals = []
    idx = 4
    for _ in range(M):
        L = data[idx]
        R = data[idx + 1]
        idx += 2
        intervals.append((L, R))

    S = 1 << B
    FULL = S - 1

    lower = (1 << (A - 1)) - 1
    wmask = FULL & ~lower

    first = array('I', [0]) * S
    for mask in range(S):
        reach = 1 if (mask & wmask) else 0
        first[mask] = ((mask << 1) & FULL) | reach

    levels = [first]
    max_bit = max(1, N.bit_length())

    for _ in range(1, max_bit):
        prev = levels[-1]
        cur = array('I', [0]) * S
        for i in range(S):
            cur[i] = prev[prev[i]]
        levels.append(cur)

    def apply_good(mask, length):
        bit = 0
        while length:
            if length & 1:
                mask = levels[bit][mask]
            length >>= 1
            bit += 1
        return mask

    mask = 1
    cur_pos = 1

    for L, R in intervals:
        gap = L - cur_pos - 1
        if gap > 0:
            mask = apply_good(mask, gap)

        length = R - L + 1
        if length >= B:
            mask = 0
        else:
            mask = (mask << length) & FULL

        cur_pos = R

    gap = N - cur_pos
    if gap > 0:
        mask = apply_good(mask, gap)

    print("Yes" if (mask & 1) else "No")

if __name__ == "__main__":
    main()
