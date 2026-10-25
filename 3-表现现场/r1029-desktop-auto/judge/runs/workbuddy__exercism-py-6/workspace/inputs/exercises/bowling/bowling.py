class BowlingGame:
    def __init__(self):
        self.frames = []          # completed frames (first nine, then the tenth)
        self.current = []         # rolls of the frame in progress
        self.finished = False

    def roll(self, pins):
        if not isinstance(pins, int) or isinstance(pins, bool):
            raise ValueError("Pin count must be an integer")
        if pins < 0:
            raise ValueError("Pin count cannot be negative")
        if pins > 10:
            raise ValueError("Pin count cannot be greater than 10")
        if self.finished:
            raise ValueError("Cannot roll after the game is over")

        if len(self.frames) < 9:
            self._roll_open_frame(pins)
        else:
            self._roll_tenth_frame(pins)

    def _roll_open_frame(self, pins):
        if not self.current:
            if pins == 10:
                self.frames.append([10])
            else:
                self.current.append(pins)
            return
        if self.current[0] + pins > 10:
            raise ValueError("Two rolls in a frame cannot score more than 10")
        self.current.append(pins)
        self.frames.append(self.current)
        self.current = []

    def _roll_tenth_frame(self, pins):
        first = self.current[0] if self.current else None

        if first is None:
            self.current.append(pins)
            return

        if first == 10:
            # Fresh pair after a strike in the tenth frame.
            if len(self.current) == 1:
                self.current.append(pins)
                return
            second = self.current[1]
            if second != 10 and second + pins > 10:
                raise ValueError("Two rolls in a frame cannot score more than 10")
            self.current.append(pins)
            self.frames.append(self.current)
            self.finished = True
            return

        if len(self.current) == 1:
            if first + pins > 10:
                raise ValueError("Two rolls in a frame cannot score more than 10")
            self.current.append(pins)
            if first + pins < 10:
                self.frames.append(self.current)
                self.finished = True
            return

        # Spare in the tenth frame: one bonus roll, anything up to 10.
        self.current.append(pins)
        self.frames.append(self.current)
        self.finished = True

    def _all_rolls(self):
        rolls = []
        for frame in self.frames:
            rolls.extend(frame)
        return rolls

    def score(self):
        if len(self.frames) < 10 or not self.finished:
            raise ValueError("Cannot score an incomplete game")

        rolls = self._all_rolls()
        total = 0
        index = 0
        for _ in range(10):
            if rolls[index] == 10:
                total += 10 + rolls[index + 1] + rolls[index + 2]
                index += 1
            elif rolls[index] + rolls[index + 1] == 10:
                total += 10 + rolls[index + 2]
                index += 2
            else:
                total += rolls[index] + rolls[index + 1]
                index += 2
        return total
