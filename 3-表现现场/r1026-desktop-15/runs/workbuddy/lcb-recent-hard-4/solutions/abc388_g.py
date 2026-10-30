import sys
from array import array
from bisect import bisect_left


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    a = [int(v) for v in data[1:1 + n]]
    q = int(data[1 + n])

    INF = 1 << 30
    # need[i] = minimal index j with a[j] >= 2*a[i]; cost[i] = need[i]-i
    cost = [0] * n
    for i in range(n):
        j = bisect_left(a, 2 * a[i], i + 1)
        cost[i] = (j - i) if j < n else INF

    # sparse table for range maximum
    sp = [array('i', cost)]
    k = 1
    while (1 << k) <= n:
        prev = sp[-1]
        half = 1 << (k - 1)
        length = n - (1 << k) + 1
        cur = array('i', [0]) * length
        for i in range(length):
            x = prev[i]
            y = prev[i + half]
            cur[i] = x if x > y else y
        sp.append(cur)
        k += 1

    out = []
    p = 2 + n
    for _ in range(q):
        l = int(data[p]) - 1
        r = int(data[p + 1]) - 1
        p += 2
        length = r - l + 1
        lo = 0
        hi = length // 2
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            kk = mid.bit_length() - 1
            e = l + mid - 1
            t1 = sp[kk][l]
            t2 = sp[kk][e - (1 << kk) + 1]
            mx = t1 if t1 > t2 else t2
            if mx <= length - mid:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out) + "\n")


main()
