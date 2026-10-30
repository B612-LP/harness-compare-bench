import sys


def main():
    n, mod = map(int, sys.stdin.buffer.read().split())
    max_edges = n * (n - 1) // 2
    half = n // 2

    fact = [1] * (n + 1)
    for i in range(1, n + 1):
        fact[i] = fact[i - 1] * i % mod

    inv_fact = [1] * (n + 1)
    inv_fact[n] = pow(fact[n], mod - 2, mod)
    for i in range(n, 0, -1):
        inv_fact[i - 1] = inv_fact[i] * i % mod

    values = []
    for t in range(max_edges + 1):
        q = (1 + t) % mod
        power_limit = max(n, max_edges)
        q_pow = [1] * (power_limit + 1)
        for i in range(1, power_limit + 1):
            q_pow[i] = q_pow[i - 1] * q % mod

        coefficient = [[0] * (n + 1) for _ in range(n + 1)]
        for previous_size in range(1, n + 1):
            base = (q_pow[previous_size] - 1) % mod
            power = 1
            for size in range(1, n + 1):
                power = power * base % mod
                coefficient[previous_size][size] = (
                    power
                    * q_pow[size * (size - 1) // 2]
                    % mod
                    * inv_fact[size]
                    % mod
                )

        dp = [None] * (n + 1)
        for i in range(n + 1):
            dp[i] = {}
        dp[1][(1, 1, 0)] = 1

        for used in range(1, n):
            remaining = n - used
            for (even_count, last_size, parity), current_value in dp[used].items():
                next_parity = 1 - parity
                for size in range(1, remaining + 1):
                    new_even = even_count + (size if next_parity == 0 else 0)
                    if new_even > half:
                        continue

                    rest = remaining - size
                    future_even = rest if next_parity == 1 else max(0, rest - 1)
                    if new_even + future_even < half:
                        continue

                    weight = coefficient[last_size][size]
                    if weight == 0:
                        continue

                    new_used = used + size
                    key = (new_even, size, next_parity)
                    target = dp[new_used]
                    target[key] = (target.get(key, 0) + current_value * weight) % mod

        evaluated = 0
        for (even_count, _last_size, _parity), value in dp[n].items():
            if even_count == half:
                evaluated += value
        values.append(evaluated % mod * fact[n - 1] % mod)

    differences = []
    row = values[:]
    for _ in range(max_edges + 1):
        differences.append(row[0])
        row = [(row[i + 1] - row[i]) % mod for i in range(len(row) - 1)]

    inverses = [0] * (max_edges + 2)
    if max_edges + 1 >= 1:
        inverses[1] = 1
    for i in range(2, max_edges + 2):
        inverses[i] = mod - (mod // i) * inverses[mod % i] % mod

    result = [0] * (max_edges + 1)
    basis = [1]
    for k in range(max_edges + 1):
        diff = differences[k]
        if diff:
            for degree, value in enumerate(basis):
                result[degree] = (result[degree] + diff * value) % mod

        if k < max_edges:
            inverse = inverses[k + 1]
            next_basis = [0] * (len(basis) + 1)
            for degree, value in enumerate(basis):
                next_basis[degree] = (next_basis[degree] - k * value) % mod
                next_basis[degree + 1] = (next_basis[degree + 1] + value) % mod
            for degree in range(len(next_basis)):
                next_basis[degree] = next_basis[degree] * inverse % mod
            basis = next_basis

    print(" ".join(map(str, result[n - 1:])))


if __name__ == "__main__":
    main()
