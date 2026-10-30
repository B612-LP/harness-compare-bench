# BIRD q26/q27 独立语义复核（2026-10-24）

**结论：原“未独立复核”的证据缺口可结清，但不等于合同已经修好。** q26 已确认中文题面与 gold 使用的字段不一致，不应把本批 q26 的不匹配当作模型能力扣分证据；q27 的人群、缺失分数、标识键归一规则仍需下一合同版本明确。冻结参考分保留，敏感性与反事实都不是正式新评分。

仅离线只读分析；**新增模型/agent 运行 0、GUI 运行 0**。SQLite 使用 `mode=ro` 和 `PRAGMA query_only=ON`。不导入 checker；先取三张基础表，在 Python 中独立筛选、按主键构造关联并投影，再与独立 SQL 对照；不是“执行 gold 等于它自己”。8 场所有 15 题另行只读计算，逐题结论与冻结参考分完全一致，这一步只验证冻结执行结果，不证明其余 13 题语义正确。

## 1. 产物、复跑与收据

- [review.py](<review.py>)：可复跑独立算法与所有对照 SQL。
- [results.json](<results.json>)：完整机器结果；含源码/输入/8 场答案/既有复算结果的前后 SHA-256、11 项断言、每场 15 题命中与三轨敏感性、238 个重复投影组的主键溯源、64 条前导零诊断。
- [review.stdout.txt](<review.stdout.txt>)：简明执行收据，**11/11 断言通过，exit 0**。
- [upstream-q26-q27.json](<upstream-q26-q27.json>)：仅 q26/q27 两条本地历史题源摘录及完整来源文件 SHA-256，复跑不需要保留 `/tmp` 题源。不复制全数据集、不含凭据。数据摘录沿用BIRD来源及CC BY-SA 4.0，来源说明见[原用例规格](<../../../../2-用例/bird-ca-schools-15/spec.md#10-来源与许可证>)。
- [Lead补强验收程序](<../review_acceptance.py>)与[23/23机器收据](<acceptance.json>)：双方法三轨一致、374个历史文件及规则指纹不变、两组案例的产物／严格分数／四得一失、引用与未知状态均实际核对。

从仓库根目录执行（根目录由脚本位置自动推导，不需要原机器路径）：

```bash
python3 -B 5-评测报告/复算/2026-10-24/bird-semantic-review/review.py
python3 -B 5-评测报告/复算/2026-10-24/bird-semantic-review/independent-review.py
```

已另外测试题源路径不存在的离线回退，仍 11/11、exit 0：

```bash
python3 -B 5-评测报告/复算/2026-10-24/bird-semantic-review/review.py \
  --official-source no-upstream-required.json
```

该离线回退命令故意指定不存在的题源，只从已保留的两条摘录复核，不依赖 `/tmp`、不联网；默认命令也只读摘录。gold/checker/inputs、8份答案与既有复算结果的 SHA-256 前后全部一致。spec文档仅追加本次已发现的语义警告，非修改gold或冻结计分合同。

本目录由Lead将已完成的仓外独立草稿导入，补齐可克隆路径与SELECT authorizer后实际重跑；[另一套独立SQL复核意见](<independent-review.md>)、[程序](<independent-review.py>)和[机器结果](<independent-results.json>)分别记录八场重算与12项只读哈希核对，不依赖本review算法。二者都不是新模型运行。

## 2. 确定事实：q26

题面来源：[中文/英文/evidence:120–134](<../../../../2-用例/bird-ca-schools-15/inputs/questions.json#L120-L134>)；gold：[truth:74–76](<../../../../2-用例/bird-ca-schools-15/truth.json#L74-L76>)；列定义：[schema:23–32](<../../../../2-用例/bird-ca-schools-15/inputs/schema.sql#L23-L32>)。

1. 中文要求“**5–17 岁免费或减价餐人数 >800**”，gold 实际使用 `Free Meal Count (Ages 5-17)`，而 schema 同时存在另一个 `FRPM Count (Ages 5-17)`。原英文题面也写 `free or reduced price meals`，但年龄写 **15–17**，不是数据列的 5–17；evidence 只解释地址，不授权将 FRPM 换成 Free Meal。
2. 独立按学校主键关联、按 Monterey 县及 `High Schools (Public)` 筛选，共 16 所候选：Free Meal>800 得 **5 所**；FRPM>800 得 **6 所**，恰好多出 **North Monterey County High**（CDSCode `27738252730034`，Free Meal=**611**，FRPM=**804**）。两组各自无重复投影，无 JOIN 扇出。
3. 四款首跑和 CLI 四场重复（共 8 场）的 q26 均输出同一组 FRPM **6 行**：冻结 gold 下全失败，FRPM 单题反事实下全通过。
4. 本库该组学校 `frpm.School Name` 与 `schools.School` 全部相同；`frpm.County Name='Monterey'` 与 `schools.County='Monterey'` 的学校集合无差异。该 6 所学校 Street/City/State/Zip 与相应 Mail* 四字段也无差异。因此这批 q26 的一行之差来自 **FRPM vs Free Meal**，不是 School Name、县字段、地址字段或 DISTINCT。

**口径解释**：按中文“免费或减价餐”与列名，FRPM 是直接相符的业务映射。沿用官方 SQL 可以是“与历史基准兼容”的规则，但不能据此把中文合同已满足的答案解释为能力错误。

## 3. 确定事实：q27

题面/evidence：[questions:136–148](<../../../../2-用例/bird-ca-schools-15/inputs/questions.json#L136-L148>)；gold：[truth:78–80](<../../../../2-用例/bird-ca-schools-15/truth.json#L78-L80>)。三表主键均唯一：schools **17,686**、frpm **9,986**、satscores **2,269** 行。

Python 独立按完整年份（开办年份>1991 或关闭年份<2000）筛出 **8,574 个不同 CDSCode**；数据中没有非空非法日期，SQL 年份筛选与该 Python 筛选完全一致。

| 关联/投影变体 | 行数 | 去重后行数 | score NULL | score 非 NULL |
|---|---:|---:|---:|---:|
| raw-key LEFT（冻结 gold） | 8,574 | 8,217 | 8,120 | 454 |
| raw-key INNER | 749 | 749 | 295 | 454 |
| 前导零容错 LEFT | 8,574 | 8,217 | 8,081 | 493 |
| 前导零容错 INNER | 813 | 813 | 320 | 493 |

### 为什么重复？不是 JOIN 扇出

- raw-key LEFT 每个源 schools.CDSCode 恰好一行；无匹配 SAT 的学校 **7,825** 所，另有 SAT 行但写作分 NULL 的 **295** 所，因此总计 **8,120** 个 NULL 分数。
- **238 个投影重合组**共涉及 **595 所不同主键学校**；去重会移除 **357 行**。这些组均无 exact SAT 匹配，且 score 和 Phone 都为 NULL。学校同名，投影又不含主键/县/学区，于是不同学校形成相同 `(School,NULL,NULL)`。
- 例：`Juvenile Court Schools` 的 Alameda 与 Solano 两所不同 CDSCode 均投影为同一三元组；`Amador Valley Adult Education` 也有不同 CDSCode。完整组及主键在机器结果中保留。因此 DISTINCT **不是**简单修复 JOIN 重复，而是在合并不同实体。
- 八场 q27 都不等于 LEFT，也不等于 `LEFT DISTINCT`。Codex/DSH/WorkBuddy 首跑及四场 CLI 重复均恰好等于 raw-key INNER **749 行**；豆包首跑等于前导零容错 INNER **813 行**。仅去重不会使任何一场通过冻结 gold。

### 前导零与 rtype 是两个不同因素

豆包使用 `(schools.CDSCode=satscores.cds OR schools.CDSCode='0'||satscores.cds)` 并要求 `rtype='S'`。raw-key 已匹配的 749 行本来全为 S，故 rtype 筛选对本题行数无影响。前导零额外恢复 **64** 个学校匹配，其中 **39** 个有非空写作分；64 个均 rtype=S，**61** 个学校名称与 SAT 名称逐字一致，其余 3 个名称存在差异，不能把64条全当已核实的业务同实体。该容错在本库没有产生多匹配扇出。

**口径解释**：题面“对这些学校列出分数”可按“保留所有日期命中的学校，缺分数给 NULL”理解（LEFT）；也可能按“有 SAT 记录/有写作分的学校”理解（INNER 或过滤非空，且二者也不相等）。中文只明确联系电话“有则给”，没有明确缺 SAT/缺分数的人群规则。原始键是否应保留前导零、是否按学校实体去重也未声明。官方 raw-key LEFT 是确定的冻结执行规则，**不据此宣称它是唯一业务正确口径**；也不据此认定 INNER/补零一定正确。

## 4. 八场三轨敏感性（均不覆盖旧分）

第一轨为全15题**冻结参考分**，不再把 q26 扣分解释为能力错误。第二轨仅剔除 q26，14 题仍按旧规则和 0.8 阈值计算。第三轨只把 q26 对照结果换成 FRPM 6 行，是**非正式反事实**，不是补发正式得分；q27 及其余题不变。

| 场次 | 冻结15题 | 剔除q26：14题敏感性 | 仅q26换FRPM：15题反事实 |
|---|---|---|---|
| Codex 首跑 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |
| DSH 首跑 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |
| WorkBuddy 首跑 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |
| 豆包首跑 | 9/15 · 60.00 · 不过 | 9/14 · 64.29 · 不过 | 10/15 · 66.67 · 不过 |
| Codex 重复2 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |
| Codex 重复3 | 12/15 · 80.00 · 过 | 12/14 · 85.71 · 过 | 13/15 · 86.67 · 过 |
| DSH 重复2 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |
| DSH 重复3 | 13/15 · 86.67 · 过 | 13/14 · 92.86 · 过 | 14/15 · 93.33 · 过 |

八场三轨二值通过/失败均不变。该敏感性仍受 q27 及其他未独立复核题目的合同口径限制，不代表14题已经获完整语义认证，更不能推出产品因果排名。

## 5. 题源核对与尚未知

本地历史题源为 `/tmp/tb-probe/bird/mini_dev.json`，完整文件 SHA-256：

`88ceb0710163cae46a256ecea8f0a8c98286599530b60587fda5c3cfe57d45d2`

两条摘录的 SQL 与现有 gold 逐字相同，英文 question/evidence 与仓内保留原文逐字相同。此为**本地历史题源摘录校验**，不是本轮对 BIRD 官网的独立在线核验；不能凭本地文件自报“官方”推断其业务语义无误。

| 分层 | 可结论 / 仍需处理 |
|---|---|
| 已确定并可结清的证据缺口 | q26字段造成的一行差异、8场命中影响；q27 LEFT/INNER/DISTINCT差异、NULL人口、重复投影来源、前导零影响；本地历史题源与现行gold一致 |
| 合同解释而非新真值 | q26按中文应映射FRPM；q27可选择保留所有学校及NULL，但须显式声明，不由gold自验证决定 |
| 新版本合同修订仍open | q26到底采用FRPM还是将题面明确改为仅免费、年龄5–17与原文15–17如何披露；q27 SAT缺失/NULL是否保留、前导零归一、投影重合学校是否保留多重行，均须先确定合同、另立版本再修订 |
| 本轮尚未知 | 原数据业务层面年龄15–17的真实统计（现列无该年龄段）；前导零匹配中3条名字差异的身份沿革；原始发布方对上述歧义的正式说明；其他13题的一般语义正确性 |

建议登记为：旧“未复核”项 closed（已有独立复核证据）；新“BIRD题面/键/NULL合同修订”项 open。**这不等于已修gold、不等于可默默补分、不等于将语义争议判给某款产品。**
