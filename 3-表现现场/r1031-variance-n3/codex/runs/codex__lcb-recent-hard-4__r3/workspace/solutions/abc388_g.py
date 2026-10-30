import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n = data[0]
    a = data[1:1 + n]
    pos = 1 + n
    q = data[pos]
    queries = data[pos + 1:pos + 1 + 2 * q]

    nearest = [0] * n
    right = 0
    for i in range(n):
        if right <= i:
            right = i + 1
        threshold = 2 * a[i]
        while right < n and a[right] < threshold:
            right += 1
        nearest[i] = right - i

    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1

    sparse = [nearest]
    level = 1
    while (1 << level) <= n:
        previous = sparse[-1]
        half = 1 << (level - 1)
        length = n - (1 << level) + 1
        current = [0] * length
        for i in range(length):
            x = previous[i]
            y = previous[i + half]
            current[i] = x if x >= y else y
        sparse.append(current)
        level += 1

    answers = []
    for qi in range(q):
        left = queries[2 * qi] - 1
        right_end = queries[2 * qi + 1] - 1
        length = right_end - left + 1

        low = 0
        high = length // 2 + 1
        while low + 1 < high:
            mid = (low + high) // 2
            distance = length - mid

            k = logs[mid]
            row = sparse[k]
            maximum = row[left]
            other = row[left + mid - (1 << k)]
            if other > maximum:
                maximum = other

            if maximum <= distance:
                low = mid
            else:
                high = mid

        answers.append(str(low))

    sys.stdout.write("\n".join(answers))


if __name__ == "__main__":
    main()
