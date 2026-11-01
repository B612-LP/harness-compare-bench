class BowlingGame:
    def __init__(self):
        self.frames = []
        self.complete = False

    def roll(self, pins):
        if self.complete:
            raise ValueError("Cannot roll after game is over")
        if not isinstance(pins, int) or isinstance(pins, bool):
            raise ValueError("Invalid roll")
        if pins < 0:
            raise ValueError("Negative roll is invalid")
        if pins > 10:
            raise ValueError("Pin count exceeds pins on the lane")

        if not self.frames:
            self.frames.append([])
        else:
            last = self.frames[-1]
            if len(self.frames) < 10 and (last[0] == 10 or len(last) == 2):
                self.frames.append([])

        frame = self.frames[-1]
        frame_no = len(self.frames)

        if frame_no < 10:
            if len(frame) == 0:
                frame.append(pins)
            elif len(frame) == 1:
                if frame[0] + pins > 10:
                    raise ValueError("Pin count exceeds pins on the lane")
                frame.append(pins)
            else:
                raise ValueError("Cannot roll after game is over")
            return

        n = len(frame)
        if n == 0:
            frame.append(pins)
        elif n == 1:
            first = frame[0]
            if first == 10:
                frame.append(pins)
            else:
                if first + pins > 10:
                    raise ValueError("Pin count exceeds pins on the lane")
                frame.append(pins)
                if first + pins < 10:
                    self.complete = True
        elif n == 2:
            first, second = frame[0], frame[1]
            if first == 10:
                if second == 10:
                    frame.append(pins)
                    self.complete = True
                else:
                    if second + pins > 10:
                        raise ValueError("Pin count exceeds pins on the lane")
                    frame.append(pins)
                    self.complete = True
            else:
                frame.append(pins)
                self.complete = True
        else:
            raise ValueError("Cannot roll after game is over")

    def score(self):
        if not self.complete:
            raise ValueError("Game is not complete")
        rolls = [p for frame in self.frames for p in frame]
        total = 0
        i = 0
        for _ in range(10):
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
