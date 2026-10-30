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

    h = [0] * N
    for i, a in enumerate(A):
        h[i] = bisect_left(A, 2 * a) - i

    log = [0] * (N + 1)
    for i in range(2, N + 1):
        log[i] = log[i >> 1] + 1

    st = [h]
    j = 1
    while (1 << j) <= N:
        prev = st[-1]
        half = 1 << (j - 1)
        ln = N - (1 << j) + 1
        cur = [0] * ln
        for i in range(ln):
            x = prev[i]
            y = prev[i + half]
            cur[i] = x if x >= y else y
        st.append(cur)
        j += 1

    out = []
    for _ in range(Q):
        L = data[idx] - 1
        R = data[idx + 1] - 1
        idx += 2
        m = R - L + 1
        lo, hi = 0, m // 2
        while lo < hi:
            k = (lo + hi + 1) // 2
            jj = log[k]
            row = st[jj]
            x = row[L]
            y = row[L + k - (1 << jj)]
            mx = x if x >= y else y
            if mx + k <= m:
                lo = k
            else:
                hi = k - 1
        out.append(str(lo))

    sys.stdout.write('\n'.join(out))

if __name__ == '__main__':
    main()
