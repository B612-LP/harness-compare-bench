import sys
from bisect import bisect_left

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    a = [0] + data[1:1+n]
    pos = 1 + n
    q = data[pos]
    pos += 1
    # nxt[i] = first index j with A[j] >= 2*A[i] (or n+1)
    nxt = [0]*(n+1)
    for i in range(1, n+1):
        nxt[i] = bisect_left(a, 2*a[i], i+1, n+1)
    c = [0]*(n+1)
    for i in range(1, n+1):
        c[i] = nxt[i] - i

    # sparse table for range maximum of c[1..n]
    base = c[1:]
    st = [base]
    k = 1
    while (1 << k) <= n:
        prev = st[-1]
        half = 1 << (k-1)
        length = n - (1 << k) + 1
        cur = [0]*length
        for i in range(length):
            x = prev[i]
            y = prev[i+half]
            cur[i] = x if x >= y else y
        st.append(cur)
        k += 1

    def range_max(l, r):
        # 0-based inclusive
        length = r - l + 1
        kk = length.bit_length() - 1
        row = st[kk]
        x = row[l]
        y = row[r - (1 << kk) + 1]
        return x if x >= y else y

    out = []
    for _ in range(q):
        L = data[pos]
        R = data[pos+1]
        pos += 2
        S = R - L + 1
        lo, hi = 0, S // 2
        base_idx = L - 1
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            mx = range_max(base_idx, base_idx + mid - 1)
            if mid + mx <= S:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))
    sys.stdout.write("\n".join(out) + "\n")

if __name__ == '__main__':
    main()
