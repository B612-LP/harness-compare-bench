class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if not isinstance(pins, int) or isinstance(pins, bool) or pins < 0 or pins > 10:
            raise ValueError("Invalid roll")
        valid, complete = self._analyze(self.rolls)
        if valid and complete:
            raise ValueError("Game is already complete")
        new_rolls = self.rolls + [pins]
        valid, complete = self._analyze(new_rolls)
        if not valid:
            raise ValueError("Invalid roll")
        self.rolls = new_rolls

    def score(self):
        valid, complete = self._analyze(self.rolls)
        if not valid:
            raise ValueError("Invalid game")
        if not complete:
            raise ValueError("Game is not complete")

        rolls = self.rolls
        total = 0
        i = 0
        for frame in range(10):
            if frame < 9:
                if rolls[i] == 10:
                    total += 10 + rolls[i + 1] + rolls[i + 2]
                    i += 1
                elif rolls[i] + rolls[i + 1] == 10:
                    total += 10 + rolls[i + 2]
                    i += 2
                else:
                    total += rolls[i] + rolls[i + 1]
                    i += 2
            else:
                if rolls[i] == 10:
                    total += 10 + rolls[i + 1] + rolls[i + 2]
                elif rolls[i] + rolls[i + 1] == 10:
                    total += 10 + rolls[i + 2]
                else:
                    total += rolls[i] + rolls[i + 1]
        return total

    def _analyze(self, rolls):
        i = 0
        n = len(rolls)
        for frame in range(1, 11):
            if frame < 10:
                if i >= n:
                    return True, False
                first = rolls[i]
                if first < 0 or first > 10:
                    return False, False
                if first == 10:
                    i += 1
                else:
                    if i + 1 >= n:
                        return True, False
                    second = rolls[i + 1]
                    if second < 0 or second > 10 or first + second > 10:
                        return False, False
                    i += 2
            else:
                if i >= n:
                    return True, False
                first = rolls[i]
                if first < 0 or first > 10:
                    return False, False
                if first == 10:
                    if i + 1 >= n:
                        return True, False
                    second = rolls[i + 1]
                    if second < 0 or second > 10:
                        return False, False
                    if i + 2 >= n:
                        return True, False
                    third = rolls[i + 2]
                    if third < 0 or third > 10:
                        return False, False
                    if second != 10 and second + third > 10:
                        return False, False
                    i += 3
                    return (i == n), (i == n)
                else:
                    if i + 1 >= n:
                        return True, False
                    second = rolls[i + 1]
                    if second < 0 or second > 10 or first + second > 10:
                        return False, False
                    if first + second == 10:
                        if i + 2 >= n:
                            return True, False
                        third = rolls[i + 2]
                        if third < 0 or third > 10:
                            return False, False
                        i += 3
                    else:
                        i += 2
                    return (i == n), (i == n)
        return True, False
