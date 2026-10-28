import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]
    n = N // 2
    maxdeg = N * (N - 1) // 2

    # Binomial coefficients modulo P (P is prime, but only additions are used).
    C = [[0] * (maxdeg + 1) for _ in range(maxdeg + 1)]
    for i in range(maxdeg + 1):
        row = C[i]
        row[0] = 1 % P
        prev = C[i - 1] if i else None
        for j in range(1, i + 1):
            v = prev[j - 1] + prev[j]
            if v >= P:
                v -= P
            row[j] = v

    # Transfer from a layer of size a to the next layer of size b.
    # All edges are counted through y = 1 + x, where x marks an edge.
    # T[a][b](y) = sum_j (-1)^j C(b,j) y^(a(b-j) + C(b,2)).
    T = [[None] * (n + 1) for _ in range(n + 1)]
    for a in range(1, n + 1):
        for b in range(1, n + 1):
            base = b * (b - 1) // 2
            terms = []
            for j in range(b + 1):
                coef = C[b][j]
                if j & 1 and coef:
                    coef = P - coef
                if coef:
                    terms.append((a * (b - j) + base, coef))
            T[a][b] = terms

    # dp[t][(e,a,p)] is a polynomial in y.
    # t     : vertices used so far (root included)
    # e     : vertices in even layers so far (root included)
    # a     : size of the current (last) layer
    # p     : parity of the current layer (0 = even, 1 = odd)
    dp = [{} for _ in range(N + 1)]
    dp[1][(1, 1, 0)] = [1]

    for t in range(1, N):
        states = dp[t]
        if not states:
            continue
        rem = N - t
        for (e, a, p), poly in states.items():
            maxb = min(n, rem)
            if p == 0:
                # The next layer is odd.
                cap = n - (t - e)
            else:
                # The next layer is even.
                cap = n - e
            if cap < maxb:
                maxb = cap
            lp = len(poly)
            for b in range(1, maxb + 1):
                terms = T[a][b]
                ne = e + b if p == 1 else e
                key = (ne, b, 1 - p)
                dest = dp[t + b].get(key)
                newlen = lp + terms[0][0]
                if dest is None:
                    dest = [0] * newlen
                    dp[t + b][key] = dest
                elif len(dest) < newlen:
                    dest.extend([0] * (newlen - len(dest)))
                mul = C[rem][b]
                for sh, coef in terms:
                    cc = coef * mul % P
                    for i in range(lp):
                        dest[i + sh] = (dest[i + sh] + poly[i] * cc) % P

    R = None
    for (e, a, p), poly in dp[N].items():
        if e != n:
            continue
        if R is None:
            R = poly[:]
        else:
            if len(R) < len(poly):
                R.extend([0] * (len(poly) - len(R)))
            for i, v in enumerate(poly):
                R[i] = (R[i] + v) % P

    if R is None:
        R = []

    # R(y) = sum_d r[d] y^d with y = 1+x, so convert back to powers of x.
    ans = []
    for M in range(N - 1, maxdeg + 1):
        s = 0
        for d in range(M, len(R)):
            s = (s + R[d] * C[d][M]) % P
        ans.append(str(s))

    sys.stdout.write(" ".join(ans) + "\n")


if __name__ == "__main__":
    main()
