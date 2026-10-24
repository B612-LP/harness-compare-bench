# exercism-py-6 判分规格（spec）

版本：**v1.1（2026-10-24）** ｜ 判分入口：[checker.py](<checker.py>)
定位：**medium-hard · TDD 多题实现题**（6 道 Exercism Python 练习题连做），测「读官方测试反推规格 → 实现 → 自测 → 修到全绿」的任务链与代码耐力。

## 1. 用例定位

`inputs/exercises/` 下 6 题（forth / poker / dominoes / bowling / zipper / pov），每题给**骨架 + 官方 unittest 测试 + 要点 README**。题目全部来自 Exercism Python track 的真实练习题，测试由 canonical-data 自动生成，覆盖正常路径与边界/错误路径；其中 forth、poker、dominoes、bowling 偏算法与规则细节，zipper、pov 偏数据结构与树操作，难度梯度覆盖中到难。

与 `corpus-squeeze`（单点深度优化）互补：本题测**多目标任务下的完成度与正确性**，不依赖迭代调优。

## 2. 判分模式

- **headline 二值 0/1**（`BINARY=True`）：6 题中通过数 **≥5** 且输入完整性守卫通过 → `reward=1`；否则 0。
- `weighted = 通过题数 / 6 × 100`（精确到 0.01）：3 题 → 50.0；4 题 → 66.67；5 题 → 83.33；6 题 → 100.0。
- 每题通过口径：复制题目录到临时目录，仅在副本还原官方测试；通过 `sys.executable -I -S -B trusted_runner.py <temp-exdir> <receipt>` 执行（超时 120s）。除返回码 0，还必须有 runner 正常结束后写出的独立完成回执：发现数、运行数等于 canonical 固定计数，start/stop/success 三组测试身份完整匹配，失败/错误/跳过/expectedFailure/unexpectedSuccess 均为 0。返回码或控制台“OK”不能单独作通过证据。
- 结果新增 `checker_version=1.1` 与每题 `completion`（expected/discovered/tests_run/started/stopped/succeeded/identities_match 等）；旧 reward/weighted/checks API 不变。**无 LLM judge**。
- 判卷器自身不再覆盖原现场官方测试或删除原现场缓存；历史证据复算仍应先复制到 temp，再判卷。
- **安全边界**：runner 在加载候选前安装 stdlib 与计数回调，`-I -S` 防候选目录抢先遮蔽 stdlib/site；可拦早退、伪造控制台摘要、空套件、少回调与跳过，但不是安全沙箱。同进程候选仍可 introspect/monkeypatch 计数器、伪造文件/回执、访问同用户文件、启动子进程、耗尽资源或用绝对路径写回原现场。不能宣称任意敌意代码完全安全；敌意样本需外层低权限 OS 沙箱/容器、无网络、只读证据挂载与资源/进程组限制。

### 三重守卫

1. **truth 与素材一致性（守卫③）**：`truth.json` 里 `input_sha256` / `test_sha256` 与实际 `inputs/`、`tests/` 逐文件不符 → 打印 ERROR JSON，**退出码 2**；`truth.json` 的 `exercises` / `reward_threshold` / `timeout_s` / `binary` 与 checker 常量不一致同样 ERROR。
2. **运行目录输入完整性（守卫②）**：运行目录若带 `inputs/` 副本，其中 6 个 `*_test.py` 缺失或被改动 → 记 `input_integrity` fail，**reward 直接 0**（即使还原官方测试后题目全过）。骨架 `<name>.py` 本来就要被改，不参与该校验；未附 `inputs/` 时记「未核验」（不单独扣分）。
3. **还原官方测试**：每题仅在临时副本还原 canonical 测试，原现场完整性结果在复制前核验。固定计数为 forth=54、poker=37、dominoes=13、bowling=31、zipper=14、pov=15（共 164）；truth 的版本与计数字典也必须匹配 checker。

## 3. 观察项与权重

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| `input_integrity` | 输入/测试完整性（守卫，一票否决） | 0（否决项） | 运行目录内 6 个官方测试与 canonical 一致；未附副本视为未核验 | 任一测试缺失/被改动 → 总分 0 |
| `forth` | Forth 子集解释器 | 16.67 | 官方 `forth_test.py` 全绿（54 例） | 任一用例失败/超时 |
| `poker` | 扑克牌型比较 | 16.67 | 官方 `poker_test.py` 全绿（37 例） | 同上 |
| `dominoes` | 多米诺闭环 | 16.67 | 官方 `dominoes_test.py` 全绿（13 例） | 同上 |
| `bowling` | 保龄球计分 | 16.67 | 官方 `bowling_test.py` 全绿（31 例） | 同上 |
| `zipper` | 二叉树 zipper | 16.67 | 官方 `zipper_test.py` 全绿（14 例） | 同上 |
| `pov` | 树的换根视角与路径 | 16.65 | 官方 `pov_test.py` 全绿（15 例） | 同上 |

权重合计 100；`weighted` 实际按「通过题数 / 6 × 100」计算（与上表等权一致）。`input_integrity` 是否决项，不计入 weighted，但失败时把 reward 压为 0。

## 4. 运行目录约定

```
<run_dir>/
  inputs/
    README.md
    exercises/
      <name>/<name>.py        # 必需：待实现骨架，agent 直接改这里
      <name>/<name>_test.py   # 官方测试（判分前还原）
      <name>/README.md        # 要点速览
      <name>/*.py             # 可选：agent 自己新增的辅助模块
```

- agent 只需「读文件 + 写文件」，允许其自跑 `python3 -m unittest` 自测，但不强制。
- 不要求产出额外报告；运行目录里的其他文件不参与判分。
- 环境：Python 3.9，仅标准库（6 个官方测试只 `import unittest` 与被测模块，无第三方依赖）；不联网。

```bash
python3 checker.py <run_dir>          # 人读明细 + 末行结果 JSON
python3 checker.py <run_dir> --json   # 只输出一行结果 JSON（供脚本聚合）
python3 checker.py --selftest         # 自测：全 PASS 退出 0，否则退出 2
```

退出码：正式判分完成即 `0`（无论 reward 0/1，结果看 JSON）；用法错误 / truth 漂移 / 用例自身不一致 → `2`；`--selftest` 全过 `0`，否则 `2`。

## 5. 判分器自测（`--selftest`，16 组）

v1.1 在原 10 组外新增 6 个精确负例：六题 import 时 `os._exit(0)`、`sys.exit(0)`、伪造 unittest 摘要后早退、参考解+空套件、参考解+无测试回调、参考解+全部跳过。全部要求官方测试完整性仍 PASS，但六题全部 FAIL、reward=0、weighted=0。独立红绿脚本还核验原现场字节/文件清单不变。

全部在 `tempfile.TemporaryDirectory()` 内构造，不污染仓库；每组都核对 `reward`，并对负例做**失败原因精检**（不能「错原因红」冒充通过）。

| # | 组 | 构造 | 期望 |
|---|---|---|---|
| 1 | nop | 空运行目录 | reward=0, weighted=0.0 |
| 2 | oracle | `solution/<name>/<name>.py` 6 份参考解 | reward=1, weighted=100.0，6 题全 PASS |
| 3 | 负例①骨架未实现 | 原样 `inputs/` | reward=0，6 题全 FAIL |
| 4 | 负例②只过一半 | 只放 bowling/zipper/pov 参考解 | reward=0, weighted=50.0 |
| 5 | 负例③改测试 | 6 个测试换成「必过」占位测试 + 骨架未实现 | reward=0；还原后题目仍 FAIL，且 `input_integrity` fail |
| 6 | 负例④删测试 | 删 6 个测试 + 放 6 份参考解 | 还原后 6 题全 PASS（weighted=100.0），但 `input_integrity` fail → reward=0 |
| 7 | 负例⑤语法错误 | 6 份参考解末尾追加非法 Python 语句 | reward=0, 6 题全 FAIL |
| 8 | 负例⑥只写 5 题 | 4 份正确 + 1 份有缺陷实现 + 1 题未动 | 4/6 通过（66.67）< 达标线 → reward=0 |
| 9 | 达标线边界 | 5 份参考解 + 1 题未动 | **reward=1**, weighted=83.33（证明 ≥5/6 口径） |
| 10 | 守卫 | 复制用例目录并篡改其中 `inputs/`，跑子进程 checker | 退出码 2（truth 漂移 ERROR） |

### 达标线与负例口径说明

本题按题面要求采用「通过数 **≥5/6** → reward=1」的宽松达标线（留 1 题容错）。因此「只实现 5 题」本身按口径会拿到 reward=1（见第 9 组边界），不能当作负例。第 8 组负例按「只写了 5 份实现、其中 1 份有缺陷、另 1 题未动 → 4/6」构造，既保留「只写 5 题」的语义，又落在达标线下 → reward=0。若后续希望 6 题全对才给 1，把 `PASS_THRESHOLD` 与 `truth.reward_threshold` 同步改成 6 即可（自测第 9 组期望随之改为 0）。

## 6. 来源与许可证

- **来源**：Aider polyglot-benchmark（https://github.com/Aider-AI/polyglot-benchmark）中的 Python 练习题打包；上游为 **Exercism Python track**（https://github.com/exercism/python），测试数据来自 Exercism problem-specifications（https://github.com/exercism/problem-specifications）。
- **许可证**：MIT License（Exercism 与 polyglot-benchmark 均为 MIT）。
- **读取日期**：2026-10-22（素材取自本机已落盘的 polyglot-benchmark 快照，未联网）。
- **是否改写**：
  - 6 份官方测试（`*_test.py`）与骨架（`*.py`）**原样保留、未改写**（SHA-256 记录在 `truth.json`）；
  - 题面 `instruction.md`、`spec.md`、各题 `README.md`、`inputs/README.md` 为中文重写（不整段照抄官方题面），保留关键约束与输入输出格式；
  - `checker.py` 与 `solution/` 下 6 份参考解为本题库新写代码（仅标准库），参考解均已跑通官方测试。
- **署名**：Exercises and tests © Exercism contributors, MIT License；benchmark packaging © Aider polyglot-benchmark contributors, MIT License。

## 7. 变更记录

- 2026-10-22 v1.0：首版入库。6 题（forth/poker/dominoes/bowling/zipper/pov）+ 官方测试还原守卫 + 逐题 120s 超时 + ≥5/6 达标线；6 份参考解实测全绿；`--selftest` 10 组（nop / oracle / 6 负例 / 达标线边界 / truth 漂移守卫）全 PASS。