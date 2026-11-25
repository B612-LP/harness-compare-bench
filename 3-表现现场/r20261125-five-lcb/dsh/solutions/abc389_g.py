import sys

SHIFT = 72
MASK = (1 << SHIFT) - 1


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]
    maxM = N * (N - 1) // 2

    # factorials for binomial coefficients C(n, k) modulo P (P is prime)
    maxC = N * N + maxM + 5
    fact = [1] * (maxC + 1)
    for i in range(1, maxC + 1):
        fact[i] = fact[i-1] * i % P
    invfact = [1] * (maxC + 1)
    invfact[maxC] = pow(fact[maxC], P - 2, P)
    for i in range(maxC, 0, -1):
        invfact[i-1] = invfact[i] * i % P

    def C(n, k):
        if k < 0 or k > n:
            return 0
        return fact[n] * invfact[k] % P * invfact[n-k] % P

    # All level-to-level transition polynomials
    # H[t][s] = ((1+x)^t - 1)^s * (1+x)^(s*(s-1)/2)
    Hpack = [[0] * (N + 1) for _ in range(N + 1)]
    for t in range(1, N + 1):
        for s in range(1, N + 1):
            if t + s > N:
                continue
            base = s * (s - 1) // 2
            deg = min(t * s + base, maxM)
            # Correct construction using factorial binomials
            h = [0] * (deg + 1)
            for i in range(s + 1):
                K = t * i + base
                upto = min(K, deg)
                coef = C(s, i)
                if (s - i) & 1:
                    coef = (-coef) % P
                if coef == 0:
                    continue
                fK = fact[K]
                for j in range(upto + 1):
                    val = fK * invfact[j] % P * invfact[K-j] % P
                    h[j] = (h[j] + coef * val) % P
            Hpack[t][s] = int.from_bytes(
                b''.join(x.to_bytes(9, 'little') for x in h), 'little')

    degmax = [min(i * (i - 1) // 2, maxM) for i in range(N + 1)]

    def pack(a):
        return int.from_bytes(b''.join(x.to_bytes(9, 'little') for x in a), 'little')

    def extract_normalized(packed, length):
        res = []
        c = packed
        for _ in range(length):
            res.append((c & MASK) % P)
            c >>= SHIFT
        return res

    # small binomial coefficients
    comb_small = [[0] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        comb_small[i][0] = comb_small[i][i] = 1 % P
        for j in range(1, i):
            comb_small[i][j] = (comb_small[i-1][j-1] + comb_small[i-1][j]) % P

    # dp[m][parity] : (last_level_size, even_count) -> packed polynomial
    dp = [[{}, {}] for _ in range(N + 1)]
    dp[1][0][(1, 1)] = 1  # polynomial 1 (= x^0)

    half = N // 2

    for m in range(1, N):
        for parity in (0, 1):
            states = dp[m][parity]
            if not states:
                continue
            L = degmax[m] + 1
            remaining = N - m
            items = list(states.items())
            states.clear()
            for (t, e), packed in items:
                if packed == 0:
                    continue
                coeffs = extract_normalized(packed, L)
                pa = pack(coeffs)
                for s in range(1, remaining + 1):
                    newparity = 1 - parity
                    if newparity == 0:
                        ne = e + s
                    else:
                        ne = e
                    no = (m + s) - ne
                    if ne > half or no > half:
                        continue
                    out_len = degmax[m + s] + 1
                    prod = pa * Hpack[t][s]
                    res = extract_normalized(prod, out_len)
                    mul = comb_small[remaining][s]
                    if mul != 1:
                        res = [(x * mul) % P for x in res]
                    rp = pack(res)
                    key = (s, ne)
                    target = dp[m + s][newparity]
                    target[key] = target.get(key, 0) + rp

    total_packed = 0
    for parity in (0, 1):
        for (t, e), packed in dp[N][parity].items():
            if e == half:
                total_packed += packed

    ans = extract_normalized(total_packed, maxM + 1)
    out = ans[N - 1:]
    sys.stdout.write(' '.join(map(str, out)) + '\n')


if __name__ == '__main__':
    main()
