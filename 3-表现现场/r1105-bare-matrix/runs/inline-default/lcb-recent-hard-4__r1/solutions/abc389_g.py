import sys


def solve():
    N, P = map(int, sys.stdin.buffer.readline().split())
    half = N // 2
    max_edges = N * (N - 1) // 2

    max_v = max(max_edges, N)
    comb = [[0] * (max_v + 1) for _ in range(max_v + 1)]
    comb[0][0] = 1 % P

    for n in range(1, max_v + 1):
        comb[n][0] = comb[n][n] = 1 % P
        prev = comb[n - 1]
        row = comb[n]
        for k in range(1, n):
            row[k] = (prev[k - 1] + prev[k]) % P

    poly_list = [[None] * (N + 1) for _ in range(N + 1)]

    for p in range(1, N + 1):
        for t in range(1, N - p + 1):
            poly = [1]

            for _ in range(t):
                new = [0] * (len(poly) + p)
                rowp = comb[p]
                for i, a in enumerate(poly):
                    if a:
                        for k in range(1, p + 1):
                            new[i + k] = (new[i + k] + a * rowp[k]) % P
                poly = new

            internal = t * (t - 1) // 2
            if internal:
                rowc = comb[internal]
                new = [0] * (len(poly) + internal)
                for i, a in enumerate(poly):
                    if a:
                        for r in range(internal + 1):
                            new[i + r] = (new[i + r] + a * rowc[r]) % P
                poly = new

            poly_list[p][t] = poly

    dp = [{} for _ in range(N + 1)]
    dp[1][(1, 1, 0)] = [1]

    for used in range(1, N):
        states = dp[used]
        if not states:
            continue

        for key, arr in list(states.items()):
            for i in range(len(arr)):
                arr[i] %= P
            while arr and arr[-1] == 0:
                arr.pop()
            if not arr:
                del states[key]
            else:
                states[key] = arr

        if not states:
            dp[used] = None
            continue

        q_cache = {}
        start_min = 0 if used == 1 else used - 1
        max_t = N - used

        for (p, even_count, parity), arr in list(states.items()):
            if not arr:
                continue

            for t in range(1, max_t + 1):
                new_parity = 1 - parity
                new_even = even_count + (t if new_parity == 0 else 0)

                if new_even > half:
                    continue

                new_used = used + t
                if new_even + (N - new_used) < half:
                    continue

                keyq = (p, t)
                item = q_cache.get(keyq)

                if item is None:
                    base = poly_list[p][t]
                    factor = comb[N - used][t]

                    if factor == 0:
                        item = (t, [])
                    else:
                        offset = t
                        coeff = [
                            base[j] * factor % P
                            for j in range(offset, len(base))
                        ]
                        while coeff and coeff[-1] == 0:
                            coeff.pop()
                        item = (offset, coeff)

                    q_cache[keyq] = item

                offset, qcoeff = item
                if not qcoeff:
                    continue

                target_key = (t, new_even, new_parity)
                target = dp[new_used].get(target_key)

                if target is None:
                    target = [0] * (new_used * (new_used - 1) // 2 + 1)
                    dp[new_used][target_key] = target

                for i in range(start_min, len(arr)):
                    ai = arr[i]
                    if ai:
                        base_idx = i + offset
                        for j, bj in enumerate(qcoeff):
                            target[base_idx + j] += ai * bj

        dp[used] = None

    ans = [0] * (max_edges + 1)

    for (p, even_count, parity), arr in dp[N].items():
        if even_count == half:
            for m, val in enumerate(arr):
                if val:
                    ans[m] += val

    out = []
    for m in range(N - 1, max_edges + 1):
        out.append(str(ans[m] % P))

    print(" ".join(out))


if __name__ == "__main__":
    solve()
