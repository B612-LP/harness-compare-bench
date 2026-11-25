import sys
from bisect import bisect_left


def main():
    input = sys.stdin.buffer.readline
    n = int(input())
    a = list(map(int, input().split()))
    q = int(input())
    queries = [tuple(map(int, input().split())) for _ in range(q)]

    inf = 10**9
    b = [inf] * n
    for i in range(n):
        j = bisect_left(a, 2 * a[i], i + 1, n)
        if j < n:
            b[i] = j - i

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1

    st = [b]
    length = 1
    while (length << 1) <= n:
        prev = st[-1]
        size = n - (length << 1) + 1
        cur = [0] * size
        for i in range(size):
            x = prev[i]
            y = prev[i + length]
            cur[i] = x if x >= y else y
        st.append(cur)
        length <<= 1

    def range_max(left, right):
        length = right - left + 1
        k = logs[length]
        row = st[k]
        x = row[left]
        y = row[right - (1 << k) + 1]
        return x if x >= y else y

    out = []
    for left, right in queries:
        left -= 1
        right -= 1
        lo, hi = 0, (right - left + 1) // 2
        while lo < hi:
            mid = (lo + hi + 1) >> 1
            if range_max(left, left + mid - 1) <= right - mid + 1 - left:
                lo = mid
            else:
                hi = mid - 1
        out.append(str(lo))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
