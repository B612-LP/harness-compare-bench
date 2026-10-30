import sys

sys.setrecursionlimit(1 << 20)


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    it = iter(data)
    N = next(it)
    M = next(it)
    A = next(it)
    B = next(it)
    bad = [(next(it), next(it)) for _ in range(M)]

    full = (1 << B) - 1
    window_mask = (1 << (B - A + 1)) - 1

    def step(mask):
        new = 1 if ((mask >> (A - 1)) & window_mask) else 0
        return ((mask << 1) & full) | new

    def process_segment(s, t, mask, has_seed1):
        """Return mask after processing good segment [s, t] (inclusive)."""
        length = t - s + 1

        if A == B:
            # r(x) = r(x - A): periodic with period A.
            active = set()
            for d in range(1, B + 1):
                if (mask >> (d - 1)) & 1:
                    active.add((s - d) % A)
            if has_seed1:
                active.add(1 % A)
            end = 0
            for k in range(B):
                y = t - k
                if y >= s:
                    if (y % A) in active:
                        end |= 1 << k
                else:
                    # position before segment: use incoming mask bits
                    d = s - y
                    if 1 <= d <= B and ((mask >> (d - 1)) & 1):
                        end |= 1 << k
            return end

        # A < B: any seed saturates within a bounded number of steps.
        x = s
        if has_seed1:
            # process cell 1 (reachable)
            mask = 1
            x = 2
        done = x - s
        if has_seed1:
            done = 1
        while done < length:
            if mask == full:
                break
            if mask == 0:
                break
            mask = step(mask)
            done += 1
        if done < length:
            if mask == full:
                mask = full
            else:
                mask = 0
        return mask

    mask = 0
    cur = 1
    ok = False
    for idx, (L, R) in enumerate(bad + [(None, None)]):
        if L is None:
            seg_s, seg_t = cur, N
        else:
            seg_s, seg_t = cur, L - 1
        if seg_s <= seg_t:
            mask = process_segment(seg_s, seg_t, mask, seg_s == 1)
        if L is None:
            ok = bool(mask & 1)
            break
        # shift across bad interval [L, R]
        gap = R - L + 1
        mask = (mask << gap) & full
        cur = R + 1

    print("Yes" if ok else "No")


if __name__ == '__main__':
    main()
