import sys
from bisect import bisect_left


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    A = list(map(int, data[1:1 + n]))
    q = int(data[1 + n])

    # w[t] = (smallest index j with A[j] >= 2*A[t]  [n if none]) - t
    # K pairs are feasible for [l, r]  <=>  max_{t in [l, l+K-1]} w[t] <= r-K+1-l
    w = [0] * n
    for t in range(n):
        w[t] = bisect_left(A, 2 * A[t], t + 1, n) - t

    # sparse table for range maximum
    logs = [0] * (n + 2)
    for i in range(2, n + 2):
        logs[i] = logs[i >> 1] + 1
    st = [w]
    k = 1
    while (1 << k) <= n:
        prev = st[-1]
        half = 1 << (k - 1)
        st.append([a if a > b else b for a, b in zip(prev, prev[half:])])
        k += 1

    out = []
    pos = 2 + n
    for _ in range(q):
        l = int(data[pos]) - 1
        r = int(data[pos + 1]) - 1
        pos += 2
        lo, hi = 0, (r - l + 1) >> 1
        # tight loop: binary search the largest feasible K
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            length = mid                      # window [l, l+mid-1]
            kk = logs[length]
            x = st[kk][l]
            y = st[kk][l + length - (1 << kk)]
            mx = x if x > y else y
            if mx <= r - mid + 1 - l:
                lo = mid
            else:
                hi = mid - 1
        out.append(lo)
    sys.stdout.write("\n".join(map(str, out)) + "\n")


main()
