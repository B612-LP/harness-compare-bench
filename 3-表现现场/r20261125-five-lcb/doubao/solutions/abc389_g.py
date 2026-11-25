import sys


def main():
    data = sys.stdin.buffer.read().split()
    N = int(data[0])
    P = int(data[1])

    maxE = N * (N - 1) // 2
    # binomial table mod P
    C = [[0] * (maxE + 1) for _ in range(maxE + 1)]
    for i in range(maxE + 1):
        row = C[i]
        row[0] = 1 % P
        prev = C[i - 1] if i > 0 else None
        for j in range(1, i + 1):
            v = prev[j - 1] + prev[j]
            if v >= P:
                v -= P
            row[j] = v

    half = N // 2
    # dp[u][(a, ec, par)] -> polynomial in z (=1+x), coefficient index = number of "pairs" W
    dp = [dict() for _ in range(N + 1)]
    dp[1][(1, 1, 0)] = [1 % P]

    for u in range(1, N):
        cur = dp[u]
        for (a, ec, par), poly in cur.items():
            L = len(poly)
            rem = N - u
            for s in range(1, rem + 1):
                newpar = 1 - par
                nec = ec + (s if newpar == 0 else 0)
                if nec > half or (u + s) - nec > half:
                    continue
                key = (s, nec, newpar)
                factor = C[rem][s]
                base = s * (s - 1) // 2
                need = L + base + a * s
                np = dp[u + s].get(key)
                if np is None:
                    np = [0] * need
                    dp[u + s][key] = np
                elif len(np) < need:
                    np.extend([0] * (need - len(np)))
                Cs = C[s]
                for t in range(s + 1):
                    c = Cs[t] * factor % P
                    if t & 1:
                        c = (-c) % P
                    sh = base + a * (s - t)
                    for idx in range(L):
                        np[sh + idx] = (np[sh + idx] + c * poly[idx]) % P

    total = [0] * (maxE + 1)
    for (a, ec, par), poly in dp[N].items():
        if ec != half:
            continue
        for i, v in enumerate(poly):
            total[i] = (total[i] + v) % P

    out = []
    for M in range(N - 1, maxE + 1):
        acc = 0
        for W in range(M, maxE + 1):
            acc += total[W] * C[W][M]
        out.append(str(acc % P))
    sys.stdout.write(" ".join(out) + "\n")


main()
