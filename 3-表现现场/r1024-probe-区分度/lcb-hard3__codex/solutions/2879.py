class Solution:
    def minimumChanges(self, s: str, k: int) -> int:
        n = len(s)
        inf = 10**9

        divisors = [[] for _ in range(n + 1)]
        for length in range(2, n + 1):
            for d in range(1, length // 2 + 1):
                if length % d == 0:
                    divisors[length].append(d)

        cost = [[inf] * (n + 1) for _ in range(n)]
        for left in range(n):
            for right in range(left + 2, n + 1):
                length = right - left
                best = inf

                for d in divisors[length]:
                    changes = 0
                    for offset in range(d):
                        i = left + offset
                        j = right - d + offset
                        while i < j:
                            if s[i] != s[j]:
                                changes += 1
                            i += d
                            j -= d
                    if changes < best:
                        best = changes

                cost[left][right] = best

        dp = [[inf] * (n + 1) for _ in range(k + 1)]
        dp[0][0] = 0

        for parts in range(1, k + 1):
            for end in range(2 * parts, n + 1):
                best = inf
                for start in range(2 * (parts - 1), end - 1):
                    previous = dp[parts - 1][start]
                    if previous != inf:
                        candidate = previous + cost[start][end]
                        if candidate < best:
                            best = candidate
                dp[parts][end] = best

        return dp[k][n]
