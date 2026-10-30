# 2026-10-26 判卷审计 · BIRD q26 并入正式合同（v1.1 → v1.2-q26-frpm）+ q27 裁定

> 事后链接修订说明：本页已事后修正链接及说明，不是原封印字节；历史结果不代表本次开展了新的验证。

范围：bird-ca-schools-15 一题（q26）金标并入 + q27 已知尖角裁定。不新增题目、不新增产品运行、不改历史分数。
依据链：[独立语义复核 2026-10-24](<../../../5-评测报告/复算/2026-10-24/bird-semantic-review/README.md>) → [候选与复核包](<../../../5-评测报告/补充材料/2026-10-24/候选与复核.zip>)（候选 1.2-q26-frpm，独立验收 19/19）→ 本收据（并入 + 全量有效运行回放）。

## 1. 变更内容（q26）

- **字段**：gold 由「仅免费餐」`frpm.\`Free Meal Count (Ages 5-17)\`` 改为「免费或减价餐」`frpm.\`FRPM Count (Ages 5-17)\``（其余过滤条件逐字不变：Monterey 县、`High Schools (Public)`、严格 `> 800`）。
- **结果集变化**：5 所 → **6 所**，多出 **North Monterey County High**（CDSCode `27738252730034`，Free Meal=611、FRPM=804）；同组 16 所候选中无 FRPM 恰等于 800 的记录（严格 `>` 与 `>=` 在本库不可区分，边界由合成 CTE 799/800/801 验证，见补充材料包 build_replay.py）。
- **口径依据**：中文题面与英文原文均要求「免费或减价餐」（free or reduced price meals），schema 中直接对应列为 `FRPM Count (Ages 5-17)`；四款产品 10 场有效运行中 9 场按 FRPM 作答。本地合同年龄明确 5–17（数据列实际口径）；原英文题面 15–17 为来源差异，不作为本地要求（`questions.json` 仅 q26 `evidence_zh`/`source_note` 两处澄清，题干与英文原文未动）。
- **其余 14 题 gold、db、schema、sample_rows 逐字不变**（SHA 对照见 §3）。

## 2. 版本对照

| 项 | 旧（v1.1，2026-10-24） | 新（v1.2-q26-frpm，2026-10-26 并入） |
|---|---|---|
| checker_version / case_version | 1.1 | 1.2-q26-frpm（`contract_status: adopted-2026-10-26`） |
| q26 gold 字段 | `Free Meal Count (Ages 5-17)` | `FRPM Count (Ages 5-17)` |
| q26 金标行数 | 5 | 6（+North Monterey County High） |
| `inputs/questions.json` | SHA `0cbe99d6…cbe1aa8`（15547 B） | SHA `144bf7c3…53543f3e`（15842 B，仅 q26 evidence/source 说明） |
| `--selftest` | 21 项 | **25 项**（+4 项 q26 合同负例） |

旧版保留（不静默覆盖）：① git 历史（基线提交 a2234fc 及此前 d247cde）；② 补充材料包内 `bird-q26/baseline-1.1/` 全套只读快照；③ [判卷审计 2026-10-24 冻结件](<../../判卷审计-2026-10-24/numeric/frozen/bird-ca-schools-15/>)（v1.0 字节）。旧 q26 gold SQL 原文已录入 [spec.md §13.2](<../../../2-用例/bird-ca-schools-15/spec.md>)。

## 3. 新旧文件 SHA-256（摘录，全表见 [sha256-manifest.json](<sha256-manifest.json>)）

| 文件 | 旧 v1.1 | 新 v1.2 |
|---|---|---|
| truth.json | `748fd14771b3dc440258625cbd6fd87be14cfdaa5b859627901b89423fc1caf7` | `c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19` |
| checker.py | `81c750da2bbfe9b5fb9c459d4af1ee96806e0776993d6d2befee50c06683547e` | `01447ab6112af9ee317de448aec39133b048971e8777052c81920da6696b049a` |
| inputs/questions.json | `0cbe99d6419d809f1d6030ec486c340fdf2a709c7854bfbfcd712b587cbe1aa8` | `144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e` |
| solution/answers.jsonl | `d8ae18f6286feeaa8501d552999dc685132e27c09599509833d3ea75b518564f` | `9b63a1846f0955cf2976c1ebb310c30e16eb740c9f09b7a7a45b5fe11b251929` |
| inputs/db/california_schools.sqlite | `a9e7d92a…bf72322d`（**不变**） | 同左 |

与补充材料包内候选的判分逻辑逐字一致；并入仅把 `contract_status` 由 `candidate-not-adopted` 改为 `adopted-2026-10-26` 并同步文档表述。

## 4. 正反例自测（stdout 留档：[selftest-2026-10-26.stdout.txt](<selftest-2026-10-26.stdout.txt>)）

- 新版 `--selftest`：**25/25 通过，exit 0**（v1.1 旧版 21/21 见包内 `bird-q26/old-1.1.selftest.txt`）。
- 新增 4 项 q26 负例（第 20–23 项，均已固化进判卷自测）：①旧口径 Free Meal 5 行答案 → **q26 判错**（14/15，reward 1）；②漏 North 一校（5 行）→ q26 判错；③附加一行假学校（7 行）→ q26 判错；④重复一行（7 行，多重集敏感）→ q26 判错。
- oracle 交叉：新 oracle（v1.2 solution）**15/15** reward 1；旧 oracle（v1.1 solution，即"仅免费餐"5 所答案）在新合同下 **14/15、q26 红**（逐题判错但整场过线仍通过——单题口径错误不整场否决）。

## 5. 历史回放（10 场全部有效运行；脚本 [replay_2026_10_26.py](<replay_2026_10_26.py>)、机器结果 [replay-results.json](<replay-results.json>)）

方法：旧合同自补充材料包 baseline-1.1 解出、新合同=并入后正式目录；每场在 /tmp 临时副本判分（复制对应版本 canonical inputs），`3-表现现场` 与历史元数据零写入；逐场核对总账登记的 answers.jsonl SHA-256（10/10 一致），旧合同复算分与[运行总账](<../../../5-评测报告/运行总账-2026-10-24.md>)登记分完全一致。r1024 探针 2 场为 invalid（污染），不回放。

| 场次（总账 run_id） | 旧 v1.1 | 新 v1.2 | q26 | reward |
|---|---|---|---|---|
| r1025-candidates/bird-ca-schools-15__codex | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1025-candidates/bird-ca-schools-15__dsh | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1026-desktop-15/runs/doubao/bird-ca-schools-15 | 9/15 · 60.00 | 10/15 · 66.67 | 错→对 | 0→0 |
| r1026-desktop-15/runs/workbuddy/bird-ca-schools-15 | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1028-repeats/codex__bird-ca-schools-15__r2 | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1028-repeats/codex__bird-ca-schools-15__r3 | 12/15 · 80.00 | 13/15 · 86.67 | 错→对 | 1→1 |
| r1028-repeats/dsh__bird-ca-schools-15__r2 | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1028-repeats/dsh__bird-ca-schools-15__r3 | 13/15 · 86.67 | 14/15 · 93.33 | 错→对 | 1→1 |
| r1029-desktop-auto/runs/doubao/bird-ca-schools-15 | 10/15 · 66.67 | 11/15 · 73.33 | 错→对 | 0→0 |
| r1029-desktop-auto/runs/workbuddy/bird-ca-schools-15 | 14/15 · 93.33 | **13/15 · 86.67** | **对→错** | 1→1 |

结论：10 场逐题翻转**均仅 q26**、二值达标状态 **10/10 不变**，符合并入预期。说明两点：① 与第 2 期周报"八场均仅增加该题"的差异来自回放范围扩大——r1029 两场（10-25 执行）在周报之后；② r1029 WorkBuddy 一场按旧口径 Free Meal 作答、旧合同下判对，新合同下 q26 判错（93.33→86.67，仍达标）——合同修订双向生效，不针对任何产品补分。回放分仅作合同迁移证据，**不回写历史现场分数与总账**。

注意：内附 `inputs/` 副本的历史 run_dir（如 r1029，副本为 v1.1 字节 `questions.json`）直接重判会触发 input_integrity 守卫判 0（canonical 已是 v1.2 字节，实测复核）；未附副本的（如 r1028）不受影响。历史重判须用本收据的临时副本协议。

## 6. q27 裁定：已知尖角，金标不动

**结论：gold 正确、口径自洽——维持 raw-key LEFT JOIN；在 [spec.md §13.4](<../../../2-用例/bird-ca-schools-15/spec.md>) 登记为「已知尖角」。** 机器验证：[q27-verify-2026-10-26.json](<q27-verify-2026-10-26.json>)（脚本 [q27_verify.py](<q27_verify.py>)，只读复算，4/4 断言通过，数字与 2026-10-24 独立复核完全一致）。

- **要求口径**：q27 需要「raw-key `schools.CDSCode = satscores.cds` 等值 LEFT JOIN」——保留全部日期命中学校（含无 SAT 记录者，分数 NULL）、不去重同名异校、不做前导零归一。
- **自洽证据**：题面人群定义在 schools 侧；SQL 年份过滤与 Python 独立筛选人群完全一致（8,574 所）；gold 输出 8,574 行 = 8,574 所不同学校、每校恰一行（键两侧唯一、无扇出无遗漏）；8,120 行 NULL 分数（7,825 所无 SAT 记录 + 295 所有记录无分）与题面「联系电话（有则给）」的 NULL 容忍写法同口径。
- **为何不改 INNER（749 行）**：会静默丢弃 91% 题面人群，是更强的解释跳跃；**前导零容错**额外 64 所匹配中有 3 所与 SAT 端名称不一致，不能唯一确认同实体；**DISTINCT** 会合并 238 组同名异校投影（357 行），改变实体集合。三者均属题面未授权的合同选择。
- **停止追查条件**：① BIRD 官方发布 q27 口径说明或修正题源；② 出现按 INNER/前导零/去重口径作答且其余 14 题全对的实际现场；③ 上游数据/题面更新使 8,574/749 基线失效。

## 7. 边界

- 本收据结清的是 q26 口径缺口与 q27 裁定登记，不证明判卷器一般正确，不对其余 13 题作语义认证（见语义复核"本轮尚未知"）。
- v1.2 的官方上游（BIRD 榜单）仍用原句 `Free Meal Count (Ages 5-17) > 800`；本仓按题面优先原则本地修订，与官方榜单分数不可直接互比。
- 未触碰：CHANGELOG.md（未获授权）、未知登记.json、运行总账、.git、3-表现现场（只读）、5-学习笔记。
