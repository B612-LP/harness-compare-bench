# bowling

实现保龄球计分：一局 10 格，每格两次投球机会；全中（strike）或补中（spare）有加投奖励，第 10 格可加投。

- `roll(pins)` 逐球记录，`score()` 返回整局总分。
- 所有非法输入都要抛出带非空消息的异常（类型不限，测试用 `assertRaisesRegex(Exception, r".+")` 校验）。
- 非法情形包括：负分、单球超过 10、单格两球合计超过 10、局已结束还继续投、未完成的局就计分等。

实现目标文件：`bowling.py`（`BowlingGame` 类）。
