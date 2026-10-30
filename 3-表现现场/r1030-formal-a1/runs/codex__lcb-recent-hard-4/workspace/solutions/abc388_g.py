import sys
from array import array
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n = data[0]
    values = data[1:1 + n]
    q = data[1 + n]

    # need[i] - i is the minimum offset D such that A[i+D] >= 2*A[i].
    need = [bisect_left(values, 2 * x) - i for i, x in enumerate(values)]

    sparse = [array('i', need)]
    half = 1
    while 2 * half <= n:
        previous = sparse[-1]
        length = n - 2 * half + 1
        sparse.append(array('i', (
            max(previous[i], previous[i + half]) for i in range(length)
        )))
        half *= 2

    def range_max(left, right):
        level = (right - left + 1).bit_length() - 1
        width = 1 << level
        row = sparse[level]
        x = row[left]
        y = row[right - width + 1]
        return x if x >= y else y

    out = []
    pos = 2 + n
    for _ in range(q):
        left = data[pos] - 1
        right = data[pos + 1] - 1
        pos += 2
        length = right - left + 1

        low, high = 0, length // 2
        while low < high:
            mid = (low + high + 1) // 2
            offset = length - mid
            if range_max(left, left + mid - 1) <= offset:
                low = mid
            else:
                high = mid - 1
        out.append(str(low))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
