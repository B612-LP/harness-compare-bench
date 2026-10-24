import sys
from bisect import bisect_left


def main() -> None:
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n = data[0]
    arr = data[1:1 + n]
    q = data[1 + n]
    queries = data[2 + n:]

    # nxt[i] - i is what matters when i is the t-th upper mochi of a range.
    values = [0] * n
    for i, x in enumerate(arr):
        values[i] = bisect_left(arr, 2 * x) - i

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1

    sparse = [values]
    step = 1
    while (step << 1) <= n:
        prev = sparse[-1]
        size = n - (step << 1) + 1
        sparse.append([max(prev[i], prev[i + step]) for i in range(size)])
        step <<= 1

    def range_max(left: int, right: int) -> int:
        length = right - left + 1
        level = logs[length]
        row = sparse[level]
        width = 1 << level
        return max(row[left], row[right - width + 1])

    out = []
    for qi in range(q):
        left = queries[2 * qi] - 1
        right = queries[2 * qi + 1] - 1

        low, high = 0, (right - left + 1) // 2
        while low < high:
            mid = (low + high + 1) >> 1
            # For the t-th upper mochi (index left+t), the corresponding
            # lower mochi has index right-mid+1+t.
            threshold = right - mid + 1 - left
            if range_max(left, left + mid - 1) <= threshold:
                low = mid
            else:
                high = mid - 1
        out.append(str(low))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
