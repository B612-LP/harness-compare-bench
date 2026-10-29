import sys


def main():
    data = sys.stdin.buffer.read().split()
    N = int(data[0]); MOD = int(data[1])
    E = N * (N - 1) // 2

    fact = [1] * (N + 1)
    for i in range(1, N + 1):
        fact[i] = fact[i - 1] * i % MOD
    invfact = [1] * (N + 1)
    invfact[N] = pow(fact[N], MOD - 2, MOD)
    for i in range(N, 0, -1):
        invfact[i - 1] = invfact[i] * i % MOD

    # binomials C(i,j), i <= max(N, E)
    K = max(N, E)
    cb = [[1]]
    for i in range(1, K + 1):
        prev = cb[-1]
        row = [1] * (i + 1)
        for j in range(1, i):
            row[j] = (prev[j - 1] + prev[j]) % MOD
        cb.append(row)

    # monomials of  y^{C(t,2)} * (y^s - 1)^t / t!
    mono = {}
    for s in range(1, N):
        for t in range(1, N):
            lst = []
            sh = t * (t - 1) // 2
            row = cb[t]
            for j in range(t + 1):
                c = row[j] * invfact[t] % MOD
                if (t - j) & 1:
                    c = (-c) % MOD
                lst.append((sh + j * s, c))
            mono[(s, t)] = lst

    half = N // 2

    def addmul(dst, src, ml, MOD=MOD, E=E):
        lim = len(src)
        for deg, c in ml:
            if c == 0:
                continue
            for i in range(lim):
                v = src[i]
                if v:
                    j = deg + i
                    if j > E:
                        break
                    dst[j] = (dst[j] + v * c) % MOD

    layers = [dict() for _ in range(N + 1)]
    layers[1][(0, 1, 1)] = [1]
    for n in range(1, N):
        cur = layers[n]
        if not cur:
            continue
        rem = N - n
        for (p, s, e), poly in cur.items():
            pn = 1 - p
            for t in range(1, rem + 1):
                ne = e + t if p == 1 else e
                if ne > half:
                    continue
                key = (pn, t, ne)
                nxt = layers[n + t]
                dst = nxt.get(key)
                if dst is None:
                    nn = n + t
                    L = nn * (nn - 1) // 2
                    if L > E:
                        L = E
                    dst = [0] * (L + 1)
                    nxt[key] = dst
                addmul(dst, poly, mono[(s, t)])

    total = [0] * (E + 1)
    for (p, s, e), poly in layers[N].items():
        if e == half:
            for i, v in enumerate(poly):
                total[i] = (total[i] + v) % MOD

    f = fact[N - 1]
    for i in range(E + 1):
        total[i] = total[i] * f % MOD

    res = []
    for M in range(N - 1, E + 1):
        acc = 0
        for d in range(M, E + 1):
            if total[d]:
                acc += total[d] * cb[d][M]
        res.append(str(acc % MOD))
    sys.stdout.write(" ".join(res) + "\n")


main()
