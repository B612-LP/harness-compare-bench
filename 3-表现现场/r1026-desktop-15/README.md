# r1026-desktop-15：桌面三端 × v2.0 五题（正式矩阵的桌面 15 格）

> 目的：补齐正式 25 场矩阵里的桌面部分——**WorkBuddy 桌面端 / 元宝专家模式 / 豆包办公 × 5 题**，每格 n=1。
> 与 `r1025-candidates/`（两个 CLI 的 10 格）合起来即完整矩阵；判分器同为 `2-用例/<case>/checker.py`，口径一致。
> 原则：**目录即契约** —— 预置工作目录 → 被测端在里面干活 → 判分器直接读目录。人的动作只剩「开新会话」和「按 Enter」。

> **⚠️ 批次作废重做（2026-10-23）**：本批 run_dir 建在题库仓库内，被测端可用 `ls ..` / 相对路径摸到 `2-用例/<case>/{spec.md,truth.json,solution/,reference/}`。落盘 5 格后回查轨迹发现：
> - `workbuddy × tb-cargo-plan`：读了 `2-用例/tb-cargo-plan/reference/test_outputs.py`（27 项断言原题）并自跑 `checker.py` → **原 1 / 100 作废**；
> - `workbuddy × dabstep-payments-10`：读了 `2-用例/dabstep-payments-10/spec.md`（逐题权重 + q70 负例）→ **原 1 / 80 标 suspect**；
> - `workbuddy × lcb-recent-hard-4`：WebSearch 命中 AtCoder 官方 editorial（联网为该形态默认放开）→ **原 1 / 100 标 suspect（含联网助力）**；
> - `workbuddy × bird-ca-schools-15`、`workbuddy × exercism-py-6`：轨迹干净，原判有效。
>
> 修法：工作区挪到仓库外 `~/bench-workspaces/r1027/`、题面追加「工作纪律」软约束后重跑，见 [`../r1027-isolated/`](../r1027-isolated/)。本批 `MATRIX.md` / `matrix.json` 中 WorkBuddy 的 tb、dabstep 两格**以 r1027 为准**；`checker.py` 判分口径本身不变。
>
> **重跑结果（2026-10-23，隔离工作区）**：`workbuddy × tb-cargo-plan` = **0 / 70.37**（206s，18 步，越界 0）、`workbuddy × dabstep-payments-10` = **0 / 70.0**（271s，27 步，越界 0），失败项分别与两个 CLI 干净格**完全一致**。至此 WorkBuddy 有效格：bird 1/86.67、exercism 1/100 + 重跑两格 0/70.0、0/70.37；lcb 仍为 suspect（联网命中 editorial，未重跑）。A 组三形态（Codex CLI / DSH CLI / WorkBuddy 桌面）5 题逐题同分，headline 均 3/5、weighted 均 427.04。
>
> **豆包 5 格独立复核：干净，不适用上面的污染结论。** 逐条扫 `runs/doubao/<case>/traces/conversation.jsonl`：0 处访问 `2-用例/`、`truth.json`、`spec.md`、`checker.py`，0 个目录外绝对路径，工具集无 web/搜索（仅 Read / Bash / Write / Edit / task_create / task_update / present_files）；扫描命中的 `http://` 与 `atcoder` 全部来自 `inputs/` 内原文（exercism 测试文件头注释、lcb 题面 JSON），不是联网或越界读取。判分独立复算一致：bird 0/60、exercism 1/100、dabstep 0/70、lcb 1/100、tb 0/81.48 → **2/5，weighted 411.48**。元宝 5 格仍未采集。
>
> **证据形态（2026-10-23 用户修订）**：桌面端不再要求截图。豆包 5 格 `shots/` 为空是既定口径，不作为缺陷；证据 = `traces/`（conversation.jsonl + assignment.md + board.md）+ workspace 产物 + TASK.md 留档，过程行为判断以 trace 为准，报告披露“无截图、以对话导出取证”。例外：元宝本地无轨迹，若日后补跑需单独定证据方案。

## 1. 变量固定

| 变量 | 取值 |
|---|---|
| 形态 | 桌面 GUI 原生交互（**不用** CLI/API/插件入口；WorkBuddy 自带 `codebuddy` CLI 不用于本批） |
| 开场白 | 同一份 `TASK.md`（= `instruction.md` + 绝对工作目录声明），只换产品名 |
| 用例 | v2.0 五题，与 CLI 批完全一致 |
| 联网 | 产品默认（**放开**）——与 CLI 批（联网关）不同，见 §6 披露 |
| 插件/SKILL | 产品默认，不额外装、不改配置 |
| 模型 | WorkBuddy = `DeepSeek V4.1-Flash`（A 组，与两 CLI 同模型）；元宝 / 豆包 = 各自默认（B 组） |
| 计时 | 脚本记 wall clock：**发送时刻 → 收尾时刻**，不用产品自报耗时 |
| 收尾 | 人按 Enter，或屏幕静默 150s 自动收尾（两者都记 `finish_reason`） |

## 2. 目录即契约

```
runs/<产品>/<用例>/
  inputs/        预置输入（从 2-用例/<case>/inputs 拷入；exercism / tb 允许改代码）
  TASK.md        开场白（含绝对工作目录 + 交付约定）
  .baseline.json 输入指纹（用于「有没有产物」与「input 是否被动过」的判定）
  产物…          按各题要求：answers.jsonl / solutions/ / flight_plan.json …
  shots/         自动截图
  meta.json      机器可读的建档
```

判分只认这个目录：`python3 2-用例/<case>/checker.py runs/<产品>/<用例> --json`。
换目录不换判分器 → 与 CLI 批可直接并列比较。

## 3. 自动化边界（谁做什么）

| 事项 | 谁做 | 实现 |
|---|---|---|
| 开场白、绝对路径声明 | 脚本 | `desk.py setup` 生成 `TASK.md`；`run` 时 `pbcopy` |
| 粘贴 + 发送 | 脚本（辅助功能权限） | `osascript` 发 `Cmd+V` + `Return`；失败降级手动 |
| 计时 | 脚本 | 发送时刻 → 收尾时刻 |
| 过程截图 | 脚本 | `screencapture` 每 20s，收尾选 6 张压成 jpg |
| 判分 + 半程分 | 脚本 | `checker.py --json` |
| 建档 | 脚本 | `meta.json` + `checker.stdout.json` |
| **步数** | WorkBuddy: 脚本 / 元宝·豆包: 人工或空 | WorkBuddy 从 `~/.workbuddy/projects/<slug>/*.jsonl` 按 `cwd` 命中本场，数 `type=function_call`（已在 r1021 历史场上验过：5 步 = Read×2 + Bash×2 + present_files×1）；另两家可给 `--probe` 抓本地存储差异，第二轮再写解析器 |
| 开新会话 | 人 | GUI 操作，无法可靠脚本化 |
| 收尾 | 人（或空闲检测） | Enter / 静默 150s |

## 4. 命令

```bash
cd 3-表现现场/r1026-desktop-15
python3 tools/desk.py setup                # 生成/修复 15 个 run_dir（幂等）
./tools/run.sh workbuddy bird-ca-schools-15 # 跑一场
python3 tools/desk.py status               # 看进度
python3 tools/desk.py judge <run_dir>      # 单场重判
python3 tools/desk.py judge-all            # 全量重判
python3 tools/desk.py land <run_dir>       # 把 ~/Downloads 本场新文件搬进来（只能下载的端）
python3 tools/desk.py collect              # 汇总 → MATRIX.md / matrix.json
```

`run` 常用参数：`--force`（重跑并恢复 inputs）、`--idle-s 150`（自动收尾阈值）、`--shot-every 20`、`--keep-shots 6`、`--paste auto|manual`、`--land`、`--probe`、`--max-minutes N`。

## 5. 判分与汇总

- headline：`reward`（0/1，达标线见各 `2-用例/<case>/spec.md`）
- 半程分：`weighted`（未达标时的完成度，用于并列/归因）
- 过程指标：`duration_s`、`steps`、`shots`
- 汇总：`MATRIX.md`（自动生成，每格含达标/半程分/耗时/步数）

## 6. 披露

1. 每格 n=1，只能作**定标与归因线索**，不是通过率。
2. 桌面端**联网默认开**，CLI 批**联网关**；跨形态的耗时/步数比较只在同形态内有效，报告里分形态并列。
3. 元宝专家模式、豆包办公为闭源模型（B 组），不与 A 组（同模型 `deepseek-flash`）做同模型排名。
4. 若某端无本地文件系统：记 `fs=unavailable`，按「上传输入 / 下载产物 + `land` 搬回」执行，并在该格注明取产物方式——这属 Harness 能力差异，不视为测量偏差。
5. 步数口径：WorkBuddy 的 `function_call` 计数 = App 界面的执行步数；两家闭源端若为人工填写，标注 `steps_source=manual`。
6. 截图是整屏的，可能带其它窗口；提交前按需删除敏感帧（脚本只压不发）。

## 7. 与其它批次的关系

| 批次 | 内容 | 状态 |
|---|---|---|
| `r1023-cli-dsf-low` | 旧 5 题 × 2 CLI | 已完成（10/10 满分，题饱和 → 换库） |
| `r1024-probe-区分度` | 出题探针 | 已完成 |
| `r1025-candidates` | 新 5 题 × 2 CLI 闸门 | 已完成（Codex 4/5、DSH 3/5） |
| `r1021-intsum-workbuddy` | 旧题 WorkBuddy 补跑 1 场 | 已完成（旧题，仅作历史） |
| **`r1026-desktop-15`** | 新 5 题 × 3 桌面端 | **本批** |