# BIRD q26/q27 独立只读复核意见

时间：2026-10-24；复核人：execution-graders（本次未参与 BIRD checker/题面/gold 修改）。

## 结论摘要

1. **q26 是实质题面—gold 合同冲突，不宜将当前该题失分直接解释为模型理解错误。** 中文要求“免费或减价餐”，schema 分别提供 Free Meal 与 FRPM 两列，gold 却筛选 Free Meal。数据库上两者确有差异：5 行 vs 6 行。八场提交都符合 FRPM 反事实答案。
2. **q27 的主要差异是学校总体范围与缺 SAT 记录保留政策，不是去重。** gold LEFT JOIN 得 8574 行、8217 个不同结果行。三个 A 组产品首跑及四次重复提交均为 INNER JOIN 的749行；豆包为附加补零匹配与 rtype 条件的813行。即使 gold、pred 双方去重，八场仍全部不等。
3. **q27 可确认为范围口径欠明确，不宜与 q26 一起定性为已经证明的 gold 错误。** “对……学校列出学校名称、SAT写作平均分”可以合理解释为保留全部符合日期条件的学校，缺分数给 NULL（LEFT）；也容易被理解成有 SAT 记录的学校（INNER）。题面仅对电话写了“有则给”，没有明确规定无 SAT 记录的学校是否保留。应先澄清题意，再决定是否修订/接受多答案；不能仅因四款都写 INNER 就宣布它对。
4. 八场全量独立 SQL 重算均与当前复算收据一致。**剔除 q26 的14题敏感性、或仅将 q26 gold 的 Free 改为 FRPM 的15题反事实，八场 headline 均不翻转**。这是局部敏感性结论，不是证明其余14题无缺陷，也不是新模型运行。

## 方法与只读保证

- 只读取中文题面、schema、本地 gold SQL，以及现有复算收据中的八个 BIRD `source`；**未导入或调用 numeric 作者代码、项目 checker 或其自测**。没有以作者提供的计算结果作为计算输入。
- 使用自写标准库 SQLite 执行器，数据库 URI 为 `mode=ro&immutable=1`，附 `query_only=ON` 与只允许 SELECT/READ/FUNCTION/RECURSIVE 的 authorizer。独立实现 NULL/字符串/6位浮点归一与 `Counter` 行多重集比较。
- 每场实际读入15条答案，核对15个唯一 question_id，逐题执行全部15个 gold/pred，而非只按既有正确题数做加减。计算完成后才与既有收据交叉检查。
- 数据库、题面、truth、复算收据与八份答案的12个文件哈希，执行前后全部不变。最初独立复核仅写仓外；Lead将该意见及程序导入本专属派生目录并重跑，**不写原始现场、gold及原复算结果，不运行模型/GUI，不触及其他session。**
- 可复跑脚本：[independent-review.py](<independent-review.py>)；结构化结果：[independent-results.json](<independent-results.json>)；命令输出：[independent-review.log](<independent-review.log>)。本次执行 **exit=0**，八场收据全部匹配，12项只读哈希检查全部通过。

```bash
python3 -B 5-评测报告/复算/2026-10-24/bird-semantic-review/independent-review.py
```

## q26：确定的列含义冲突

题面出处：[questions.json:121–134](<../../../../2-用例/bird-ca-schools-15/inputs/questions.json#L121-L134>)。

- 中文：“5-17 岁**免费或减价餐**人数超过800”。英文溯源也写“free or reduced price meals”，但原文年龄有15-17的笔误，本复核只按本地操作口径5-17审查。
- schema 明确将 [Free Meal Count 与 FRPM Count 分列](<../../../../2-用例/bird-ca-schools-15/inputs/schema.sql#L28-L32>)。
- [本地 gold](<../../../../2-用例/bird-ca-schools-15/truth.json#L74-L77>) 的筛选却是 `Free Meal Count (Ages 5-17) > 800`。题面没有将“免费或减价”特别重新定义成 Free Meal。
- 仅将 gold 这一列替换成 `FRPM Count (Ages 5-17)`，其余连接、县、学校类型、输出列不动：**5行→6行**。新增 `North Monterey County High`：CDSCode=`27738252730034`，Free=**611**，FRPM=**804**，完整地址为 `13990 Castroville Boulevard / Castroville / CA / 95012-9749`。所以不是 SQL 表达式不同但结果等价，也不是四舍五入或边界800造成的假差异。
- 八份提交均返回该 FRPM 六行，多重集精确等于此反事实 gold。部分提交用 frpm 的 County Name、部分用 schools.County，在本固定数据库上均结果相等。

**建议**：原 gold 与历史原分数保留溯源，不直接覆盖；主报告将 q26 标为题面/gold不一致，并并列给剔除敏感性。若决定按中文发布新版题，应另有版本化修订，不能将“保留官方未改写 SQL”的来源声明当作语义正确性证明。本复核未联网核实 BIRD 原始发布内容，只核验仓内实际合同。

## q27：缺记录范围与重复行必须分开讨论

题面：[questions.json:137–148](<../../../../2-用例/bird-ca-schools-15/inputs/questions.json#L137-L148>)；[gold SQL](<../../../../2-用例/bird-ca-schools-15/truth.json#L78-L81>)。

### 1. LEFT 与 INNER 的实测差异

| 独立执行事实 | 数量 |
|---|---:|
| 日期条件命中的学校数 / 不同 CDSCode 数 | 8574 / 8574 |
| gold LEFT JOIN 结果行 | 8574 |
| 有精确 cds 匹配的 INNER JOIN 行 | 749 |
| 没有 SAT 行匹配的学校 | 7825 |
| 有 SAT 匹配、但 AvgScrWrite 本身为 NULL | 295 |
| gold 中写作分数为 NULL 的行 | 8120 |

七场 A 组现有提交的749行**逐行等于精确 INNER 反事实**：相对于 gold 缺7825行，没有额外行。它们不是漏掉几个重复显示的学校，而是排除了全部无精确 SAT 记录的学校。

豆包813行不等于上述 INNER。其 SQL 增加 `s.CDSCode = '0' || st.cds` 的补零匹配，并要求 `st.rtype='S'`；对 gold 多重集，缺7800行、额外39行（重合774行）。因此不能把豆包与另外三款解释成完全相同的 JOIN 失误，也不能把补零匹配直接判为“更符合真实数据”；这已经改变本地 gold 所定义的精确连接关系。

把 gold 的 `strftime('%Y', …)` 换成提交采用的 `OpenDate > '1991-12-31' OR ClosedDate < '2000-01-01'`，保留 LEFT JOIN 后，本数据库输出完全相同。**本次观测中日期谓词不是主因**；此等价性不外推到有非规范日期的其他数据库。

### 2. 8574→8217 去重的实际含义

- gold 有 **238组**重复的三列显示结果，共多出 **357行**；原始行与归一后 distinct 数都为8217，不是 strip/round 意外合并造成的。
- 这238组的 AvgScrWrite **均为 NULL**。学校主键并未重复：不同 CDSCode 的学校可能同名，且输出中不包含 CDSCode，投影后 `School / NULL / Phone` 恰相同。例如多所 `Community Day` 有不同 CDSCode，显示为相同 `Community Day / NULL / NULL`；`Washington Elementary / NULL / NULL` 出现15次。
- 因而这些行不是 JOIN 一对多导致的脏重复，也不是仅按显示三列能区分的同一学校重复。普通 SQL 未指定 DISTINCT 时保留这种重复是合理的；当前 [truth 的归一契约](<../../../../2-用例/bird-ca-schools-15/truth.json#L12-L13>) 明确采用多重集。不能在看到多行同名后自动断言 gold 应去重。
- **对现有八场评分影响为零**：七场 A 输出749个不同结果行，去重后依然缺 `8217-749=7468` 个不同 gold 行；豆包813个不同结果行，去重后仍缺7443个、额外39个。八场在 set 与 bag 下都 FAIL，不会因此加一题。
- 去重策略确实影响另一个反事实：如果提交是“完整 gold LEFT 查询加 DISTINCT”，set 比较会放过，而现行 bag 会因少357次出现判错。这说明应明示重复行策略，但**不是当前八场 q27 失分的因果解释**。本复核不声称旧 checker 曾采用 set 口径。

**建议**：q27 文案明确写成“保留所有符合日期条件的学校，包括无SAT记录者，分数记NULL；不同学校即使三列相同也保留重复行”，或另行约定只统计有 SAT 的学校。未澄清前，主报告可将其列为“范围口径欠明确，gold采用LEFT”，不要把“七场INNER都错”机械归因为纯粹模型能力问题，也不要未经裁定直接把 INNER 全接纳为标准答案。

## 八场分数敏感性（仅反事实，不改正式原分）

现行15题阈值0.8，即至少12题正确。剔除q26后，以其余14题重新计算准确率、仍以0.8为阈值，至少12题正确；原提交仍保有完整15题交付，不把敏感性假设变成缺题交付失败。FRPM反事实仅改 q26 gold 的一列，其余14题判据全部保持。

| 产品/轮次 | 现行15题 | 剔除q26：14题 | q26改FRPM：15题 | headline变化 |
|---|---:|---:|---:|---|
| Codex 首跑 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |
| DSH 首跑 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |
| WorkBuddy 首跑 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |
| 豆包 首跑 | 9/15，60.00，0 | 9/14，64.29，0 | 10/15，66.67，0 | 无 |
| Codex r2 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |
| Codex r3 | 12/15，80.00，1 | 12/14，85.71，1 | 13/15，86.67，1 | 无 |
| DSH r2 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |
| DSH r3 | 13/15，86.67，1 | 13/14，92.86，1 | 14/15，93.33，1 | 无 |

各格末项为reward。三种口径均首跑3/4通过、四次重复4/4通过、八场合计7/8；原始分数与 headline 不作覆盖。分母变化的weighted不是同一尺度，不应将差值当作性能提升。该敏感性没有修复或豁免q27，也未审定其他13题。

## 八场 source 定位

来源索引：[results.json](<../../../../5-评测报告/复算/2026-10-24/results.json>)。逐份SQL已读取，完整run_id/source/答案哈希均在本独立结构化结果中。

- [Codex首跑答案](<../../../../3-表现现场/r1025-candidates/bird-ca-schools-15__codex/answers.jsonl>)
- [DSH首跑答案](<../../../../3-表现现场/r1025-candidates/bird-ca-schools-15__dsh/answers.jsonl>)
- [WorkBuddy首跑答案](<../../../../3-表现现场/r1026-desktop-15/runs/workbuddy/bird-ca-schools-15/answers.jsonl>)
- [豆包首跑答案](<../../../../3-表现现场/r1026-desktop-15/runs/doubao/bird-ca-schools-15/answers.jsonl>)
- [Codex r2答案](<../../../../3-表现现场/r1028-repeats/runs/codex__bird-ca-schools-15__r2/workspace/answers.jsonl>)
- [Codex r3答案](<../../../../3-表现现场/r1028-repeats/runs/codex__bird-ca-schools-15__r3/workspace/answers.jsonl>)
- [DSH r2答案](<../../../../3-表现现场/r1028-repeats/runs/dsh__bird-ca-schools-15__r2/workspace/answers.jsonl>)
- [DSH r3答案](<../../../../3-表现现场/r1028-repeats/runs/dsh__bird-ca-schools-15__r3/workspace/answers.jsonl>)

## 不可外推事项

- 八场是4产品首跑加 Codex/DSH 重复，非平衡全产品重复实验；不能由7/8通过或上述差异给 Harness 因果排名。
- SQL单库执行等价不等于所有可能数据库上的逻辑等价；本复核未用生成数据库反例证明其他题SQL的普适正确性。
- q26 修订后现有八场均加一题，不表示以后模型均正确；headline未翻转不表示这个合同缺陷无关紧要。
- 本意见独立验证 q26/q27 局部结论与八场敏感性，不替代全15题语义复核、数据来源审计或 grader 安全性证明。
