class BowlingGame:
    def __init__(self):
        self.rolls = []
        self.frame = 1
        self.first_roll = None  # first roll of the current frame
        # bonus phase (after the 10th frame)
        self.bonus_needed = 0
        self.bonus_done = 0
        self.bonus_first = None
        self.complete = False

    def roll(self, pins):
        if not 0 <= pins <= 10:
            raise Exception("pins must be between 0 and 10")
        if self.complete:
            raise Exception("game is already complete")

        self.rolls.append(pins)

        if self.bonus_needed > 0:
            if self.bonus_needed == 2:
                # bonus after a strike in the 10th frame
                if self.bonus_done == 0:
                    self.bonus_first = pins
                else:
                    if self.bonus_first != 10 and self.bonus_first + pins > 10:
                        raise Exception(
                            "two bonus rolls cannot knock down more than 10 pins"
                        )
            self.bonus_done += 1
            if self.bonus_done == self.bonus_needed:
                self.complete = True
            return

        if pins == 10:
            # strike
            if self.frame == 10:
                self.bonus_needed = 2
            else:
                self.frame += 1
        elif self.first_roll is None:
            self.first_roll = pins
        else:
            if self.first_roll + pins > 10:
                raise Exception(
                    "two rolls in a frame cannot knock down more than 10 pins"
                )
            if self.frame == 10:
                if self.first_roll + pins == 10:
                    # spare
                    self.bonus_needed = 1
                else:
                    self.complete = True
            else:
                self.frame += 1
            self.first_roll = None

    def score(self):
        if not self.complete:
            raise Exception("game is not complete")

        total = 0
        i = 0
        for _ in range(10):
            if self.rolls[i] == 10:
                total += 10 + self.rolls[i + 1] + self.rolls[i + 2]
                i += 1
            elif self.rolls[i] + self.rolls[i + 1] == 10:
                total += 10 + self.rolls[i + 2]
                i += 2
            else:
                total += self.rolls[i] + self.rolls[i + 1]
                i += 2
        return total
