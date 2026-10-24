import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    N = int(data[0])
    P = int(data[1])
    h = N // 2
    MAXE = N * (N - 1) // 2

    # Pascal's triangle mod P, up to MAXE (needed for C(K, M)).
    Cb = [[0] * (i + 1) for i in range(MAXE + 1)]
    Cb[0][0] = 1
    for i in range(1, MAXE + 1):
        row = Cb[i]
        prev = Cb[i - 1]
        row[0] = 1
        row[i] = 1
        for j in range(1, i):
            row[j] = (prev[j - 1] + prev[j]) % P

    # dp[i][(parity of last layer, #even used, last layer size)] = list of
    # coefficients in the (1+x)^K basis.
    dp = [dict() for _ in range(N + 1)]
    dp[1][(0, 1, 1)] = [1]

    for i in range(1, N):
        cur = dp[i]
        if not cur:
            continue
        rem = N - i
        for (p, e, c), w in cur.items():
            o = i - e
            lw = len(w)
            for a in range(1, rem + 1):
                if p == 1:
                    e2 = e + a
                    o2 = o
                else:
                    e2 = e
                    o2 = o + a
                if e2 > h or o2 > h:
                    continue
                nd = dp[i + a]
                key = (1 - p, e2, a)
                base = c * a + (a * (a - 1)) // 2
                need = base + lw
                t = nd.get(key)
                if t is None:
                    t = [0] * need
                    nd[key] = t
                elif len(t) < need:
                    t.extend([0] * (need - len(t)))
                mult = Cb[rem][a]
                rowA = Cb[a]
                for k in range(a + 1):
                    wk = rowA[k] * mult % P
                    sh = base - c * k
                    if k & 1:
                        for idx in range(lw):
                            t[sh + idx] = (t[sh + idx] - wk * w[idx]) % P
                    else:
                        for idx in range(lw):
                            t[sh + idx] = (t[sh + idx] + wk * w[idx]) % P

    tot = [0] * (MAXE + 1)
    for (p, e, c), w in dp[N].items():
        if e != h:
            continue
        for idx in range(min(len(w), MAXE + 1)):
            tot[idx] = (tot[idx] + w[idx]) % P

    out = []
    L = MAXE + 1
    for M in range(N - 1, MAXE + 1):
        s = 0
        for K in range(M, L):
            s += tot[K] * Cb[K][M]
        out.append(str(s % P))
    sys.stdout.write(" ".join(out) + "\n")


main()
