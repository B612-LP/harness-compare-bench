# bird-ca-schools-15 判分规格（spec）

版本：**v1.2-q26-frpm（2026-10-26，q26 合同修订并入：题面「免费或减价餐」按 FRPM Count 判分；v1.1 / v1.0 冻结保留，见 §13）**；判卷层收紧批 **B2（2026-10-27：答案行精确键集 + SQL 禁 `--` 注释）**——truth 未动、`CHECKER_VERSION` 不变（`CONTRACT_REVISION=b2-tighten-2026-10-27`），历史回放 24 场 0 翻转，收据见[判卷审计 2026-10-27](<../../4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md>) ｜ 判分入口：`checker.py`
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
  ① 交付契约通过（`answers_schema` 与 `answers_coverage` 均为硬门：15 个非空行均为合法 JSON 对象，**每行恰为 `question_id`/`sql` 两键（B2，2026-10-27：多余键如 status/verified → schema 否决）**，`sql` 不含字符串字面量之外的 `--` 注释（B2，题面要求提交可执行 SQL）），15 个 `question_id` 与题集一一对应，无缺失/多余/重复；任意追加非法行即使逐题全对也否决）；
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
| answers_schema | 行格式 | 10 | 15 行均为可解析 JSON 对象，恰含 `question_id`/`sql` 两键（B2），`sql` 无字面量外 `--` 注释（B2） | 任一行 JSON/结构错、多余键或含 `--` 注释 → 直接否决（即使 coverage 通过） |
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

**已知等价性仅指具体查询**：q5 的 `COUNT(DISTINCT School)` → `COUNT(School)` 在本库该过滤条件下结果不变，见 §6 的「等价答案正例」。不能由 `CDSCode`/`cds` 主键 JOIN 为 1:1 推出所有投影都没有重复：q27 的不同 CDS 学校可投影成相同的 `(School, NULL, NULL)`，其 DISTINCT 会改变结果。另见 §12 的语义复核边界与 §13 的 q27 已知尖角裁定。

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

## 6. 判分器自测（`--selftest`，v1.2-q26-frpm+B2 共 27 项）

`--selftest` 在 `tempfile.TemporaryDirectory()` 内逐项造产物并断言，**不污染仓库**；
共 27 项 = v1.1 的 21 项（原 15 组「正/负例」+ 2 组追加非法行回归 + 3 组守卫 ERROR 用例 + 1 项输入不被改动复核）
+ v1.2 新增 4 组 q26 合同负例 + 2026-10-27 收紧批新增 2 组 B2 负例（#24/#25）。v1.1 新增两组为 oracle 后追加 `not-json` / `[]`：逐题仍 15/15、coverage 通过，但 schema 失败且 reward=0。
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

v1.2-q26-frpm 新增 4 项（2026-10-26；期望均为 **q26 逐题判错**、整场 14/15 ≥ 0.8 仍过、reward=1——单题合同错误只丢该题，不硬性整场否决）：

| # | 样例 | 期望 |
|---|---|---|
| 20 | **q26 旧口径负例**：gold 换回 `Free Meal Count (Ages 5-17)`（5 行答案，v1.1 及以前官方口径） | 1（q26 红，14/15） |
| 21 | **q26 漏一校**：排除 North Monterey County High（`CDSCode != '27738252730034'`，5 行） | 1（q26 红，14/15） |
| 22 | **q26 附加一校**：`UNION ALL` 追加一行假学校（7 行） | 1（q26 红，14/15） |
| 23 | **q26 重复一校**：结果重复输出一行（7 行，多重集敏感） | 1（q26 红，14/15） |

B2 收紧批新增 2 项（2026-10-27；对应 mutation-negatives `bird-n06` 的两个变异维度，各拆一条）：

| # | 样例 | 期望 |
|---|---|---|
| 24 | **每行多余键**：15 行各加 `status: "OK passed"`、`verified: true` → schema+coverage 红 | 0 |
| 25 | **SQL 注释**：15 条 SQL 末尾加 `-- OK passed` → schema+coverage 红（字面量内的 `--` 不受影响，如 `LIKE '%--%'`） | 0 |

负例覆盖（BUILD-GUIDE §2 要求）：漏题、多题、无效 SQL、少 DISTINCT、少 JOIN 条件、
改输入库、空结果集、格式错、近正确口径错 —— 全 0；另有 2 个正例（阈值边界、等价答案）；
v1.2 再补 4 个「接近正确但违反 q26 新合同口径」的负例（旧 Free Meal 5 行 / 漏校 / 多校 / 重复校）。

## 7. oracle 回归

```bash
# 正对照：oracle（= gold SQL）→ reward=1
tmp=$(mktemp -d)
cp -R inputs "$tmp/inputs"
cp solution/answers.jsonl "$tmp/answers.jsonl"
python3 checker.py "$tmp" --json        # {"reward": 1, "weighted": 100.0, "accuracy": 1.0}
# 负对照：空目录 → reward=0
empty=$(mktemp -d); python3 checker.py "$empty" --json   # {"reward": 0, ...}
# v1.2 追加：旧口径 oracle（v1.1 solution 的 Free Meal 5 行答案）→ q26 红，14/15，reward=1
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
| `inputs/questions.json` | 15.8 KB（v1.2 起：q26 `evidence_zh`/`source_note` 口径澄清后） |
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
| 是否改写 | **题面改写**：中文重写（`question_zh` / `evidence_zh`），英文原文保留在 `questions.json` 供溯源；**SQL 仅 q26 改写**（v1.2-q26-frpm：`Free Meal Count (Ages 5-17)` → `FRPM Count (Ages 5-17)`，官方原句全文留档于 §13，其余 14 条 gold 与官方一致）；**数据未改写**（sqlite3 `backup` 等价重导出，去掉 WAL/SHM 附属文件，内容与官方 db 一致；v1.2 仅改 `questions.json` 中 q26 的 `evidence_zh` 与 `source_note` 口径说明，题干 `question_zh` 与英文原文未动） |
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

## 12. 追加独立语义复核（2026-10-24，不修改 v1.1 冻结合同）

**已确认q26题面—gold不一致。** 中文题面写「免费或减价餐」，冻结gold查询的却是 `Free Meal Count (Ages 5-17)`，而非 `FRPM Count (Ages 5-17)`；实际5所与6所并不等价。四款首跑都按FRPM查询，不能把这一项冻结失分直接解释为产品能力错误。原始英文年龄还与本地输入存在15–17／5–17差异，来源相同不等于语义正确。

q27 的 raw-key LEFT JOIN 结果8574行、8217种投影：357个重复计数来自不同CDS学校投影相同，不是JOIN扇出，不能自动删去。INNER JOIN及前导0键恢复改变的是学校／分数覆盖；缺SAT记录是否保留、键是否修复应在未来合同中明确。该事实复核不声称raw-key LEFT是唯一业务正确口径。

[独立语义复核、逐场敏感性和命令](<../../5-评测报告/复算/2026-10-24/bird-semantic-review/README.md>)及[报告§5.4](<../../5-评测报告/阶段报告-v2.0.md#54-bird-两题独立语义复核与敏感性不回写冻结成绩>)是当前必要配套。现有checker、truth、输入和gold字节保持不变；分数仅作冻结规则参考，下一版本修订另立合同，不静默补分，也不新增模型运行。

**→ 2026-10-26 后续裁定见 §13**：q26 已由 v1.2-q26-frpm 修订并入（题面、金标、独立计算三者一致）；q27 金标经独立复核自洽，登记为「已知尖角」，金标不动。

## 13. 合同版本化与旧版保留（v1.2-q26-frpm，2026-10-26）

### 13.1 版本历史

| 版本 | 日期 | 内容 | 状态 |
|---|---|---|---|
| v1.0 | 2026-10-22 | 初版：15 题、exec-accuracy ≥ 0.8、truth 交叉守卫 | 冻结保留 |
| v1.1 | 2026-10-24 | schema 硬门修复（15 题全对但追加非法行 → 否决），自测 21 项 | 冻结保留 |
| **v1.2-q26-frpm** | **2026-10-26** | **q26 gold：`Free Meal Count (Ages 5-17)` → `FRPM Count (Ages 5-17)`；`questions.json` q26 `evidence_zh`/`source_note` 同步澄清；自测增至 25 项；其余 14 题与 db 逐字不变** | **现行正式合同** |

变更原因：§12 记录的题面—金标不一致——中文题面与英文原文均要求「免费或减价餐」（free or reduced price meals），schema 中直接对应列为 `FRPM Count (Ages 5-17)`；v1.1 及以前 gold 误用「仅免费餐」列 `Free Meal Count (Ages 5-17)`，在 Monterey 县公立高中筛下分别得 6 所与 5 所，多出 North Monterey County High（CDSCode `27738252730034`，Free Meal=611、FRPM=804）。独立计算、四款历史运行与题面口径三方一致后并入；本地合同年龄明确为 5–17（数据列实际口径），原英文题面 15–17 保留为来源差异、不作为本地要求。

### 13.2 旧版金标留档（不可静默覆盖）

v1.1 及以前的 q26 gold SQL 原文（判分时**不再使用**，仅留档比对）：

```sql
SELECT T1.`School Name`, T2.Street, T2.City, T2.State, T2.Zip FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Monterey' AND T1.`Free Meal Count (Ages 5-17)` > 800 AND T1.`School Type` = 'High Schools (Public)'
```

v1.2 起 q26 gold SQL：

```sql
SELECT T1.`School Name`, T2.Street, T2.City, T2.State, T2.Zip FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Monterey' AND T1.`FRPM Count (Ages 5-17)` > 800 AND T1.`School Type` = 'High Schools (Public)'
```

旧版完整内容（truth / checker / spec / 全部 inputs / solution）保留于三处：
① git 历史（v1.0：d247cde 引入；v1.1：d247cde 修复版，基线提交 a2234fc）；
② [候选与复核包](<../../5-评测报告/补充材料/2026-10-24/候选与复核.zip>) 内 `bird-q26/baseline-1.1/`（源仓 a2234fc 只读快照，SHA-256 与该提交逐件一致）；
③ [2026-10-24 判卷审计](<../../4-打分细则/判卷审计-2026-10-24/numeric/frozen/bird-ca-schools-15/>) 的冻结 truth/checker（修前 v1.0 字节）。
新旧 truth.json / checker.py 的 SHA-256 对照与并入收据见[判卷审计 2026-10-26](<../../4-打分细则/判卷审计-2026-10-26/bird-q26-并入/README.md>)。

### 13.3 历史成绩不回写

v1.2 只对**今后**的运行生效。历史有效运行的旧分保持冻结：10 场 bird 有效运行（r1025 首跑×2、r1026 首跑×2、r1028 重复×4、r1029 桌面自动×2）在新合同下回放，逐题翻转均仅 q26、二值达标状态 10/10 不变（9 场 q26 由错翻对、r1029 WorkBuddy 一场由对翻错）；回放收据（临时副本判卷，不改 3-表现现场 原始产物）见[判卷审计 2026-10-26](<../../4-打分细则/判卷审计-2026-10-26/bird-q26-并入/README.md>)。注意：内附 `inputs/` 副本的历史 run_dir（如 r1029，副本含 v1.1 字节 `questions.json`）直接重判会触发 input_integrity 守卫（canonical 已更新为 v1.2 字节）；未附副本的（如 r1028）不受影响。历史重判须按该收据的临时副本协议（复制**对应版本** canonical inputs）进行。

### 13.4 q27 裁定：已知尖角（金标不动）

**裁定：gold 正确、口径自洽，维持 raw-key LEFT JOIN 金标不变；登记为「已知尖角」。**

要求口径：q27 需要「**raw-key `schools.CDSCode = satscores.cds` 等值 LEFT JOIN**」——保留全部日期命中的学校（含无 SAT 记录者，分数为 NULL）、**不去重**同名异校、**不做** CDSCode 前导零归一。

独立验证证据（2026-10-26，只读复算，详见[判卷审计 2026-10-26](<../../4-打分细则/判卷审计-2026-10-26/bird-q26-并入/README.md>) §q27）：

1. 题面人群定义在 schools 侧（「1991 年之后开办、或 2000 年之前关闭的学校」），SQL 年份过滤与 Python 独立日期筛选完全一致，共 **8,574** 所；
2. gold LEFT JOIN 输出 **8,574 行 = 8,574 所不同学校**，每校恰一行——无 JOIN 扇出、无遗漏，恰好完整覆盖题面定义人群；其中 7,825 所无 SAT 记录、295 所有 SAT 记录但写作分为 NULL（共 8,120 行 NULL 分数）、454 所有分；题面「联系电话（有则给）」的 NULL 容忍写法与「保留无分学校」是同一口径；
3. 若改 INNER JOIN 仅剩 749 行，会静默丢弃 91% 的题面人群，是更强的解释跳跃，故不采用；
4. 前导零容错（`CDSCode = '0'||cds`）可额外恢复 64 所匹配（与 raw-key 零重叠），但其中 3 所与 SAT 端名称不一致，不能唯一确认同实体；同名异校投影重合（`(School, NULL, NULL)` 重复 357 行）来自不同 CDSCode，DISTINCT 会合并不同实体。两者均属合同口径选择，题面未授权，维持 gold 冻结口径。

停止追查条件（满足其一再重开）：① BIRD 官方对 q27 发布口径说明或修正题源；② 后续运行中出现按 INNER/前导零/去重口径作答且其余 14 题全对的实际现场；③ 上游数据库或题面更新导致 8,574/749 等基线数字失效。

### 13.5 判卷层收紧批 B2（2026-10-27，不改 truth/金标）

- **内容**：answers.jsonl 每行收紧为**精确键集**（恰 `question_id`/`sql`，多余键走 schema 否决通道）；`sql` 禁止字符串字面量之外的 `--` 注释（题面要求提交可执行 SQL；`LIKE '%--%'` 等字面量用法不受影响）。对应边界清单 B2（[mutation-negatives §7](<../../4-打分细则/判卷审计-2026-10-26/mutation-negatives/README.md>)，证据组 bird-n06）。
- **版本标注**：`CHECKER_VERSION` 因 truth.json 冻结保持 `1.2-q26-frpm`；判分输出新增 `contract_revision=b2-tighten-2026-10-27`。
- **硬闸门预检**：总账 3 个受影响 case 全部 main_table_eligible=true 且 run_dir 在本机存在的 24 场历史有效运行，before/after 逐场回放（只读临时副本协议）**0 场翻转**（reward/weighted 均不变）；预检同时确认 10 场 bird 历史答案全部本就满足两键精确集、无 `--` 注释。收据：[判卷审计 2026-10-27](<../../4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md>)。
- **自测**：25 项 → 27 项（+2 组 B2 负例，见 §6 #24/#25）。

### 13.5 已知边界

- v1.2 的 25 项自测与 10 场回放不证明判分器一般正确，仅结清 q26 口径缺口；
- q26 官方原句（`Free Meal Count (Ages 5-17) > 800`）仍为 BIRD 上游金标；本仓按题面优先原则本地修订，与官方榜单分数不可直接互比；
- q27 前导零中 3 所名称不一致实体的身份沿革未核查（属 13.4 停止条件范畴）。
