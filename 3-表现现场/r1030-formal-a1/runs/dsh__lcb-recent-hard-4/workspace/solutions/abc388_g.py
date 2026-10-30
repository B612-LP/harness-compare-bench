import sys
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    A = data[1:1 + n]
    pos = 1 + n
    q = data[pos]
    pos += 1

    # nxt[i] = first index j with A[j] >= 2*A[i]  (0-indexed, n if none)
    nxt = [0] * n
    for i in range(n):
        nxt[i] = bisect_left(A, 2 * A[i])

    # D[i] = nxt[i] - i.  For a query [L,R] and K pairs we need
    # max_{i=L..L+K-1} D[i] <= (R-L+1) - K.
    D = [nxt[i] - i for i in range(n)]

    # Sparse table for range maximum of D.
    st = [D]
    length = 2
    while length <= n:
        half = length >> 1
        prev = st[-1]
        size = n - length + 1
        cur = [0] * size
        for i in range(size):
            a = prev[i]
            b = prev[i + half]
            cur[i] = a if a >= b else b
        st.append(cur)
        length <<= 1

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1

    out = []
    for _ in range(q):
        L = data[pos] - 1
        R = data[pos + 1] - 1
        pos += 2
        total = R - L + 1
        lo, hi = 0, total // 2
        # binary search for the largest feasible K
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            k = logs[mid]
            # max D over [L, L+mid-1]
            a = st[k][L]
            b = st[k][L + mid - (1 << k)]
            mx = a if a >= b else b
            if mx <= total - mid:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out) + ("\n" if out else ""))


if __name__ == "__main__":
    main()
