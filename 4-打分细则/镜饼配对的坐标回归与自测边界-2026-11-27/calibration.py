"""Pure combinatorial calibration; no archive, subprocess, or candidate access."""
import json
from collections import Counter
from functools import lru_cache
from itertools import combinations_with_replacement


def require(ok, label):
    if not ok:
        raise ValueError(label)


@lru_cache(None)
def matching(arr):
    """Matching on distinct positions, no assumption on the optimal split."""
    if not arr:
        return 0
    best = matching(arr[1:])
    for j in range(1, len(arr)):
        if arr[0] * 2 <= arr[j]:
            best = max(best, 1 + matching(arr[1:j] + arr[j + 1:]))
    return best


def extreme(arr, accept=all):
    m = len(arr)
    return max(k for k in range(m // 2 + 1)
               if k == 0 or accept(arr[i] * 2 <= arr[m - k + i]
                                  for i in range(k)))


def distances(arr):
    """Linear abstract relation, deliberately not candidate bisect or RMQ."""
    n = len(arr)
    return tuple(next((j - i for j in range(i + 1, n)
                       if arr[j] >= 2 * arr[i]), n + 1)
                 for i in range(n))


def max_k(d, l, r, old=False):
    lo, hi = 0, (r - l + 1) // 2
    while lo < hi:
        k = (lo + hi + 1) // 2
        threshold = r - k + 1 - (0 if old else l)
        if max(d[l:l + k]) <= threshold:
            lo = k
        else:
            hi = k - 1
    return lo


def min_s(d, l, r):
    m = r - l + 1
    lo, hi = (m + 1) // 2, m
    while lo < hi:
        s = (lo + hi) // 2
        if max(d[l:l + m - s], default=-1) <= s:
            hi = s
        else:
            lo = s + 1
    return m - lo


def cases():
    arrays, windows = Counter(), Counter()
    changes, overestimate = Counter(), Counter()
    first = None
    for n in range(2, 9):
        for a in combinations_with_replacement(range(1, 6), n):
            arrays[n] += 1
            d = distances(a)
            for l in range(n):
                for r in range(l + 1, n):
                    arr = a[l:r + 1]
                    want = matching(arr)
                    clean = max_k(d, l, r)
                    require(want == extreme(arr) == clean == min_s(d, l, r),
                            'predicate or boundary disagree')
                    wrong = max_k(d, l, r, old=True)
                    require(wrong >= clean, 'old to new direction')
                    windows[n] += 1
                    if wrong != clean:
                        changes[n] += 1
                        overestimate[wrong - clean] += 1
                        if first is None:
                            first = [a, [l + 1, r + 1], clean, wrong]
    require(first == [(1, 1, 1, 2), [2, 3], 0, 1], 'minimum witness')
    return dict(arrays=arrays, windows=windows, changed=changes,
                overshoot=overestimate, minimum=first)


def sample_diffs():
    samples = [
        ((1, 1, 2, 3, 4, 4, 7, 10, 11, 12, 20),
         [(2, 5), (3, 8), (7, 11), (1, 2), (1, 11)],
         [2, 3, 1, 0, 5], [2, 3, 2, 0, 5]),
        ((127, 148, 170, 174, 258, 311, 331, 414, 416, 436, 517, 523,
          532, 587, 591, 638, 660, 748, 760, 776, 837, 857, 972, 984),
         [(7, 11), (8, 9), (8, 13), (12, 15), (9, 23), (1, 17),
          (8, 12), (1, 5), (6, 17), (3, 7), (12, 19), (13, 18),
          (7, 22), (1, 12), (14, 15)],
         [0, 0, 0, 0, 2, 6, 0, 1, 1, 0, 0, 0, 3, 5, 0],
         [0, 0, 0, 0, 2, 6, 0, 1, 4, 2, 0, 0, 4, 5, 0])]
    out = []
    for a, pairs, expected, prior in samples:
        d = distances(a)
        before = [max_k(d, l - 1, r - 1, old=True) for l, r in pairs]
        after = [max_k(d, l - 1, r - 1) for l, r in pairs]
        require(before == prior and after == expected, 'archived vector mismatch')
        out.append([[i, [l, r], old, new] for i, ((l, r), old, new)
                    in enumerate(zip(pairs, before, after), 1) if old != new])
    return out


def main():
    w = (1, 2, 2, 3)
    shared_bad = extreme(w, any)
    actual = matching(w)
    require((shared_bad, actual) == (2, 1), 'shared-criterion negative control')
    print(json.dumps(dict(cases=cases(), sample_diffs=sample_diffs(),
                          shared_any_control=[w, shared_bad, actual]),
                     sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
