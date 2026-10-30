import sys
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    idx = 0
    N = data[idx]; idx += 1
    A = data[idx:idx + N]; idx += N
    Q = data[idx]; idx += 1

    # nxt[s] = smallest j >= s+1 with 2*A[s] <= A[j]; N if none.
    nxt = [0] * N
    for s in range(N):
        j = bisect_left(A, 2 * A[s], s + 1, N)
        nxt[s] = j
    # m[s] = nxt[s] - s
    m = [nxt[s] - s for s in range(N)]

    # Sparse table for range maximum of m.
    LOG = N.bit_length()
    st = [m]
    k = 1
    while (1 << k) <= N:
        prev = st[-1]
        half = 1 << (k - 1)
        length = N - (1 << k) + 1
        cur = [0] * length
        for i in range(length):
            a = prev[i]
            b = prev[i + half]
            cur[i] = a if a >= b else b
        st.append(cur)
        k += 1

    def rmq_max(l, r):
        # inclusive [l, r]
        length = r - l + 1
        k = length.bit_length() - 1
        block = 1 << k
        a = st[k][l]
        b = st[k][r - block + 1]
        return a if a >= b else b

    out = []
    for _ in range(Q):
        L = data[idx] - 1; idx += 1
        R = data[idx] - 1; idx += 1
        nseg = R - L + 1
        half = (nseg + 1) // 2  # big pointer starts L + ceil(n/2)
        lo, hi = 0, nseg // 2
        # K feasible iff L + K - 1 + max(half, max m[L..L+K-1]) <= R
        while lo < hi:
            mid = (lo + hi + 1) // 2
            mx = rmq_max(L, L + mid - 1)
            if mx < half:
                mx = half
            if mx + L + mid - 1 <= R:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))
    sys.stdout.write("\n".join(out))


if __name__ == '__main__':
    main()
