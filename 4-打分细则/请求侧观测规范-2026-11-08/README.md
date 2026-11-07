# 请求侧用量观测规范（2026-11-08，loop28）

对应课题要求：评测须保证结论可复核、判断写明置信依据；老师要求②「预先指定可由请求侧/运行器直接观测的输入大小指标，并保留产品自报值为辅助」；追问②「如何绕开 Codex 自报用量」。本规范定义一套**不依赖产品自报**的请求侧观测量与采样纪律，并随附可复算工具与真实试点。

## 1. 动机与定位

- 此前报告 v1.9 行100 已采用「指定客户端字段的规范序列化比产品自报 token 更可审」的口径（原生夹具字节分解），但停留在单场分析；本规范把该口径推广为面向未来批次的标准观测协议。
- 请求侧观测量（rollout 日志字节/计数）与产品自报用量（token 计数）**分列**：前者为本规范的裁定依据，后者一律冠 `self_reported_` 前缀、标注 auxiliary，仅作辅助参考。两者单位不同（字节 vs token），比值仅作描述性换算参考，不建立恒等式。
- 两种量各自回答不同问题：请求侧字节回答「实际送入/产生多少文本负载」，自报 token 回答「计费/缓存口径下的账面量」；对照两者的差值方向即是「自报与实测脱节」的检测信号。

## 2. 指标定义（R1–R5）

| # | 指标 | 定义 |
|---|------|------|
| R1 | 文件字节/行数 | rollout jsonl 原件 `bytes`、`lines`（含 `unparsable_lines` 容错计数） |
| R2 | 类型计数 | 两级：`type` 与 `type/payload.type`（如 `response_item/function_call`） |
| R3 | 逐 turn 重构输入字节 | 上一 `token_usage_record` 边界之后全部 `response_item` 载荷 canonical JSON 序列化字节和（边界行不计入下一 turn）；合计 `response_item_bytes_reconstructed_total` |
| R4 | 逐 turn 输出侧字节 | 同一边界内 `payload.type∈{message,reasoning}` 的字节和；合计 `output_message_reasoning_bytes_total` |
| R5 | 自报 usage 汇总 | 每边界 `usage.{input,cached_input,cache_write_input,output,reasoning_output,total}_tokens`，字段冠 `self_reported_`、`auxiliary=true` |

R3 的构造含义：turn 边界由自报记录切分，但边界内**计量的是日志字节而非自报 token**——即边界借用、计量不借用。

## 3. 采样纪律（面向未来批次）

1. 发射批每臂每题全量保存会话侧原始事件日志（Codex rollout jsonl 或等价物）到专用 `CODEX_HOME`，批后归档并登记 sha256；不落盘的会话不得作为用量结论依据。
2. 每臂每题跑 `tools-request-side-observe.py` 生成聚合收据并做机器见证（shasum 独立实现+确定性重放）；聚合件仅含计数/字节/token/哈希/basename，零内容字段，可直接公开。
3. 报告引用任何用量数字时，请求侧字节为主证，`self_reported_*` 为辅证；两者必须同时给出或明示缺失。
4. 历史局限（如实声明）：本课题历史正式批（2026-10-27/28 等）的请求侧原始日志未按本规范归档，仅有 curated 证据与单场字节分解（v1.9 行100）；本规范不回溯宣称历史批次已按 R1–R5 观测。现有可观测原件为 2026-10-27 消融批 2 份 rollout（见 §5 试点）。

## 4. 工具

`tools-request-side-observe.py` v1（Python3 stdlib，py3.9+）：

```
主跑   python3 tools-request-side-observe.py --input A.jsonl [--input B.jsonl ...] \
           [--input-dir DIR] --out aggregate.json [--receipt run.json]
见证   python3 tools-request-side-observe.py --witness aggregate.json \
           --witness-out witness.json --input A.jsonl [...]
```

- 防泄漏断言：源日志中长度>24 的内容字符串值（非白名单键）逐一检查不得出现在输出，命中即 FATAL rc=2，不写出文件。
- 确定性：输出无墙钟时间戳、键排序；同输入重放逐字节一致（见证即验证此性质）。
- write-once：`--out/--receipt/--witness-out` 已存在即拒绝（rc=3）。
- 见证=机器见证（shasum 外部实现复算文件 sha + 同输入确定性重放对比 aggregate_sha256），**不是真人签名**；与 [敏感现场脱敏收据](<../敏感现场脱敏收据-2026-11-08/README.md>) 的诚实边界口径一致。

## 5. 真实试点（2026-10-27 消融批 2 份 rollout，零内容公开）

`request-side-observe-pilot-ablation.json`（`aggregate_sha256=bca62149b0dd1a70df1218d2ed93430297c44a01ec084c3301ad1d34983d8908`）+ `request-side-observe-pilot-ablation.witness.json`（`all_ok=true`）。合计：

| 量 | 值 |
|---|---|
| 文件 | 2（1,091,525 B/327 行；556,846 B/171 行） |
| turns_closed | 58（39+19） |
| R3 重构输入字节 | 664,048 |
| R4 输出侧字节 | 336,030 |
| response_item 计数 | 223 |
| 自报 input/cached | 3,579,818 / 3,509,504（auxiliary） |
| 自报 output/reasoning | 116,875 / 69,744（auxiliary） |

试点聚合经防泄漏断言+人工抽查：公开件内长字符串值仅 sha256/basename/说明文字，无 prompt/回复内容。运行元数据（basename 含 session uuid 片段）按[脱敏收据](<../敏感现场脱敏收据-2026-11-08/README.md>)的字段分离口径可公开。

## 6. 与冻结件的关系

本目录为新增规范与工具，不改两版报告正文、ledger、正式25格、周报、gold 与历史判卷；报告 v1.9 §4.5 的机制与口径声明不受影响。发射阶段仍未放行；本规范在放行后的首批发射中即按 §3 采样纪律生效。
