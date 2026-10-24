# bird-ca-schools-15 判分规格（spec）

版本：**v1.1（2026-10-24，schema 硬门修复；v1.0 冻结保留）** ｜ 判分入口：`checker.py`
定位：**medium · 多题 Text-to-SQL（BIRD exec-accuracy 口径）**，与 `corpus-squeeze`（工程迭代闭环）、`jielong-fullchain`（对话链路重放）互补，考「读 schema + 题面口径 → 写对 SQL」的稳定正确率。

## 1. 用例定位

输入是一个真实 SQLite 库（加州学校数据，3 表、约 11 MB）与 15 道自然语言问题，
要求产品在运行目录交付 `answers.jsonl`（15 行 `{"question_id", "sql"}`）。
判分不看 SQL 写法，只看**结果集**：逐题执行 pred SQL 与 gold SQL，结果集归一后比对，
**15 题里 ≥ 12 题一致（准确率 ≥ 0.8）才通过**。

- 题源：BIRD `mini_dev`（`db_id=california_schools` 共 30 题）里取 15 题：
  **5 challenging（28/36/62/83/87）+ 7 moderate（12/23/24/25/26/27/31）+ 3 simple（5/11/17）**。
- 为什么选这 15 题：覆盖单表聚合、多表 JOIN、`MAX/COUNT`、`GROUP BY … HAVING`、窗口函数
  （`RANK() OVER`）、`LIMIT` 偏移、日期字符串处理（`strftime`）、`IS NULL` 过滤、
  官方 evidence 口径（比例、百分数、码值映射）——失败模式互不重叠，正好落在
  「会写 SQL 但不熟 schema/口径」与「能稳定答对」之间。

## 2. 判分模式

- **headline 二值 0/1**（`BINARY=True`）：reward = 1 当且仅当
  ① 交付契约通过（`answers_schema` 与 `answers_coverage` 均为硬门：15 个非空行均为合法 JSON 对象，15 个 `question_id` 与题集一一对应，无缺失/多余/重复；任意追加非法行即使逐题全对也否决）；
  ② 输入完整性未被破坏（run_dir 里若带 `inputs/` 副本，逐件 SHA-256 与 canonical 一致）；
  ③ 逐题 exec-accuracy **≥ 0.8**（15 题至少 12 题结果集一致）。
- `weighted = 准确率 × 100`（即主观察项「exec_accuracy」的得分率；`0.8` 达标线就落在这个口径上）。
- 三个守卫：
  ① **truth 交叉校验**：`truth.json` 的 `case_id / checker_version / threshold / n_questions /
     answers 的 question_id 集合` 与 `checker.py` 常量任一不一致 → 启动即 ERROR，退出码 2；
  ② **输入 SHA-256 交叉校验**：canonical `inputs/` 四件（db / schema / sample_rows / questions）
     实际 SHA-256 与 `truth.json` 记录不符 → ERROR，退出码 2；
  ③ **gold 可执行性**：15 条 gold SQL 任一执行失败或结果为空 → 视为用例缺陷 → ERROR，退出码 2。
- 判分器只读 `run_dir` 与自身同目录文件，不联网、不装包、不读 `/tmp`；仅用标准库
  （`sqlite3` / `hashlib` / `json` / `subprocess` / `tempfile`）。**无 LLM judge**。

## 3. 观察项与权重

| id | 观察项 | 权重 | 通过条件 | 0 分条件 |
|---|---|---:|---|---|
| answers_file | 产物存在 | 5 | 运行目录有 `answers.jsonl` | 缺失（其余逐题项连带全红） |
| answers_schema | 行格式 | 10 | 15 行均为可解析 JSON 对象，含 `question_id` 与字符串 `sql` | 任一非空行 JSON/结构错 → 直接否决（即使 coverage 通过） |
| answers_coverage | 交付契约（硬门） | 15 | 恰好 15 行，`question_id` 集合与题集**完全一致**，无缺失/多余/重复 | 缺题、多题、重复 id → 直接不通过 |
| input_integrity | 输入完整性（守卫，硬门） | 10 | run_dir 附带的 `inputs/` 副本逐件与 canonical SHA-256 一致 | 任一件被修改 → 直接不通过；未附副本 → 未核验（不扣分） |
| exec_accuracy | 逐题结果集一致率（主观察项） | 60 | 15 题逐题 = gold 结果集（0/1 计分，每题 4 分） | 准确率 < 0.8 不通过 |

`weighted` 口径 = `exec_accuracy` 得分率 × 100（0–100）；`reward` 口径见 §2。
说明：契约项是「硬门」而非扣分项——缺 1 题即便其余 14 题全对（准确率 0.933）也判不通过，
因为产物未按 `answers.jsonl：恰好 15 行` 约定交付。

## 4. 结果集归一与比对口径

逐题执行 gold SQL 与 pred SQL（都在 canonical 库上，`PRAGMA query_only=ON` 只读守卫）：

1. 单元格归一：`None → "<NULL>"`；`float → round(v, 6)`（保留 6 位小数）；`int` 原样；
   `bytes → hex`；其他 `str(v).strip()`（去首尾空白）；
2. 行内单元格**按列序**成组（列顺序敏感、列数必须一致）；
3. 行**排序后**逐行比对：行顺序不敏感（`ORDER BY` 缺失不扣分），但**重复行敏感**
   （多行结果重复输出会判错）；
4. **不得用字符串直接比较**：比较在类型化 cellule 元组上进行（`1 == 1.0` 视为数值相等），
   不是把整行拼成字符串再 `==`。

**已知等价性**：`COUNT(DISTINCT School)` → `COUNT(School)` 等在本库上结果不变的改写，
判分结果一致（本库 `CDSCode`/`cds` 均为主键，JOIN 为 1:1，DISTINCT 在本数据上没有区分度）——
见 §6 的「等价答案正例」。

## 5. 运行目录约定

```
<run_dir>/
  answers.jsonl              # 必需产物：15 行 {"question_id", "sql"}
  inputs/                    # 运行器整目录拷入（agent 可读、不可改）
    db/california_schools.sqlite
    schema.sql
    sample_rows.json
    questions.json
  meta.json                  # 可选：产品/模型/版本/迭代日志，不参与判分
```

```bash
python3 checker.py <run_dir>          # 人读报告 + 最后一行 JSON
python3 checker.py <run_dir> --json   # 只输出一行 JSON（正式判分）
python3 checker.py --selftest         # 负控制/守卫自测，必须全 PASS 才可用于正式评分
```

正式判分输出（JSON 最后一行，`--json` 时只打这一行）：

```json
{"case": "bird-ca-schools-15", "reward": 0或1, "weighted": 0-100, "checks": [{"id": "...", "pass": true/false, "note": "..."}]}
```

退出码：`0` = reward 1；`1` = reward 0；`2` = 用法错误 / 自测失败 / 用例自身不一致（truth 漂移、gold 失败）。

## 6. 判分器自测（`--selftest`，v1.1 共 21 项）

`--selftest` 在 `tempfile.TemporaryDirectory()` 内逐项造产物并断言，**不污染仓库**；
共 21 项：原 15 组「正/负例」+ 2 组追加非法行回归 + 3 组守卫 ERROR 用例 + 1 项输入不被改动复核。
新增两组为 oracle 后追加 `not-json` / `[]`：逐题仍 15/15、coverage 通过，但 schema 失败且 reward=0。
v1.0 的 19 项记录如下保留为历史；独立修前/修后执行收据见[数值判卷审计](../../4-打分细则/判卷审计-2026-10-24/numeric/README.md)。

| # | 样例 | 期望 | 实测 |
|---|---|---|---|
| 1 | nop：空运行目录 | 0 | 0（accuracy 0.000） |
| 2 | oracle：`solution/answers.jsonl` 原样 | 1 | 1（accuracy 1.000） |
| 3 | **漏 1 题**（删 q36 一行）→ coverage 红 | 0 | 0（accuracy 0.933） |
| 4 | **多 1 题**（追加 `question_id=9999`）→ coverage 红 | 0 | 0 |
| 5 | **重复 question_id**（q28 写两遍，16 行）→ coverage 红 | 0 | 0 |
| 6 | **无效 SQL**（6 题查不存在的表） | 0 | 0（accuracy 0.600） |
| 7 | **空结果集**（6 题 `SELECT 1 WHERE 0`） | 0 | 0（accuracy 0.600） |
| 8 | **少 JOIN 条件**（5 题 `ON 1=1` 笛卡尔积，限行） | 0 | 0（accuracy 0.667） |
| 9 | **少 DISTINCT/未去重**（5 题多行结果翻倍） | 0 | 0（accuracy 0.667） |
| 10 | **近正确负例**（4 题口径差一处：删 `*100` / `LIMIT` 偏移 / 阈值 `>31`、`>900`） | 0 | 0（accuracy 0.733） |
| 11 | **格式错**（首行不是 JSON）→ coverage 红 | 0 | 0 |
| 12 | **改输入库**（run_dir 内 db 副本翻 1 字节）→ input_integrity 红 | 0 | 0（accuracy 仍 1.000，仅守卫拒绝） |
| 13 | **改输入文件**（run_dir 内 schema.sql 被追加）→ input_integrity 红 | 0 | 0 |
| 14 | **阈值边界正例**（3 题错 → 12/15=0.8） | 1 | 1 |
| 15 | **等价答案正例**（q5 去掉 DISTINCT，结果不变） | 1 | 1 |
| 16 | 守卫：truth 注入坏 gold → gold 执行失败 | ERROR exit 2 | exit 2 |
| 17 | 守卫：truth 的输入 SHA-256 与实际 inputs 不符 | ERROR exit 2 | exit 2 |
| 18 | 守卫：threshold 与 checker 常量不一致（0.5） | ERROR exit 2 | exit 2 |
| 19 | 收尾：canonical 输入自测前后未被改动 | PASS | PASS |

负例覆盖（BUILD-GUIDE §2 要求）：漏题、多题、无效 SQL、少 DISTINCT、少 JOIN 条件、
改输入库、空结果集、格式错、近正确口径错 —— 全 0；另有 2 个正例（阈值边界、等价答案）。

## 7. oracle 回归

```bash
# 正对照：oracle（= gold SQL）→ reward=1
tmp=$(mktemp -d)
cp -R inputs "$tmp/inputs"
cp solution/answers.jsonl "$tmp/answers.jsonl"
python3 checker.py "$tmp" --json        # {"reward": 1, "weighted": 100.0, "accuracy": 1.0}
# 负对照：空目录 → reward=0
empty=$(mktemp -d); python3 checker.py "$empty" --json   # {"reward": 0, ...}
```

`--selftest` 内部已含 oracle 回归（#2）与 nop（#1），CI 只需跑 `--selftest`。

## 8. 桌面可做性（三款桌面产品）

- 任务只要求「读文件 + 写文件」：读 `inputs/questions.json`（题面/口径）+ `inputs/schema.sql`
  + `inputs/sample_rows.json`，写 `answers.jsonl`；
- **不必真的连库执行**：`sample_rows.json` 给出每表前 3 行，`schema.sql` 给出列名与类型，
  足够人工判读字段与码值（`Virtual`、`DOC`、`SOC`、`Magnet`、`FundingType` 等）；
- 不要求终端、不要求第三方库（判分器也只用标准库）。
- 题面明确写了这条捷径（instruction.md「环境」节），避免桌面产品因不能连库而直接弃权。

## 9. 输入体积

| 项 | 大小 |
|---|---:|
| `inputs/db/california_schools.sqlite` | 11.1 MB |
| `inputs/schema.sql` | 3.9 KB |
| `inputs/sample_rows.json` | 7.6 KB |
| `inputs/questions.json` | 15.2 KB |
| **inputs/ 合计** | **≈ 11.17 MB**（≤ 25 MB 目标；db 为 `journal_mode=DELETE` 导出版，无 WAL/SHM 附属文件） |
| 用例目录合计（含 db） | ≈ 11.2 MB |

若需进一步瘦身：可只保留 15 题涉及的表/列（本库 3 表全用上，裁剪收益有限）；
不建议 VACUUM 之外再压缩（保持官方库字节等价便于复核）。

## 10. 来源与许可证

| 项 | 值 |
|---|---|
| 来源 | **BIRD**（BIg Bench for LaRge-scale Database Grounded Text-to-SQL Evaluation）· `mini_dev` split · `db_id=california_schools` |
| 官网（榜单） | <https://bird-bench.github.io/> |
| 论文 | <https://arxiv.org/abs/2305.03111> |
| 数据许可 | **CC BY-SA 4.0**（署名—相同方式共享） |
| 读取日期 | **2026-10-22** |
| 选取 | 该库 30 题中取 15 题：5 challenging（28/36/62/83/87）+ 7 moderate（12/23/24/25/26/27/31）+ 3 simple（5/11/17） |
| 是否改写 | **题面改写**：中文重写（`question_zh` / `evidence_zh`），英文原文保留在 `questions.json` 供溯源；**SQL 未改写**（15 条 gold SQL 与官方一致）；**数据未改写**（sqlite3 `backup` 等价重导出，去掉 WAL/SHM 附属文件，内容与官方 db 一致） |
| 判分器来源 | 自建实现（BIRD exec-accuracy 口径，非官方脚本移植）；`checker.py` 文件头已注明 |
| 再分发 | 本用例以 CC BY-SA 4.0 同源共享（含 `inputs/` 数据库与 `truth.json` 的 gold SQL） |

## 11. 难度论证（为什么是 medium）

1. **不能靠单一技能通关**：15 题里 12 题必须结果集一致，覆盖 JOIN 键选择（`CDSCode`/`cds`
   两种命名）、聚合口径（`AVG`/`SUM/COUNT`/`MAX`）、`GROUP BY … HAVING`、窗口函数、
   `LIMIT` 偏移（`LIMIT 9, 2` 取第 10/11）、日期字符串（`strftime('%Y', OpenDate)`）、
   比例 vs 百分数（q62 `*100` 与 0.18 阈值）、`IS NULL` 过滤 —— 任一类口径错就丢分；
2. **官方 evidence 有坑**：`Virtual = 'F'` 表示「纯虚拟」、`Charter = 0` 表示非特许、
   百分数口径 `*100`、`GROUP BY` 后 `HAVING SUM/COUNT` 等，均需按 evidence 逐条对齐；
3. **量化区分度**：只有 SQL 写法稳、schema 熟、口径读得准的产品能稳定 ≥ 12/15；
   「会写 SQL 但按直觉猜列/漏 JOIN/漏 DISTINCT/忘 `*100`」的产物落在 8–11 题（0.53–0.73），
   正好被 0.8 达标线卡住；本批 r1024 探针实测同库 15 题在 Codex/DSH 上可跑通，
   适合作为「中等偏上」区分度用例。
4. **与同批用例互补**：`corpus-squeeze` 考迭代闭环、`jielong-fullchain` 考对话内多约束，
   本题考「陌生库 + 多题 + 结果集口径」的一次性正确率。