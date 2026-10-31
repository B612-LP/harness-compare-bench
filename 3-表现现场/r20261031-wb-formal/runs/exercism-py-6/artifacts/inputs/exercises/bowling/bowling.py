class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pin count must be between 0 and 10")
        self._frames(self.rolls + [pins])
        self.rolls.append(pins)

    def _frames(self, rolls):
        """Split rolls into frames, validating them along the way."""
        frames = []
        i = 0
        while i < len(rolls):
            if len(frames) == 10:
                raise ValueError("Cannot roll after the game is over")
            if len(frames) < 9:
                if rolls[i] == 10:
                    frames.append([10])
                    i += 1
                elif i + 1 < len(rolls):
                    if rolls[i] + rolls[i + 1] > 10:
                        raise ValueError("Two rolls in a frame cannot exceed 10")
                    frames.append([rolls[i], rolls[i + 1]])
                    i += 2
                else:
                    frames.append([rolls[i]])
                    i += 1
            else:
                frame = list(rolls[i:])
                if len(frame) >= 2:
                    if frame[0] != 10 and frame[0] + frame[1] > 10:
                        raise ValueError("Two rolls in a frame cannot exceed 10")
                bonus = frame[0] == 10 or (
                    len(frame) >= 2 and frame[0] + frame[1] == 10
                )
                if len(frame) > (3 if bonus else 2):
                    raise ValueError("Too many rolls in the last frame")
                if bonus and len(frame) >= 3 and frame[0] == 10:
                    if frame[1] != 10 and frame[1] + frame[2] > 10:
                        raise ValueError("Two rolls in a frame cannot exceed 10")
                frames.append(frame)
                i = len(rolls)
        return frames

    def score(self):
        frames = self._frames(self.rolls)
        if len(frames) < 10:
            raise ValueError("Cannot score an incomplete game")
        last = frames[9]
        if last[0] == 10 or (len(last) >= 2 and last[0] + last[1] == 10):
            complete = len(last) == 3
        else:
            complete = len(last) == 2
        if not complete:
            raise ValueError("Cannot score an incomplete game")

        rolls = self.rolls
        total = 0
        index = 0
        for _ in range(10):
            if rolls[index] == 10:
                total += 10 + sum(rolls[index + 1:index + 3])
                index += 1
            elif rolls[index] + rolls[index + 1] == 10:
                total += 10 + rolls[index + 2]
                index += 2
            else:
                total += rolls[index] + rolls[index + 1]
                index += 2
        return total
