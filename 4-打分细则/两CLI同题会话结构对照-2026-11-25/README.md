# 两 CLI 同题会话结构对照 — 2026-11-25（离线静态）

问题：[当日五产品实跑](../../3-表现现场/r20261125-five-lcb/README.md)中，Codex 与 DSH 在**同任务、同模型（deepseek-flash/low）、同轮隔离重发**下各自留下一份公开会话事件流。两份流的结构与自报 usage 口径有何差异？方法为纯静态解析当日已公开源件（`stdout-r2.jsonl` 与 `postflight-r2.json` 各两份），当日完成；本页只作观察层陈述。

## 流结构（84 行 vs 78 行）

| 观察项 | Codex（codex-cli 0.163.0） | DSH（dsh 0.2.2-rc.3） |
|---|---|---|
| 事件组织 | thread → 单 turn → item 流 | session → 单 turn 15 步 status 流 |
| 工具/命令调用 | command_execution **35** 次（exit code 多重集 {0:29, 1:5, 130:1}） | tool_call **14** 次（bash 13、read 1；14 个结果全 completed） |
| 消息/思考 | agent_message 10、error 1 | thinking 15、text 1、final 1（completed） |
| error 内容 | 「Model metadata for `deepseek-flash` not found. Defaulting to fallback metadata」（元数据回退） | 无 error 事件 |

## 自报 usage 口径（不可互换比较）

| 观察项 | Codex（turn 级累计） | DSH（step 级逐段，15 步） |
|---|---|---|
| input | 2,017,204（cached 1,992,960，占 98.80%；cache_write 0） | ∑input 14,409 |
| output | 60,749（其中 reasoning 43,704） | ∑output 38,867 |
| 缓存 | cached_input 占比口径 | 逐步 cacheWrite 全 0；cacheRead 末值 51,584（单调不减、15 个互异值） |
| total | 未报 total | 末步 totalTokens 51,927 |

两流计进口径不同（turn 累计 vs step 逐段）、缓存语义不同（服务端缓存读 vs 逐步缓存写≈0），**数值不可换算、不比大小**；usage 为 Harness 自报，不等于服务端实际摄入或计费。两流 postflight 与 stdout 互证一致（codex `usage_turn_completed` 与 turn.completed usage 逐字段相同；dsh `usage_last_step` 与末步相同）。

## 判读（谨慎口径）

1. 同一 4 题任务、同一模型，两个 Harness 的事件组织、工具调用量级（35 vs 14）与自报计量形态差异显著——这是**观察层结构差异**的记录；n=1，无因果、无排名、无成本结论，不推断「哪个 Harness 更好」。
2. Codex 流的模型元数据回退是 Harness 层现象（流内原文可查）；其影响未评估，仅登记。
3. final 文本「4 题解全部样例通过并对拍通过」为被试自述，判卷隔离不达标未验证、不计分；本页不回填正式 25 格。
4. 两流事件均无墙钟时间戳，本页不含时延类主张。

## 复核

私有分析（预注册、提取器、10 项单测、逐项聚合）于当日窗口内完成非作者独审后发布；复算入口与逐项明细以仓库外私有归档为准（私有路径不入公开文档）。
