import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    A = [int(x) for x in data[1:1 + n]]
    qn = int(data[1 + n])
    ptr = 2 + n
    INF = 1 << 60

    # c[i] = smallest j with 2*A[i] <= A[j]   (non decreasing)
    c = [0] * n
    j = 0
    for i in range(n):
        if j < i + 1:
            j = i + 1
        ai2 = 2 * A[i]
        while j < n and A[j] < ai2:
            j += 1
        c[i] = j if j < n else INF + i
    d = [c[i] - i for i in range(n)]

    # sparse table for range max of d
    LOG = [0] * (n + 1)
    for i in range(2, n + 1):
        LOG[i] = LOG[i >> 1] + 1
    K = LOG[n] + 1
    st = [d]
    k = 1
    while (1 << k) <= n:
        prev = st[-1]
        step = 1 << (k - 1)
        ln = n - (1 << k) + 1
        cur = [0] * max(ln, 1)
        for i in range(ln):
            x = prev[i]
            y = prev[i + step]
            cur[i] = x if x > y else y
        st.append(cur)
        k += 1

    out = []
    for _ in range(qn):
        l = int(data[ptr]) - 1
        r = int(data[ptr + 1]) - 1
        ptr += 2
        lo_k = 0
        hi_k = (r - l + 1) >> 1
        limit = r + 1 - l
        # binary search largest k with max(d[l..l+k-1]) + k <= limit
        best = 0
        a1, b1 = 0, hi_k
        while a1 <= b1:
            mid = (a1 + b1) >> 1
            if mid == 0:
                best = 0
                a1 = 1
                continue
            rr = l + mid - 1
            ln = rr - l + 1
            kk = LOG[ln]
            row = st[kk]
            x = row[l]
            y = row[rr - (1 << kk) + 1]
            mx = x if x > y else y
            if mx + mid <= limit:
                best = mid
                a1 = mid + 1
            else:
                b1 = mid - 1
        out.append(str(best))

    sys.stdout.write("\n".join(out) + "\n")


main()
