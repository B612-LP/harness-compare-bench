import sys

# BFS layer DP:
# layers V_0, V_1, ... from vertex 1; edges between consecutive layers
# (each new-layer vertex needs >=1 parent) and arbitrary edges inside a layer.
# State (e, o, a) = (#even vertices, #odd vertices, last layer size);
# polynomial in edge count.


def solve(N, P):
    n = N // 2
    maxe = N * (N - 1) // 2

    # binomial coefficients (up to maxe = C(N,2))
    Cbig = maxe
    C = [[0] * (Cbig + 1) for _ in range(Cbig + 1)]
    C[0][0] = 1
    for i in range(1, Cbig + 1):
        C[i][0] = 1
        for j in range(1, i + 1):
            C[i][j] = (C[i - 1][j - 1] + C[i - 1][j]) % P

    # T[a][b] = ((1+x)^a - 1)^b * (1+x)^(b(b-1)/2)
    T = [[None] * (n + 1) for _ in range(n + 1)]
    for a in range(1, n + 1):
        base = [0] * (a + 1)
        for k in range(1, a + 1):
            base[k] = C[a][k]
        for b in range(1, n + 1):
            poly = [1]
            for _ in range(b):
                deg = len(poly) + a
                np = [0] * deg
                for i, v in enumerate(poly):
                    if v:
                        for k in range(1, a + 1):
                            np[i + k] = (np[i + k] + v * base[k]) % P
                poly = np
            c2 = b * (b - 1) // 2
            if c2:
                deg = len(poly) + c2
                np = [0] * deg
                for i, v in enumerate(poly):
                    if v:
                        lim = min(c2, deg - 1 - i)
                        for k in range(lim + 1):
                            np[i + k] = (np[i + k] + v * C[c2][k]) % P
                poly = np
            T[a][b] = poly

    def conv(p, q):
        # p coefficients < P, q coefficients < P; reduce once at the end.
        lp, lq = len(p), len(q)
        r = [0] * (lp + lq - 1)
        for j, w in enumerate(q):
            if w:
                for i, v in enumerate(p):
                    r[i + j] += v * w
        return [v % P for v in r]

    def conv_scale(p, q, mult):
        # conv(p, q) with every output coefficient multiplied by mult
        lp, lq = len(p), len(q)
        r = [0] * (lp + lq - 1)
        if mult == 1:
            for j, w in enumerate(q):
                if w:
                    for i, v in enumerate(p):
                        r[i + j] += v * w
        else:
            for j, w in enumerate(q):
                if w:
                    w *= mult
                    for i, v in enumerate(p):
                        r[i + j] += v * w
        return [v % P for v in r]

    # states keyed (e,o,a,par) -> poly ; par = parity of last layer
    states = {(1, 0, 1, 0): [1]}
    final = [0] * (maxe + 1)

    while states:
        nxt = {}
        for (e, o, a, par), poly in states.items():
            if e == n and o == n:
                for i, v in enumerate(poly):
                    final[i] = (final[i] + v) % P
                continue
            if par == 0:
                # next layer is odd
                if o < n:
                    rem = n - o
                    for b in range(1, rem + 1):
                        np = conv_scale(poly, T[a][b], C[rem][b])
                        key = (e, o + b, b, 1)
                        if key in nxt:
                            t = nxt[key]
                            for i, v in enumerate(np):
                                t[i] += v
                        else:
                            nxt[key] = np
            else:
                # next layer is even
                if e < n:
                    rem = n - e
                    for b in range(1, rem + 1):
                        np = conv_scale(poly, T[a][b], C[rem][b])
                        key = (e + b, o, b, 0)
                        if key in nxt:
                            t = nxt[key]
                            for i, v in enumerate(np):
                                t[i] += v
                        else:
                            nxt[key] = np
        for t in nxt.values():
            for i in range(len(t)):
                t[i] %= P
        states = nxt

    mult = C[N - 1][n - 1]
    ans = [v * mult % P for v in final]
    return ans[N - 1:]


def main():
    N, P = map(int, sys.stdin.buffer.read().split())
    ans = solve(N, P)
    print(" ".join(map(str, ans)))


if __name__ == '__main__':
    main()
