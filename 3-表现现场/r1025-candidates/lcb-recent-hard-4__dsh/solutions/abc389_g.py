import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]
    n = N // 2
    maxE = N * (N - 1) // 2

    fact = [1] * (N + 1)
    for i in range(1, N + 1):
        fact[i] = fact[i - 1] * i % P
    invfact = [1] * (N + 1)
    invfact[N] = pow(fact[N], P - 2, P)
    for i in range(N, 0, -1):
        invfact[i - 1] = invfact[i] * i % P

    C = [[0] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        C[i][0] = C[i][i] = 1
        for j in range(1, i):
            C[i][j] = C[i - 1][j - 1] + C[i - 1][j]

    terms = {}
    for a in range(1, N + 1):
        for b in range(1, N - a + 1):
            arr = []
            ib = invfact[b]
            base = b * (b - 1) // 2
            for j in range(b + 1):
                sh = base + a * j
                co = ib * C[b][j] % P
                if (b - j) & 1:
                    co = (-co) % P
                if co:
                    arr.append((sh, co))
            terms[(a, b)] = arr

    dp0 = [{} for _ in range(N + 1)]
    dp1 = [{} for _ in range(N + 1)]
    dp0[1][(1, 1)] = [1]

    for v in range(1, N + 1):
        for (e, a), poly in list(dp0[v].items()):
            o = v - e
            if o > n:
                continue
            maxb = min(N - v, n - o)
            for b in range(1, maxb + 1):
                tr = terms[(a, b)]
                nv = v + b
                key = (e, b)
                tgt = dp1[nv].get(key)
                if tgt is None:
                    tgt = [0] * (nv * (nv - 1) // 2 + 1)
                    dp1[nv][key] = tgt
                lt = len(tgt)
                for k, val in enumerate(poly):
                    if val:
                        for sh, co in tr:
                            nk = k + sh
                            if nk < lt:
                                tgt[nk] = (tgt[nk] + val * co) % P

        for (e, a), poly in list(dp1[v].items()):
            maxb = min(N - v, n - e)
            for b in range(1, maxb + 1):
                tr = terms[(a, b)]
                nv = v + b
                key = (e + b, b)
                tgt = dp0[nv].get(key)
                if tgt is None:
                    tgt = [0] * (nv * (nv - 1) // 2 + 1)
                    dp0[nv][key] = tgt
                lt = len(tgt)
                for k, val in enumerate(poly):
                    if val:
                        for sh, co in tr:
                            nk = k + sh
                            if nk < lt:
                                tgt[nk] = (tgt[nk] + val * co) % P

    final = [0] * (maxE + 1)
    for dpp in (dp0, dp1):
        for (e, a), poly in dpp[N].items():
            if e == n:
                for k, val in enumerate(poly):
                    if val:
                        final[k] = (final[k] + val) % P

    mul = fact[N - 1]
    for i in range(len(final)):
        final[i] = final[i] * mul % P

    g = [0] * (maxE + 1)
    for M in range(maxE + 1):
        cM = final[M]
        if cM:
            choose = 1
            for k in range(M + 1):
                g[k] = (g[k] + cM * choose) % P
                choose = choose * (M - k) // (k + 1)

    print(' '.join(map(str, g[N - 1:])))

if __name__ == '__main__':
    main()
