# bird-schools15：Text-to-SQL（BIRD mini_dev 切片）

## 任务

`inputs/` 给了一个 SQLite 数据库切片（加州学校数据，`california_schools`）与 15 道自然语言问题：

| 文件 | 内容 |
|---|---|
| `inputs/db/california_schools.sqlite` | 三张表 `frpm` / `satscores` / `schools` 的完整 SQLite 库（约 11 MB） |
| `inputs/schema.sql` | 建表语句（列名、类型） |
| `inputs/sample_rows.json` | 每张表前 3 行样例（列名 + 值），便于不便连库时判读字段 |
| `inputs/questions.json` | 15 道题：`question_id` / `question` / `evidence`（官方口径提示）/ `difficulty` |

## 产物

在当前运行目录写 `answers.jsonl`，**每行一个 JSON**，恰好 15 行：

```json
{"question_id": 1471, "sql": "SELECT ... FROM ..."}
```

- `sql` 必须是能在该库上直接执行的单条 SQLite 查询（不要包含分号结尾之外的多语句、不要建表/改数据）；
- 列名、聚合口径、过滤条件按题面与 `evidence` 的要求写；返回列的顺序不敏感，但**返回的列集合与行内容要正确**；
- 允许你先在 `inputs/db/...` 上跑 SQL 自测，但**不要修改** `inputs/` 下任何文件。

## 环境

- 可用 `python3`（3.9，标准库含 `sqlite3`）；不联网。
- 也可以只用题面 + `schema.sql` + `sample_rows.json` 直接写 SQL，不必真的连库。

完成后结束，不需要额外解释。
