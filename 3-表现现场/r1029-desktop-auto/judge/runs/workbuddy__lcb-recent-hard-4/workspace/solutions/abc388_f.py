import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    m = int(data[1])
    A = int(data[2])
    B = int(data[3])

    bad = []
    idx = 4
    for _ in range(m):
        bad.append((int(data[idx]), int(data[idx + 1])))
        idx += 2

    full = (1 << B) - 1
    shift = A - 1                      # bit d of mask = position p-d
    span = (1 << (B - A + 1)) - 1

    # Step one cell. For a good cell: reachable iff some d in [A,B] behind is reachable.
    good_step = lambda mask: (((mask << 1) | (1 if ((mask >> shift) & span) else 0)) & full)

    def advance_good(mask, run):
        """Advance 'run' consecutive good cells (mask holds reachability window).
        Uses cycle detection on the deterministic state to jump over long runs.
        Returns the new mask, or None if it turned 0 (nothing reachable anymore)."""
        if run <= 0:
            return mask if mask else None
        seen = {}
        steps = 0
        while steps < run:
            if mask == 0:
                return None
            prev = seen.get(mask)
            if prev is not None:
                cyc = steps - prev
                skip = ((run - steps) // cyc) * cyc
                if skip > 0:
                    steps += skip
                    continue
                for _ in range(run - steps):
                    mask = good_step(mask)
                return mask if mask else None
            seen[mask] = steps
            mask = good_step(mask)
            steps += 1
        return mask if mask else None

    # mask bit 0 = current position p reachable, window covers p-B+1 .. p
    mask = 1
    p = 1

    for (L, R) in bad:
        # cells p+1 .. L-1 are good
        mask = advance_good(mask, L - 1 - p)
        if mask is None:
            print("No")
            return
        p = L - 1
        # cells L .. R are bad
        ln = R - L + 1
        if ln >= B:
            # B consecutive bad cells always wipe out the whole window
            print("No")
            return
        for _ in range(ln):
            mask = (mask << 1) & full
        p = R
        if mask == 0:
            print("No")
            return

    # cells p+1 .. n are good
    mask = advance_good(mask, n - p)
    print("Yes" if (mask is not None and (mask & 1)) else "No")


main()
