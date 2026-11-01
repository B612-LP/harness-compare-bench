import sys


def solve() -> None:
    data = sys.stdin.read().split()
    if not data:
        return

    N = int(data[0])
    P = int(data[1])

    D = N * (N - 1) // 2
    half = N // 2
    MAX = max(D, N)

    C = [[0] * (MAX + 1) for _ in range(MAX + 1)]
    C[0][0] = 1
    for i in range(1, MAX + 1):
        C[i][0] = C[i][i] = 1
        prev = C[i - 1]
        row = C[i]
        for j in range(1, i):
            row[j] = (prev[j - 1] + prev[j]) % P

    def conv(a, b, limit=D):
        la = len(a)
        lb = len(b)
        if la == 0 or lb == 0:
            return []

        res_len = la + lb - 1
        if res_len > limit + 1:
            res_len = limit + 1

        res = [0] * res_len
        for i, ai in enumerate(a):
            if ai == 0:
                continue
            max_j = lb
            if i + max_j > res_len:
                max_j = res_len - i
            for j in range(max_j):
                res[i + j] += ai * b[j]

        for i in range(res_len):
            res[i] %= P
        return res

    W = [[None] * (N + 1) for _ in range(N + 1)]

    for p in range(1, N + 1):
        max_c = N - p
        if max_c <= 0:
            continue

        base = [0] * (p + 1)
        for k in range(1, p + 1):
            base[k] = C[p][k] % P

        power = [1]

        for c in range(1, max_c + 1):
            power = conv(power, base, D)
            internal_deg = c * (c - 1) // 2

            if internal_deg == 0:
                W[p][c] = power[:]
            else:
                row = [C[internal_deg][j] for j in range(internal_deg + 1)]
                W[p][c] = conv(power, row, D)

    dp = [{} for _ in range(N + 1)]
    dp[1][(1, 1, 0)] = [1]

    for u in range(1, N):
        if not dp[u]:
            continue

        remaining = N - u
        items = list(dp[u].items())

        for (e, p, par), poly in items:
            if not poly:
                continue

            for c in range(1, remaining + 1):
                npar = 1 - par
                ne = e + (c if npar == 0 else 0)

                if ne > half:
                    continue

                nodd = (u + c) - ne
                if nodd > half:
                    continue

                wp = W[p][c]
                if wp is None:
                    continue

                choose = C[remaining][c] % P
                if choose == 0:
                    continue

                npoly = conv(poly, wp, D)
                if choose != 1:
                    npoly = [(x * choose) % P for x in npoly]

                key = (ne, c, npar)
                dest = dp[u + c]
                old = dest.get(key)

                if old is None:
                    dest[key] = npoly
                else:
                    if len(old) < len(npoly):
                        old.extend([0] * (len(npoly) - len(old)))
                    for i, val in enumerate(npoly):
                        old[i] = (old[i] + val) % P

    ans = [0] * (D + 1)

    for (e, p, par), poly in dp[N].items():
        if e != half:
            continue
        for i, val in enumerate(poly):
            ans[i] = (ans[i] + val) % P

    out = []
    for M in range(N - 1, D + 1):
        out.append(str(ans[M]))

    print(" ".join(out))


if __name__ == "__main__":
    solve()
