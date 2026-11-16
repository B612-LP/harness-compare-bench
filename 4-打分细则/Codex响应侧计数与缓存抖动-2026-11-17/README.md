# Codex 响应侧计数与缓存抖动（2026-11-17）

## 范围与授权
- **0 新产品运行。** 全部观测值来自 2026-11-17 已授权四次真实运行（环14 两次：`Codex请求侧最小捕获`；环15 两次：`Codex深链与加密推理回放`）已留档的响应流（SSE `response.completed` 事件内 `usage`）。本包只读私档、发布哈希与整数，不发射、不改旧包。
- 冻结：2026-11-17T06:10+08:00（Asia/Shanghai）。基线 `b40ce6e346597846c6b451f7e1296128ae9a3247`。

## 端点（全部描述性；事后分析，非盲预测——见执行记录先验披露）
- **E1 prompt 稳定性**：同链位、请求字节长度相等且按已发布 req1 分类 id 归一后恒等的跨 run 请求对，`usage.input_tokens` 相等对数 / 2（loop14 r1↔r2 req1、loop15 r1↔r2 req1）。注意 Codex req1 原始字节跨 run 不逐字节相同（恰 11 个 id 类叶，见环14 包）——这与[请求侧计数与缓存抖动](<../请求侧计数与缓存抖动-2026-11-17/README.md>)的 DSH「同字节」对条件更弱，结论只到「长度相等+id 归一恒等」层面。
- **E2 缓存波动**：上述同条件对中 `input_tokens_details.cached_tokens` 不等的对数 / 2；并登记各 run 首请求的 cached_tokens 值（含首 run>0 的观察，不解释成因）。
- **E3 链内增量登记**：每 run 相邻请求的（字节增量, input_tokens 增量）逐对登记，不判定比例性结论。
- 每响应附登记：`reasoning_tokens`（`output_tokens_details`）与加密回放观测（环15）**并列**呈现，不合并因果。

## 边界与不可认证项（沿用[请求侧计数与缓存抖动](<../请求侧计数与缓存抖动-2026-11-17/README.md>)）
- 全部数值是 **product-reported counters**；不认证 provider 计费、真实 KV 复用、缓存命中机制或请求实际摄入；数值自洽不能补齐来源证明。
- 字节≠token：E3 只登记，不拟合；n=2 任务对、单模型（deepseek-flash 官方 API id）。
- 响应原文只在私档；公开 evidence 只含请求/响应 SHA-256、链位、整数。

## 复算入口
- `python3 verify.py --root <repo> --output <out>`（公档重放：核对封印链内登记的 README SHA——evidence.frozen_readme_sha256 与 verify 常量互核，磁盘 README 变动由 Git 追踪承接、重放不重复哈希磁盘文件；环14/15 两个公开 evidence 的 per-request SHA pin、全部算术与分类）。
- `python3 verify.py --root <repo> --archive-root <capture-root> --build-evidence <e> --output <r>`（私档重建）。
- `CXUSAGE_TEST_ROOT=<本目录父级> python3 test_verify.py`（13 用例；无环境变量时 2 个真档用例 skip）。

## 验收
非作者独审通过后并入 v1.74；独审与本页冻结一致、六件 SHA 由 SELF-ACCEPT 封印。
