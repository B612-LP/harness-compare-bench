class BowlingGame:
    def __init__(self):
        self.frames = []

    def roll(self, pins):
        if not isinstance(pins, int) or isinstance(pins, bool):
            raise ValueError("Pin count must be an integer")
        if pins < 0 or pins > 10:
            raise ValueError("Pin count must be between 0 and 10")

        if len(self.frames) == 10:
            last = self.frames[9]
            if len(last) == 3:
                raise ValueError("Game is complete")
            if last[0] == 10:
                if len(last) == 2 and last[1] != 10 and last[1] + pins > 10:
                    raise ValueError("Frame total exceeds 10 pins")
                last.append(pins)
            elif len(last) == 1:
                if last[0] + pins > 10:
                    raise ValueError("Frame total exceeds 10 pins")
                last.append(pins)
            elif sum(last) == 10:
                last.append(pins)
            else:
                raise ValueError("Game is complete")
        elif self.frames and len(self.frames[-1]) == 1 and self.frames[-1][0] != 10:
            if self.frames[-1][0] + pins > 10:
                raise ValueError("Frame total exceeds 10 pins")
            self.frames[-1].append(pins)
        else:
            self.frames.append([pins])

    def _is_complete(self):
        if len(self.frames) < 10:
            return False
        last = self.frames[9]
        if last[0] == 10 or (len(last) >= 2 and last[0] + last[1] == 10):
            return len(last) == 3
        return len(last) == 2

    def score(self):
        if not self._is_complete():
            raise ValueError("Game is not complete")

        rolls = [pins for frame in self.frames for pins in frame]
        total = 0
        index = 0
        for number, frame in enumerate(self.frames):
            if number < 9:
                if frame[0] == 10:
                    total += 10 + rolls[index + 1] + rolls[index + 2]
                    index += 1
                elif sum(frame) == 10:
                    total += 10 + rolls[index + 2]
                    index += 2
                else:
                    total += sum(frame)
                    index += 2
            else:
                total += sum(frame)
        return total
