class BowlingGame:
    def __init__(self):
        self.rolls = []

    def _is_complete(self, rolls):
        index = 0

        for _ in range(9):
            if index == len(rolls):
                return False

            first = rolls[index]
            if first < 0 or first > 10:
                raise ValueError("Invalid roll")
            if first == 10:
                index += 1
                continue

            if index + 1 == len(rolls):
                return False

            second = rolls[index + 1]
            if second < 0 or second > 10 or first + second > 10:
                raise ValueError("Invalid frame")
            index += 2

        if index == len(rolls):
            return False

        first = rolls[index]
        if first < 0 or first > 10:
            raise ValueError("Invalid roll")

        if index + 1 == len(rolls):
            return False
        second = rolls[index + 1]
        if second < 0 or second > 10:
            raise ValueError("Invalid roll")

        if first == 10:
            if index + 2 == len(rolls):
                return False
            third = rolls[index + 2]
            if third < 0 or third > 10 or (second != 10 and second + third > 10):
                raise ValueError("Invalid bonus roll")
            if len(rolls) != index + 3:
                raise ValueError("Game is already complete")
            return True

        if first + second > 10:
            raise ValueError("Invalid frame")
        if first + second < 10:
            if len(rolls) != index + 2:
                raise ValueError("Game is already complete")
            return True

        if index + 2 == len(rolls):
            return False
        third = rolls[index + 2]
        if third < 0 or third > 10:
            raise ValueError("Invalid bonus roll")
        if len(rolls) != index + 3:
            raise ValueError("Game is already complete")
        return True

    def roll(self, pins):
        if type(pins) is not int or pins < 0 or pins > 10:
            raise ValueError("Invalid roll")

        candidate = self.rolls + [pins]
        self._is_complete(candidate)
        self.rolls.append(pins)

    def score(self):
        if not self._is_complete(self.rolls):
            raise ValueError("Game is not complete")

        total = 0
        index = 0
        for _ in range(9):
            if self.rolls[index] == 10:
                total += 10 + self.rolls[index + 1] + self.rolls[index + 2]
                index += 1
            elif self.rolls[index] + self.rolls[index + 1] == 10:
                total += 10 + self.rolls[index + 2]
                index += 2
            else:
                total += self.rolls[index] + self.rolls[index + 1]
                index += 2

        return total + sum(self.rolls[index:])
