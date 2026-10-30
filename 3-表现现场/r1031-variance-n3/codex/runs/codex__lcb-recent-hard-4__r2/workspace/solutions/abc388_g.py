import sys
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n = data[0]
    a = data[1:1 + n]
    q = data[1 + n]
    at = 2 + n

    nxt = [bisect_left(a, 2 * x) for x in a]
    offset = [i - nxt[i] for i in range(n)]

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i // 2] + 1

    sparse = [offset]
    width = 1
    while width * 2 <= n:
        previous = sparse[-1]
        size = n - width * 2 + 1
        sparse.append([min(previous[i], previous[i + width]) for i in range(size)])
        width *= 2

    def range_min(left, right):
        length = right - left + 1
        k = logs[length]
        row = sparse[k]
        width_k = 1 << k
        return min(row[left], row[right - width_k + 1])

    out = []
    for _ in range(q):
        left = data[at] - 1
        right = data[at + 1] - 1
        at += 2
        length = right - left + 1
        low, high = 0, length // 2
        while low < high:
            mid = (low + high + 1) // 2
            if mid <= length + range_min(left, left + mid - 1):
                low = mid
            else:
                high = mid - 1
        out.append(str(low))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
