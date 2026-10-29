class BowlingGame:
    def __init__(self):
        self.rolls = []

    # -- validation ------------------------------------------------------
    def _analyze(self, rolls):
        """Walk the roll list frame by frame.

        Returns (complete, frames) where frames is a list of lists of rolls
        for each completed frame. Raises ValueError on any illegal sequence.
        """
        index = 0
        total = len(rolls)
        frames = []

        for frame_number in range(1, 11):
            if frame_number < 10:
                if index >= total:
                    return False, frames
                if rolls[index] == 10:
                    frames.append([10])
                    index += 1
                    continue
                if index + 1 >= total:
                    return False, frames
                if rolls[index] + rolls[index + 1] > 10:
                    raise ValueError("frame score is more than 10")
                frames.append([rolls[index], rolls[index + 1]])
                index += 2
            else:
                # Tenth frame.
                if index >= total:
                    return False, frames
                first = rolls[index]
                if first == 10:
                    if index + 2 >= total:
                        return False, frames
                    second = rolls[index + 1]
                    third = rolls[index + 2]
                    if second != 10 and second + third > 10:
                        raise ValueError("bonus rolls score is more than 10")
                    frames.append([first, second, third])
                    index += 3
                else:
                    if index + 1 >= total:
                        return False, frames
                    second = rolls[index + 1]
                    if first + second > 10:
                        raise ValueError("frame score is more than 10")
                    if first + second == 10:
                        if index + 2 >= total:
                            return False, frames
                        frames.append([first, second, rolls[index + 2]])
                        index += 3
                    else:
                        frames.append([first, second])
                        index += 2

        if index != total:
            raise ValueError("cannot roll after the game is over")
        return True, frames

    # -- public API ------------------------------------------------------
    def roll(self, pins):
        if not isinstance(pins, int) or isinstance(pins, bool):
            raise TypeError("pins must be an integer")
        if pins < 0:
            raise ValueError("negative rolls are not allowed")
        if pins > 10:
            raise ValueError("a roll cannot score more than 10 points")
        self.rolls.append(pins)
        try:
            self._analyze(self.rolls)
        except ValueError:
            self.rolls.pop()
            raise

    def score(self):
        complete, frames = self._analyze(self.rolls)
        if not complete:
            raise ValueError("game is not complete")

        flattened = [pin for frame in frames for pin in frame]
        index = 0
        total = 0
        for frame_number in range(10):
            frame = frames[frame_number]
            if frame_number < 9:
                if frame[0] == 10:
                    total += 10 + flattened[index + 1] + flattened[index + 2]
                    index += 1
                elif frame[0] + frame[1] == 10:
                    total += 10 + flattened[index + 2]
                    index += 2
                else:
                    total += frame[0] + frame[1]
                    index += 2
            else:
                total += sum(frame)
        return total
