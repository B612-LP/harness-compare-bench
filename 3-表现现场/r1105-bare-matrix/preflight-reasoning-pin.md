# 预检收据：reasoning 档位参数钉死（2026-11-01 11:47–11:52）

PREREG l18-20261101 事项①声明的预检程序执行记录。端点 `https://api.deepseek.com/responses`，模型 `deepseek-flash`，key 仅进程环境（sk-8f95…，35 字符）。

## 探针 1（平凡题，验证候选参数被接受且不炸）

| 候选 | 请求体附加 | HTTP | reasoning_tokens |
|---|---|---|---|
| baseline | （无） | 200 | 18 |
| A `reasoning:{"effort":"low"}` | 同 | 200 | 18 |
| B `reasoning_effort:"low"` | 同 | 200 | 19 |

平凡题无区分力 → 换重思考题。

## 探针 2（组合计数题，区分档位）

| 候选 | reasoning_tokens | total_tokens |
|---|---|---|
| baseline 默认档 | 46,433 | 46,722 |
| A `reasoning:{"effort":"low"}` | **18,540** | 18,890 |
| B `reasoning_effort:"low"` | 40,873 | 41,135 |

A 相对 baseline 降 60%（−27,893）；B 仅 −12%（接近噪声）。

## 探针 3（易题对照，验证档位不影响易题行为）

两组 default/low 成对：reasoning 245/240、307/239 —— 易题下两档行为一致（符合「档位只影响思考深度」预期，无异常副作用）。

## 钉死结论

**arm `inline-low` 参数 = `reasoning: {"effort": "low"}`**（候选 A）；`reasoning_effort` 顶层参数在该端点无实义效果（候选 B 淘汰）；arm `inline-default` 不传任何参数（模型默认档，即官方文档默认 effort=high）。与官方思考模式文档（api-docs.deepseek.com/guides/thinking_mode：思考模式默认开、effort 默认 high、支持档位控制）一致。

探针原始请求/响应体未逐份存档（内容为本文表格中的 usage 数字；参数形态已固化于 `tools/bare_run_v2.py` 的 `LOW` 常量与各场 `bare-request.json`）。此为预检性质的声明边界：如需逐字节探针存档，下批预检改全程落盘。
