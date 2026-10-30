import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]
    half = N // 2
    max_edges = N * (N - 1) // 2

    # Binomial coefficients modulo P (P is prime and larger than all n used).
    LIM = max(N, half * half, half * (half - 1) // 2) + 2
    # B[p][c] uses C(p*(c-i), e), with p*(c-i) <= half*half <= 225.
    LIM = max(LIM, half * half + 2)
    C = [[0] * (LIM + 1) for _ in range(LIM + 1)]
    for i in range(LIM + 1):
        C[i][0] = C[i][i] = 1
        row = C[i]
        prev = C[i - 1] if i else None
        for j in range(1, i):
            row[j] = (prev[j - 1] + prev[j]) % P

    # T[p][c][z] = number of ways to add a new BFS layer of size c
    # after a previous layer of size p, including edges inside the new layer.
    # z is the number of edges added.
    T = [[None] * (half + 1) for _ in range(half + 1)]
    for p in range(1, half + 1):
        for c in range(1, half + 1):
            maxbc = p * c
            B = [0] * (maxbc + 1)
            for i in range(c + 1):
                ways = p * (c - i)
                coef = C[c][i]
                if i & 1:
                    coef = -coef
                row = C[ways]
                for e in range(ways + 1):
                    B[e] += coef * row[e]
            B = [x % P for x in B]

            maxin = c * (c - 1) // 2
            deg = maxbc + maxin
            poly = [0] * (deg + 1)
            for x, bx in enumerate(B):
                if bx:
                    row = C[maxin]
                    for y in range(maxin + 1):
                        poly[x + y] = (poly[x + y] + bx * row[y]) % P
            T[p][c] = poly

    # Pack polynomials in base 2^SHIFT for fast convolution.
    SHIFT = 76
    MASK = (1 << SHIFT) - 1

    def pack(poly):
        res = 0
        sh = 0
        for x in poly:
            res |= x << sh
            sh += SHIFT
        return res

    def reduce_pack(x, factor):
        res = 0
        sh = 0
        while x:
            d = (x & MASK) % P
            if d:
                d = d * factor % P
                res |= d << sh
            x >>= SHIFT
            sh += SHIFT
        return res

    TP = [[None] * (half + 1) for _ in range(half + 1)]
    for p in range(1, half + 1):
        for c in range(1, half + 1):
            TP[p][c] = pack(T[p][c])

    # state: (even_count, odd_count, last_layer_size, last_layer_parity)
    # polynomial coefficients are indexed by the number of edges.
    dp = {(1, 0, 1, 0): 1}
    answer = [0] * (max_edges + 1)

    while dp:
        ndp = {}
        for (e, o, p, q), poly in dp.items():
            t = e + o
            if t == N:
                if e == half:
                    x = poly
                    sh = 0
                    while x:
                        d = (x & MASK) % P
                        if d:
                            answer[sh // SHIFT] = (answer[sh // SHIFT] + d) % P
                        x >>= SHIFT
                        sh += SHIFT
                continue

            remaining = N - t
            nq = 1 - q
            if nq == 0:  # new layer is even
                maxc = min(remaining, half - e)
            else:
                maxc = min(remaining, half - o)

            for c in range(1, maxc + 1):
                if nq == 0:
                    e2, o2 = e + c, o
                else:
                    e2, o2 = e, o + c
                key = (e2, o2, c, nq)
                conv = poly * TP[p][c]
                old = ndp.get(key)
                if old is None:
                    ndp[key] = conv
                else:
                    ndp[key] = old + conv

        for key in ndp:
            e2, o2, c, nq = key
            t2 = e2 + o2
            remaining = N - (t2 - c)
            factor = C[remaining][c]
            ndp[key] = reduce_pack(ndp[key], factor)

        dp = ndp

    out = []
    for m in range(N - 1, max_edges + 1):
        out.append(str(answer[m] % P))
    sys.stdout.write(" ".join(out))

if __name__ == "__main__":
    main()
