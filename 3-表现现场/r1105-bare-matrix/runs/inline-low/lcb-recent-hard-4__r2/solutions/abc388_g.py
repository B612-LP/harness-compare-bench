import sys
from bisect import bisect_left


def solve() -> None:
    input = sys.stdin.readline
    N = int(input())
    A = list(map(int, input().split()))

    pos = [bisect_left(A, 2 * a) for a in A]
    D = [pos[i] - i for i in range(N)]

    st = [D]
    length = 1
    while (length << 1) <= N:
        prev = st[-1]
        step = length
        length <<= 1
        size = N - length + 1
        cur = [0] * size
        for i in range(size):
            a = prev[i]
            b = prev[i + step]
            cur[i] = a if a > b else b
        st.append(cur)

    def range_max(l: int, r: int) -> int:
        length = r - l + 1
        k = length.bit_length() - 1
        arr = st[k]
        a = arr[l]
        b = arr[r - (1 << k) + 1]
        return a if a > b else b

    Q = int(input())
    out = []

    for _ in range(Q):
        L, R = map(int, input().split())
        L -= 1
        R -= 1

        lo = 0
        hi = (R - L + 1) // 2

        while lo < hi:
            mid = (lo + hi + 1) // 2
            max_d = range_max(L, L + mid - 1)
            limit = R - mid + 1 - L
            if max_d <= limit:
                lo = mid
            else:
                hi = mid - 1

        out.append(str(lo))

    print("\n".join(out))


if __name__ == "__main__":
    solve()
