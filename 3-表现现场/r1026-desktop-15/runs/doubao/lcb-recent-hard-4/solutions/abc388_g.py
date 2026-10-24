import sys
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    it = iter(data)
    N = next(it)
    A = [next(it) for _ in range(N)]
    Q = next(it)

    # C[i] = first index j with 2*A[i] <= A[j]
    C = [bisect_left(A, 2 * a) for a in A]
    E = [C[i] - i for i in range(N)]

    # sparse table for range maximum of E
    LOG = N.bit_length()
    st = [E]
    k = 1
    while (1 << k) <= N:
        prev = st[-1]
        half = 1 << (k - 1)
        length = N - (1 << k) + 1
        cur = [max(prev[i], prev[i + half]) for i in range(length)]
        st.append(cur)
        k += 1
    # log2 table
    lg = [0] * (N + 2)
    for i in range(2, N + 2):
        lg[i] = lg[i >> 1] + 1

    def range_max(l, r):
        # inclusive
        t = lg[r - l + 1]
        row = st[t]
        return max(row[l], row[r - (1 << t) + 1])

    out = []
    for _ in range(Q):
        L = next(it) - 1
        R = next(it) - 1
        n = R - L + 1
        hi = n // 2
        lo = 0
        # K feasible iff max(E[L..L+K-1]) + L + K - 1 <= R
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if range_max(L, L + mid - 1) + L + mid - 1 <= R:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
