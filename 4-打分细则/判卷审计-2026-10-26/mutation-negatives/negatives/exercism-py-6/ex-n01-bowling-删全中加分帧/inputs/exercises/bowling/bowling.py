"""bowling 参考解：逐球推进的保龄球计分器（含全部非法输入校验）。"""


class BowlingGame:
    def __init__(self):
        self.frames = []  # 已完成的格子（第 10 格含加投）
        self.current = []  # 当前格进行中的投球

    def roll(self, pins):
        if isinstance(pins, bool) or not isinstance(pins, int):
            raise ValueError("pins must be an integer")
        if pins < 0:
            raise ValueError("pins cannot be negative")
        if pins > 10:
            raise ValueError("a roll cannot score more than 10 points")
        if len(self.frames) == 10:
            raise ValueError("cannot roll after the game is complete")
        if len(self.frames) < 9:
            self._roll_regular(pins)
        else:
            self._roll_tenth(pins)

    def _roll_regular(self, pins):
        if not self.current:
            if pins == 10:
                self.frames.append([10])
            else:
                self.current.append(pins)
            return
        if self.current[0] + pins > 10:
            raise ValueError("two rolls in a frame cannot score more than 10 points")
        self.current.append(pins)
        self.frames.append(self.current)
        self.current = []

    def _roll_tenth(self, pins):
        rolls = self.current
        if len(rolls) == 0:
            rolls.append(pins)
            return
        if len(rolls) == 1:
            if rolls[0] == 10:
                rolls.append(pins)
                return
            if rolls[0] + pins > 10:
                raise ValueError("two rolls in a frame cannot score more than 10 points")
            rolls.append(pins)
            if rolls[0] + rolls[1] == 10:  # spare：还要等第 10 格加投
                return
            self._close_tenth()
            return
        # 已有两投：只有 spare 或 strike 才会走到这里
        if rolls[0] == 10 and rolls[1] != 10 and rolls[1] + pins > 10:
            raise ValueError("bonus rolls cannot score more than 10 points")
        rolls.append(pins)
        self._close_tenth()

    def _close_tenth(self):
        self.frames.append(self.current)
        self.current = []

    def score(self):
        if len(self.frames) != 10 or self.current:
            raise ValueError("cannot score an incomplete game")
        flat = [pins for frame in self.frames for pins in frame]
        total = 0
        index = 0
        for frame_number in range(10):
            frame = self.frames[frame_number]
            if frame_number == 9:
                total += sum(frame)
                continue
            if frame[0] == 10:
                total += 10 + flat[index + 1]
            elif frame[0] + frame[1] == 10:
                total += 10 + flat[index + 2]
            else:
                total += frame[0] + frame[1]
            index += len(frame)
        return total