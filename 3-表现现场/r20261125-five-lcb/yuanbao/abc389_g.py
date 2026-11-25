import sys

def solve() -> None:
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    V = int(data[0]); P = int(data[1])
    n = V // 2
    MAXC = V * (V - 1) // 2
    L = MAXC + 1
    CH = 10
    W = 80

    comb = [[0] * (MAXC + 1) for _ in range(MAXC + 1)]
    comb[0][0] = 1
    for i in range(1, MAXC + 1):
        row = comb[i]
        prev = comb[i - 1]
        row[0] = 1
        for j in range(1, i + 1):
            s = prev[j - 1] + prev[j]
            if s >= P:
                s -= P
            row[j] = s

    def pack_list(lst):
        return int.from_bytes(b''.join(x.to_bytes(CH, 'little') for x in lst), 'little')

    masks = [0] * (L + 1)
    mask = 0
    full_chunk = (1 << W) - 1
    for k in range(1, L + 1):
        mask = (mask << W) | full_chunk
        masks[k] = mask

    coef_pack = [[None] * (V + 1) for _ in range(V + 1)]
    for a in range(1, V):
        for b in range(1, V - a + 1):
            T = a * b + b * (b - 1) // 2
            coef = [0] * (T + 1)
            cb2 = b * (b - 1) // 2
            for k in range(b + 1):
                cb = comb[b][k]
                top = a * (b - k) + cb2
                row = comb[top]
                if k & 1:
                    for t in range(top + 1):
                        coef[t] -= cb * row[t]
                else:
                    for t in range(top + 1):
                        coef[t] += cb * row[t]
            for t in range(T + 1):
                coef[t] %= P
            coef_pack[a][b] = (pack_list(coef), T + 1)

    layers = [dict() for _ in range(V + 1)]
    layers[1][(0, 1, 0, 1)] = [1]

    for s in range(1, V):
        cur = layers[s]
        if not cur:
            continue
        remaining = V - s
        for (par, e, o, c), poly in cur.items():
            nd = len(poly)
            dp_pack = pack_list(poly)
            np_ = 1 - par
            for b in range(1, remaining + 1):
                if np_ == 0:
                    ne = e + b
                    no = o
                    if ne > n:
                        continue
                else:
                    ne = e
                    no = o + b
                    if no > n:
                        continue
                info = coef_pack[c][b]
                if info is None:
                    continue
                cp, clen = info
                out_len = nd + clen - 1
                if out_len > L:
                    out_len = L
                prod = dp_pack * cp
                low = prod & masks[out_len]
                buf = low.to_bytes(out_len * CH, 'little')
                lf = comb[remaining][b]
                key = (np_, ne, no, b)
                ns = s + b
                tgt = layers[ns].get(key)
                if tgt is None:
                    tgt = [0] * out_len
                    layers[ns][key] = tgt
                elif len(tgt) < out_len:
                    tgt.extend([0] * (out_len - len(tgt)))
                for idx in range(out_len):
                    ci = int.from_bytes(buf[idx * CH:(idx + 1) * CH], 'little')
                    if ci == 0:
                        continue
                    v = (ci % P) * lf % P
                    if v == 0:
                        continue
                    nv = tgt[idx] + v
                    if nv >= P:
                        nv -= P
                    tgt[idx] = nv

    ans = [0] * L
    for (par, e, o, c), poly in layers[V].items():
        if e == n and o == n:
            for i, val in enumerate(poly):
                if i >= L:
                    break
                nv = ans[i] + val
                if nv >= P:
                    nv -= P
                ans[i] = nv

    out = [str(x % P) for x in ans[V - 1:MAXC + 1]]
    sys.stdout.write(' '.join(out))

if __name__ == '__main__':
    solve()