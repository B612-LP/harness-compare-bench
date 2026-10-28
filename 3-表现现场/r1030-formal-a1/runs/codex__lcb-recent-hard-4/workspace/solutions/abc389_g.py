import sys


def main():
    n, mod = map(int, sys.stdin.buffer.read().split())
    half = n // 2
    max_edges = n * (n - 1) // 2

    # Binomial coefficients, including those used for (1+x)^e.
    comb = [[0] * (max_edges + 1) for _ in range(max_edges + 1)]
    comb[0][0] = 1
    for i in range(1, max_edges + 1):
        comb[i][0] = comb[i][i] = 1
        previous = comb[i - 1]
        row = comb[i]
        for j in range(1, i):
            row[j] = (previous[j - 1] + previous[j]) % mod

    # A BFS layer has a fixed parity.  State:
    # (used_even, used_odd, previous_layer_size, previous_layer_parity).
    # The attached polynomial is stored as coefficients of (1+x)^e.
    dp = {(0, 0, 1, 0): [1] + [0] * max_edges}
    final_poly = [0] * (max_edges + 1)
    target_even = half - 1
    target_odd = half

    for _ in range(1, n):
        next_dp = {}
        for (used_even, used_odd, previous_size, parity), poly in dp.items():
            if parity == 0:
                remaining = target_odd - used_odd
            else:
                remaining = target_even - used_even
            if remaining <= 0:
                continue

            for size in range(1, remaining + 1):
                choose_vertices = comb[remaining][size]
                inside_edges = size * (size - 1) // 2

                if parity == 0:
                    key = (used_even, used_odd + size, size, 1)
                else:
                    key = (used_even + size, used_odd, size, 0)

                out = next_dp.get(key)
                if out is None:
                    out = [0] * (max_edges + 1)
                    next_dp[key] = out

                # Inclusion-exclusion over new vertices with no edge to the
                # previous layer.  Each term contributes (1+x)^delta.
                for zero_degree in range(size + 1):
                    delta = inside_edges + previous_size * (size - zero_degree)
                    coefficient = choose_vertices * comb[size][zero_degree] % mod
                    if zero_degree & 1:
                        coefficient = (-coefficient) % mod
                    limit = max_edges - delta
                    for exponent in range(limit + 1):
                        value = poly[exponent]
                        if value:
                            out[exponent + delta] = (
                                out[exponent + delta] + value * coefficient
                            ) % mod

        for (used_even, used_odd, _, _), poly in next_dp.items():
            if used_even == target_even and used_odd == target_odd:
                for exponent, value in enumerate(poly):
                    if value:
                        final_poly[exponent] = (
                            final_poly[exponent] + value
                        ) % mod
        dp = next_dp

    # Choose which non-root vertices have even distance.
    parity_choices = comb[n - 1][half - 1]

    answers = []
    for edges in range(n - 1, max_edges + 1):
        ways = 0
        for exponent in range(edges, max_edges + 1):
            ways = (ways + final_poly[exponent] * comb[exponent][edges]) % mod
        answers.append(str(ways * parity_choices % mod))

    sys.stdout.write(" ".join(answers))


if __name__ == "__main__":
    main()
