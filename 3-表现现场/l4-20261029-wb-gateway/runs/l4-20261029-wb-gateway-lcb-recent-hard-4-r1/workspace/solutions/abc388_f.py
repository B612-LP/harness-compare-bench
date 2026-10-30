import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0]); m = int(data[1]); a = int(data[2]); b = int(data[3])
    bad = []
    pos = 4
    for _ in range(m):
        l = int(data[pos]); r = int(data[pos + 1]); pos += 2
        bad.append((l, r))

    if a == b:
        # reachable cells are exactly 1, 1+a, 1+2a, ... (1 <= ... <= n)
        if (n - 1) % a != 0:
            sys.stdout.write("No\n")
            return
        for l, r in bad:
            first = l + ((1 - l) % a)   # smallest value >= l congruent to 1 mod a
            if first <= r:
                sys.stdout.write("No\n")
                return
        sys.stdout.write("Yes\n")
        return

    full = (1 << b) - 1
    # bit i of state: cell (cur - i) is reachable (0 <= i < b)
    sel = ((1 << (b - a + 1)) - 1) << (a - 1)   # bits [a-1, b-1]

    segs = []
    cur = 2
    for l, r in bad:
        if l < cur:
            l = cur
        if l > r:
            continue
        if l > cur:
            segs.append((0, cur, l - 1))
        segs.append((1, l, r))
        cur = r + 1
    if cur <= n:
        segs.append((0, cur, n))

    LIMIT = b * b + 40   # in an all-good stretch the window becomes full within this many steps
    state = 1
    for kind, l, r in segs:
        L = r - l + 1
        if kind == 1:
            if L >= b:      # any jump would land inside this bad block
                sys.stdout.write("No\n")
                return
            state = (state << L) & full
        else:
            steps = LIMIT if L > LIMIT else L
            step = 0
            while step < steps:
                if state == full:
                    # every remaining cell of this stretch is reachable
                    break
                if state & sel:
                    state = ((state << 1) | 1) & full
                else:
                    state = (state << 1) & full
                step += 1
        if state == 0:
            sys.stdout.write("No\n")
            return

    sys.stdout.write("Yes\n" if (state & 1) else "No\n")


main()
