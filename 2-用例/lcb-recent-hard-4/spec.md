# lcb-recent-hard-4 判分规格（spec）

版本：**v0.1（2026-10-22，首版 staging）；v0.1·B8 披露式修订（2026-10-27：stderr 口径显式化，判分行为不变）** ｜ 判分入口：`checker.py`
定位：**hard · 近期竞赛算法题（4 题达标线制，含隐藏私有测试）**，CLI 为主、产物判分；与既有 hard 三题（迭代优化 / 多源冲突 / 账本重放）互补，考「多文件算法交付 + 自带隐藏测试的抗过拟合」。

## 1. 用例定位

投喂 `inputs/problems.json`：官方 [LiveCodeBench v6](https://github.com/LiveCodeBench/LiveCodeBench) 从 `test6.jsonl` 抽取的 **4 道 2025-01 近期 AtCoder hard（F/G）**，题面中文重写（保留输入/输出格式、约束、全部样例）。要求产品在运行目录交付 `solutions/<problem_id>.py`（stdin → stdout），判分器用每道题**公开样例 + 40 组隐藏私有测试**逐组实跑。
这是 r1024 探针用例 `lcb-v6-hard4` 的**五件套正式化改造**：题面由英文原文改为**中文重写**、检查器改成本仓 `checker.py` 契约（三重守卫 + `--selftest` 11 项）、补 `truth.json` 测试集 SHA-256、`solution/` oracle 用本 checker 复验 4/4。

## 2. 判分模式

- **headline 为二值 0/1**（`BINARY=True`）：4 题中 **通过 ≥ `PASS_THRESHOLD`=2 题** → reward=1，否则 0。
- **weighted = 通过题数 / 4 × 100**（单题内部无部分分：该题测试全过才算通过）。
- 每题权重 25；守卫项（输入完整性）权重 0，失败时直接压制 reward=0（不影响 weighted 数值，但 headline 归零）。
- 单题判定：把该题全部测试逐组喂给 `python3 solutions/<id>.py`（stdin 注入，单组超时 10s），输出按行 rstrip 比较；**首个失败即短路**，该题判 fail 并记录失败测试序号与失败类型（`missing`/`timeout`/`exit`/`wrong`/`budget`）。

## 3. 观察项与权重

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| `input_integrity` | 输入完整性（守卫） | 0（守卫） | run_dir 未附输入副本（未核验）或附带的 `inputs/problems.json` 与 canonical SHA-256 一致 | 附带副本被修改 → 直接压制 reward=0 |
| `abc387_f` | Count Arrays（ABC387 F，43 组测试） | 25 | 43/43 全过 | 任一测试 fail / 缺文件 |
| `abc388_f` | Dangerous Sugoroku（ABC388 F，43 组） | 25 | 43/43 全过 | 同上 |
| `abc388_g` | Simultaneous Kagamimochi 2（ABC388 G，42 组） | 25 | 42/42 全过 | 同上 |
| `abc389_g` | Odd Even Graph（ABC389 G，43 组） | 25 | 43/43 全过 | 同上 |

达标线：`passed_problems ≥ 2`（写死 checker `PASS_THRESHOLD=2`，与 truth.json `pass_threshold` 交叉校验）。
计分示例：4/4 → reward 1、weighted 100；2/4 → reward 1、weighted 50；1/4 → reward 0、weighted 25；0/4 → reward 0、weighted 0。

## 4. 运行目录约定

```
<run_dir>/
  solutions/<problem_id>.py   # 必需产物，每题一个（abc387_f / abc388_f / abc388_g / abc389_g）
  inputs/problems.json        # 可选：本次读取的输入副本（附了就会核验 SHA-256）
```

- 只接受 `solutions/` 子目录下的 `<problem_id>.py`；文件名必须与题目 id 完全一致，不接受改名/合并文件。
- 程序必须从 stdin 读、向 stdout 写；不得依赖运行目录中的输入文件。
- staging 运行器按 `case.json` 把 `cases/lcb-recent-hard-4/inputs/` 整个拷成 `run_dir/inputs/`，因此任务书路径写 `inputs/problems.json`。

```bash
python3 checker.py <run_dir>           # 人读报告 + 末行 RESULTS_JSON
python3 checker.py <run_dir> --json    # 只输出一行 JSON（供脚本聚合）
python3 checker.py --selftest          # 自测：nop/oracle/边界/8 组负例（含 B8 披露项）/真值漂移守卫
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / run_dir 不存在 / 用例自身不一致（truth 漂移）。

## 5. 判分器实现口径（可复核）

1. **逐组实跑外部产物**：不采信产品自述，只读 run_dir 文件 + `subprocess(sys.executable, solutions/<id>.py, stdin=测试输入)`；不联网、不装包、不读 `/tmp` 或仓库其它路径。
2. **超时**：单组 10s（`TEST_TIMEOUT_S=10`）；另有单题累计预算 240s（`PROBLEM_BUDGET_S=240`）防病态解拖死判分（超预算该题 fail，记 `fail_kind=budget`）。oracle 最慢单组实测 1.37s（abc389_g 最大用例），距 10s 有 7.3× 余量；oracle 全部 171 组总耗时约 7.3s。
3. **比较口径**：`norm()` = 统一 CRLF/LF → 逐行 `rstrip()` → 丢弃末尾空行；不做字段级解析（Yes/No、多行数字、空格分隔均按原文比较）。行首多余空格/词间多空格/多余行都会判错。
   **stderr 口径（B8，2026-10-27 显式披露）**：**stderr 完全不参与输出比较**——只比对 stdout（按行 rstrip）、退出码（非 0 判 fail）与超时；程序向 stderr 打印「OK passed all tests」等伪造成功标记**不影响分值**。取「披露式」而非加严的理由：与上游 AtCoder 官方判定一致（官方同样只比对 stdout，stderr 输出不参与判定），伪造标记不改变答案正确性；本口径与 v0.1 判分行为完全一致，仅把隐式行为显式化并由自测 #12 断言防回归（证据组：mutation-negatives `lcb-n05`；收据：[判卷审计 2026-10-27](<../../4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md>)）。
4. **三重守卫**：
   - ① **truth 漂移**：`truth.json` 记录的 `inputs/problems.json` SHA-256 与字节数须与磁盘一致，否则 ERROR exit 2；
   - ② **运行目录输入副本**：run_dir 若带 `inputs/problems.json`（或根目录同名）且 SHA-256 与 canonical 不符 → `input_integrity` fail、reward 强制 0；
   - ③ **truth 与 checker 常量一致**：题数=4、达标线=2、单组超时=10、各题测试数（43/43/42/43）、每题测试集 SHA-256（`tests_sha256`）任一不符 → ERROR exit 2。
5. **仅标准库**：`argparse/hashlib/json/shutil/subprocess/sys/tempfile/time/pathlib`；Python 3.9 兼容。

## 6. 负例与自测（`--selftest` 12 项，2026-10-27 实测全绿；v0.1 为 11 项）

| # | 项 | 期望 | 实测 | 说明 |
|---:|---|---:|---:|---|
| 1 | nop（空 run_dir） | 0 | 0 | 空跑预期 ≤0.3 的闸门 1 |
| 2 | oracle（`solution/` 四题） | 1 | 1 | 43/43、43/43、42/42、43/43，weighted 100 |
| 3 | 边界：恰好 2/4 通过 | 1 | 1 | weighted 50，验证达标线 |
| 4 | 负例：只交 1 题正确解 | 0 | 0 | 1/4 未达标（weighted 25） |
| 5 | 负例：四题空文件 | 0 | 0 | 每题首个失败 #0（输出为空） |
| 6 | 负例：四题 `print(0)` | 0 | 0 | 四题均输出不符 |
| 7 | 负例：只过公开样例不过私有 | 0 | 0 | 样例查表解：每题**首个失败点恰为第 n_public 组**（3/3、3/3、2/2、3/3 之后失败），证明公开样例与隐藏测试分离有效 |
| 8 | 负例：超时死循环 | 0 | 0 | `while True: pass` → `fail_kind=timeout`、#0 超时 10s |
| 9 | 负例：输出格式多空格 | 0 | 0 | 答案全对但行首 +2 空格、词间双空格 → 四题均 `fail_kind=wrong`（证明格式真的参与判分） |
| 10 | 负例：run_dir 输入副本被篡改 | 0 | 0 | 四题全过但 `input_integrity` fail → reward 压制为 0 |
| 11 | 守卫：truth SHA-256 漂移 | exit 2 | exit 2 | 拷走 checker+truth 改 SHA 后运行 → ERROR exit 2 |
| 12 | **B8 披露项（2026-10-27）**：abc389_g stdout 与 oracle 一致、仅向 stderr 打 `OK passed all tests` | 1（4/4） | 1 | 显式断言「stderr 不参与比较」防回归（v0.1 行为本就如此，见 §5 口径 3） |

自测用 `tempfile.TemporaryDirectory()`，不污染仓库；自测原始输出见 `selftest.stdout.txt` 与 `3-表现现场/r1025-candidates/selftest/lcb-recent-hard-4.log`。

## 7. oracle 回归

`solution/` 四文件来自 r1024 探针批次的已实测全过解法：`3-表现现场/r1024-probe-区分度/lcb-v6-hard4__dsh/solutions/`（r1024 探针中 codex 与 dsh 两批各 4/4，均 100 分；本用例选用 dsh 批，逐字节复制）。**复制后用本 checker 复验：4/4 全过（43/43、43/43、42/42、43/43，reward=1）**。

- 复验命令：`cp solution/*.py <run_dir>/solutions/ && python3 checker.py <run_dir>`；
- 实测耗时（python 3.9.6 本机）：abc387_f 1.65s / abc388_f 0.43s / abc388_g 0.45s / abc389_g 4.75s，合计 7.3s；最慢单组 abc389_g#29 = 1.37s。

## 8. 来源与许可证

| 项 | 内容 |
|---|---|
| 题库来源 | **LiveCodeBench v6**（`code_generation_lite` 的 `test6.jsonl`，2025-01 窗口；官方仓库 <https://github.com/LiveCodeBench/LiveCodeBench>，HF <https://huggingface.co/datasets/livecodebench/code_generation_lite>） |
| 许可证 | **MIT**（LiveCodeBench 仓库） |
| 读取日期 | 2026-10-22（本机实拉后落 `/tmp/lcb_recent.jsonl`，抽取 hard 6 题中取 4 题） |
| 是否改写 | **题面按中文重写**（保留输入/输出格式、约束、样例与样例解释），**非英文原文照抄**；测试数据（公开 + 私有）原样使用 |
| 题目出处 | AtCoder Beginner Contest（题面与测试的原始出处，见下）；题面版权归 AtCoder，本用例仅作中文改写教学用 |
| 判分器来源 | 移植 LiveCodeBench 官方评测的「逐测试 stdin 注入 + 超时 + 输出规整比较」口径，用 Python 标准库重写（MIT） |

| problem_id | 题名 | 出处 | 日期 | URL | 公开/私有测试 |
|---|---|---|---|---|---:|
| `abc387_f` | Count Arrays | ABC387 F | 2025-01-04 | <https://atcoder.jp/contests/abc387/tasks/abc387_f> | 3 / 40 |
| `abc388_f` | Dangerous Sugoroku | ABC388 F | 2025-01-11 | <https://atcoder.jp/contests/abc388/tasks/abc388_f> | 3 / 40 |
| `abc388_g` | Simultaneous Kagamimochi 2 | ABC388 G | 2025-01-11 | <https://atcoder.jp/contests/abc388/tasks/abc388_g> | 2 / 40 |
| `abc389_g` | Odd Even Graph | ABC389 G | 2025-01-18 | <https://atcoder.jp/contests/abc389/tasks/abc389_g> | 3 / 40 |

## 9. 体积与资源

- `inputs/problems.json`：**7,884 B**，SHA-256 `0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673`（拷进 run_dir 的只有这一个文件，远低于 25MB 目标）。
- `truth.json`：**328,220 B**（171 组测试全文 + 每题 `tests_sha256` + 来源/协议元数据）；整个用例目录约 **370 KB**。
- 判分机资源：仅开 subprocess 跑 4 个 Python 程序，171 组总耗时约 7.3s（oracle），无第三方依赖。

## 10. 难度与区分度说明（诚实披露）

1. **难度基准**：4 题均为 2025-01 AtCoder F/G（近期 hard，落在 LiveCodeBench 的防污染时间窗内），非 2023 老题。
2. **r1024 探针实测**：codex 与 dsh 在旧版（英文题面）该 4 题上**都是 4/4、weighted 100**，耗时分别 414.4s / 303.2s、工具调用 43 / 29 次。→ 单看二值口径，这两款当前都已饱和；本题的区分度不在「能否做对」，而在**耗时/自测轮次/隐藏测试鲁棒性**（题面改中文不影响测试数据）。
3. **本用例相对探针的差异**：①题面中文化（信息等价，但减少英文阅读理解负担，更接近正式题库风格）；②检查器换成带三重守卫与 11 项自测的 `checker.py`，input 副本被改/truth 漂移/缺文件/格式错全部能精确变红；③公开样例与隐藏测试分离（7 项负例中的「样例查表解」被精确拒绝）。
4. **风险与未决**：若 lead 的正式场次仍 4/4 打满，本题建议只作为「耗时区分」用例保留，或按 r1024 结论降级为探针/对照题，不强行晋升。

## 11. 过程锚点（人工跑记 0–3，自动批跑记 N/A）

| 观察项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 逐题自测 | 无，写完直接交 | 只跑过 1 题样例 | 4 题都跑过样例 | 4 题都跑样例 + 自造边界数据并修过 bug |
| 处理隐藏测试风险 | 只针对样例硬编码 | 大方向对但边界缺失 | 写通用解，N 大/取模/Yes-No 等边界考虑过 | 主动按约束造最大规模数据压复杂度并复测 |
| 失败后重试 | 卡住即放弃/静默少交 | 盲目改写 | 定位到具体题/测试后修改 | 多轮「跑样例→发现反例→修正→复测」链路 |

## 12. 变更记录

- 2026-10-22 v0.1：首版 staging 入库。`inputs/problems.json`（4 题中文改写题面 + 样例，7,884 B，SHA-256 `0ce2f9c1…`）、`truth.json`（171 组测试 + 每题 `tests_sha256` + MIT 来源）、`checker.py` v0.1（逐组 subprocess、10s/组、按行 rstrip、≥2/4 达标、三重守卫、`--selftest` 11 项）、`solution/`（r1024 dsh 批 4 题，本 checker 复验 4/4）、`case.json`（timeout_s=3000）、`task.toml`。`--selftest` 11/11 全绿（oracle=1、nop=0、7 负例全 0、truth 漂移 exit 2）。
- 2026-10-27 v0.1·B8 披露式修订：**判分行为不变**（stderr 本就不参与比较）。spec §5 增补 stderr 口径声明（披露式不加严的理由：与上游 AtCoder 官方判定一致，伪造标记不影响答案正确性）；`checker.py` 文件头同步口径声明、`--selftest` 增至 12 项（+#12 stderr 伪造标记显式断言）。`truth.json`/`inputs`/`solution/` 逐字节未动；历史回放 24 场（三受影响 case）before/after 0 翻转。收据：[判卷审计 2026-10-27](<../../4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md>)。