# 规范 v1.5「不产值」条款实现一致性 + 跨解析器复核稳定性（2026-11-27，R1）

> 状态：**已收口（独审 PASS-with-notes，minor 已整改）**——本轮（until10 窗）零新增模型/产品运行，全部为已冻结原档与公开件的离线分析 + 合成探针。现行规范仍为 [v1.5](<../Harness统一观测规范-2026-11-19/README.md>)（冻结）；本页为实现层证据，v1.6 文本修订另环按预注册流程处理。

## 问题

[v1.5 §1](<../Harness统一观测规范-2026-11-19/README.md>) 已声明：重复键、非法 UTF-8、不成对 surrogate、非有限量、超边界输入**不产值**。但该条款的**实现基线**（stdlib `json.loads`）并未对齐：

- 重复键：`json.loads('{"a":1,"a":2}')` 静默 last-wins → 同一字节串**静默产值**且与原义不符；
- NaN/Infinity、孤立代理项：解析**静默接受**，随后 canon 层（`allow_nan=False` / UTF-8 编码）**裸崩溃**（`ValueError`/`UnicodeEncodeError`），不是规范要求的「按 §1 判不产值」；
- BOM、超深嵌套：解析层裸异常（`JSONDecodeError`/`RecursionError`）。

这构成 v1.5 §1 与实现之间的缺口。本轮验证：缺口是否在受控探针下按预测复现；一个条款对齐的**候选加固器**能否全部转为分类拒绝且不误伤合法输入；以及 Python/node 双解析器对真实档的投影是否逐字节一致（跨解析器复核稳定性）。

## 预注册判定（PREREG → 结果，5/5 成立）

| # | 预测 | 结果 |
| --- | --- | --- |
| PA1 | stdlib 对 6 类病态探针全部非分类不产值 | **成立 6/6**：dup_key 静默产值；NaN/-Infinity/孤立代理项解析静默+canon 裸异常（ValueError/UnicodeEncodeError）；BOM（JSONDecodeError）与深 2000（RecursionError）解析层裸崩溃 |
| PB1 | node v24 跨解析器对真实档全量逐字节一致 | **成立**：820/820 全配（含 W1 497+W2 69 SSE 帧与 235 条公开 JSONL 行）；float/大整数边界预声明、本语料 0 载荷未触发 |
| PC1 | 真实档病态特征全零 + 深度 ≤512 | **成立**：820 载荷 dup_key/NaN/lone/BOM/U+2028-9/float/非ASCII键全 0，max_depth=13（公开 235 行 max_depth=6） |
| PD1 | 候选加固器 6/6 分类拒绝 + 合法输入 parity | **成立**：DUP_KEY/NON_FINITE×2/LONE_SURROGATE/BOM/DEPTH_LIMIT 全部分类拒绝；820/820 parity（0 误拒）；深度上限 512 |
| PN1 | 篡改探针 3/3 检出 | **成立**：drop_field/num_tweak 靠钉定 canon SHA 翻转检出；dup_inject stdlib 静默收下而加固器 `DUP_KEY` 直接拒——加固器独有检出点（只比哈希知「变了」，加固器知「为何变」） |

## 关键结论

1. **v1.5 §1 缺口在实现层被证实，且可闭合**：候选加固器（对象 `object_pairs_hook` 查重 + `parse_constant` 拒非有限量 + 后置 surrogate 编码检查 + 深度 512 检查 + BOM 前缀拒绝）把 6/6 病态输入全部转为**分类拒绝码**（PARSE/BOM/DUP_KEY/NON_FINITE/LONE_SURROGATE/DEPTH_LIMIT），对全部 820 真实载荷 parity 逐字节一致——为 v1.6 文本修订提供实现依据（本页不改冻结规范）。
2. **跨解析器复核稳定性在现语料成立**：node v24.22.0 独立 JSON.parse + 码点序键排序 canon，与 Python 钉定 SHA256 820/820 一致。已知边界（JS `String(1e-07)='1e-7'` vs Python `'1e-07'`、>2^53 整数精度）预声明且本语料未触发。
3. **语料构成**：820 = W1 16 请求+497 SSE 帧 + W2 3 请求+69 SSE 帧（11-14 两链冻结原档）+ 公开 [r20261125-five-lcb](<../../3-表现现场/r20261125-five-lcb/>) dsh 78 / codex 84 / doubao 73 行。

## 公开复算：不需要原件或账号

在本目录运行（Python 3.9+、仅标准库；node ≥18 可选，缺则 C 部分如实 SKIP）：

```sh
python3 -IB verify.py
python3 -IBO verify.py
```

[verify.py](verify.py)：A 部分=合成探针 6+3 与 canon 决定性（内存构造，不依赖任何原件）；B 部分=公开档 235 行逐行 census + 加固器 parity；C 部分=[crossparse.mjs](crossparse.mjs) 对 B 语料独立解析比对。本机实测：A 全过、B 235/235 全零病态、C 235/235 match（node v24.22.0）。

**raw 绑定披露（C4 条款）**：W1/W2 585 载荷来自仓外冻结原档，公开端不可机器复算；该部分以非作者独审（独立复算+抽查回源）替代验收。公开端可完整复算的 E/D 235 行与本页 B/C 部分一一对应。

## 边界

- 全部为**合成探针 + 已冻结原档 + 公开件**；零新增模型/产品运行、零新捕获。
- 结论不自动外推到未采样的其他 harness 版本或格式演进后的新档；float/大整数边界本语料未触发，属预声明非实测排除。
- v1.6 候选加固器是**候选实现**，文本修订须另走 v1.5→v1.6 预注册流程；本页不具规范效力。

## 独审

非作者独审（仓外子代理，独立实现全量复算，2026-11-27）：**PASS-with-notes**。全部数值声明复算无一失实（含独立全新 node 序列化器 820/820、抽样回源逐字节核对、大整数/词面 NaN 补扫全零）；3 条 minor 中 2 条（parity 字节级实测化、源清单落盘）已当场整改并重跑确认（byte_agree 820/820），1 条（篡改检出面机制）在判定节已如实披露。公开页 A/B/C 部分与仓外 820 载荷结论同源；W1/W2 部分以本独审替代公开复算（见 raw 绑定披露）。
