import sys
from bisect import bisect_left


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    pos = 0
    n = int(data[pos]); pos += 1
    A = [int(x) for x in data[pos:pos + n]]; pos += n
    q = int(data[pos]); pos += 1

    # nxt[i] = smallest j with A[j] >= 2*A[i]  (n if none)
    nxt = [0] * n
    for i in range(n):
        nxt[i] = bisect_left(A, 2 * A[i], i + 1)
    h = [nxt[i] - i for i in range(n)]

    # sparse table for range maximum of h
    LOG = max(1, n.bit_length())
    sp = [h]
    k = 1
    while (1 << k) <= n:
        prev = sp[-1]
        half = 1 << (k - 1)
        cur = [prev[i] if prev[i] >= prev[i + half] else prev[i + half]
               for i in range(n - (1 << k) + 1)]
        sp.append(cur)
        k += 1
    logt = [0] * (n + 1)
    for i in range(2, n + 1):
        logt[i] = logt[i >> 1] + 1

    out = []
    for _ in range(q):
        L = int(data[pos]) - 1; R = int(data[pos + 1]) - 1; pos += 2
        lo, hi = 0, (R - L + 1) // 2
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            kk = logt[mid]
            row = sp[kk]
            mx = row[L]
            v2 = row[L + mid - (1 << kk)]
            if v2 > mx:
                mx = v2
            if R - mid + 1 >= L + mx:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out) + "\n")


main()
