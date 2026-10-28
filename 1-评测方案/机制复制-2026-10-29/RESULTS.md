# 机制复制实验结果（2026-10-29 凌晨完成）

预注册：[PREREGISTRATION.md](<PREREGISTRATION.md>)（先于任何复制运行定稿）。性质：研究诊断（experiment=true，不入官方表）。

## 观察

三场复制全部完成，夹具三方字节一致（35767 B，SHA `fed5759…`）：

| 运行 | 产品/臂 | 调用1 输入(含缓存) | 调用2 输入(含缓存) | 增量 | raw SSE |
|---|---|---|---|---|---|
| repl-dsh-01 | DSH / spill 512 | 443 | 1,514 | +1,071 | 两段完整，message_stop 均到达 |
| repl-dsh-02 | DSH / spill 512 | 443 | 1,495 | +1,052 | 两段完整，message_stop 均到达 |
| repl-codex-01 | Codex / 无 spill | 8,610 | 15,093 | **+6,483** | 无请求级抓取（产品自报） |

两端应答都精确报出 HEAD_KEY/TAIL_KEY（6/6 场次观察正确）。原始实验的大配对对照值：19,697→1,492（差 18,205）。

## 证据

- DSH 侧：逐请求 `NN-request.json`/`NN-response.sse`（v4 逐块追加 observer，两段 raw SSE 完整）、`01/02-transport.json`（host=api.deepseek.com）、`capture-status`（raw_response_sha256 存在）、`tool-process.json`（35,767 B 进程产物哈希）。目录：[evidence-dsh/](<evidence-dsh/>)。
- Codex 侧：隔离 CODEX_HOME 配置、MCP server 日志、`session-rollout.jsonl` 的 token_count 事件（产品自报，无请求级抓取）。目录：[evidence-codex/](<evidence-codex/>)。
- 分析脚本（只读收据）：[analyze_replication.py](<analyze_replication.py>) → [replication-analysis.json](<replication-analysis.json>)。

## 解释

同一模型、同一字节级夹具下：**有外溢策略的 Harness（DSH，spill 512）第二次调用输入保持 ~1.5K tokens（工具结果未内联）；无外溢策略的 Harness（Codex）第二次调用输入增长 ≈6.5K tokens（35,767 B 工具结果全量内联）**。骤降现象跟随 Harness 的上下文管理机制出现/消失，而不是跟随模型或服务端——与原实验「工具结果外溢→下一次调用输入骤降」的归因一致，且本次两段 raw SSE 完整（原 pair-1 的观测缺口由**新运行**补上，不替代原六场）。

## 未排除因素

1. **思考 token 混杂**（沿袭原实验登记，[未知登记-r2](<../../5-评测报告/未知登记-2026-10-29-r2.json>)）：调用间差异不能唯一归因于工具结果外溢。
2. **跨 Harness 绝对值不可比**：DSH/Codex 两环境系统上下文不同（调用1 输入 443 vs 8,610），可复制的现象是「增量模式」（是否骤增），不是绝对 token 数。
3. Codex 用量为产品自报（无请求级抓取）；缓存语义（cache_read 8,576）服务端不披露。
4. 每臂 n=1（复制目的为方向对照，不做方差声明）。

## 可复现实验

```sh
# DSH 臂（两场，逐块 raw SSE observer）
python3 -B 1-评测方案/机制复制-2026-10-29/run_replication_dsh.py \
  --workspace ~/bench-workspaces/r1031-replication/dsh \
  --evidence 1-评测方案/机制复制-2026-10-29/evidence-dsh \
  --credential-store ~/.dsh/.credentials.yaml
# Codex 臂（MCP 夹具）
python3 -B 1-评测方案/机制复制-2026-10-29/run_replication_codex.py \
  --workspace ~/bench-workspaces/r1031-replication/codex \
  --evidence 1-评测方案/机制复制-2026-10-29/evidence-codex
# 离线分析
python3 1-评测方案/机制复制-2026-10-29/analyze_replication.py
```

运行凭证：DSH `repl-dsh-large-bounded-01-239e08cd`、`repl-dsh-large-bounded-02-adfb64c0`；Codex `repl-codex-large-01-a8e6bc72`。五事件已导入 v2 六账（research，不入官方表）。
