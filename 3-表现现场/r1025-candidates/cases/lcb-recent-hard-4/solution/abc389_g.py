import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]

    max_e = N * (N - 1) // 2
    comb_size = max(N, max_e)

    # Binomial coefficients modulo P up to max_e (and at least N).
    comb = [[0] * (comb_size + 1) for _ in range(comb_size + 1)]
    for i in range(comb_size + 1):
        row = comb[i]
        row[0] = row[i] = 1 % P
        if i:
            prev = comb[i - 1]
            for j in range(1, i):
                row[j] = (prev[j - 1] + prev[j]) % P

    # For a layer of size b above a layer of size a, after substituting y = 1+x:
    #   B_{a,b}(x) * (1+x)^{C(b,2)}
    #     = sum_j (-1)^j C(b,j) y^{a(b-j)+C(b,2)}.
    factor = {}
    for a in range(1, N + 1):
        for b in range(1, N + 1):
            base = b * (b - 1) // 2
            terms = []
            for j in range(b + 1):
                c = comb[b][j]
                if j & 1:
                    c = (-c) % P
                terms.append((a * (b - j) + base, c))
            factor[(a, b)] = terms

    target = N // 2

    # state: (previous layer size, used vertices, even-distance vertices)
    # value: polynomial in y = 1+x, stored sparsely as q -> coefficient.
    dp = {(1, 1, 1): {0: 1}}
    final_poly = {}
    next_parity = 1  # the next layer has odd distance from vertex 1

    while dp:
        ndp = {}
        for (a, t, e), poly in dp.items():
            rem = N - t
            items = list(poly.items())
            for b in range(1, rem + 1):
                nt = t + b
                if next_parity == 0:
                    ne = e + b
                else:
                    ne = e
                if ne > target or nt - ne > target:
                    continue

                if nt == N:
                    if ne != target:
                        continue
                    d = final_poly
                else:
                    key = (b, nt, ne)
                    d = ndp.get(key)
                    if d is None:
                        d = {}
                        ndp[key] = d

                w = comb[rem][b]
                terms = factor[(a, b)]
                get = d.get
                for q, co in items:
                    cw = co * w
                    for qa, ca in terms:
                        qq = q + qa
                        d[qq] = get(qq, 0) + cw * ca

        for poly in ndp.values():
            for q in poly:
                poly[q] %= P
        next_parity ^= 1
        dp = ndp

    ans = []
    for M in range(N - 1, max_e + 1):
        s = 0
        for q, co in final_poly.items():
            if q >= M:
                s += co * comb[q][M]
        ans.append(str(s % P))
    print(" ".join(ans))


if __name__ == "__main__":
    main()
