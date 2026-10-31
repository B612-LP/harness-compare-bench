import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0]); P = int(data[1])
    half = n // 2
    maxE = n * (n - 1) // 2

    # binomials C[i][j] mod P for i,j <= n
    Cn = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        Cn[i][0] = 1
        for j in range(1, i + 1):
            Cn[i][j] = (Cn[i - 1][j - 1] + Cn[i - 1][j]) % P

    # binomials for p up to maxE
    bigC = [[0] * (maxE + 1) for _ in range(maxE + 1)]
    for i in range(maxE + 1):
        bigC[i][0] = 1
        for j in range(1, i + 1):
            bigC[i][j] = (bigC[i - 1][j - 1] + bigC[i - 1][j]) % P

    # precompute shift/coefficient terms for each (a, b)
    # term t contributes y^(C(b,2) + a*(b-t)) with coefficient (-1)^t C(b,t)
    terms = {}
    for a in range(1, n + 1):
        for b in range(1, n - a + 1):
            base = b * (b - 1) // 2
            lst = []
            for t in range(b + 1):
                co = Cn[b][t]
                if t & 1:
                    co = (P - co) % P
                lst.append((base + a * (b - t), co))
            terms[(a, b)] = lst

    states = {}
    states[(1, 1, 1, 0)] = [1]
    ans = [0] * (maxE + 2)

    for u in range(1, n + 1):
        keys = [k for k in states if k[0] == u]
        for key in keys:
            poly = states.pop(key)
            _, e, a, par = key
            npar = 1 - par
            L = len(poly)
            rem = n - u
            for b in range(1, rem + 1):
                if npar == 0:
                    ne = e + b
                    if ne > half:
                        continue
                else:
                    ne = e
                nu = u + b
                w = Cn[rem][b]
                tlist = terms[(a, b)]
                maxsh = tlist[0][0]  # t = 0 gives the largest shift
                newpoly = [0] * (L + maxsh)
                for sh, co in tlist:
                    cc = co * w % P
                    if cc == 0:
                        continue
                    for i in range(L):
                        v = poly[i]
                        if v:
                            j = i + sh
                            newpoly[j] = (newpoly[j] + v * cc) % P
                if nu == n:
                    if ne == half:
                        for i in range(len(newpoly)):
                            v = newpoly[i]
                            if v:
                                ans[i] = (ans[i] + v) % P
                else:
                    nk = (nu, ne, b, npar)
                    tgt = states.get(nk)
                    if tgt is None:
                        states[nk] = newpoly
                    else:
                        if len(tgt) < len(newpoly):
                            tgt.extend([0] * (len(newpoly) - len(tgt)))
                        for i in range(len(newpoly)):
                            v = newpoly[i]
                            if v:
                                tgt[i] = (tgt[i] + v) % P

    out = []
    for M in range(n - 1, maxE + 1):
        s = 0
        for p in range(M, maxE + 1):
            v = ans[p]
            if v:
                s += v * bigC[p][M]
        out.append(str(s % P))
    sys.stdout.write(" ".join(out) + "\n")


main()
