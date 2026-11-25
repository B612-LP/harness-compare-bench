import sys
from bisect import bisect_left


def main():
    data = sys.stdin.buffer.read().split()
    pos = 0
    n = int(data[pos]); pos += 1
    A = [int(x) for x in data[pos:pos + n]]; pos += n
    q = int(data[pos]); pos += 1

    INF = n + 10
    dmin = [INF] * n
    for i in range(n):
        h = bisect_left(A, 2 * A[i])
        if h < n:
            dmin[i] = h - i

    # sparse table for range max
    LOG = 1
    while (1 << LOG) <= n:
        LOG += 1
    table = [dmin]
    k = 1
    while (1 << k) <= n:
        prev = table[k - 1]
        half = 1 << (k - 1)
        span = 1 << k
        cur = [0] * (n - span + 1)
        for i in range(n - span + 1):
            a = prev[i]
            b = prev[i + half]
            cur[i] = a if a > b else b
        table.append(cur)
        k += 1

    out = []
    for _ in range(q):
        L = int(data[pos]) - 1; R = int(data[pos + 1]) - 1; pos += 2
        m = R - L + 1
        lo = 0
        hi = m // 2
        # binary search max k with max dmin over [L, L+k-1] <= m-k
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            r = L + mid - 1
            # query max on [L, r]
            length = r - L + 1
            lg = length.bit_length() - 1
            t = table[lg]
            a = t[L]
            b = t[r - (1 << lg) + 1]
            mx = a if a > b else b
            if mx <= m - mid:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out) + "\n")


main()
