import sys

def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N, M, A, B = data[:4]
    bad = []
    idx = 4
    for _ in range(M):
        L, R = data[idx], data[idx + 1]
        idx += 2
        bad.append((L, R))

    full = (1 << B) - 1
    allow = 0
    for k in range(A - 1, B):
        allow |= 1 << k

    def process_good(mask, length):
        if length <= 0:
            return mask
        if mask == 0:
            return 0

        if length <= 1000:
            for _ in range(length):
                if mask & allow:
                    mask = ((mask << 1) & full) | 1
                else:
                    mask = (mask << 1) & full
            return mask

        seen = {}
        steps = 0

        while length > 0:
            if mask in seen:
                cycle = steps - seen[mask]
                length %= cycle
                for _ in range(length):
                    if mask & allow:
                        mask = ((mask << 1) & full) | 1
                    else:
                        mask = (mask << 1) & full
                return mask

            seen[mask] = steps
            steps += 1

            if mask & allow:
                mask = ((mask << 1) & full) | 1
            else:
                mask = (mask << 1) & full

            length -= 1

        return mask

    def process_bad(mask, length):
        if length <= 0 or mask == 0:
            return mask
        if length >= B:
            return 0

        for _ in range(length):
            mask = (mask << 1) & full
        return mask

    cur = 1
    mask = 1

    for L, R in bad:
        good_len = L - cur - 1
        if good_len > 0:
            mask = process_good(mask, good_len)
            cur += good_len

        bad_len = R - L + 1
        mask = process_bad(mask, bad_len)
        cur = R

    good_len = N - cur
    if good_len > 0:
        mask = process_good(mask, good_len)

    print("Yes" if (mask & 1) else "No")


if __name__ == "__main__":
    solve()
