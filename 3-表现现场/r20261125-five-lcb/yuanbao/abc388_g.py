import sys

def solve() -> None:
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N = data[0]
    A = [0] + data[1:1 + N]
    pos = 1 + N
    Q = data[pos]
    pos += 1

    c = [0] * (N + 1)
    j = 1
    for i in range(1, N + 1):
        if j < i + 1:
            j = i + 1
        need = 2 * A[i]
        while j <= N and A[j] < need:
            j += 1
        c[i] = (j - i) if j <= N else (N + 1 - i)

    lg = [0] * (N + 1)
    for i in range(2, N + 1):
        lg[i] = lg[i >> 1] + 1
    K = lg[N] + 1
    st = [c]
    for k in range(1, K):
        half = 1 << (k - 1)
        length = 1 << k
        prev = st[k - 1]
        row = [0] * (N + 1)
        end = N - length + 1
        for i in range(1, end + 1):
            a = prev[i]
            b = prev[i + half]
            row[i] = a if a >= b else b
        st.append(row)

    def rmq(l, r):
        if l > r:
            return -1
        k = lg[r - l + 1]
        a = st[k][l]
        b = st[k][r - (1 << k) + 1]
        return a if a >= b else b

    out = []
    for _ in range(Q):
        L = data[pos]; R = data[pos + 1]
        pos += 2
        n = R - L + 1
        lo = (n + 1) // 2
        hi = n
        while lo < hi:
            mid = (lo + hi) // 2
            e = R - mid
            if e < L or rmq(L, e) <= mid:
                hi = mid
            else:
                lo = mid + 1
        d = lo
        out.append(str(n - d))
    sys.stdout.write('\n'.join(out))

if __name__ == '__main__':
    solve()