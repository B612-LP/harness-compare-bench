class BowlingGame:
    def __init__(self):
        self.rolls = []
        self.frame = 1          # current frame number, 1..10
        self.in_frame = 0       # rolls already made in current frame
        self.first = None       # first roll of current frame
        self.bonus_needed = 0   # bonus rolls after frame 10
        self.bonus_done = 0
        self.finished = False

    def roll(self, pins):
        if self.finished:
            raise ValueError("Cannot roll after game is complete")
        if not isinstance(pins, int) or pins < 0 or pins > 10:
            raise ValueError("Invalid number of pins")

        if self.frame < 10:
            if self.in_frame == 0:
                self.first = pins
                self.rolls.append(pins)
                if pins == 10:
                    self.frame += 1
                    self.in_frame = 0
                else:
                    self.in_frame = 1
            else:
                if self.first + pins > 10:
                    raise ValueError("Two rolls in a frame cannot exceed 10")
                self.rolls.append(pins)
                self.frame += 1
                self.in_frame = 0
                self.first = None
        else:
            # Tenth frame, including bonus rolls
            pos = self.in_frame
            if pos == 0:
                self.rolls.append(pins)
                self.in_frame = 1
                self.first = pins
            elif pos == 1:
                if self.first != 10 and self.first + pins > 10:
                    raise ValueError("Two rolls in a frame cannot exceed 10")
                self.rolls.append(pins)
                if self.first != 10 and self.first + pins < 10:
                    self.finished = True
                else:
                    self.in_frame = 2
            else:
                # Third roll (bonus): after strike or spare
                if self.first == 10:
                    first_bonus = self.rolls[-1]
                    if first_bonus != 10 and first_bonus + pins > 10:
                        raise ValueError("Bonus rolls cannot exceed 10")
                self.rolls.append(pins)
                self.finished = True

    def score(self):
        if not self.rolls or not self.finished:
            raise ValueError("Game is not complete")
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
