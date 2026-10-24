import sys
from bisect import bisect_left


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n = data[0]
    sizes = data[1:1 + n]
    q = data[1 + n]
    queries = data[2 + n:2 + n + 2 * q]

    need = [bisect_left(sizes, 2 * size) for size in sizes]
    gaps = [need[i] - i for i in range(n)]

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i // 2] + 1

    table = [gaps]
    level = 1
    while (1 << level) <= n:
        half = 1 << (level - 1)
        previous = table[-1]
        size = n - (1 << level) + 1
        table.append([max(previous[i], previous[i + half]) for i in range(size)])
        level += 1

    answers = []
    for index in range(0, 2 * q, 2):
        left = queries[index] - 1
        right = queries[index + 1] - 1
        length = right - left + 1
        low, high = 0, length // 2

        while low < high:
            middle = (low + high + 1) // 2
            k = logs[middle]
            row = table[k]
            span = 1 << k
            maximum = max(row[left], row[left + middle - span])
            if maximum + middle <= length:
                low = middle
            else:
                high = middle - 1

        answers.append(str(low))

    sys.stdout.write("\n".join(answers))


if __name__ == "__main__":
    main()
