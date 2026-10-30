import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, P = data[0], data[1]
    maxE = N * (N - 1) // 2
    half = N // 2

    # binomial coefficients modulo P, up to maxE
    # (all needed arguments are < P, P is prime and >= 1e8)
    C = [[0] * (maxE + 1) for _ in range(maxE + 1)]
    C[0][0] = 1
    for i in range(1, maxE + 1):
        row = C[i]
        prev = C[i-1]
        row[0] = 1
        for j in range(1, i + 1):
            v = prev[j-1] + prev[j]
            if v >= P:
                v -= P
            row[j] = v

    K = 96
    MASK = (1 << K) - 1
    BASE_BYTES = K // 8  # 12

    def reduce_poly(poly):
        if poly == 0:
            return 0
        nb = ((poly.bit_length() + K - 1) // K) * BASE_BYTES
        bs = poly.to_bytes(nb, 'little')
        out = bytearray(nb)
        step = BASE_BYTES
        for off in range(0, nb, step):
            v = int.from_bytes(bs[off:off+step], 'little') % P
            if v:
                out[off:off+step] = v.to_bytes(step, 'little')
        return int.from_bytes(out, 'little')

    # states by number of used vertices: (last_layer_size, even_count, parity)
    dp = [dict() for _ in range(N + 1)]
    dp[1][(1, 1, 0)] = 1  # vertex 1 is at even distance, D exponent 0

    for s in range(1, N):
        level = dp[s]
        if not level:
            continue
        # reduce all polynomials at this level modulo P
        for key in list(level.keys()):
            level[key] = reduce_poly(level[key])
        remain_total = N - s
        for (a, ec, par), poly in level.items():
            if poly == 0:
                continue
            for b in range(1, remain_total + 1):
                ns = s + b
                npar = 1 - par
                nec = ec + (b if npar == 0 else 0)
                # prune impossible parity balance
                if nec > half or (ns - nec) > half:
                    continue
                label = C[remain_total][b]
                d2 = b * (b - 1) // 2
                target = dp[ns]
                key = (b, nec, npar)
                old = target.get(key, 0)
                # transition: sum_j (-1)^j C(b,j) * label * t^(d2+a*(b-j))
                for j in range(b + 1):
                    coeff = label * C[b][j] % P
                    if j & 1:
                        if coeff:
                            coeff = P - coeff
                        else:
                            continue
                    inc = d2 + a * (b - j)
                    term = (poly * coeff) << (K * inc)
                    old += term
                target[key] = old

    # collect final states with balanced parity
    final = 0
    for (a, ec, par), poly in dp[N].items():
        if ec == half and poly:
            final += poly
    if final:
        # unpack to coefficient list
        nb = ((final.bit_length() + K - 1) // K) * BASE_BYTES
        bs = final.to_bytes(nb, 'little')
        coeff = [0] * (maxE + 1)
        step = BASE_BYTES
        for off in range(0, nb, step):
            d = off // step
            if d > maxE:
                break
            coeff[d] = int.from_bytes(bs[off:off+step], 'little') % P
    else:
        coeff = [0] * (maxE + 1)

    # answer[M] = sum_D coeff[D] * C(D, M)
    ans = []
    for m in range(N - 1, maxE + 1):
        total = 0
        for d in range(m, maxE + 1):
            cd = coeff[d]
            if cd:
                total = (total + cd * C[d][m]) % P
        ans.append(str(total))
    sys.stdout.write(" ".join(ans) + "\n")

if __name__ == '__main__':
    main()
