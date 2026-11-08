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

## 6. 会话轨迹扩展：DSH 臂观测（S1–S6，loop30）

老师要求②同样适用于 DSH 臂。DSH 会话轨迹原件为 `session.v4.jsonl.zstd`（JSONL v4 事件流，zstd 压缩），**该格式不记录 token usage 数值字段**——与 Codex rollout 不同，R5 无法落为自报 token 列，如实落为「声明请求配置」辅助列。工具 `tools-session-trace-observe.py` v1：

| # | 指标 | 定义 |
|---|------|------|
| S1 | 文件字节 | zstd 压缩字节、解压字节、行数、unparsable 计数 |
| S2 | 类型计数 | `type` 平铺 + `type+data 子键名`（仅键名，内容值不进计数键） |
| S3 | 输入侧字节 | `user/message`+`request/header`+`request/context` 事件 canonical JSON 字节和（会话级汇总；v4 流单 turn 为主，不逐 turn 细分） |
| S4 | 输出侧字节 | `assistant/message`+`tool/call` 字节和；`tool/result` 字节单列观察字段 |
| S5 | 声明请求配置（auxiliary） | `data.header.config`（provider/model/reasoningEffort/maxTokens）与 `request/context`（contextWindow 等），冠 `declared_` 前缀；**是配置声明，不是用量实测** |
| S6 | 会话时长 ms | timed 事件末−首（数据派生，确定性） |

行标识：run 目录标签（`dsh__*`）+批次标签（`r1030-*` 等）——两者均为公开树 `3-表现现场/` 已有目录名，不含私档路径成分。防泄漏断言/确定性/write-once/机器见证同 §4（泄漏扫描对解压后文本逐行进行；`type` 键值与类型 token 形态作为结构元数据豁免——其本身在 S2 计数键中有意披露）。

### 试点：正式批 a1 五场 + 独立重复 r2/r3 十场（15 份，2026-11-08）

`session-trace-pilot-formal-a1-n3.json`（`aggregate_sha256=b9ce96563b1e199eaf66fe90b6d27144cbaec5357fda13f5f8663fb7945feb4d`）+ `.witness.json`（`all_ok=true`，确定性重放逐字节一致）。合计：15 文件 / 压缩 2,819,303 B / 解压 10,820,141 B / 2,394 行 / unparsable=0；S3 输入侧 405,200 B、S4 输出侧 8,516,247 B、tool_result 1,627,350 B。

逐任务三跑对照（R3=输入侧字节，R4=输出侧字节；a1/r2/r3）：

| 任务 | R3（三跑） | R4（三跑） |
|------|-----------|-----------|
| bird-ca-schools-15 | 27,196 / 27,244 / 27,244 | 637,076 / 444,611 / 368,855 |
| dabstep-payments-10 | 25,939 / 27,646 / 43,944 | 645,806 / 1,090,758 / 564,407 |
| exercism-py-6 | 25,046 / 25,094 / 25,094 | 273,086 / 246,649 / 341,806 |
| lcb-recent-hard-4 | 25,295 / 25,343 / 25,343 | 721,310 / 798,114 / 634,801 |
| tb-cargo-plan | 24,892 / 24,940 / 24,940 | 574,086 / 642,354 / 532,528 |

观察（描述性，不构成新判定）：独立重复下 S3 输入侧字节高度稳定（多数任务三跑差 ≤48 B，dabstep 一场 27,646→43,944 系多一轮工具调用）；S4 输出侧随生成变化明显（同任务三跑每场 max/min 1.21–1.93×；[勘误 2026-11-08]：本句原「1.4–2.6×」无实测依据，与上方表格聚合件逐场重算不符，已更正——五场逐项 1.21/1.26/1.39/1.73/1.93）——请求侧「输入稳定/输出波动」的分离结构正是该框架要求分列观测的原因。全部 15 场 declared 配置一致（deepseek-official / deepseek-flash / reasoningEffort=low / maxTokens=256000 / contextWindow=1000000）。运行元数据（run/批次标签）按[脱敏收据](<../敏感现场脱敏收据-2026-11-08/README.md>)字段分离口径可公开。

## 7. 原生轨迹扩展：WorkBuddy 与豆包臂观测（T/D 系列，loop32）

老师要求②三轨口径补齐：A 轨（Codex rollout，§2/§5）与 DSH 轨（§6）之外，本节把观测框架落到 W（WorkBuddy 原生 trace）与豆包办公（会话 trajectory）两臂，全部基于评测期真实运行的原生轨迹**历史归档件**（零发射；原件已按[归档纪律]存评测私档归档，公开聚合件可由归档原件复算）。

| 系列 | 指标 | 口径 |
|---|---|---|
| T1/T2/T3 | 文件字节与行数 / 事件类型计数（trace_start/span_start/span_end/trace_end）/ span 类型计数（start/end 分列） | 结构面 |
| T4 | 请求侧近似=`generation`+`agent` span 的 toolInput 字节和 | **span 工具面近似，非网关 HTTP 请求体**（WB 网关侧原始请求件不在：l4/l5/l6 网关线均为 mock 自测） |
| T5 | 输出侧=toolOutput 字节和 | 结构面 |
| T6 | `self_reported_` 应用自报值（trace.totalTokens/usage 字段） | auxiliary |
| T7 | 会话时长（trace duration，ms） | 结构面 |
| D1/D2 | 文件字节行数 / role 计数 | 结构面 |
| D3 | 请求侧近似=assistant `tool_calls.function.arguments` 规范 JSON 字节和 | **会话轨迹面近似** |
| D4 | 输出侧=tool 结果 content 字节和 | 结构面 |
| D5 | usage 字段计数 | absent 如实输出，不虚构 |
| D6 | 会话时长（轨迹时间戳差） | absent 如实输出 |

工具 [tools-native-trace-observe.py](<tools-native-trace-observe.py>)：`--kind workbuddy|doubao --archive <归档目录> --out <pilot.json>`；防泄漏断言（>24 字符源内容串/本机绝对路径→FATAL rc=2 不写出；run 标识 basename 豁免）、write-once、确定性；机器见证（shasum 独立实现逐件复算+同输入确定性重放逐字节对比，非真人签名）。

试点（真实历史窗口全集）：

| 试点 | 归档件 | 字节/行数 | 请求侧近似 | 输出侧 | 自报值 | 见证 |
|---|---|---|---|---|---|---|
| [WorkBuddy 评测窗口](<native-trace-pilot-workbuddy-20261027-30.json>) | 41 trace（2026-10-27→30） | 9,398,273 B / 4,430 行 | T4=5,863,997 B（305 spans） | T5=533,551 B | T6=0/0/0（无 usage 字段、totalTokens 全 0） | [all_ok=true](<native-trace-pilot-workbuddy-20261027-30.witness.json>) |
| [豆包办公 2026-10-30](<native-trace-pilot-doubao-20261030.json>) | 4 会话 trajectory | 394,670 B / 286 行 | D3=126,146 B（148 calls） | D4=217,617 B（148 results） | D5=0（无 usage 字段）；D6 absent | [all_ok=true](<native-trace-pilot-doubao-20261030.witness.json>) |

观察（描述性，不构成新判定）：**两臂原生轨迹面均未携带 token usage**（WB totalTokens 全 0 且无 usage 字段、豆包无该字段）——W/豆包的自报 token 在原生轨迹面不可得，请求侧字节指标因此成为这两臂唯一可观测口径，这正是本规范要求「请求侧为主、自报为辅、分列输出」的原因。原文声明：豆包轨迹面不含用户 prompt 原文行（role 计数无 user 行）；WB span 面的 toolInput **含用户 prompt 文本**（305 个 generation span 的 toolInput 为含 `role:user` 的消息数组，应用侧截断约 20,000 字符）——因此 WB trace 原件属含内容原件，只存评测私档归档、不入公开树；本目录公开聚合件仅含计数/字节/哈希/basename，零内容字段。运行标识（pid/trace 文件名/会话号 basename）按[脱敏收据](<../敏感现场脱敏收据-2026-11-08/README.md>)口径可公开。

## 8. 四臂跨批对照索引（单一索引呈现）

第三周反馈要求「跨批合同、版本和提示差异需单一索引呈现」——本节为四臂请求侧观测的**索引层**（不改 §1–§7 指标定义与试点数值）：

| 臂 | 观测原件形态 | 指标系列 | 请求侧近似口径（近似性质声明） | 自报值可得性 | 试点（聚合件 sha256 摘引） |
|---|---|---|---|---|---|
| Codex（A 轨） | rollout jsonl（CODEX_HOME 会话原件） | R1–R5（§2/§5） | 重构输入字节=逐 turn 前序 response_item canonical 字节和 | **有**：token_usage_record 自报 token（`self_reported_` 前缀 auxiliary 列） | [r20261027 消融批 2 份](<request-side-observe-pilot-ablation.json>) `632a8bda…4c3e`（[见证](<request-side-observe-pilot-ablation.witness.json>)） |
| DSH | session.v4.jsonl.zstd（原生会话轨迹） | S1–S6（§6） | 输入侧=user/message+request·header/context 字节和（会话级汇总） | **无**：轨迹面无 usage 字段→`declared_` 配置（deepseek-flash/low/256000/1000000） | [formal-a1+r2/r3 15 份](<session-trace-pilot-formal-a1-n3.json>) `b9ce9656…eb4d`（[见证](<session-trace-pilot-formal-a1-n3.witness.json>)） |
| WorkBuddy（W 轨） | span trace jsonl（原生 span 面） | T1–T7（§7） | generation+agent span toolInput 字节和=**span 工具面近似，非网关 HTTP 请求体**（网关线 l4/l5/l6 原始请求件不在） | **无**：totalTokens 全 0 且 span 无 usage 字段（T6=0/0/0 如实） | [41 trace 评测窗口](<native-trace-pilot-workbuddy-20261027-30.json>) `94ef96c9…2e3a`（[见证](<native-trace-pilot-workbuddy-20261027-30.witness.json>)）；trace 原件含 prompt 文本，只存私档归档 |
| 豆包办公 | trajectory jsonl（原生会话轨迹） | D1–D6（§7） | assistant tool_calls arguments 规范 JSON 字节和=**会话轨迹面近似** | **无**：轨迹面无 usage 字段（D5=0 如实）；时长 D6 absent | [4 会话 2026-10-30](<native-trace-pilot-doubao-20261030.json>) `0868f228…ce0f`（[见证](<native-trace-pilot-doubao-20261030.witness.json>)） |

统一不变式（四臂同守）：各臂请求侧口径互不等值，**不构成跨臂字节等值比较**（合同/模型/提示/schema 各臂不同，且各臂观测面层级不同）；自报值仅辅助；聚合件零内容字段、零本机路径，含内容原件只存评测私档；跨臂可比的只有「输入稳定/输出波动」的分离结构与「自报值可得性」本身——后者正是要求②「请求侧为主、自报为辅」在三轨落地的直接证据。

### 元宝专家模式（B 组网页端）观测局限

- 元宝无本地轨迹原件：历史批次证据=产物+提示词留档+行为面记录（与评测报告桌面观测口径一致），无请求侧日志、无会话轨迹、无 span 面可归档。
- 因此元宝不入上表：无观测原件形态即无指标系列可定义；请求侧不可观测是本规范对元宝的如实边界，不虚构可观测性。
- 自报值同样不可得（网页端无本地 usage 记录）。若未来出现可归档的轨迹形态，再按本规范框架扩展对应指标系列。
- 该边界与评测报告桌面观测口径（产物+提示词+取证能力单列）一致，不因本规范存在而改变元宝的证据形态。

## 9. 与冻结件的关系

本目录为新增规范与工具，不改两版报告正文、ledger、正式25格、周报、gold 与历史判卷；报告 v1.9 §4.5 的机制与口径声明不受影响。发射阶段仍未放行；本规范在放行后的首批发射中即按 §3 采样纪律生效。
