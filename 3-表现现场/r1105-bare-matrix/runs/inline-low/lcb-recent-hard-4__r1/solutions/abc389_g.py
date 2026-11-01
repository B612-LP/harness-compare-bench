import sys


def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N, MOD = data[0], data[1]
    D = N * (N - 1) // 2

    comb = [[0] * (N + 1) for _ in range(N + 1)]
    for n in range(N + 1):
        comb[n][0] = 1
        comb[n][n] = 1
        for k in range(1, n):
            comb[n][k] = (comb[n - 1][k - 1] + comb[n - 1][k]) % MOD

    max_inv = D + 1
    inv = [0] * (max_inv + 1)
    if max_inv >= 1:
        inv[1] = 1
        for i in range(2, max_inv + 1):
            inv[i] = MOD - (MOD // i) * inv[MOD % i] % MOD

    evaluations = [0] * (D + 1)

    N1 = N + 1
    B = 2 * N + 1
    offset = N
    size = (N + 1) * (N + 1) * 2 * B

    for x in range(D + 1):
        maxpow = max(D, N)
        pow1 = [1] * (maxpow + 1)
        base1 = (1 + x) % MOD
        for i in range(1, maxpow + 1):
            pow1[i] = pow1[i - 1] * base1 % MOD

        G = [[0] * (N + 1) for _ in range(N + 1)]
        for p in range(1, N + 1):
            bp = (pow1[p] - 1) % MOD
            cur = 1
            for s in range(1, N + 1):
                cur = cur * bp % MOD
                c2 = s * (s - 1) // 2
                G[p][s] = cur * pow1[c2] % MOD

        dp = [0] * size
        init_idx = ((1 * N1 + 1) * 2 + 0) * B + offset + 1
        dp[init_idx] = 1

        for v in range(1, N):
            rem = N - v
            for p in range(1, v + 1):
                for r in range(2):
                    src_base = ((v * N1 + p) * 2 + r) * B
                    for s in range(1, rem + 1):
                        factor = comb[rem][s] * G[p][s] % MOD
                        if factor == 0:
                            continue

                        nr = 1 - r
                        shift = s if nr == 0 else -s
                        nv = v + s
                        dest_base = ((nv * N1 + s) * 2 + nr) * B

                        src_off = src_base + offset
                        dest_off = dest_base + offset + shift

                        for bal in range(-v, v + 1, 2):
                            val = dp[src_off + bal]
                            if val:
                                new_val = dp[dest_off + bal] + val * factor % MOD
                                if new_val >= MOD:
                                    new_val -= MOD
                                dp[dest_off + bal] = new_val

        total = 0
        for p in range(1, N + 1):
            for r in range(2):
                idx = ((N * N1 + p) * 2 + r) * B + offset
                total += dp[idx]
        evaluations[x] = total % MOD

    y = evaluations
    diff = y[:]
    result = [0] * (D + 1)

    binom = [0] * (D + 1)
    binom[0] = 1

    for k in range(D + 1):
        d = diff[0] % MOD
        if d:
            for m in range(D + 1):
                if binom[m]:
                    result[m] = (result[m] + d * binom[m]) % MOD

        if k == D:
            break

        for i in range(D - k):
            diff[i] = (diff[i + 1] - diff[i]) % MOD

        invk = inv[k + 1]
        new_binom = [0] * (D + 1)
        for m in range(D + 1):
            val = (binom[m - 1] if m > 0 else 0) - k * binom[m]
            new_binom[m] = (val % MOD) * invk % MOD
        binom = new_binom

    out = [str(result[m] % MOD) for m in range(N - 1, D + 1)]
    print(" ".join(out))


if __name__ == "__main__":
    solve()
