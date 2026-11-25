import sys


def main():
    n, mod = map(int, sys.stdin.buffer.readline().split())
    half = n // 2
    max_edges = n * (n - 1) // 2

    comb = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        comb[i][0] = comb[i][i] = 1
        for j in range(1, i):
            comb[i][j] = (comb[i - 1][j - 1] + comb[i - 1][j]) % mod

    terms_cache = {}

    def transition_terms(cur, nxt):
        key = (cur, nxt)
        res = terms_cache.get(key)
        if res is None:
            base = nxt * (nxt - 1) // 2
            res = []
            for j in range(nxt + 1):
                coef = comb[nxt][j]
                if (nxt - j) & 1:
                    coef = (-coef) % mod
                res.append((base + cur * j, coef))
            terms_cache[key] = res
        return res

    dp = {(1, 1, 1): (0, [1])}
    answer = [0] * (max_edges + 1)

    layer = 0
    while dp:
        layer += 1
        even_layer = (layer & 1) == 0
        nxt_dp = {}

        for (cur, used, even_used), (low, poly) in dp.items():
            remaining = n - used
            max_add = min(remaining, half - even_used if even_layer else remaining)
            poly_len = len(poly)

            for add in range(1, max_add + 1):
                new_even = even_used + (add if even_layer else 0)
                choose = comb[remaining][add]
                terms = transition_terms(cur, add)

                if used + add == n:
                    if new_even == half:
                        for shift, coef in terms:
                            value_coef = coef * choose % mod
                            start = low + shift
                            for i in range(poly_len):
                                answer[start + i] = (
                                    answer[start + i] + poly[i] * value_coef
                                ) % mod
                    continue

                key = (add, used + add, new_even)
                old = nxt_dp.get(key)

                for shift, coef in terms:
                    value_coef = coef * choose % mod
                    start = low + shift

                    if old is None:
                        old = (start, [0] * poly_len)
                        nxt_dp[key] = old
                    elif start < old[0]:
                        old = (start, [0] * (old[0] - start) + old[1])
                        nxt_dp[key] = old

                    arr = old[1]
                    begin = start - old[0]
                    need = begin + poly_len
                    if need > len(arr):
                        arr.extend([0] * (need - len(arr)))

                    for i in range(poly_len):
                        arr[begin + i] += poly[i] * value_coef

        for low, poly in nxt_dp.values():
            for i in range(len(poly)):
                poly[i] %= mod

        dp = nxt_dp

    binom = [[0] * (max_edges + 1) for _ in range(max_edges + 1)]
    for i in range(max_edges + 1):
        binom[i][0] = binom[i][i] = 1
        for j in range(1, i):
            binom[i][j] = (binom[i - 1][j - 1] + binom[i - 1][j]) % mod

    out = []
    for m_edges in range(n - 1, max_edges + 1):
        total = 0
        for k in range(m_edges, max_edges + 1):
            if answer[k]:
                total += answer[k] * binom[k][m_edges]
        out.append(str(total % mod))

    sys.stdout.write(" ".join(out))


if __name__ == "__main__":
    main()
