# dabstep-dev10：支付数据分析问答（DABstep dev 子集）

## 任务

`inputs/` 下是一份真实支付业务数据湖（Adyen 公开的 DABstep 数据）：

| 文件 | 内容 |
|---|---|
| `inputs/payments.csv` | 逐笔交易流水（约 23.5 MB，含时间、金额、币种、发卡国、IP 国、收单国、商户、设备、欺诈标记等列） |
| `inputs/fees.json` | 费率表（按支付方式/卡组织/档位） |
| `inputs/manual.md` | 业务手册（费率公式、口径定义，**做题必须读**） |
| `inputs/merchant_data.json` | 商户资料 |
| `inputs/merchant_category_codes.csv` | 商户类别码表 |
| `inputs/acquirer_countries.csv` | 收单国表 |

`inputs/questions.jsonl` 有 **10 道题**，每行一个 JSON：`task_id` / `question` / `guidelines`（该题的答案格式要求）。

## 产物

在当前运行目录写 `answers.jsonl`，**每行一个 JSON**，恰好 10 行，每题一行：

```json
{"task_id": "5", "answer": "NL"}
```

- `task_id` 必须是字符串，与题目一一对应，不允许多、少或重复；
- `answer` 严格按该题 `guidelines` 的要求书写（格式、单位、小数位、选项字母都要对；信息不足时按 guidelines 给 `Not Applicable`）；
- 只输出答案值本身，不要解释。

## 环境

- 当前目录即可读写；`inputs/` 不要修改。
- 可用 `python3`（3.9，标准库）自行统计；不联网。
- 建议先读 `inputs/manual.md` 再动手，多道题的口径（费率、欺诈率、top-N 的分母）都在里面。

完成后结束，不需要额外解释。
