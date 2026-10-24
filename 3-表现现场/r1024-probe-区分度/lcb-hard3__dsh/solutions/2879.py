class Solution:
    def minimumChanges(self, s: str, k: int) -> int:
        n = len(s)

        # cost[i][j] = minimum changes to turn s[i:j] into a semi-palindrome.
        INF = 10 ** 9
        cost = [[INF] * (n + 1) for _ in range(n)]

        for length in range(2, n + 1):
            divisors = []
            d = 1
            while d * d <= length:
                if length % d == 0:
                    if d < length:
                        divisors.append(d)
                    other = length // d
                    if other != d and other < length:
                        divisors.append(other)
                d += 1

            for i in range(0, n - length + 1):
                j = i + length
                best = INF
                for d in divisors:
                    changes = 0
                    for r in range(d):
                        left = i + r
                        right = j - 1 - ((j - 1 - (i + r)) % d)
                        # Walk pairs inside this residue class.
                        l, rr = left, right
                        while l < rr:
                            if s[l] != s[rr]:
                                changes += 1
                            l += d
                            rr -= d
                    if changes < best:
                        best = changes
                cost[i][j] = best

        # dp[t][j]: minimum cost to split prefix s[:j] into t parts.
        dp = [[INF] * (n + 1) for _ in range(k + 1)]
        dp[0][0] = 0
        for t in range(1, k + 1):
            for j in range(2 * t, n + 1):
                if k - t > n - j:
                    continue
                best = INF
                prev = dp[t - 1]
                for i in range(2 * (t - 1), j - 1):
                    if prev[i] < INF and j - i >= 2:
                        val = prev[i] + cost[i][j]
                        if val < best:
                            best = val
                dp[t][j] = best

        return dp[k][n]
