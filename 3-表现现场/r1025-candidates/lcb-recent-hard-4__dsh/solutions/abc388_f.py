import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    N, M, A, B = data[:4]
    intervals = []
    idx = 4
    for _ in range(M):
        intervals.append((data[idx], data[idx + 1]))
        idx += 2

    if A == B:
        if (N - 1) % A != 0:
            print('No')
            return
        for L, R in intervals:
            t = (L - 1 + A - 1) // A
            cand = 1 + t * A
            if cand <= R and cand < N:
                print('No')
                return
        print('Yes')
        return

    window = [False] * (B - 1) + [True]
    pos = 1
    consecutive = 1

    def process_good(s, e):
        nonlocal window, pos, consecutive
        if s > e:
            return True, True
        last = True
        for x in range(s, e + 1):
            val = any(window[:B - A + 1])
            window.append(val)
            window.pop(0)
            pos = x
            last = val
            if val:
                consecutive += 1
                if consecutive >= B:
                    window = [True] * B
                    pos = e
                    consecutive = B
                    return True, True
            else:
                consecutive = 0
                if not any(window):
                    return False, False
        return True, last

    for L, R in intervals:
        alive, _ = process_good(pos + 1, L - 1)
        if not alive:
            print('No')
            return
        length = R - L + 1
        if length >= B:
            print('No')
            return
        for _ in range(length):
            window.append(False)
            window.pop(0)
        pos = R
        consecutive = 0
        if not any(window):
            print('No')
            return

    alive, last = process_good(pos + 1, N)
    print('Yes' if (alive and last) else 'No')

if __name__ == '__main__':
    main()
