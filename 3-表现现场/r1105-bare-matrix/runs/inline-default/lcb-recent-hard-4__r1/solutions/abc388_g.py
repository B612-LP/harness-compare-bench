import sys
from bisect import bisect_left


def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N = data[0]
    A = data[1:1 + N]
    Q = data[1 + N]
    idx = 2 + N

    d = [0] * N
    for i, x in enumerate(A):
        j = bisect_left(A, 2 * x, i + 1)
        d[i] = j - i

    logs = [0] * (N + 1)
    for i in range(2, N + 1):
        logs[i] = logs[i >> 1] + 1

    st = [d]
    j = 1
    while (1 << j) <= N:
        prev = st[-1]
        step = 1 << (j - 1)
        length = N - (1 << j) + 1
        cur = [0] * length
        for i in range(length):
            a = prev[i]
            b = prev[i + step]
            cur[i] = a if a > b else b
        st.append(cur)
        j += 1

    def range_max(l, r):
        length = r - l + 1
        k = logs[length]
        row = st[k]
        a = row[l]
        b = row[r - (1 << k) + 1]
        return a if a > b else b

    answers = []

    for _ in range(Q):
        L = data[idx] - 1
        R = data[idx + 1] - 1
        idx += 2

        length = R - L + 1
        lo, hi = 0, length // 2

        while lo < hi:
            mid = (lo + hi + 1) // 2
            mx = range_max(L, L + mid - 1)
            if mx <= length - mid:
                lo = mid
            else:
                hi = mid - 1

        answers.append(str(lo))

    print("\n".join(answers))


if __name__ == "__main__":
    solve()
