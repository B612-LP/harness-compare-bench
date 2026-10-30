# 本场任务：l6-20261030-wb-gateway（WB 产品交付态）

**你的工作目录（绝对路径）：`/Users/b612-lp/bench-workspaces/l6-20261030-wb-gateway/bird-ca-schools-15`**

请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。

---

# bird-ca-schools-15 · v1.2-q26-frpm（2026-10-26 起为正式合同）

仅q26合同修订：免费或减价餐使用FRPM Count (Ages 5-17)，严格>800；不是Free Meal，800不满足。本地年龄5-17，英文15-17仅保留溯源。q27及其他14题不改；q27为已知尖角，口径见 spec.md §13（raw-key LEFT，保留缺 SAT 学校与 NULL 分数，不去重同名异校）。

## 任务

`inputs/questions.json` 给了 **15 道自然语言问题**（5 challenging + 7 moderate + 3 simple），
全部针对同一个 SQLite 数据库（加州学校数据，库名 `california_schools`，3 张表
`frpm` / `satscores` / `schools`）。请为**每一道题**写一条可执行的 SQLite 查询。

在**当前运行目录**写产物 `answers.jsonl`：**恰好 15 行**，每行一个 JSON 对象：

```json
{"question_id": 28, "sql": "SELECT ..."}
```

## 输入（不许修改 `inputs/` 下任何文件）

| 文件 | 内容 |
|---|---|
| `inputs/db/california_schools.sqlite` | 完整 SQLite 库（约 11 MB，3 张表） |
| `inputs/schema.sql` | 建表语句（列名、类型、主键/外键） |
| `inputs/sample_rows.json` | 每张表前 3 行样例（列名 + 值），便于判读字段与取值形态 |
| `inputs/questions.json` | 15 题：`question_id` / `difficulty` / `question_zh`（中文题面，以此为准）/ `evidence_zh`（口径提示）/ `answer_columns`（要求的输出列顺序）/ 以及英文原文与来源标注 |

每题都带 `answer_columns`：它给出**该题结果集的列顺序**。列名不参与判分，但
**列的顺序、列数、值**要与题面要求一致。

## 产物硬约束

- `answers.jsonl` 必须恰好 **15 行**，15 个 `question_id` 与 `questions.json` 一一对应；
  **缺失、多余、重复**任一情况即视为未按约定交付（不通过）；
- 每行 `sql` 必须是**单条**可在该库上直接执行的 SQLite 查询（只读查询；不要写
  `INSERT/UPDATE/DELETE/CREATE/DROP` 等，不要多条语句）；
- 允许你在 `inputs/db/...` 上跑 SQL 自测，但**不得修改** `inputs/` 下任何文件
  （判分器会核对输入副本的 SHA-256）。

## 判分口径

逐题执行你写的 SQL 与当前版本合同 gold SQL，把两个**结果集**做归一后比较：

- 单元格：`NULL` 记作 `<NULL>`；浮点数四舍五入保留 **6 位小数**；字符串去首尾空白；
- 行内按列序成组，**行排序后**再比（行顺序不敏感，重复行敏感）；
- 不允许用「字符串直接相等」代替结果集比较——类型与数值口径要对。

**准确率 ≥ 0.8（15 题里至少 12 题结果集一致）才算通过**；`weighted = 准确率 × 100`。
结果集一致才算对，SQL 写法不限（同一结果的等价写法同样算对）。

## 环境

- 可用 `python3`（3.9，标准库含 `sqlite3`）；不联网。
- **桌面可做**：也可以只读 `inputs/schema.sql` + `inputs/sample_rows.json` + 题面，
  直接手写 SQL，不必真的连库执行（产物只是文本文件）。

## 来源与许可

题目与数据库来自 **BIRD**（BIg Bench for LaRge-scale Database Grounded Text-to-SQL
Evaluation）的 `mini_dev` 集（`db_id=california_schools`），
官网 <https://bird-bench.github.io/>，论文 <https://arxiv.org/abs/2305.03111>，
数据许可 **CC BY-SA 4.0**，读取日期 **2026-10-22**。
本用例：题面按中文重写（英文原文保留在 `questions.json` 供溯源），仅q26 gold改写Free Meal→FRPM；其余14题gold保持官方原样，
数据库为官方库的等价重导出。详见 `spec.md`。

## 建议流程

1. 读 `schema.sql` 摸清 3 张表与连接键（`frpm.CDSCode` / `schools.CDSCode` /
   `satscores.cds`），用 `sample_rows.json` 确认取值形态（`Virtual`、`DOC`、`SOC`、
   `Magnet`、`FundingType` 等码值）；
2. 逐题按 `question_zh` + `evidence_zh` 写 SQL，注意 `answer_columns` 的顺序与列数；
3. 有 `sqlite3` 就自测行数/抽样值；没有就人工核对聚合与过滤口径；
4. 写满 15 行后检查 `question_id` 齐全、无重复、每行合法 JSON；
5. 交付，不需要额外解释。
