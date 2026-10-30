import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    it = iter(data)
    N = next(it)
    M = next(it)
    A = next(it)
    B = next(it)
    intervals = [(next(it), next(it)) for _ in range(M)]

    full = (1 << B) - 1
    low_mask = (1 << (A - 1)) - 1
    check = full ^ low_mask
    # bit k (0-based) = reachability of coordinate (cur - k)
    mask = 1  # cell 1 is reachable

    # good segments: [1, L1-1], [R1+1, L2-1], ..., [RM+1, N]
    segs = []
    good_l = 1
    for (L, R) in intervals:
        segs.append((good_l, L - 1))
        good_l = R + 1
    segs.append((good_l, N))

    reachable_N = False

    for idx, (l, r) in enumerate(segs):
        if l <= r:
            j = 2 if l == 1 else l
            seen = {}
            while j <= r:
                if mask == 0:
                    # no reachable cell in the window; nothing can change
                    break
                bit = 1 if (mask & check) else 0
                mask = ((mask << 1) | bit) & full
                if mask == full:
                    # B consecutive reachable cells: every later cell is reachable
                    break
                # detect periodic steady state (e.g. A = B)
                prev = seen.get(mask)
                pos = j
                if prev is not None:
                    cycle = pos - prev
                    remaining = r - pos
                    if remaining > cycle:
                        # advance to the last (remaining % cycle) steps
                        pos = r - (remaining % cycle)
                        j = pos + 1
                        seen = {}
                        continue
                else:
                    seen[mask] = pos
                j += 1
            if r == N:
                reachable_N = bool(mask & 1)
        # skip following bad segment [bl, br]
        if idx < M:
            bl, br = intervals[idx]
            length = br - bl + 1
            if length >= B:
                mask = 0
            else:
                mask = (mask << length) & full

    print("Yes" if reachable_N else "No")


if __name__ == "__main__":
    main()
