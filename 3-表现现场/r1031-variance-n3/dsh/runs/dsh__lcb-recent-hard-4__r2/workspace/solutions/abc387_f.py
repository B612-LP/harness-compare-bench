import sys
from collections import deque

MOD = 998244353

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return
    n, m = data[0], data[1]
    a = [0] + data[2:2+n]
    indeg = [0]*(n+1)
    for i in range(1, n+1):
        indeg[a[i]] += 1
    q = deque(i for i in range(1, n+1) if indeg[i] == 0)
    cur = [None]*(n+1)
    removed = [False]*(n+1)
    while q:
        v = q.popleft()
        removed[v] = True
        arr = cur[v]
        if arr is None:
            f = list(range(m+1))
        else:
            s = 0
            arr[0] = 0
            for t in range(1, m+1):
                s += arr[t]
                if s >= MOD:
                    s -= MOD
                arr[t] = s
            f = arr
        p = a[v]
        cp = cur[p]
        if cp is None:
            cur[p] = f
        else:
            for t in range(1, m+1):
                cp[t] = cp[t] * f[t] % MOD
            cur[v] = None
        indeg[p] -= 1
        if indeg[p] == 0:
            q.append(p)
    visited = [False]*(n+1)
    ans = 1
    for i in range(1, n+1):
        if (not removed[i]) and (not visited[i]):
            cyc = []
            x = i
            while not visited[x]:
                visited[x] = True
                cyc.append(x)
                x = a[x]
            g = None
            for v in cyc:
                arr = cur[v]
                if arr is None:
                    continue
                if g is None:
                    g = [1]*(m+1)
                for t in range(1, m+1):
                    g[t] = g[t] * arr[t] % MOD
            if g is None:
                total = m % MOD
            else:
                total = sum(g[1:]) % MOD
            ans = ans * total % MOD
    print(ans)

if __name__ == '__main__':
    main()
