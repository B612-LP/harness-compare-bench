import sys

def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M, A, B = data[0], data[1], data[2], data[3]
    intervals = []
    pos = 4
    for _ in range(M):
        L, R = data[pos], data[pos+1]
        pos += 2
        intervals.append((L, R))

    if A == B:
        if (N - 1) % A != 0:
            print("No")
            return
        for L, R in intervals:
            lo = (L - 1 + A - 1) // A
            hi = (R - 1) // A
            if lo <= hi:
                print("No")
                return
        print("yes")
        return

    full = (1 << B) - 1
    low_mask = ((1 << (B - A + 1)) - 1) << (A - 1)  # bits A-1 .. B-1

    cur = 1
    mask = 1  # bit 0: position cur is reachable

    def step_good():
        nonlocal mask
        bit = 1 if (mask & low_mask) else 0
        mask = ((mask << 1) | bit) & full
        return bit

    def step_bad():
        nonlocal mask
        mask = (mask << 1) & full

    # For A < B, after at most k0*A + B - 1 <= 361 good squares
    # the whole B-window becomes reachable, provided any reachable
    # square remains.  400 is a safe threshold.
    LIMIT = 400

    def advance(end):
        nonlocal cur, mask
        d = end - cur
        if d <= 0:
            return
        start = cur
        steps = d if d < LIMIT else LIMIT
        for _ in range(steps):
            step_good()
            if mask == full:
                break
        cur = start + steps
        if cur < end:
            if mask:
                mask = full
            cur = end

    for L, R in intervals:
        if cur >= N:
            break
        end = L - 1
        if end > N:
            end = N
        if end > cur:
            advance(end)
            if cur >= N:
                break
        if cur >= N:
            break
        # now cur == L-1 (or N already handled)
        if mask == 0:
            print("No")
            return
        length = R - L + 1
        if length >= B:
            print("No")
            return
        for _ in range(length):
            step_bad()
            cur += 1
        if mask == 0:
            print("No")
            return

    if cur < N:
        advance(N)
    print("yes" if (cur == N and (mask & 1)) else "No")

if __name__ == "__main__":
    solve()
