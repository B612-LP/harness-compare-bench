import sys


def main():
    N, P = map(int, sys.stdin.buffer.read().split())
    half = N // 2
    maxE = N * (N - 1) // 2

    # binomial coefficients
    C = [[0] * (N + 1) for _ in range(N + 1)]
    for n in range(N + 1):
        C[n][0] = C[n][n] = 1
        for k in range(1, n):
            C[n][k] = (C[n - 1][k - 1] + C[n - 1][k]) % P

    # binom_poly[t] = coefficients of (1+x)^t
    binom_poly = [[1]]
    for t in range(1, max(maxE, N) + 1):
        prev = binom_poly[-1]
        cur = [1] * (t + 1)
        for k in range(1, t):
            cur[k] = (prev[k - 1] + prev[k]) % P
        cur[t] = 1
        binom_poly.append(cur)

    # Packed convolution: coefficients are K-bit digits of one big integer.
    # A convolution coefficient is a sum of at most ~N products, each < P^2,
    # so it is < N*P^2 < 30 * 10^18 < 2^65; K=72 guarantees no carry.
    K = 72
    MASK = (1 << K) - 1

    def pack(f):
        v = 0
        for c in reversed(f):
            v = (v << K) | c
        return v

    def unpack_reduce(v):
        out = []
        while v:
            out.append((v & MASK) % P)
            v >>= K
        return out

    def mulpoly(a, b):
        v = a * b
        out = []
        while v:
            out.append((v & MASK) % P)
            v >>= K
        return pack(out)

    # q[a][s] = ((1+x)^a - 1)^s * (1+x)^(s(s-1)/2), packed
    q = [[0] * (N + 1) for _ in range(N + 1)]
    for a in range(1, N + 1):
        base_digits = binom_poly[a][:]
        base_digits[0] = 0  # (1+x)^a - 1
        base = pack(base_digits)
        for s in range(1, N - a + 1):
            p = 1
            for _ in range(s):
                p = mulpoly(p, base)
            w = pack(binom_poly[s * (s - 1) // 2])
            q[a][s] = mulpoly(p, w)

    # state: (u, a, e, p) -> packed edge polynomial
    # u = used vertices, a = last layer size, e = even-side vertices,
    # p = parity of the NEXT layer to add (1 = odd)
    states = {(1, 1, 1, 1): 1}

    for u in range(1, N):
        current = [(key, poly) for key, poly in states.items() if key[0] == u]
        for (uu, a, e, p), poly in current:
            rem = N - u
            for s in range(1, rem + 1):
                ne = e + s if p == 0 else e
                if ne > half or ne + rem - s < half:
                    continue
                np = 1 - p
                prod = poly * q[a][s]
                digits = []
                while prod:
                    digits.append((prod & MASK) % P)
                    prod >>= K
                comb = C[rem][s]
                if comb != 1:
                    digits = [d * comb % P for d in digits]
                key = (u + s, s, ne, np)
                old = states.get(key)
                if old is None:
                    states[key] = pack(digits)
                else:
                    od = []
                    while old:
                        od.append(old & MASK)
                        old >>= K
                    if len(od) < len(digits):
                        od += [0] * (len(digits) - len(od))
                    for i in range(len(digits)):
                        od[i] = (od[i] + digits[i]) % P
                    states[key] = pack(od)

    result = [0] * (maxE + 1)
    for (u, a, e, p), poly in states.items():
        if u == N and e == half:
            d = 0
            v = poly
            while v:
                result[d] = (result[d] + (v & MASK) % P) % P
                v >>= K
                d += 1

    print(" ".join(str(result[m]) for m in range(N - 1, maxE + 1)))


if __name__ == "__main__":
    main()
