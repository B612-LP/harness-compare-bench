import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    A = data[1:1+n]
    q = data[1+n]
    queries = []
    idx = 2+n
    for _ in range(q):
        queries.append((data[idx], data[idx+1]))
        idx += 2

    # B[j] (0-indexed) = first index with A[index] >= 2*A[j], or n
    import bisect
    B = [0] * n
    for j in range(n):
        B[j] = bisect.bisect_left(A, 2 * A[j], j + 1, n)
    D = [B[j] - j for j in range(n)]

    LOG = max(1, n.bit_length())
    sp = [D]
    k = 1
    while (1 << k) <= n:
        prev = sp[-1]
        step = 1 << (k - 1)
        length = n - (1 << k) + 1
        cur = [0] * length
        for i in range(length):
            x = prev[i]
            y = prev[i + step]
            cur[i] = x if x >= y else y
        sp.append(cur)
        k += 1

    def range_max(l, r):
        # inclusive, 0-indexed
        length = r - l + 1
        k = length.bit_length() - 1
        x = sp[k][l]
        y = sp[k][r - (1 << k) + 1]
        return x if x >= y else y

    out = []
    for L, R in queries:
        l = L - 1
        r = R - 1
        lo, hi = 0, (r - l + 1) // 2
        while lo < hi:
            mid = (lo + hi + 1) // 2
            mx = range_max(l, l + mid - 1)
            if r >= (l + mid - 1) + mx:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))
    sys.stdout.write("\n".join(out) + ("\n" if out else ""))

if __name__ == "__main__":
    main()
