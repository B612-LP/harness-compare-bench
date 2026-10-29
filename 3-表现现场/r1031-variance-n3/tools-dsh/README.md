# tools-dsh：r1031-variance-n3 DSH 侧运行器

`r1030-formal-a1/tools/lab.py` 的最小适配（下述差异之外，逐行语义不变）。调用方式与 r1030 完全一致：`dsh bench-cli --json -`，prompt 经 stdin（=工作区 TASK.md），`cwd=工作区`，env 仅注入 `DEEPSEEK_API_KEY`；超时取各题 `case.json` 的 `timeout_s`。判卷一律 freeze-20261029-v2 冻结 checker（preflight 逐题校验 `2-用例/<case>/checker.py` SHA-256 = v2 `config.json` 快照后才放行）。

## 与 r1030 的适配差异

1. **范围**：只保留 DSH（codex 路径整段移除——工作区根 `~/bench-workspaces/r1031/` 下的 `_codex-home` 等在 builder-codex 的写界内，DSH 侧不得触碰）。`preflight` 亦只查 DSH。
2. **批量常量**：`batch=r1031-variance-n3`；`CASES` 同 r1030 五题；`REPS=(2,3)`；一次运行 = `case × rep`。
3. **工作区**：`~/bench-workspaces/r1031/dsh/<rep>/<case>/`（r1030 无 rep 层）。
4. **证据目录**：`dsh/runs/dsh__<case>__r<rep>/`（写界 `r1031-variance-n3/dsh/**`；preflight 收据与 `run-failures.json` 也在 `dsh/` 下，批次根的跨产品汇总由 lead 负责）。
5. **标识**：`event_id=var-n3-dsh-<case>-r<rep>`，`run_id=r1031-dsh-<case>-r<rep>`；meta 增记 `rep`、`event_id`、`preregistration_commit=be39fc2`。
6. **会话轨迹匹配**：`~/.dsh/sessions` 目录名按 `-dsh-<rep>-<case>--` 全路径段匹配（r1030 按 `-<case>--`），避免 rep 间/历史批次误收；mtime ≥ started−5 过滤不变。
7. **裁定草案**：`adjudication.json` 由 builder 起草。八类模式 0 命中 → `valid`；有命中 → `pending-review`（`gates.contamination_free=false`），语义 benign 复核留 lead（与 r1030「reviewed=lead」同一信任边界）；运行级失败 → `infrastructure_invalid` 并在 `dsh/run-failures.json` 登记 `selection=null` 诊断事件。

## 随批工程项（PREREGISTRATION 包A a/b）

### a. stdout 归档去除 8192 截断

dsh-headless 0.2.0-rc.2 的 `--json` 投影把**字符串截到 8192 字节、单行截到 32KB**，且这两个上限硬编码在 `projectJsonRun(ctx, agent, sink, {cwd})` 调用点（`options.maxStringBytes ?? 8192`），CLI 旗标与环境变量均不可覆盖——不改产品代码就无法让 CLI stdout 本身不截断。因此本运行器实现为归档侧去截断：

- `agent.jsonl`：CLI 原始 stdout 原样落盘（staging 中转，沿用 r1030#1 修复）；被截字段自带 `truncated:true` 标记；
- `agent.jsonl.full`：从耐久会话轨迹（`agent-session/session.v4.jsonl.zstd`，无损 commit 事件源）按同一投影语义（session / status turn_start·step_start·step_end·turn_end / thinking / text / tool_call / tool_result(surfaceOp=append) / final）重建的**无截断完整流**；
- `meta.archived_stdout` 记双方字节数与行数、截断成因披露、重建方法。逐字节差异可由两条流 + 会话轨迹三方核对。

### b. 逐调用 usage 入库

`meta.usage.per_call[]`：每步 committed usage（`assistant/message.usage`，commit 点无损），字段 `turn/step/input_tokens/output_tokens/total_tokens/cache_read_tokens/cache_creation_tokens/reasoning_tokens`；`cache_read_tokens=cacheReadTokens`、`cache_creation_tokens=cacheWriteTokens`（anthropic-messages 语义）。`meta.usage` 另记总量与交叉核对结果（与 raw stdout 中投影 `step_end.usage` 逐 step 比对，mismatch 如实入库——理论上仅在 attempt 重试时出现）。

## 纪律落实

- **无重试**：运行级失败（非超时的非零退出且非传输层错误）不重试，归档后记 `selection=null` 诊断（`run-failures.json`），该 rep failed，继续下一场；
- **传输层退避**：仅 429/断连类（模式表见 `TRANSPORT_PATTERNS`）指数退避 5s/15s/45s 至多 3 次，属同一逻辑运行，逐次记 `meta.transport_retries`（含 stderr 尾部摘录），被替换的此前 attempt 流以 `agent.attempt<N>.jsonl` 一并归档；
- **超时**：按合同截停判分，不属重试；
- 判分、归档、完整性扫描全部仓库外工作区 + 仓库内 `dsh/**` 写界内完成；不执行 git；不改 CHANGELOG；不写周报。

## 批内发现并修复：r1030#1 归档缺陷实为未修复（r1031#1，仅波及第 1 场）

r1030 的 `archive()` 把 `rmtree(证据目录)` 放在函数**最前**，而「staging 移动」在其后——写在证据目录内的 `agent.jsonl` 先被 rmtree 删除，r1030 声称的修复（staging move）实际无效。成因：**r1030 侧当时的处置为会话内手工补救，代码级修复未生效**（r1030 README 的『tools/lab.py 已修』声明不准确；r1030 记录修订归 L1 报告问题池，本目录不改 r1030）。本批第 1 场（bird r2）因此丢失 raw stdout/stderr（运行本身完好：工作区、产物、完整会话轨迹、判分、meta 均在；完整流由会话轨迹无损重建为 `agent.jsonl.full`），已按 r1030#1 同款处置显式披露于该场 `meta.corrections`（id `r1031-archiver-log-loss`）。`tools-dsh/lab.py` 的修复是**把日志写入位置移到 staging（证据目录外）**，第 2 场起 raw stdout/stderr 完整落盘。lead 已亲自核验 r1030 源码行序并确认本定性（r1031#1）。

## 工程项 a 对未知登记「stdout 8192 截断」的推进

dsh-headless 0.2.0-rc.2 的 `--json` 投影把字符串截到 8192 字节、单行截到 32KB，且 `maxStringBytes`/`maxEventBytes` **硬编码于 `projectJsonRun` 调用点（`options.maxStringBytes ?? 8192`），CLI 旗标与环境变量均不可覆盖**（r1027 归档证据复现实证：51 个 tool_result 恰一个被截到 8192，自检重建后完整恢复）。因此「stdout 归档去除截断」在本版本上只能**缓解**而非消除：归档侧双流落盘（raw stdout 原样 + 会话轨迹无损重建的无截断完整流），meta 记双方字节数；完整产物以 `agent.jsonl.full` 为准，raw 流保留作投影行为实证。该未知登记的正式收口（如升级 headless 或上游放开上限）留 L1 报告，本批为证据推进。

## 用法

```bash
python3 tools/lab.py preflight
python3 tools/lab.py prepare <case> <rep>
python3 tools/lab.py run <case> <rep>      # 跑 + 判分 + 归档（含工程项 a/b）
python3 tools/lab.py judge <case> <rep>    # 离线复算核对（只读）
python3 tools/lab.py integrity <case> <rep> # 只读复扫归档产物
```
