class Solution:
    def countCompleteSubstrings(self, word: str, k: int) -> int:
        def count_segment(segment: str) -> int:
            length = len(segment)
            total = 0

            for distinct_count in range(1, min(26, length // k) + 1):
                window_length = distinct_count * k
                counts = [0] * 26
                distinct = 0
                exact = 0

                for index, char in enumerate(segment):
                    code = ord(char) - ord('a')
                    old = counts[code]
                    if old == 0:
                        distinct += 1
                    if old == k:
                        exact -= 1
                    counts[code] = old + 1
                    if counts[code] == k:
                        exact += 1

                    if index >= window_length:
                        removed_code = ord(segment[index - window_length]) - ord('a')
                        removed_old = counts[removed_code]
                        if removed_old == k:
                            exact -= 1
                        if removed_old == 1:
                            distinct -= 1
                        counts[removed_code] = removed_old - 1
                        if counts[removed_code] == k:
                            exact += 1

                    if index >= window_length - 1:
                        if distinct == distinct_count and exact == distinct_count:
                            total += 1

            return total

        answer = 0
        segment_start = 0

        for index in range(1, len(word) + 1):
            if index == len(word) or abs(ord(word[index]) - ord(word[index - 1])) > 2:
                answer += count_segment(word[segment_start:index])
                segment_start = index

        return answer
