# token-cause 复算（2026-10-27）

> 事后链接修订说明：本页已事后修正链接及说明，不是原封印字节；历史结果不代表本次开展了新的验证。

回应 A 组（Codex CLI 0.163.0 × DSH CLI 0.2.0-rc.2，同模型 deepseek-flash、thinking=low、联网关、SKILL 关）两 CLI token 总量 1.18–2.09× 差异的归因问题：把总量差做**算术分解**（call-1 前缀结构 × 调用数 × 对话增长/输出），产出逐场可复核的数字表。

**只读复算**：不修改运行总账、3-表现现场 或任何既有文件；不碰外部消融批目录的产出；本目录外零写入；无 git 操作。

## 1. 数据源与字段口径

| 项 | 来源 | 口径 |
|---|---|---|
| codex 逐调用 | [3-表现现场](<../../../../3-表现现场>) 各场 `agent-session/rollout-*.jsonl` 的 `token_count` 事件（`payload.info`） | `total_token_usage` 为**全场累计**，`last_token_usage` 为单次；逐调用值=相邻累计差分；`call-1 前缀代理=第一条累计的 input_tokens`；输入合计=末条累计 input（含缓存），命中=末条 `cached_input_tokens`，未命中=差值；输出/_reasoning 取末条累计 |
| codex 交叉校验 | 同场顶层 `agent.jsonl` 的 `turn.completed` | **只含 1 条**（末次全场累计），与 rollout 末条累计 **22/22 场一致**（字段 `cross_check_turn_completed`）。⚠️ 任务原始口径「第一条 turn.completed = call-1 前缀」在本批数据不成立：它只有末条，取它会得到全场累计输入（≈真前缀的 40–150 倍），已按 rollout 修正 |
| dsh 逐调用 | 各场 `agent.jsonl` 的 `status/step_end.usage` | 逐调用求和：未命中=Σ`inputTokens`、命中=Σ`cacheReadTokens`、输出=Σ`outputTokens`；call-1 前缀=第一条调用的 `inputTokens`。dsh 无 rollout |
| 禁用 | `meta.json` 的 `meta.usage` | 只是最后一次调用的快照，**禁止**当全场累计（实测 r1025 cargo：快照 56,243 vs 全场 569,216） |
| 消融批 | `/Users/b612-lp/bench-automation/runs/r20261027-ablation/<case>__<arm>/`（外部只读） | 只处理已有 `result.json` 的格；codex 臂同 rollout 口径，dsh 臂同 agent.jsonl 口径；缺格标注「批未完成，待补算」 |

各场 `cacheWriteTokens/cache_write_input_tokens` 均为 0（解析时仍留 `sum_cache_write` 备查）；codex 的 `reasoning_output_tokens` 是输出子集，dsh 轨迹无 reasoning 拆分（`sum_reasoning=null`）。

## 2. 分解口径（恒等式拆分，不是因果证明）

同题配对键 = (batch, case, 重复轮次)，c=codex、d=dsh，`Δtotal = total_c − total_d`：

1. **两因子（题给 counterfactual）**：`结构×编排 = (prefix_c−prefix_d)×n_d + (n_c−n_d)×prefix_d`；余项 = Δtotal − 结构×编排，可精确拆为 交叉项 `(n_c−n_d)(prefix_c−prefix_d)` + 增长差 `G_c−G_d` + 输出差（`G_x = input_x − prefix_x`，即首调之后全部输入）。
2. **精确三因子（推荐解读）**：`Δtotal = (prefix_c−prefix_d) + (G_c−G_d) + (out_c−out_d)`，三块相加恰等于 Δtotal、无交叉项。「调用数」不单独成项：其效应并入 G（多调用对话复利）。

脚本内置逐条断言：累计序列单调、（rollout）total = prev_total + last、每对三块相加=Δtotal。

## 3. 用法与交付

```bash
python3 "5-评测报告/复算/2026-10-27/token-cause/token_decompose.py"   # 重新生成 per_run.json + decomposition.md
python3 "5-评测报告/复算/2026-10-27/token-cause/validate.py"          # 输出契约校验（应打印 OK）
```

| 文件 | 内容 |
|---|---|
| [token_decompose.py](<token_decompose.py>) | 分析脚本（只读证据 → 写本目录两个输出；A 组清单与 cost 复算 A_RUN_DIRS 逐字一致） |
| [per_run.json](<per_run.json>) | 逐场明细：A 组 44 条（`run/batch/harness/case/n_calls/call1_prefix_tokens/sum_input_miss/sum_input_hit/sum_output/sum_reasoning/total_tokens` + 累计序列、来源标注）+ 消融 10 格状态 + 失败清单 |
| [decomposition.md](<decomposition.md>) | 中文表+结论草案：核心 5 题对照、44 场分批汇总、两因子与精确三因子分解、消融臂 call-1 差、逐行溯源 run 键 |
| [validate.py](<validate.py>) | 交付前契约校验（字段名/类型/行数/恒等式/缺格披露） |

## 4. 边界

- **n=1/格**：每格一个会话，不排除单场波动（r1028 同题 r2/r3 重跑间 codex 调用数 25↔17、35↔14 波动明显）；结论是账面分解，非统计推断。
- **前缀代理不可跨题比**：call-1 前缀含首条用户消息与题目附件，仅「同题同款（同 batch 同 case 同轮次）」内可比。
- **配对方向**：以 codex−dsh 为符号约定；r1027-isolated 两场不同 case，无配对，仅入 per_run.json。
- **总量比与成本比不同**：官方价目按命中/未命中分档，token 总量比 ≠ USD 比（见 [cost-usd 复算](<../../2026-10-26/cost-usd/README.md>)）。
- **消融批进行中**（截至 2026-10-27 13:45：4/10 格有 result.json 且已解析——codex 三臂走 rollout、dsh-base 走 `session.v4.jsonl.zstd` 内存解压；其余 6 格待补）；重跑脚本自动更新。dsh 消融轨迹是 v4 压缩格式（usage 在 `assistant/message` 的 `data.usage`，字段语义与 agent.jsonl 一致）。
- codex 首调前缀略高于 dsh 的成因（系统提示/工具模式/技能注入）与「reasoning 回放进上下文」均为**待验证假设**，本文不背书。
