# 机制面桌面复制 W 臂 · 2026-11-02（experiment 账，零正式表准入）

WorkBuddy 桌面（网关 UI 选 DeepSeek V4.1-Flash，thought low）单会话机制夹具探针（n=1）：同一 35,767 B 夹具字节级再生成自 [r20261029-mechanism](<../r20261029-mechanism/README.md>)（SHA256 `fed5759…`，逐字节一致）。**experiment=true，不入官方表**；单槽发射预算 1+1（本批用 1，无重试）。

## 五段结论

**观察**：会话内「读取夹具调用 → 写 answer.txt 调用」的下一请求输入增量 Δ=**+20,577 prompt_tokens**（29,810→50,387，产品自报），按预冻结阈值（PREREG l22-20261102：Δ≥6,000 inline / Δ<3,000 spill，依据=存量 15 槽 376 个轮间增量 median 1,205 / p90 4,009，payload≈8–10K token）判 **inline_like**——35,767 B 夹具结果全量进入后续请求输入，桌面 W 形态无「外溢→骤降」现象。

**证据**：[run-record.json](<run-record.json>)（十字段+夹具哈希+三形态锚点）、[usage-classification.json](<usage-classification.json>)（逐请求 usage 序列+阈值+判定）、[experiment-events.json](<experiment-events.json>)（分账：1 product_run[experiment kind] + 1 interface_preflight）；answer.txt 两键精确命中（HEAD_KEY=AMBER-731 / TAIL_KEY=COBALT-492）。CLI 锚点为 [机制复制-2026-10-29 RESULTS repl 表](<../../1-评测方案/机制复制-2026-10-29/RESULTS.md>)存档值（未重跑）：DSH spill-512 Δ=+1,071/+1,052（spill 侧骤降）、Codex 无 spill Δ=+6,483（inline 侧）；补充佐证=[r20261029-mechanism/analysis.json](<../r20261029-mechanism/analysis.json>) DSH 大夹具臂逐请求差分（full Δ=+19,254×2、spill-512 Δ=+1,066/+1,049，公开可复算）；桌面 W 本场 Δ=+20,577 与 inline 侧同量级、约为 spill 侧 19 倍。

**解释**：「工具结果是否内联进下一次调用」跟随 Harness 上下文管理机制出现/消失的结论延伸到第三形态：桌面 W 与 Codex 无 spill / DSH full 臂同属 inline 侧且量级相当（Δ 含会话状态增长，跨形态绝对值不可比，只作模式判定）；spill-512 的骤降行为未在 W 形态复现——W 报告结论中「Harness 贡献在交付结构与信息可达」的机制面在桌面侧获得一个观察级数据点。

**未排除因素**：n=1；用量为产品自报（无请求级抓取）；Δ 含非夹具的常规轮间增长（助手输出、文件历史快照、工具模式等），分解未做；网关后端身份未知；WB 会话是否存在自动压缩未知（本会话未见）；thresholds 依据来自任务型会话痕迹，与最小探针会话的增长分布可能不同（已按 indeterminate 区间保守化，实测值远离阈值边界）。

**可复现实验**：同夹具字节（SHA256 在案）+ 同任务文本（run-record/before 收据 SHA）在任一 WB 会话重放，提取会话 jsonl 逐请求 prompt_tokens 对比 Δ；分类阈值与判定规则见 usage-classification.json，可对任意会话机械重算。

## 执行期事件（如实）

- 批前 preflight 一次冷启动渲染竞态失败（CDP 起但无 page target，未写入收据、未发射），等待后重试成功——非产品运行失败，不占发射预算。
- 判定链更正：分析器 v1 误读痕迹字段（WB 会话 jsonl 的 name/arguments 在顶层）判 `probe_invalid`；v2 改顶层字段后确定性重放得 `inline_like`，痕迹零改动，v1/v2 均在私档（更正链可追）。
