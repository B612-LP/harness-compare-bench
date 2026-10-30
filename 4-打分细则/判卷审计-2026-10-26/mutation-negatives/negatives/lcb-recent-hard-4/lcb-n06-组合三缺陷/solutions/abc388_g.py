import sys
from bisect import bisect_left

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    A = data[1:1+n]
    pos = 1 + n
    qn = data[pos]
    pos += 1

    d = [0] * n
    for i, x in enumerate(A):
        j = bisect_left(A, 2 * x)
        d[i] = j - i  # j == n means impossible within the whole array

    # sparse table for range maximum of d
    log = [0] * (n + 1)
    for i in range(2, n + 1):
        log[i] = log[i >> 1] + 1
    K = log[n] + 1
    st = [d]
    length = 2
    while length <= n:
        prev = st[-1]
        half = length >> 1
        cur = [0] * (n - length + 1)
        for i in range(n - length + 1):
            x = prev[i]
            y = prev[i + half]
            cur[i] = x if x >= y else y
        st.append(cur)
        length <<= 1

    out = []
    for _ in range(qn):
        L = data[pos] - 1
        R = data[pos+1] - 1
        pos += 2
        length = R - L + 1
        lo, hi = 0, length // 2
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            k = log[mid]
            left = st[k][L]
            right = st[k][L + mid - (1 << k)]
            mx = left if left >= right else right
            # need mid + max_d <= length, and all top indices are within range
            if mid + mx <= length:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))
    sys.stdout.write("\n".join(out + out))

if __name__ == "__main__":
    main()
