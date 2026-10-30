# tools-dsh：r1031-variance-n3 DSH 侧运行器

> **事后脱敏摘要**：本文由原说明事后整理，移除内部协作分工和个人路径；不是原始封存文件，也不代表本次重新运行或复核。运行证据和代码未因本文整理而改变。

## 测试方法与运行限制

本运行器基于 [r1030 运行器](<../../r1030-formal-a1/tools/lab.py>) 适配，仅运行 DSH。调用 `dsh bench-cli --json -`，由 stdin 提供工作区 `TASK.md`，以工作区为 cwd，环境注入 `DEEPSEEK_API_KEY`；超时取各题 `case.json` 的 `timeout_s`。判卷使用 freeze-20261029-v2 冻结 checker，preflight 逐题校验 checker SHA-256 与 v2 配置快照。

批次为 `r1031-variance-n3`，沿用 r1030 五题，rep 为 2、3；每次运行为 case × rep。证据目录为 `dsh/runs/dsh__<case>__r<rep>/`；标识分别为 `var-n3-dsh-<case>-r<rep>` 和 `r1031-dsh-<case>-r<rep>`，meta 记录 rep、event_id 与 `preregistration_commit=be39fc2`。会话轨迹按包含 rep 和 case 的路径段及运行开始时间过滤，避免误收其他运行。

八类污染模式零命中产生 `valid` 草案，命中产生 `pending-review` 并设 `gates.contamination_free=false`；语义判定仍需人工复核。运行级失败登记为 `infrastructure_invalid`，在 `dsh/run-failures.json` 记 `selection=null` 诊断，不补跑。仅 429/断连等传输错误在同一逻辑运行内按 5/15/45 秒退避，最多重试三次，保留各次日志及 `meta.transport_retries`；超时按合同截停判分，不重试。

## stdout 与 usage 归档

- dsh-headless 0.2.0-rc.2 的 `--json` 投影将字符串截至 8192 字节、单行截至 32KB；上限在 `projectJsonRun` 调用处硬编码，CLI 旗标和环境变量不能覆盖。归档侧双流只能缓解，不能消除产品投影截断。
- `agent.jsonl` 保存原始 CLI stdout，被截字段带 `truncated:true`；`agent.jsonl.full` 由耐久会话轨迹 `agent-session/session.v4.jsonl.zstd` 按相同投影语义重建无截断完整流。`meta.archived_stdout` 记录字节、行数、原因与重建方法；两流和会话轨迹可交叉核对。r1027 归档证据记录 51 个 tool_result 中一个截至 8192，重建后恢复。上游解除限制或版本升级后的正式收口不在本批结论中。
- `meta.usage.per_call[]` 从每步 committed `assistant/message.usage` 记录 turn、step、输入/输出/总 token、缓存读写及 reasoning token；缓存读取映射 `cacheReadTokens`，缓存创建映射 `cacheWriteTokens`。逐 step 与原始 stdout 的 `step_end.usage` 比对，差异如实记录。

## 批内发现并修复：r1030#1 归档缺陷实为未修复（r1031#1，仅波及第 1 场）

r1030 的 `archive()` 先删除证据目录，再移动 staging；若日志原先写在证据目录中，会先被删除。r1030 当时是会话内手工补救，原先声称代码已修不准确；参见 [r1030 勘误](<../../r1030-formal-a1/README.md>)。本批 bird r2 的 raw stdout/stderr 因同一机制丢失；工作区、产物、完整会话轨迹、判分和 meta 仍在，完整流由会话轨迹重建为 `agent.jsonl.full`，见 [该场 meta](<../dsh/runs/dsh__bird-ca-schools-15__r2/meta.json>) 的 `corrections`（`r1031-archiver-log-loss`）。修复是从落盘开始将日志写在证据目录外的 staging；原记录称第 2 场起 raw stdout/stderr 完整落盘。重建流不等同于原始 stdout。

## 用法

在批次目录执行（仅列出原说明中的方法，不代表本次执行）：

```bash
python3 tools-dsh/lab.py preflight
python3 tools-dsh/lab.py prepare <case> <rep>
python3 tools-dsh/lab.py run <case> <rep>
python3 tools-dsh/lab.py judge <case> <rep>
python3 tools-dsh/lab.py integrity <case> <rep>
```

`judge` 为离线复算核对，`integrity` 为归档完整性复扫；实际行为以 [运行器代码](<lab.py>) 为准。

- **代码公开整理版说明**：[程序](<lab.py>) 现为仅中立化内部角色文字的公开整理版；历史代码原件不公开，旧哈希不可用于核验此版字节或历史封印；此版新执行输出不是历史原件，不能冒充旧封印证据。本条独立说明本次代码整理，不改写上文所述此前文档整理的范围。
