# FILE: solutions/abc388_g.py
import sys
from bisect import bisect_left

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N = data[0]
    A = data[1:1 + N]
    Q = data[1 + N]
    idx = 2 + N

    c = [0] * N
    for i, a in enumerate(A):
        j = bisect_left(A, a * 2)
        c[i] = j - i

    logs = [0] * (N + 2)
    for i in range(2, N + 2):
        logs[i] = logs[i >> 1] + 1

    st = [c]
    p = 1
    while (1 << p) <= N:
        step = 1 << (p - 1)
        prev = st[-1]
        size = N - (1 << p) + 1
        cur = [0] * size
        for i in range(size):
            x = prev[i]
            y = prev[i + step]
            cur[i] = x if x > y else y
        st.append(cur)
        p += 1

    def range_max(l, r):
        length = r - l + 1
        k = logs[length]
        row = st[k]
        offset = r - (1 << k) + 1
        x = row[l]
        y = row[offset]
        return x if x > y else y

    out = []
    for _ in range(Q):
        L = data[idx] - 1
        R = data[idx + 1] - 1
        idx += 2

        m = R - L + 1
        lo = 1
        hi = m // 2
        ans = 0

        while lo <= hi:
            mid = (lo + hi) >> 1
            mx = range_max(L, L + mid - 1)
            if mx <= m - mid:
                ans = mid
                lo = mid + 1
            else:
                hi = mid - 1

        out.append(str(ans))

    print("\n".join(out))

if __name__ == "__main__":
    main()
