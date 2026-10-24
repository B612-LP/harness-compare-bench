class BowlingGame:
    def __init__(self):
        self.frames = []
        self.current = []
        self.done = False

    def roll(self, pins):
        if isinstance(pins, bool) or not isinstance(pins, int):
            raise ValueError("pins must be an integer")
        if pins < 0 or pins > 10:
            raise ValueError("pins must be between 0 and 10")
        if self.done:
            raise ValueError("cannot roll after the game is over")

        if len(self.frames) < 9:
            if not self.current:
                self.current.append(pins)
                if pins == 10:
                    self.frames.append(self.current)
                    self.current = []
            else:
                if self.current[0] + pins > 10:
                    raise ValueError("frame total cannot exceed 10")
                self.current.append(pins)
                self.frames.append(self.current)
                self.current = []
            return

        # Tenth frame.
        if not self.current:
            self.current.append(pins)
        elif len(self.current) == 1:
            first = self.current[0]
            if first == 10:
                self.current.append(pins)
            else:
                if first + pins > 10:
                    raise ValueError("frame total cannot exceed 10")
                self.current.append(pins)
                if first + pins < 10:
                    self.frames.append(self.current)
                    self.current = []
                    self.done = True
        else:
            first, second = self.current
            if first == 10:
                if second != 10 and second + pins > 10:
                    raise ValueError("bonus rolls cannot exceed 10")
            self.current.append(pins)
            self.frames.append(self.current)
            self.current = []
            self.done = True

    def _next_rolls(self, frame_index, count):
        rolls = []
        for frame in self.frames[frame_index + 1:]:
            rolls.extend(frame)
        return sum(rolls[:count])

    def score(self):
        if not self.done:
            raise ValueError("game is not complete")

        total = 0
        for index, frame in enumerate(self.frames):
            if index == 9:
                total += sum(frame)
            elif frame[0] == 10:
                total += 10 + self._next_rolls(index, 2)
            elif sum(frame) == 10:
                total += 10 + self._next_rolls(index, 1)
            else:
                total += sum(frame)
        return total
