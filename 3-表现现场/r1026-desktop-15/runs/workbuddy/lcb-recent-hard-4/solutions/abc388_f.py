import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = int(data[2])
    B = int(data[3])
    segs = []
    p = 4
    for _ in range(m):
        segs.append((int(data[p]), int(data[p + 1])))
        p += 2

    full = (1 << B) - 1
    span_mask = (1 << (B - A + 1)) - 1
    sh = A - 1

    pos = 1
    mask = 1  # bit k <-> position pos-k is reachable
    idx = 0

    while pos < n:
        if idx < m and segs[idx][0] == pos + 1:
            # bad block [l, r]: nothing there is reachable, jump over it
            r = segs[idx][1]
            idx += 1
            shift = r - pos
            mask = 0 if shift >= B else (mask << shift) & full
            pos = r
            continue

        e = segs[idx][0] - 1 if idx < m else n
        # simulate good stretch pos+1 .. e, with cycle detection on the window state
        seen = {}
        y = pos
        while y < e:
            if mask in seen:
                prev = seen[mask]
                period = y - prev
                q = (e - y) // period
                if q > 0:
                    y += q * period
                    pos = y
                    seen.clear()
                    continue
            else:
                seen[mask] = y
            nbit = 1 if ((mask >> sh) & span_mask) else 0
            mask = ((mask << 1) | nbit) & full
            y += 1
            pos = y

    sys.stdout.write("Yes\n" if (mask & 1) else "No\n")


main()
