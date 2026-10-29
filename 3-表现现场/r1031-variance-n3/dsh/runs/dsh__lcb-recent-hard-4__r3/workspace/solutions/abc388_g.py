import sys
from bisect import bisect_left

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    a = data[1:1 + n]
    pos = 1 + n
    qn = data[pos]
    pos += 1

    c = [0] * n
    for i in range(n):
        j = bisect_left(a, 2 * a[i], i + 1)
        c[i] = j - i

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1
    K = logs[n] + 1
    st = [c]
    for k in range(1, K):
        prev = st[-1]
        half = 1 << (k - 1)
        length = n - (1 << k) + 1
        if length <= 0:
            break
        cur = [0] * length
        for i in range(length):
            x = prev[i]
            y = prev[i + half]
            cur[i] = x if x > y else y
        st.append(cur)

    def range_max(l, r):
        k = logs[r - l + 1]
        row = st[k]
        x = row[l]
        y = row[r - (1 << k) + 1]
        return x if x > y else y

    out = []
    for _ in range(qn):
        l = data[pos] - 1
        r = data[pos + 1] - 1
        pos += 2
        length = r - l + 1
        lo, hi = 0, length // 2
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            if range_max(l, l + mid - 1) <= length - mid:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()
