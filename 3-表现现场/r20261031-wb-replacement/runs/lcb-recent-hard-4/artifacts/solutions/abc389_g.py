import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    N = int(data[0])
    P = int(data[1])
    half = N // 2
    maxE = N * (N - 1) // 2

    maxn = max(maxE, N) + 1
    Cb = [[0] * (maxn + 1) for _ in range(maxn + 1)]
    Cb[0][0] = 1
    for i in range(1, maxn + 1):
        row = Cb[i]
        prev = Cb[i - 1]
        row[0] = 1
        for j in range(1, i + 1):
            row[j] = (prev[j - 1] + prev[j]) % P

    # L(p, q) = (1+x)^{C(q,2)} * sum_r (-1)^r C(q,r) (1+x)^{p(q-r)}
    # as a sparse list of (exponent_in_basis, coefficient)
    terms = {}
    for p in range(1, N + 1):
        for q in range(1, N + 1):
            if p + q > N:
                break
            base = q * (q - 1) // 2
            lst = []
            rowq = Cb[q]
            for r in range(q + 1):
                t = p * (q - r) + base
                coef = rowq[r]
                if (r & 1) and coef:
                    coef = P - coef
                lst.append((t, coef))
            terms[(p, q)] = lst

    # dp keyed by level u: (e, next_layer_is_even, last_layer_size) -> poly
    levels = [dict() for _ in range(N + 1)]
    levels[1][(1, 0, 1)] = [1]

    for u in range(1, N):
        lvl = levels[u]
        if not lvl:
            continue
        rem = N - u
        Cn = Cb[rem]
        for (e, flag, p), poly in lvl.items():
            lp = len(poly)
            if not any(poly):
                continue
            o = u - e
            for q in range(1, rem + 1):
                if flag:
                    e2 = e + q
                    if e2 > half:
                        break
                else:
                    if o + q > half:
                        break
                    e2 = e
                ch = Cn[q]
                if ch == 0:
                    continue
                uu = u + q
                newlen = uu * (uu - 1) // 2 + 1
                newp = [0] * newlen
                for (t, c) in terms[(p, q)]:
                    cc = c * ch % P
                    if cc:
                        for k in range(lp):
                            v = poly[k]
                            if v:
                                newp[k + t] += v * cc
                newp = [x % P for x in newp]
                d = levels[uu]
                key = (e2, 1 - flag, q)
                old = d.get(key)
                if old is None:
                    d[key] = newp
                else:
                    if len(old) < newlen:
                        old.extend([0] * (newlen - len(old)))
                    for k in range(newlen):
                        old[k] = (old[k] + newp[k]) % P

    coeff = [0] * (maxE + 1)
    for (e, flag, p), poly in levels[N].items():
        if e != half:
            continue
        for k, v in enumerate(poly):
            if v:
                coeff[k] = (coeff[k] + v) % P

    # convert from basis (1+x)^k to monomial coefficients
    ans = [0] * (maxE + 1)
    for k in range(maxE, -1, -1):
        ck = coeff[k]
        if ck:
            row = Cb[k]
            for mm in range(k + 1):
                c2 = row[mm]
                if c2:
                    ans[mm] = (ans[mm] + ck * c2) % P

    out = [str(ans[mm] % P) for mm in range(N - 1, maxE + 1)]
    sys.stdout.write(" ".join(out) + "\n")


main()
