# FILE: solutions/abc389_g.py
import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    N, P = data[0], data[1]

    maxE = N * (N - 1) // 2
    target_even = N // 2 - 1

    maxn = max(N * N, maxE, N)
    fact = [1] * (maxn + 1)
    for i in range(1, maxn + 1):
        fact[i] = fact[i - 1] * i % P

    invfact = [1] * (maxn + 1)
    invfact[maxn] = pow(fact[maxn], P - 2, P)
    for i in range(maxn, 0, -1):
        invfact[i - 1] = invfact[i] * i % P

    def comb(n, k):
        if k < 0 or k > n:
            return 0
        return fact[n] * invfact[k] % P * invfact[n - k] % P

    choose_rem = [[0] * (N + 1) for _ in range(N + 1)]
    for rem in range(N + 1):
        for b in range(rem + 1):
            choose_rem[rem][b] = comb(rem, b)

    nzT = [[None] * (N + 1) for _ in range(N + 1)]

    for a in range(1, N + 1):
        for b in range(1, N + 1):
            if a + b > N:
                continue

            maxX = min(a * b, maxE)
            cover = [0] * (maxX + 1)

            for j in range(b + 1):
                n = a * (b - j)
                cb = comb(b, j)
                if cb == 0:
                    continue
                sign = 1 if (j & 1) == 0 else -1
                lim = min(n, maxX)
                for x in range(lim + 1):
                    term = cb * comb(n, x) % P
                    if sign == 1:
                        cover[x] = (cover[x] + term) % P
                    else:
                        cover[x] = (cover[x] - term) % P

            kb = b * (b - 1) // 2
            t = [0] * (maxE + 1)

            for x, cx in enumerate(cover):
                if cx == 0:
                    continue
                maxy = min(kb, maxE - x)
                for y in range(maxy + 1):
                    t[x + y] = (t[x + y] + cx * comb(kb, y)) % P

            nz = []
            for e, val in enumerate(t):
                if val:
                    nz.append((e, val))
            nzT[a][b] = nz

    dp = [dict() for _ in range(N + 1)]

    init_poly = [0] * (maxE + 1)
    init_poly[0] = 1
    dp[1][(1, 1, 0)] = init_poly

    ans = [0] * (maxE + 1)

    for used in range(1, N):
        max_cur_edges = used * (used - 1) // 2

        for (a, parity, even_count), poly in dp[used].items():
            poly_nz = []
            for e in range(max_cur_edges + 1):
                val = poly[e]
                if val:
                    poly_nz.append((e, val))

            if not poly_nz:
                continue

            rem = N - used

            for b in range(1, rem + 1):
                new_even = even_count + (b if parity == 0 else 0)
                if new_even > target_even:
                    continue

                nz = nzT[a][b]
                if not nz:
                    continue

                coeff0 = choose_rem[rem][b]
                new_used = used + b
                new_parity = parity ^ 1

                if new_used == N:
                    if new_even != target_even:
                        continue

                    for e, val in poly_nz:
                        fv = val * coeff0 % P
                        max_add = maxE - e
                        for add, coef in nz:
                            if add > max_add:
                                break
                            ne = e + add
                            ans[ne] = (ans[ne] + fv * coef) % P
                else:
                    key = (b, new_parity, new_even)
                    dest_dict = dp[new_used]
                    dest = dest_dict.get(key)
                    if dest is None:
                        dest = [0] * (maxE + 1)
                        dest_dict[key] = dest

                    for e, val in poly_nz:
                        fv = val * coeff0 % P
                        max_add = maxE - e
                        for add, coef in nz:
                            if add > max_add:
                                break
                            ne = e + add
                            dest[ne] = (dest[ne] + fv * coef) % P

    out = [str(ans[m] % P) for m in range(N - 1, maxE + 1)]
    print(" ".join(out))

if __name__ == "__main__":
    main()
