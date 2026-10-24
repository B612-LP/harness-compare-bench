from typing import List

class Solution:
    def countSubMultisets(self, nums: List[int], l: int, r: int) -> int:
        MOD = 10 ** 9 + 7

        max_val = max(nums) if nums else 0
        occ = [0] * (max_val + 1)
        for x in nums:
            occ[x] += 1

        dp = [0] * (r + 1)
        dp[0] = 1

        for x in range(1, max_val + 1):
            c = occ[x]
            if c == 0 or x > r:
                continue
            # newdp[s] = sum(dp[s - t*x] for t in [0, c])
            newdp = [0] * (r + 1)
            for rem in range(x):
                window = 0
                # s = rem + q*x
                q = 0
                s = rem
                while s <= r:
                    window += dp[s]
                    if q - c - 1 >= 0:
                        window -= dp[rem + (q - c - 1) * x]
                    window %= MOD
                    newdp[s] = window
                    q += 1
                    s += x
            dp = newdp

        zeros = occ[0]
        multiplier = zeros + 1
        ans = 0
        for s in range(l, r + 1):
            ans += dp[s]
        return (ans % MOD) * multiplier % MOD
