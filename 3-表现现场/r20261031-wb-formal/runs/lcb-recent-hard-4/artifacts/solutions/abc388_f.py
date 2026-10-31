import sys


def merge(ivs):
    ivs.sort()
    out = []
    for l, r in ivs:
        if out and l <= out[-1][1] + 1:
            if r > out[-1][1]:
                out[-1][1] = r
        else:
            out.append([l, r])
    return out


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0]); m = int(data[1]); A = int(data[2]); B = int(data[3])
    idx = 4
    ivs = []
    for _ in range(m):
        L = int(data[idx]); R = int(data[idx + 1]); idx += 2
        if ivs and ivs[-1][1] + 1 >= L:
            if R > ivs[-1][1]:
                ivs[-1] = (ivs[-1][0], R)
        else:
            ivs.append((L, R))

    # --- degenerate case: every move has length exactly A ---
    if A == B:
        start = 1 + A
        for L, R in ivs:
            lo = L if L > start else start
            if lo > R:
                continue
            p0 = lo + ((1 - lo) % A)          # smallest cell >= lo with p == 1 (mod A)
            if p0 <= R and p0 <= n:
                sys.stdout.write("No\n")
                return
        sys.stdout.write("Yes\n" if n % A == 1 % A else "No\n")
        return

    # --- maximal runs of good cells ---
    segs = []
    cur = 1
    for L, R in ivs:
        if L > cur:
            segs.append((cur, L - 1))
        if R + 1 > cur:
            cur = R + 1
    if cur <= n:
        segs.append((cur, n))

    reach = [[1, 1]]      # position 1 is good (all L_i > 1)

    for s, e in segs:
        entries = []
        for l, r in reach:
            x = s if s > l + A else l + A
            y = e if e < r + B else r + B
            if x <= y:
                entries.append([x, y])        # landings inside this segment
            x = s if s > l else l
            y = e if e < r else r
            if x <= y:
                entries.append([x, y])        # already reachable inside this segment
        if not entries:
            # nothing reachable here; drop intervals unable to reach any later cell
            reach = [iv for iv in reach if iv[1] + B >= s]
            continue
        entries = merge(entries)

        res = list(entries)
        for l, r in entries:
            if r - l + 1 >= A:
                res.append([l, e])            # contiguous block of length >= A never dies out
                continue
            k = 1
            while True:
                x = l + k * A
                if x > e:
                    break
                if l + (k + 1) * A <= r + k * B + 1:
                    res.append([x, e])        # blocks from here on touch -> whole suffix
                    break
                y = r + k * B
                res.append([x, e if e < y else y])
                k += 1
                if k > A + 2:                 # safety (unreachable when B > A)
                    res.append([x, e])
                    break

        keep = [iv for iv in reach if iv[1] + B >= s]
        reach = merge(keep + res)

    for l, r in reach:
        if l <= n <= r:
            sys.stdout.write("Yes\n")
            return
    sys.stdout.write("No\n")


main()
