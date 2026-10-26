# cost-usd 复算（2026-10-26）

回应[未知登记](<../../未知登记.json>)条目 `cost-usd`：成本口径此前为 null（只有 token 数、无可比货币成本）。本目录用官方价目对 **A 组（CLI×DeepSeek V4.1-Flash）44 场**完成离线 USD 换算；B 组模型封闭不换算（见 §5）。

**只读复算**：不修改运行总账、未知登记或任何既有文件；本目录外零写入。未做任何 git 操作。

## 1. 费率来源（prices.json）

- 来源：DeepSeek 官方文档 [中文价目页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) 与 [英文价目页](https://api-docs.deepseek.com/quick_start/pricing/)，**取数时间 2026-10-26 23:51–23:53（Asia/Shanghai）**，web_fetch 直接抓取页面原文。
- 采用模型 **deepseek-flash（= DeepSeek-V4.1-Flash-1017）**，与 A 组 44 场 meta.model 逐场核对一致。官方 USD 价（每 1M tokens）：

| 档位 | 输入·缓存命中 | 输入·缓存未命中 | 输出 |
|---|---:|---:|---:|
| 空闲时段 | $0.003 | $0.15 | $0.60 |
| 高峰时段 | $0.006 | $0.30 | $1.20 |

- **缓存折扣**：官方价目本身分命中/未命中两档（命中≈未命中的 1/50），本换算对命中部分直接用官方命中价，即**含官方缓存折扣**；无其他折扣。CLI 场协议为联网关、无 Search/Fetch 调用（该项官方 2026-11-01 起才计费），不计入。
- 官方同时给出 CNY 价目（空闲 $对应：命中 0.02 元 / 未命中 1 元 / 输出 4 元每 1M），已留档 prices.json；换算**直接采用官方 USD 价，不引入自行汇率**。
- 页面未标注生效/调价日期，且声明价格可能调整——本表仅对取数时点费率负责。

## 2. Token 数据可得性（盘点结论）

**per-run token 数据可得，44 场 A 组全部换算成功，无缺口。** 但三种来源口径不同，混用会算错：

| 来源 | 内容 | 本复算用法 |
|---|---|---|
| [运行总账-2026-10-24.json](<../../运行总账-2026-10-24.json>) `runs[].original_fields.usage`（codex 15 场） | **全场累计**：input_tokens（含缓存）、cached_input_tokens、output_tokens | 直接可用；逐场与 `agent.jsonl` 的 `turn.completed` 核对 **15/15 一致** |
| 同上（dsh 15 场） | ⚠️ **只是最后一次 API 调用的快照**，非全场累计（实测 r1025 cargo：快照 56,175 输入 vs 全场 538,896） | **不可直接用**；改从 `agent.jsonl` 逐调用求和（每场末次调用与总账快照 15/15 对上，佐证字段语义） |
| 同上（r1027/r1028 的 14 场） | 总账未存 usage（meta.usage 为 null） | 从 `agent.jsonl` 提取：codex 取唯一 `turn.completed`（全场累计），dsh 逐调用求和 |
| [3-表现现场](<../../../3-表现现场>) 各场 `agent.jsonl` | 逐调用 usage（dsh：`inputTokens`=未命中、`cacheReadTokens`=命中；codex：`input_tokens` 含命中、`cached_input_tokens`=命中子集） | dsh 全部 22 场的真值来源；字段语义与 [复算/token-recompute.py](<../../token-recompute.py>) 既有结论一致（Codex 输入含缓存、DSH 不含） |

换算公式：`cost = miss/1M×未命中价 + hit/1M×命中价 + out/1M×输出价`。`reasoning_output_tokens` 是输出子集，不重复计费；各场 `cacheWrite=0`，官方亦无写入计费列。

## 3. 峰谷时段判定

官方分高峰/空闲两档（北京时间周一至五 9–12、14–18 点为高峰）。轨迹未存逐调用时间戳，按每场 `meta.started_at + duration_s` 判定；**44 场均整体落在单一档内、无跨界**：r1023（10-22 周四 17:38–17:44）与 r1027（10-23 周五 16:35–16:46）为高峰，r1024/r1025（10-22 20 点档）与 r1028（10-23 周五 18:32 之后）为空闲。CSV 同时给出两档上下界列备查。

## 4. 结果（cost_table.csv / cost_details.json）

| 范围 | 场数 | 缓存命中 tok | 未命中 tok | 输出 tok | USD |
|---|---:|---:|---:|---:|---:|
| A 组全部（含 5 场 X 留档） | 44 | 35,987,456 | 1,085,208 | 1,182,830 | **$1.0998** |
| 仅裁定 V（主表口径） | 39 | 33,309,440 | 851,592 | 1,124,767 | **$1.0219** |
| ├ codex | 22 | — | — | — | $0.5650 |
| └ dsh | 22 | — | — | — | $0.5348 |

- 单场区间约 $0.0007–$0.0976；最贵为 r1027 `dsh__dabstep-payments-10`（$0.0976，高峰档）。X 场（作废/可疑替换场）合计 $0.0779，**仅留档、不计主表**，与「不计有效/主表但不抹历史」的总账口径一致。
- 缓存命中占输入总量 97.1%——官方缓存折扣是本组成本能压到 1 美元级的决定性因素。

## 5. 口径边界（不换算部分）

- **B 组（豆包、WorkBuddy 桌面/网页，含 r1021/r1026/r1029/r1030/r1031/r20261026）：不换算。** 模型封闭，计费体系非 DeepSeek API 按量价目（WorkBuddy 走积分/订阅、豆包/元宝产品内嵌），总账对这些场也未存 usage 字段；r1029 WorkBuddy trace 内虽有 usage 痕迹，但模型不是 deepseek-flash，按官方 DeepSeek 价折算会造出虚假可比性。
- **C 组（r1022 五场裸模型）：按任务范围未换算。** 其模型同为 deepseek-flash、总账有 OpenAI 风格 usage（cached=0），如需扩展可用同一公式直接补算。
- **历史 10-16 行**（`historical_inventory`，模型为 GLM/mimo 等）：不属本期 62 场口径，未换算。
- 本表是**账面重算价**，非 DeepSeek 后台账单：不含余额折扣、赠送金、失败重试的计费差异；峰谷按整场归档而非逐调用时间戳。

## 6. 交付与复现

| 文件 | 内容 |
|---|---|
| [prices.json](<prices.json>) | 官方价目原文数字、取数时间、来源 URL、峰谷规则、缓存折扣说明 |
| [cost_table.csv](<cost_table.csv>) | 44 场逐场：token 三分项、峰谷档、USD、两档上下界、校验标记 |
| [cost_details.json](<cost_details.json>) | 机器可读明细 + 分批/分 harness/全量汇总 |
| [recompute_cost.py](<recompute_cost.py>) | 复现脚本（只读仓内证据，重跑即重生成 CSV/JSON） |

复现：`python3 "5-评测报告/复算/2026-10-26/cost-usd/recompute_cost.py"`（输出 `runs=44 failures=0` 即口径自洽）。
