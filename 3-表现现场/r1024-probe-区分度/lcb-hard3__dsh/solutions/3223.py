class Solution:
    def countCompleteSubstrings(self, word: str, k: int) -> int:
        n = len(word)

        # Split into maximal segments where every adjacent pair differs by <= 2.
        segments = []
        start = 0
        for i in range(1, n):
            if abs(ord(word[i]) - ord(word[i - 1])) > 2:
                segments.append((start, i))
                start = i
        segments.append((start, n))

        ans = 0
        for lo, hi in segments:
            seg_len = hi - lo
            max_m = min(26, seg_len // k)
            for m in range(1, max_m + 1):
                L = m * k
                if L > seg_len:
                    break
                cnt = [0] * 26
                # bad = number of letters whose count is neither 0 nor k.
                bad = 0
                for idx in range(lo, lo + L):
                    c = ord(word[idx]) - 97
                    old = cnt[c]
                    if old != 0 and old != k:
                        bad -= 1
                    cnt[c] = old + 1
                    if cnt[c] != 0 and cnt[c] != k:
                        bad += 1
                if bad == 0:
                    ans += 1
                for idx in range(lo + L, hi):
                    add = ord(word[idx]) - 97
                    rem = ord(word[idx - L]) - 97

                    old = cnt[rem]
                    if old != 0 and old != k:
                        bad -= 1
                    cnt[rem] = old - 1
                    if cnt[rem] != 0 and cnt[rem] != k:
                        bad += 1

                    old = cnt[add]
                    if old != 0 and old != k:
                        bad -= 1
                    cnt[add] = old + 1
                    if cnt[add] != 0 and cnt[add] != k:
                        bad += 1

                    if bad == 0:
                        ans += 1
        return ans
