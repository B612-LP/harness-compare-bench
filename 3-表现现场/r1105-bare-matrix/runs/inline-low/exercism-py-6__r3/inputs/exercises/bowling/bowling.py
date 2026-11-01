class BowlingGame:
    def __init__(self):
        self.rolls = []

    def _validate(self):
        rolls = self.rolls
        i = 0
        for frame in range(10):
            if i >= len(rolls):
                return False
            first = rolls[i]
            if first < 0 or first > 10:
                raise ValueError("Invalid roll")
            if frame < 9:
                i += 1
                if first == 10:
                    continue
                if i >= len(rolls):
                    return False
                second = rolls[i]
                if second < 0 or second > 10:
                    raise ValueError("Invalid roll")
                if first + second > 10:
                    raise ValueError("Invalid frame")
                i += 1
            else:
                i += 1
                if first == 10:
                    if i >= len(rolls):
                        return False
                    second = rolls[i]
                    if second < 0 or second > 10:
                        raise ValueError("Invalid roll")
                    i += 1
                    if i >= len(rolls):
                        return False
                    third = rolls[i]
                    if third < 0 or third > 10:
                        raise ValueError("Invalid roll")
                    if second != 10 and second + third > 10:
                        raise ValueError("Invalid bonus")
                    i += 1
                else:
                    if i >= len(rolls):
                        return False
                    second = rolls[i]
                    if second < 0 or second > 10:
                        raise ValueError("Invalid roll")
                    if first + second > 10:
                        raise ValueError("Invalid frame")
                    i += 1
                    if first + second == 10:
                        if i >= len(rolls):
                            return False
                        third = rolls[i]
                        if third < 0 or third > 10:
                            raise ValueError("Invalid roll")
                        i += 1
        if i != len(rolls):
            raise ValueError("Too many rolls")
        return True

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Invalid roll")
        self.rolls.append(pins)
        try:
            self._validate()
        except Exception:
            self.rolls.pop()
            raise

    def score(self):
        if not self._validate():
            raise ValueError("Game is incomplete")
        rolls = self.rolls
        total = 0
        i = 0
        for frame in range(10):
            if rolls[i] == 10:
                total += 10 + rolls[i + 1] + rolls[i + 2]
                i += 1
            elif rolls[i] + rolls[i + 1] == 10:
                total += 10 + rolls[i + 2]
                i += 2
            else:
                total += rolls[i] + rolls[i + 1]
                i += 2
        return total
