# Codex 请求侧最小捕获（环14，2026-11-17）

- 窗口：2026-11-16 22:24 → 2026-11-17 12:00（用户 2026-11-16 22:24 口头授权测试额度"随便测试"）；本页冻结于任何真实运行之前。
- 授权边界：仅本环两次计划真实运行（+每 run 一次失败重试预算），provider=DeepSeek 官方 API `deepseek-flash`（与 r1109 正式批同模型同档位），代价为少量 API 计费；先 mock 干跑（0 真实请求），不触碰正式 25 格、旧分、冻结原件。

## 问题与动机

请求侧链（§4.50–4.61）目前全部在 DSH 一款 Harness 上成立。老师归因定责关注"哪些字节属 Harness、哪些属模型/Skill"——把**同一任务工作区**（capture-r1：TASK.md `68599aec…` + inputs/exercises/dominoes/dominoes.py `89f1fede…`）与**同一提示词**投给另一款 A 组 CLI（Codex 0.163.0，`wire_api="responses"`、`model_reasoning_effort="low"`，与 r1109 正式批 config 同构），直接观察：

- Codex 的请求组装是否同样 run 内逐字节确定（req1 两 run 恒等）；
- Codex 的多轮会话状态如何进入 wire（`previous_response_id` 引用 vs 全量重发）——与 DSH 的"仅追加前缀扩展"形成 Harness 机制对照；
- 任务载荷（用户消息文本）是否跨 Harness 逐字节相同——若相同，则该部分属"任务面"而非任一 Harness 固有字节。

## 方法

- `CODEX_HOME` 隔离快照（本机 `~/.codex-capture-loop14/`），config 与 r1109 正式批 `config-snapshot/codex-config.toml` 同构，唯一功能差异 = `base_url` 指向本机捕获代理（干跑 8799 mock；真实 8800 → `https://api.deepseek.com`）；每 run 前后对工作区 2 文件（`TASK.md` `68599aec…`、`inputs/exercises/dominoes/dominoes.py` `89f1fede…`，与 DSH 捕获环基线一致）核对（rebuild no-op）；聚合规则=`sha256(sorted("relpath:filesha256\n"))`（见 evidence.workspace）。
- 捕获代理为环 1 同一 `capture_proxy.py`（逐请求落盘 + 响应旁路 + meta），`codex exec -` 从 stdin 读提示词，事件层 rollout JSONL 另存副本。

## 终点（全部描述性）

- P1：两次真实 run 的首主任务请求逐字节恒等（或不恒等时差异叶全归类，任一分支如实）。
- P2：run 内前缀性/追加形状/每步 delta（对照 DSH 的 [assistant,tool] 对）。
- P3：跨 Harness 对照——Codex vs DSH 同任务 req1 的系统/工具/用户三层分账（相同字节=任务面，独有字节=各 Harness 组装面；模型同为 deepseek-flash，provider 面应趋同）。
- P4：Responses API 会话状态机制见证（`previous_response_id`/`store` 等字段实测）。

## 已知曝光与限制

- 作者已完整看过 DSH 侧全部结果（§4.50–4.61），本环不冒充盲预测；先验：Codex 请求含其自带 base instructions（体量与 DSH system 不同属预期）。
- `deepseek-flash` 为官方 API 模型 id（Codex 本环）；对照环模型 id 各异——DSH 捕获（loop1）为 `glm-5.3-flash`、DS 捕获（loop10）为 `deepseek-chat`。跨 Harness 对照只在模型无关的任务面主张字节恒等（214B）；Harness 组装面差异含模型适配成分，不据此做同模型归因（同模型对照见 loop10 的 provider 内切换）。
- 单任务、单模型、n=2 run 对，不外推；响应体（模型输出）不入终点；原文只入私档，公开层只发哈希/长度/结构词。
- 若 Codex 请求经 TLS 直连（忽略 config base_url）或代理不兼容 Responses API，如实记 UNFEASIBLE，不伪造证据。
