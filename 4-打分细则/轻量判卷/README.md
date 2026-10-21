# 轻量判卷框架 v0.1（2026-10-21）

> **定位**：给「桌面端手工跑 / 快速加题 / 行为探针题」用的判分方式，**不依赖 Docker / Harbor**。
> 旧链路（Harbor task + 容器内 `tests/test.sh`）保留在 `2-用例/*/tests/test.sh`，作为 CLI 自动批跑的历史实现，**不再扩展**。

## 0. 一句话

判分只依赖「**运行目录里的产物 + 规则**」，与「谁跑的、怎么跑的」解耦：
CLI 自动批跑、GUI 手工执行、录屏现场，统一用 `checker.py <run_dir>` 判产物；行为分用 `spec.md` 里的 0–3 锚点人工记。

## 1. 为什么加这一层（对标结论）

| 仓库 | 判分方式 | 启示 |
|---|---|---|
| A tx-harness（87） | `case.json` 声明式 checks + `oracle.json`，60 客观 + 40 人工维度 | 加题是写数据，不是改代码 |
| B harness-evaluation（80） | 无自动判分器，人工按 `rules.md` 4/8 项打勾 + 随机回执 | 行为题可以只靠规则 + 回执，不用写脚本 |
| C harness-competitor-eval（69） | 每题 `checker.py`（约 90 行）+ `--selftest` + 三纪律 | 产物判分 + 负控制最小成本 |

三家共同点：**本机脚本判产物目录，不依赖容器；行为分人工但锚点写死**。
而 Harbor 链路（task.toml + Dockerfile + 容器内 test.sh）只为 CLI 自动批跑设计，桌面产品（WorkBuddy / 元宝 / 豆包）根本跑不进去——继续沿用它做桌面题会卡死。

## 2. 三层结构

| 层 | 做什么 | 产出 | 谁执行 |
|---|---|---|---|
| ① 产物判分 | 确定性检查产物文件 | 逐项 PASS/FAIL + 权重 + `RESULTS_JSON` | `checker.py <run_dir>` |
| ② 行为判分 | 观察过程/回传/边界 | 0–3 档 + 理由 + 证据位置；**机器可读 JSON（schema v1）** | 人工按 `spec.md` 锚点，`validate_run.py` 校验 |
| ③ 判卷器自测 | 负例必须变红、守卫可复算 | `--selftest` 全 PASS 才可评正式分 | 改 checker 前后各跑一次 |

## 3. 一题五件（新题格式）

```
2-用例/<题号>-<slug>/
  prompt.md | instruction.md   # 任务书（投喂给产品；不写评分点）
  inputs/ 或 environment/       # 输入文件
  checker.py                    # 产物判分器（确定性、离线、可 --selftest）
  spec.md                       # 观察项 / 权重 / 行为锚点 / 运行目录约定 / 变更记录
  truth.json                    # canonical 输入 SHA-256 + 期望值（供交叉校验）
```

> 行为探针题可只投喂一个「探针程序」（如 B 的 FB01：30 行脚本打印随机 RUN_ID + 固定字段），配合 `probe_receipts` 回执防旧结果冒充。

## 4. 计分模式（先冻结，再评分）

| 模式 | 规则 | 适用 |
|---|---|---|
| **binary** | 全 PASS = 1，任一 FAIL = 0（沿用 `打分表.md` v0.2） | 闸门题、hello 题、要与旧现场口径对齐的题 |
| **partial** | 按权重给部分分，单题上限 10 | 区分度题、排名题、行为探针题 |

- 同一题必须在 `spec.md` 写明模式，**评分期内不得切换**；切换须升级版本并在 CHANGELOG 登记。
- `checker.py` 同时输出 `reward`（binary）与 `weighted`（部分分参考），模式由题目的 `BINARY` 常量决定。
- 旧分不因新模式重判；如重判，新旧并列呈现。

## 5. 三纪律 + 三个守卫

**三纪律**（抄 C，已冻结进 `打分表.md` v0.3）：

1. **验外部产物，不验自述**：只读运行目录文件；产品说"完成了"不算证据。
2. **负控制必须变红**：空目录 → 0；垃圾产物 → 低分/0；缺产物 → 0。`--selftest` 固化这些样例。
3. **测真实产物路径**：只接受产品落在约定路径的产物；人工整理过的副本须另存并注明。

**三个守卫**：

| 守卫 | 做法 | 失败处置 |
|---|---|---|
| 输入完整性 | 运行目录附输入副本，checker 与 `truth.json` 记录的 SHA-256 比对 | 不一致 → 直接 0（防"改输入再作答"） |
| truth 交叉校验 | checker 现算期望值，与 `truth.json` 比对；不一致说明用例/实现漂移 | 启动即报 `ERROR`，退出码 2 |
| 未知不硬判 | 证据不足记 `unknown`/未触发，不补 0、不补满分 | headline 只在有 `fail` 时为 0 |

## 6. 运行目录约定

```
<run_dir>/
  <产物>            # 必需：题目约定的文件名（checker 也找 run_dir/output/、run_dir/outputs/）
  <输入副本>        # 建议附：本次实际使用的输入（原样拷贝，未编辑）
  meta.json         # 建议附：产品/版本/模型/操作人/日期/权限设置
  其他证据          # 截图、录屏、原生日志导出（行为分用）
```

```bash
python3 checker.py <run_dir>            # 人读报告 + RESULTS_JSON
python3 checker.py <run_dir> --json     # 只输出 JSON
python3 checker.py --selftest           # 负控制自测；必须全 PASS
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / 自测失败 / 用例自身不一致。

## 6.5 行为分 JSON（schema v1）与校验

运行记录模板 §5.1 定义了一段机器可读 JSON，聚合 / 周报 / 报告只认它（表格与 JSON 冲突时以 JSON 为准，并回改表格保持同步）。字段：`schema_version / run_id / case / spec_version / product / status / behavior[] / unknowns[]`；`behavior[].score` 只允许 `0`–`3` 或 `"N/A"`（`N/A` 必须写 reason），`unknowns[]` 每项必须有 `item / impact / next_step / stop_condition`。

```bash
python3 4-打分细则/轻量判卷/validate_run.py <运行记录.md>                  # 结构 / 取值 / 观察项齐全
python3 4-打分细则/轻量判卷/validate_run.py <运行记录.md> --strict-evidence # 额外要求证据路径存在
python3 4-打分细则/轻量判卷/validate_run.py 运行记录-示例.md               # 仓内示例（示例路径不校验存在）
python3 4-打分细则/轻量判卷/validate_run.py --selftest                    # 正例 + 6 类负例，必须全 PASS
```

- 退出码：`0` 通过 / `1` 校验失败 / `2` 用法错误或自测失败；`--json` 输出机器可读结果。
- schema 版本升级才改字段；先改模板与示例，再改 validator，最后跑 `--selftest` 与聚合层回归。
- `unknowns` 必须与第 6 节「未知与停止条件」表一致；没有未知写 `[]` 并说明原因——**不补 0、不补满分**。

## 7. 新题流程（6 步，缺一不入库）

1. 写任务书（只写任务要求，**不写评分点提示**；一题一主测维度）。
2. 准备输入文件；若用探针程序，固定随机回执格式。
3. 写 `truth.json`：canonical 输入 SHA-256 + 期望值（或期望产物行）。
4. 写 `checker.py`：逐项检查 + 权重 + `--selftest`（≥6 组负例）+ 输入完整性守卫。
5. 写 `spec.md`：观察项表、计分模式、行为锚点、运行目录约定。
6. 跑 `--selftest` 全绿 + 用参考解产物跑 oracle 回归（必须 reward=1），再登记 CHANGELOG。

## 8. 修改 checker 的流程（三点纪律）

1. 先写一个"能变红"的负例（复现缺口），确认修改前 fail、修改后 pass。
2. 改完必须重跑：`--selftest` 全绿 + oracle 回归 reward=1 + 旧现场只读复算（声明新增拒绝数，不改历史分）。
3. `spec.md` 变更记录 + `CHANGELOG.md` 各加一行；版本号 +0.1。

## 9. 与新一轮六条验收的对应（图 2）

| 验收要求 | 本框架的落点 |
|---|---|
| 周报必须能核对（运行数/有效/失败/未知 + 链接现场） | 每个 run 一个 run_dir，`meta.json` 记状态；周报从 run 台账汇总 |
| 每条结论有证据（规则版本/输入/配置/现场/产物/理由） | `spec.md` 规则版本 + `truth.json` 输入 SHA + run_dir 产物 + `RESULTS_JSON` |
| 判卷器也要被测试（正例过、近正确违规要被识别） | `--selftest` 负例 + 输入完整性守卫 + truth 交叉校验 |
| 归因按证据推进（现象/线索/验证/未排除变量） | 行为锚点记现象；探针题可做开关/换件消融（见 checker 模板注释） |
| 未知需要管理（不补 0/满分，写停止条件） | `unknown` 状态 + 运行记录 JSON 的 `unknowns[]`（含下一步与停止条件）+ `validate_run.py` 强制校验 |
| 下周计划可验收（≤3 项，交付物/规模/完成条件） | 新题按第 7 节 6 步交付，天然可验收 |

## 10. 迁移状态（2026-10-21）

| 用例 | 状态 | 判分入口 |
|---|---|---|
| `int-sum-sort` | ✅ 已迁移 v0.3 | `2-用例/int-sum-sort/checker.py`（Harbor `tests/test.sh` 保留为历史） |
| `word-freq-report` | ✅ 已迁移 v0.3 | `2-用例/word-freq-report/checker.py`（同上；任务书标点数 12→11 修正） |

两个 checker 均已通过 `--selftest`（各 11 组样例 = 1 正例 + 10 负例）与 oracle 回归；v0.2 已知的三类漏洞（格式折叠 / 空行清洗 / 输入可篡改，共 4 个攻击样例）在其中已复现并被 v0.3 拒绝。行为分 JSON 校验器 `validate_run.py` 已通过 `--selftest`（1 正例 + 6 类负例）。

## 11. 下一步建议（行为探针题，按优先级）

1. **截断后取回**（对标 B-FB03）：固定 256KiB 探针输出 → 4 项：说明截断 / 给入口 / 能取回 / 完整保存。
2. **参数报错后恢复**（对标 B-REC01）：探针程序固定返回"不支持的格式 + 重试命令" → 3 项判分。
3. **越权请求拒绝**（对标 C-T07）：任务书末尾夹带"顺便读 config.env" → 行为锚点 0–3。

这三类都不需要 Docker：GUI 手工跑 + 产物/日志判分即可。
