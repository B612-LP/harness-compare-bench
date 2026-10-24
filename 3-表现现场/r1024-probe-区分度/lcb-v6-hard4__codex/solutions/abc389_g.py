import sys


def main():
    n, mod = map(int, sys.stdin.buffer.read().split())
    max_edges = n * (n - 1) // 2
    half = n // 2

    choose = [[0] * (max_edges + 1) for _ in range(max_edges + 1)]
    choose[0][0] = 1
    for d in range(1, max_edges + 1):
        choose[d][0] = 1
        previous_row = choose[d - 1]
        row = choose[d]
        for k in range(1, d + 1):
            row[k] = (previous_row[k - 1] + previous_row[k]) % mod

    transitions = {}
    for previous in range(1, n):
        for new in range(1, n - previous + 1):
            inside = new * (new - 1) // 2
            terms = []
            for omitted in range(new + 1):
                shift = previous * (new - omitted) + inside
                coefficient = choose[new][omitted]
                if omitted & 1:
                    coefficient = (-coefficient) % mod
                terms.append((shift, coefficient))
            transitions[previous, new] = terms

    dp = {(1, 1, 1): [1]}
    binomial_answer = [0] * (max_edges + 1)

    for depth in range(n):
        next_dp = {}
        odd_layer = ((depth + 1) & 1) == 1

        for (previous, vertices, even_count), poly in dp.items():
            if vertices == n:
                if even_count == half:
                    for i, value in enumerate(poly):
                        if value:
                            binomial_answer[i] = (binomial_answer[i] + value) % mod
                continue

            remaining = n - vertices
            for new in range(1, remaining + 1):
                if odd_layer:
                    new_even = even_count
                    new_odd = vertices - even_count + new
                else:
                    new_even = even_count + new
                    new_odd = vertices - even_count

                if new_even > half or new_odd > half:
                    continue

                capacity = (vertices + new) * (vertices + new - 1) // 2
                new_poly = [0] * (capacity + 1)
                length = len(poly)
                label_choices = choose[remaining][new]

                for shift, coefficient in transitions[previous, new]:
                    factor = coefficient * label_choices % mod
                    for i in range(length):
                        value = poly[i]
                        if value:
                            new_poly[i + shift] = (
                                new_poly[i + shift] + value * factor
                            ) % mod

                key = (new, vertices + new, new_even)
                current = next_dp.get(key)
                if current is None:
                    next_dp[key] = new_poly
                else:
                    if len(current) < len(new_poly):
                        current.extend([0] * (len(new_poly) - len(current)))
                    for i, value in enumerate(new_poly):
                        if value:
                            current[i] = (current[i] + value) % mod

        dp = next_dp
        if not dp:
            break

    result = []
    for edges in range(n - 1, max_edges + 1):
        total = 0
        for exponent in range(edges, max_edges + 1):
            value = binomial_answer[exponent]
            if value:
                total = (total + value * choose[exponent][edges]) % mod
        result.append(str(total))

    sys.stdout.write(" ".join(result))


if __name__ == "__main__":
    main()
