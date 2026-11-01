import sys
from functools import lru_cache

def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N, M, A, B = data[:4]
    intervals = []
    idx = 4
    for _ in range(M):
        intervals.append((data[idx], data[idx + 1]))
        idx += 2

    full = (1 << B) - 1
    win = 0
    for d in range(A, B + 1):
        win |= 1 << (d - 1)

    def trans_good(mask):
        return ((mask << 1) | (1 if (mask & win) else 0)) & full

    @lru_cache(None)
    def jump(mask, k):
        if k == 0:
            return trans_good(mask)
        return jump(jump(mask, k - 1), k - 1)

    def apply_good(mask, length):
        bit = 0
        while length:
            if length & 1:
                mask = jump(mask, bit)
            length >>= 1
            bit += 1
        return mask

    mask = 0
    pos = 1

    for L, R in intervals:
        end = L - 1
        if pos <= end:
            length = end - pos + 1
            if pos == 1:
                mask = ((mask << 1) | 1) & full
                pos += 1
                length -= 1
            if length > 0:
                mask = apply_good(mask, length)
                pos += length

        if pos <= R:
            bad_len = R - pos + 1
            if bad_len >= B:
                mask = 0
            else:
                for _ in range(bad_len):
                    mask = (mask << 1) & full

        pos = R + 1

    if pos <= N:
        length = N - pos + 1
        if pos == 1:
            mask = ((mask << 1) | 1) & full
            pos += 1
            length -= 1
        if length > 0:
            mask = apply_good(mask, length)

    print("Yes" if (mask & 1) else "No")


if __name__ == "__main__":
    solve()
