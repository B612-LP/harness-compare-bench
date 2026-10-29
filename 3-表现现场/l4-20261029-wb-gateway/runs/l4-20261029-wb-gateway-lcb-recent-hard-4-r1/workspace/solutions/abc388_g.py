import sys
from bisect import bisect_left


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    idx = 0
    n = int(data[idx]); idx += 1
    A = [int(x) for x in data[idx:idx + n]]; idx += n
    q = int(data[idx]); idx += 1

    INF = 1 << 60
    # g[i] = f(i) - i, where f(i) = smallest j with 2*A[i] <= A[j]
    g = [0] * n
    for i in range(n):
        j = bisect_left(A, 2 * A[i])
        g[i] = (j if j < n else INF) - i

    LOG = max(1, n.bit_length())
    sp = [g]
    k = 1
    while (1 << k) <= n:
        prev = sp[k - 1]
        half = 1 << (k - 1)
        length = n - (1 << k) + 1
        sp.append([prev[i] if prev[i] >= prev[i + half] else prev[i + half]
                   for i in range(length)])
        k += 1

    out = []
    for _ in range(q):
        L = int(data[idx]) - 1; R = int(data[idx + 1]) - 1; idx += 2
        lo = 0
        hi = (R - L + 1) >> 1
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            kk = mid.bit_length() - 1
            row = sp[kk]
            w = 1 << kk
            a = row[L]
            b2 = row[L + mid - w]
            mx = a if a >= b2 else b2
            if mx <= R - mid + 1 - L:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out) + "\n")


main()
