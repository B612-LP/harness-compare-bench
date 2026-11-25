import sys

def solve() -> None:
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    it = iter(data)
    N = int(next(it)); K = int(next(it)); A = int(next(it)); B = int(next(it))
    intervals = []
    for _ in range(K):
        L = int(next(it)); R = int(next(it))
        intervals.append((L, R))

    full = (1 << B) - 1
    W = B - A + 1
    window = full ^ ((1 << (A - 1)) - 1) if A > 1 else full

    Blen = B
    Tgood = [0] * Blen
    Tgood[0] = window
    for i in range(1, Blen):
        Tgood[i] = 1 << (i - 1)
    Ident = [1 << i for i in range(Blen)]

    def mat_apply(T, state):
        out = 0
        bit = 1
        for row in T:
            if state & row:
                out |= bit
            bit <<= 1
        return out

    def mat_mul(X, Y):
        Z = [0] * Blen
        for i in range(Blen):
            row = Y[i]
            acc = 0
            while row:
                lsb = row & -row
                k = lsb.bit_length() - 1
                acc |= X[k]
                row ^= lsb
            Z[i] = acc
        return Z

    def mat_pow(T, exp):
        res = Ident
        base = T
        while exp:
            if exp & 1:
                res = mat_mul(res, base)
            exp >>= 1
            if exp:
                base = mat_mul(base, base)
        return res

    if W == 1:
        def advance_good(mask, length):
            if length <= 0:
                return mask
            k = length % A
            if k == 0:
                return mask
            return ((mask << k) & full) | (mask >> (A - k))
    else:
        D = B - A
        K0 = (A - 1 + D - 1) // D
        Thr = K0 * A
        LIMIT = Thr + B + 5

        def advance_good(mask, length):
            if length <= 0:
                return mask
            if mask == 0:
                return 0
            if mask == full:
                return full
            sim = length if length < LIMIT else LIMIT
            m = mask
            win = window
            f = full
            for _ in range(sim):
                new = 1 if (m & win) else 0
                m = ((m << 1) & f) | new
                if m == f or m == 0:
                    return m
            if length <= LIMIT:
                return m
            return mat_apply(mat_pow(Tgood, length - LIMIT), m)

    def advance_bad(mask, length):
        if length >= B:
            return 0
        return (mask << length) & full

    cur = 1
    mask = 1
    for L, R in intervals:
        glen = L - 1 - cur
        if glen > 0:
            mask = advance_good(mask, glen)
        blen = R - L + 1
        if blen >= B:
            print('No')
            return
        mask = advance_bad(mask, blen)
        cur = R

    glen = N - cur
    if glen > 0:
        mask = advance_good(mask, glen)
    print('Yes' if (mask & 1) else 'No')

if __name__ == '__main__':
    solve()