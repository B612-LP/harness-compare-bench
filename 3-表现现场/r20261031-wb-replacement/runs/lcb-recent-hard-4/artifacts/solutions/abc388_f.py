import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = int(data[2])
    B = int(data[3])

    # maximal runs of good cells
    ranges = []
    cur = 1
    idx = 4
    for _ in range(m):
        l = int(data[idx])
        r = int(data[idx + 1])
        idx += 2
        if cur < l:
            ranges.append((cur, l - 1))
        cur = r + 1
    if cur <= n:
        ranges.append((cur, n))

    full = (1 << B) - 1
    rngmask = ((1 << (B - A + 1)) - 1) << (A - 1)

    # mask at position i: bit (d-1) == reachable(i-d), d = 1..B
    # transition over a good cell:  mask -> ((mask<<1) | dp) & full,
    #   dp = 1 iff mask & rngmask
    cache = {}

    def succ(mask, j):
        if j == 0:
            dp = 1 if (mask & rngmask) else 0
            return ((mask << 1) | dp) & full
        key = (mask, j)
        r = cache.get(key)
        if r is None:
            r = succ(succ(mask, j - 1), j - 1)
            cache[key] = r
        return r

    def advance(mask, k):
        j = 0
        while k:
            if k & 1:
                mask = succ(mask, j)
            k >>= 1
            j += 1
        return mask

    # position 2: bit0 == reachable(1) == True
    mask = 1
    cur = 2
    final = 0
    for (s, e) in ranges:
        a = s if s > 2 else 2
        if a > cur:
            gap = a - cur
            mask = 0 if gap >= B else (mask << gap) & full
            cur = a
        if a > e:
            continue
        nxtmask = advance(mask, e - cur + 1)
        if e == n:
            final = nxtmask & 1
        mask = nxtmask
        cur = e + 1

    sys.stdout.write("Yes\n" if final else "No\n")


main()
