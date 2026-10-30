import sys


def main() -> None:
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, mod = data
    half = n // 2
    max_edges = n * (n - 1) // 2

    choose = [[0] * (max_edges + 1) for _ in range(max_edges + 1)]
    choose[0][0] = 1
    for i in range(1, max_edges + 1):
        row = choose[i]
        prev = choose[i - 1]
        row[0] = 1
        for j in range(1, i):
            row[j] = (prev[j - 1] + prev[j]) % mod
        row[i] = 1

    # State: (even vertices, odd vertices, last level size, parity of last level).
    # A polynomial is represented in the basis (1+x)^k, not in the monomial basis.
    buckets = [dict() for _ in range(n + 1)]
    buckets[1][(1, 0, 1, 0)] = [1]

    for used in range(1, n):
        remaining = n - used
        for (even, odd, last, parity), poly in buckets[used].items():
            for size in range(1, remaining + 1):
                if parity == 0:
                    new_even, new_odd = even, odd + size
                else:
                    new_even, new_odd = even + size, odd
                if new_even > half or new_odd > half:
                    continue

                key = (new_even, new_odd, size, parity ^ 1)
                dest = buckets[used + size].get(key)
                if dest is None:
                    dest = []
                    buckets[used + size][key] = dest

                label_factor = choose[remaining][size]
                base_shift = size * (size - 1) // 2 + last * size

                # Inclusion-exclusion for requiring every new vertex to have
                # at least one edge to the preceding level.
                for missing in range(size + 1):
                    coefficient = label_factor * choose[size][missing] % mod
                    if missing & 1:
                        coefficient = (-coefficient) % mod
                    shift = base_shift - last * missing
                    needed = len(poly) + shift
                    if len(dest) < needed:
                        dest.extend([0] * (needed - len(dest)))
                    for degree, value in enumerate(poly):
                        if value:
                            index = degree + shift
                            dest[index] = (dest[index] + coefficient * value) % mod

    final = [0] * (max_edges + 1)
    for (even, odd, _last, _parity), poly in buckets[n].items():
        if even == half and odd == half:
            for degree, value in enumerate(poly):
                final[degree] = (final[degree] + value) % mod

    answers = []
    for edges in range(n - 1, max_edges + 1):
        total = 0
        for degree in range(edges, max_edges + 1):
            total = (total + final[degree] * choose[degree][edges]) % mod
        answers.append(str(total))

    print(" ".join(answers))


if __name__ == "__main__":
    main()
