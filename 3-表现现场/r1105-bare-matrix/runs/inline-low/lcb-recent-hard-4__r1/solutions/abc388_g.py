import sys
import bisect


def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    it = iter(data)
    N = next(it)
    A = [next(it) for _ in range(N)]
    Q = next(it)

    h = [0] * N
    for i, a in enumerate(A):
        p = bisect.bisect_left(A, a * 2)
        h[i] = p - i

    logs = [0] * (N + 1)
    for i in range(2, N + 1):
        logs[i] = logs[i // 2] + 1

    st = [h]
    j = 1
    while (1 << j) <= N:
        step = 1 << (j - 1)
        prev = st[-1]
        length = N - (1 << j) + 1
        cur = [0] * length
        for i in range(length):
            a = prev[i]
            b = prev[i + step]
            cur[i] = a if a >= b else b
        st.append(cur)
        j += 1

    out = []

    for _ in range(Q):
        L = next(it) - 1
        R = next(it) - 1
        n = R - L + 1

        lo = 0
        hi = n // 2

        while lo < hi:
            mid = (lo + hi + 1) // 2

            r = L + mid - 1
            jj = logs[mid]
            step = 1 << jj
            level = st[jj]

            a = level[L]
            b = level[r - step + 1]
            mx = a if a >= b else b

            if mx <= n - mid:
                lo = mid
            else:
                hi = mid - 1

        out.append(str(lo))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    solve()
