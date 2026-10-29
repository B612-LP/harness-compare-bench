import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M, A, B = data[0], data[1], data[2], data[3]
    intervals = []
    idx = 4
    for _ in range(M):
        L, R = data[idx], data[idx+1]
        idx += 2
        intervals.append((L, R))

    if A == B:
        if (N - 1) % A != 0:
            print("No")
            return
        for L, R in intervals:
            k = (L - 1 + A - 1) // A
            v = 1 + k * A
            if v <= R:
                print("No")
                return
        print("Yes")
        return

    # threshold C: from one reachable cell, every cell at distance >= C is reachable
    # on an obstacle-free line.
    k0 = (B - 1 + (B - A) - 1) // (B - A)
    C = (k0 - 1) * A
    if C < B:
        C = B
    T = 2 * C + B

    full = (1 << B) - 1
    window = full & ~((1 << (A - 1)) - 1)

    cur = 1
    mask = 1  # cell 1 is reachable

    def simulate_good(end):
        nonlocal cur, mask
        if end <= cur:
            return
        length = end - cur
        if length <= T:
            for _ in range(length):
                nb = 1 if (mask & window) else 0
                mask = ((mask << 1) | nb) & full
            cur = end
        else:
            found = False
            for _ in range(C):
                nb = 1 if (mask & window) else 0
                mask = ((mask << 1) | nb) & full
                if nb:
                    found = True
            if found:
                mask = full
            else:
                mask = 0
            cur = end

    for L, R in intervals:
        simulate_good(L - 1)
        # process bad interval [L, R]
        ln = R - L + 1
        if ln >= B:
            mask = 0
        else:
            mask = (mask << ln) & full
        cur = R

    simulate_good(N)
    print("Yes" if (mask & 1) else "No")

if __name__ == '__main__':
    main()
