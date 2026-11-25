import sys


def main():
    data = sys.stdin.buffer.read().split()
    N = int(data[0])
    M = int(data[1])
    A = int(data[2])
    B = int(data[3])
    bad = []
    idx = 4
    for _ in range(M):
        L = int(data[idx]); R = int(data[idx + 1])
        idx += 2
        bad.append((L, R))

    if A == B:
        ok = ((N - 1) % A == 0)
        if ok:
            for L, R in bad:
                # first x >= L with x ≡ 1 (mod A)
                x = L + ((1 - L) % A)
                if x <= R and x <= N:
                    ok = False
                    break
        sys.stdout.write("Yes\n" if ok else "No\n")
        return

    # good runs
    runs = []
    prev = 1
    for L, R in bad:
        if prev <= L - 1:
            runs.append((prev, L - 1))
        prev = R + 1
    if prev <= N:
        runs.append((prev, N))

    low_mask = (1 << (B - A + 1)) - 1
    full = (1 << B) - 1

    p = 0
    mask = 0
    for s, e in runs:
        gap = s - 1 - p
        if gap > 0:
            if gap >= B:
                mask = 0
            else:
                mask >>= gap
            p = s - 1
        if s == 1 and p == 0:
            mask = 1 << (B - 1)
            p = 1
            i = 2
        else:
            i = s
        if mask == 0:
            p = e
            continue
        while i <= e:
            if mask == full:
                p = e
                break
            bit = 1 if (mask & low_mask) else 0
            mask = ((mask >> 1) | (bit << (B - 1))) & full
            p = i
            i += 1
            if mask == 0:
                p = e
                break

    ok = (p == N and ((mask >> (B - 1)) & 1) == 1)
    sys.stdout.write("Yes\n" if ok else "No\n")


main()
