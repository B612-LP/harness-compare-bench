from collections import Counter
from typing import List


class Solution:
    def countSubMultisets(self, nums: List[int], l: int, r: int) -> int:
        mod = 10**9 + 7
        frequencies = Counter(nums)
        zero_count = frequencies.pop(0, 0)

        dp = [0] * (r + 1)
        dp[0] = 1

        for value, count in frequencies.items():
            if value > r:
                continue

            next_dp = [0] * (r + 1)
            for remainder in range(min(value, r + 1)):
                window = 0
                for total in range(remainder, r + 1, value):
                    window += dp[total]
                    excluded = total - (count + 1) * value
                    if excluded >= 0:
                        window -= dp[excluded]
                    window %= mod
                    next_dp[total] = window
            dp = next_dp

        answer = sum(dp[l:r + 1]) % mod
        return answer * (zero_count + 1) % mod
