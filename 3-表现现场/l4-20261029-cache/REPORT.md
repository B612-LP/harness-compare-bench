# 缓存裸模型探针事实摘要

> 本文是事后整理的公开摘要，**不是封印原件**；本文及其整理时间不能证明规则冻结、登记和运行之间的时序。所述为旧报告当时记载，不等于当前独立复核结论。裸模型接口探针与产品运行分账，不能当作 Harness 得分。

## 运行与观察

旧报告记载 2026-10-29 共 18 槽、18 次 HTTP 请求，全部执行且无失败；三种协议各两个区组，组成 **6 对** fresh/repeat，而非早期短报的 9 对。每对请求体相同，间隔至少 5 秒。逐槽账及原始响应可由 [probes](<probes/>) 查阅；[批收据](<probe-receipt.json>) 的具体字段和阶段须单独核对。

离线复核记载三种协议各两次 repeat 的缓存读取数均为 2048，fresh/control 为 0；anthropic-messages 的 creation 字段六次均为 0，chat-completions 无对应 creation 映射。responses 的原始响应实际含嵌套 cached_tokens，旧映射漏掉该路径，将其记为 missing；原始响应和缺陷层均保留，详见[离线复算侧车](<execution-accounting-sidecar.json>)。同一数值的别名不应重复累计。

## 未知与边界

fresh 是新 nonce，不证明冷缓存；repeat 读数不证明由本实验创建缓存或证实写入机制。协议字段缺失不等于无缓存，不同协议 usage 分母不应直接相加；未观测成本数据。进一步结论应逐条复核原始响应及映射，避免把字段缺失、null 和零混同。
