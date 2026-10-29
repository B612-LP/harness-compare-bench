import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n, mod = data[0], data[1]
    half = n // 2
    max_edges = n * (n - 1) // 2
    extra_degree = max_edges - (n - 1)

    states = [(1, 0, 1, 0)]
    state_index = {(1, 0, 1, 0): 0}
    index = 0

    while index < len(states):
        even, odd, last, parity = states[index]
        if not (even == half and odd == half):
            if parity == 0:
                max_add = min(n - even - odd, half - odd)
            else:
                max_add = min(n - even - odd, half - even)

            for add in range(1, max_add + 1):
                if parity == 0:
                    nxt = (even, odd + add, add, 1)
                else:
                    nxt = (even + add, odd, add, 0)
                if nxt not in state_index:
                    state_index[nxt] = len(states)
                    states.append(nxt)
        index += 1

    order = sorted(
        range(len(states)),
        key=lambda i: states[i][0] + states[i][1],
    )
    new_index = [0] * len(states)
    for i, old in enumerate(order):
        new_index[old] = i

    outgoing = [[] for _ in states]
    for old, state in enumerate(states):
        even, odd, last, parity = state
        if even == half and odd == half:
            continue

        if parity == 0:
            max_add = min(n - even - odd, half - odd)
        else:
            max_add = min(n - even - odd, half - even)

        u = new_index[old]
        for add in range(1, max_add + 1):
            if parity == 0:
                nxt = (even, odd + add, add, 1)
            else:
                nxt = (even + add, odd, add, 0)
            outgoing[u].append((new_index[state_index[nxt]], last, add))

    terminal = [
        new_index[i]
        for i, state in enumerate(states)
        if state[0] == half and state[1] == half
    ]
    start = new_index[state_index[(1, 0, 1, 0)]]

    factorial = [1] * (n + 1)
    for i in range(1, n + 1):
        factorial[i] = factorial[i - 1] * i % mod
    inv_factorial = [1] * (n + 1)
    inv_factorial[n] = pow(factorial[n], mod - 2, mod)
    for i in range(n, 0, -1):
        inv_factorial[i - 1] = inv_factorial[i] * i % mod

    values_at = []
    state_count = len(states)

    for x in range(extra_degree + 1):
        base = (1 + x) % mod

        if x == 0:
            ratio = [a % mod for a in range(n + 1)]
        else:
            inv_x = pow(x, mod - 2, mod)
            ratio = [0] * (n + 1)
            power = 1
            for a in range(n + 1):
                ratio[a] = (power - 1) * inv_x % mod
                power = power * base % mod

        transition = [[0] * (n + 1) for _ in range(n + 1)]
        for a in range(1, n + 1):
            step = ratio[a]
            power = 1
            row = transition[a]
            for b in range(n + 1):
                row[b] = power * inv_factorial[b] % mod
                power = power * step % mod

        within = [1] * (n + 1)
        power = 1
        for size in range(2, n + 1):
            power = power * pow(base, size - 1, mod) % mod
            within[size] = power

        for a in range(1, n + 1):
            row = transition[a]
            for b in range(n + 1):
                row[b] = row[b] * within[b] % mod

        dp = [0] * state_count
        dp[start] = 1
        for u in range(state_count):
            current = dp[u]
            if current:
                for v, a, b in outgoing[u]:
                    dp[v] = (dp[v] + current * transition[a][b]) % mod

        total = 0
        for v in terminal:
            total += dp[v]
        values_at.append(total % mod)

    differences = values_at[:]
    coefficients = [0] * (extra_degree + 1)
    binomial_basis = [1]

    for k in range(extra_degree + 1):
        delta = differences[0]
        if delta:
            for j, value in enumerate(binomial_basis):
                coefficients[j] = (coefficients[j] + delta * value) % mod

        if k == extra_degree:
            break

        differences = [
            (differences[i + 1] - differences[i]) % mod
            for i in range(len(differences) - 1)
        ]

        inv = pow(k + 1, mod - 2, mod)
        next_basis = [0] * (len(binomial_basis) + 1)
        for j, value in enumerate(binomial_basis):
            next_basis[j] = (next_basis[j] - k * value * inv) % mod
            next_basis[j + 1] = (next_basis[j + 1] + value * inv) % mod
        binomial_basis = next_basis

    label_factor = factorial[n - 1]
    answers = [
        str(coefficients[i] * label_factor % mod)
        for i in range(extra_degree + 1)
    ]
    sys.stdout.write(" ".join(answers))


if __name__ == "__main__":
    main()
