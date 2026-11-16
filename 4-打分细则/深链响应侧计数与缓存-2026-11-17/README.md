# 深链响应侧计数与缓存（t2 两 run，0 新运行）

> **状态：协议冻结（探索性事后分析，先验已全披露）。** 作者在冻结前已读取全部 14 行 usage（草探脚本 loop18/probe_usage.py，数值在私立题 loop18/DIRECTION.md 原样披露）；本页不伪装盲预测。数据为 2026-11-16 深链两 run（t2-r1/t2-r2）的既有捕获响应，本环零新真实运行。

## 1. 问题与老师反馈对照

环8（§4.51）在单发任务上建立「prompt 稳定/cache 波动」，环16 延伸到 Codex 通道；DSH 深链（t2-r1/t2-r2，7 请求 × 2 run = 14 响应）尚未分析。对齐老师 P1①「输入减少是工具外溢、历史截断还是消息重组」的请求侧计量面：若深链 prompt 计数逐位稳定而 cache 行为有结构，可进一步约束「链增长 = 纯追加」的计量证据。

## 2. 数据源与行绑定

- 私档：`loop7/t2-r1/responses/`、`loop7/t2-r2/responses/` 各 7 个 `NNN.response.bin`（SSE 正文）+ 7 个 `NNN.response.bin.meta.json`。
- 公开 evidence 每行绑定：`run`、`seq`、响应 raw 文件 SHA-256、meta 内 `response_body_sha256`（须与 raw 相等）、meta 内 `request_body_sha256`（把响应对回其请求）、`duration_ms` 分档（<2s/<8s/≥8s 三档，不发布原值）、SSE `data:` 帧数、末帧 `finish_reason`、usage 六数值（prompt_tokens、cached_tokens、completion_tokens、total_tokens 与 details 两键存在性）。
- 响应正文（含任务文本与模型输出）不入公开档。

## 3. 终点（全部 product-reported，描述性）

- **E1 prompt 跨 run 稳定**：主链 6 请求 + 辅助请求共 7 个位置，t2-r1 与 t2-r2 的 `prompt_tokens` 逐位置相等 = 7/7。
- **E2 cache 跨 run 互异**：`cached_tokens` 跨 run 逐位置比较，互异数 = 6/7（仅 pos7 相等）；且 t2-r2 首请求 cached=7552>0——同前缀跨 run 缓存复用的**响应侧见证**（不认证服务端内部机制、命中路径或计费）。
- **E3 run 内单调**：每 run 主链（pos1、pos3–pos7）cached 随链位单调不减；辅助 pos2 允许回落（r2 实测 128）。
- **E4 schema 恒定**：每响应恰一次 usage chunk，顶层恰 5 键（prompt_tokens/completion_tokens/total_tokens/prompt_tokens_details/completion_tokens_details），`finish_reason ∈ {tool_calls, stop}`，`reasoning` 类字段不存在。

## 4. 边界

- 全部为 product-reported 计数（/chat/completions chunk usage），不认证 provider 内部、实际摄入、计费或 KV 复用机制。
- 探索性事后：先验=全部 14 行数值；复算只证明「公开 evidence 与私档重算一致、终点算术成立」，不证明冻结时点先后。
- 旧结论不改写：§4.51/环16 保持原文，本包为范围延伸；25 正式格、旧门、历史分数不动。

## 5. 验收

- `verify.py --archive-root <loop7 根> --build-evidence E --output R`（私档重建）与 `verify.py --evidence E --output R`（公档重放）双模式；公档重放核封印与全部终点算术；测试套件普通/-O 全绿；非作者独审后整合 v1.76。
