# 请求侧计数与缓存抖动（2026-11-17，环12 · R-A7 · 零新运行）

同一任务、同一构建、同一提示词的 **8 次真实运行存档**（GLM r1–r6，DeepSeek r1–r2）中，每个请求的字节已由前置包证明恒定；本页把每个请求的 **provider-reported usage** 与请求字节并排分列，回答第四周反馈 P1② 的请求侧部分：**同字节请求下，产品计数是否稳定？缓存命中是否可控？** 本页零新增运行，只读既有私档中的响应体（数值投影公开，原始响应不公开）。

## 来源与可比性

- 8 个真实 run：GLM r1–r6（[跨运行重建验证]与[跨运行重建扩展]、[跨日重建复核]三包已证 req1/req2 逐字节恒定、req3 归一恒等）；DS r1–r2（[跨模型捕获]已证 ds_assembly_stable）。
- 响应体为私档：GLM 为明文 SSE；DS 为 gzip（`content-encoding: gzip`，解压确定，解压后 SHA 私档记录）。每个响应恰一个含 `usage` 的 SSE 行（末 chunk），本页只取该行数值。
- 全部 24 对 upstream_status=200。

## 终点（全部描述性）

- **E1 计数稳定性**：24/24 对中，字节恒定的请求得到逐字节相同的 `prompt_tokens`（GLM：req1=7620×6、req2=190×6、req3=7827×6；DS：req1=8089×2、req2=188×2、req3=8361×2）。
- **E2 缓存抖动**：`cached_tokens` 在同字节请求间**不稳定**：GLM req1 ∈ {0,0,0,7616,7616,0}、req2 ∈ {0,0,0,128,128,128}、req3 ∈ {7616,7616,7616,7808,7808,7616}；DS req1 ∈ {0,7936}、req2 ∈ {0,0}、req3 ∈ {8192,8192}。缓存命中由 provider 侧决定，**成本/延迟混杂如实保留**（呼应「不写完全受控」）。
- **E3 字节↔计数比值**：逐请求描述性比值（如 GLM req1 ≈ 4.34 B/token、DS req1 ≈ 4.17 B/token），不做通用换算、不折算成本。
- **E4 方言**：GLM 单字段 `prompt_tokens_details.cached_tokens`；DS 双字段 `prompt_cache_hit_tokens/miss_tokens` 且与 `cached_tokens` 镜像。
- **E5 completion 波动**：同任务 completion_tokens 在 GLM 8–10、DS 8–9（标题请求）间波动，属响应侧差异，**不评分**。

## 已知限制

n=1 任务 × 2 provider；计数为 product-reported（不认证 provider 内部计量或计费）；响应体原始字节不公开（数值投影+私档 SHA）；E2 的缓存语义由 provider 定义。

## 复算

`python3 verify.py --evidence evidence.json --output /tmp/verify-out.json`（stdlib，重放只需公开件）；私档重建：`--archive-base <until14根> --build-evidence evidence.json --output result.json`。冻结基线 50c073c0…；pin [请求侧跨运行重建验证]（a6206a2a…）与[请求侧跨模型捕获]（3de9ded7…）的请求 SHA 常量。
