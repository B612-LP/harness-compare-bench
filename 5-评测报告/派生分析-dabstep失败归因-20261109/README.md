# 派生分析：dabstep-payments-10 三失败题的确定性失败模式归因（2026-11-09）

> **身份与边界（先读）**：本文是**事后探索性派生分析**，不是预注册研究：问题、口径与分类均在 r1109 复测完成（2026-11-09 14:37）之后提出。不改变任何正式成绩、判卷、预注册文件与已发周报；全部结论只基于已在公开仓或已披露收据中的运行证据与公开用例数据。作者=AI Agent（lead），验收=非作者独审。置信依据逐条标注，不确定处如实标注。

## 1. 问题

正式表 A/W 轨 dabstep-payments-10 的 reward=0（三轮加权 70.00/60.00 等），三道固定失败题 q49、q70、q2697 在 r1109 双臂复测中 6/6 轮复现。本分析回答：**这三题的失败是采样方差、单一 Harness 缺陷，还是任务×模型的系统性失败模式？** 这直接影响正式行 dabstep=0 的解释强度与老师 Week3「五题区分力」追问的回应。

## 2. 证据基线（11 轮 × 3 形态）

全部 dabstep 运行的三题答案（公开证据：`3-表现现场/r1030-formal-a1/runs/`、`3-表现现场/r1109-mech-n3/runs/`；WorkBuddy 原批轨迹经其判卷收据披露于 6-周报第4期与复测登记）：

| 来源 | 臂 | 轮次 | q49 | q70 | q2697 |
|---|---|---|---|---|---|
| r1030-formal-a1 | DSH CLI | r1 | A. NL | yes | NexPay:3.49 |
| r1030-formal-a1 | Codex CLI | r1 | A. NL | yes | B:54.21 |
| r1109-mech-n3 | DSH CLI | r1–r3 | A. NL ×3 | yes ×3 | E:77.68 ×3 |
| r1109-mech-n3 | Codex CLI | r1 | A. NL | yes | B:54.21 |
| r1109-mech-n3 | Codex CLI | r2–r3 | A. NL ×2 | yes ×2 | E:77.68 ×2 |
| wb-n3-20261101（原批 W 轨） | WorkBuddy 桌面 | r1–r3 | A. NL ×3 | yes ×3 | E:77.68 / NexPay:3.49 / E:77.68 |

- **q49：11/11 轮全部答 "A. NL"**（gold="B. BE"）——跨 DSH/Codex/WorkBuddy 三形态、11 次独立运行，零例外。
- **q70：11/11 轮全部答 "yes"**（gold="Not Applicable"）——同上，零例外。
- **q2697：11/11 全错**；错误值收敛于 "E:77.68"（7/11，含 DSH 臂 r1109 三轮一致与 W 轨两轮），其余 B:54.21×2、NexPay:3.49×2。

**判定**：q49/q70 的失败不是采样方差（方差定义下 11 次独立采样不应零例外同值）；也不是单一 Harness 缺陷（跨三形态一致）。是**任务×模型的确定性失败模式**。

## 3. 逐题机理（置信依据）

### q49「What is the top country (ip_country) for fraud? A. NL, B. BE, C. ES, D. FR」→ gold="B. BE"

- 用例手册 `2-用例/dabstep-payments-10/inputs/manual.md:225` 明确定义：「Fraud is defined as the **ratio** of fraudulent volume over total volume」。
- 按该定义复算（payments.csv，`has_fraudulent_dispute=True`）：BE 10.85%（2493/22976）> NL 9.93%（2955/29760）> FR 5.93% > ES 5.73%。gold 正确。
- 11 轮模型答案 NL 与**件数口径**（NL 2955 > BE 2493）一致——模型按自然语言默认的「数量最多」理解「top country for fraud」，而手册定义 fraud 为比率。
- **失败机理：题面口径歧义×手册定义（比率）**。题面文字对「top for fraud」的自然读法是计数，定义藏在 manual.md 第 225 行。这是任务构造的系统性陷阱，非模型计算错误（模型的数字本身是对的）。（置信：高——manual 原文、复算数字、11/11 答案一致三重闭合。）

### q70「Is Martinis_Fine_Steakhouse in danger of getting a high-fraud rate fine?」→ gold="Not Applicable"

- 该商户在数据中**存在**且 fraud rate=8.00%（1105/13805）——数据本身带诱饵性「看似高」的值。
- manual.md 全文检索：唯一罚款制度是 **PCI DSS 非合规罚款**（EUR5,000–100,000/月，§7.4）；**不存在「high-fraud rate fine」制度**。
- questions.jsonl guidelines 明示：「If a question does not have a relevant or applicable answer for the task, please respond with 'Not Applicable'」。
- 11 轮模型全部答 "yes"——把「8% 看似高」直接当作存在罚款风险的依据，未检验「该罚款制度是否在手册/数据范围内存在」。
- **失败机理：failed-premise 识别失败**（对数据范围内无适用答案的问题给出实质判断）。gold 要求识别「手册中无此制度→不适用」。（置信：高——手册全文检索+商户存在性+11/11 一致；局限：无法从行为面证明模型「未检查」而非「检查后仍答 yes」，两种路径答案相同。）

### q2697「Belles_cookbook_store January，fraud 交易迁移 ACI 的最低费用选择」→ gold="E:13.57"

- 数据事实（复算）：Belles 1 月 fraud 交易 94 笔，全部 ACI=G、Ecommerce、国际（issuing EU→acquirer US）、四种 card_scheme 混合；费用表 fees.json 共 1000 条多维规则（card_scheme/account_type/fraud_level/volume/MCC/aci…）。
- 11 轮全错，错误值三种：E:77.68（7/11，含 DSH 臂 r1109 三轮一致与 W 轨两轮）、B:54.21（2）、NexPay:3.49（2）。
- **失败机理：多条件规则匹配计算错误**。与 q49/q70 不同，本题错误值**有跨会话方差**（三种错误值、三种规则匹配路径），但**臂内高度收敛**（r1109 DSH 三轮逐字节同值 77.68）——同 prompt 同数据→同计算路径的确定性。gold 的精确推导（为何 E 与 13.57）本分析未完整复算，**如实标注：本题 gold 推导不可完整复现，结论只到「计算错误+臂内收敛」层级**。（置信：中——分布与收敛有据，gold 推导未复核。）

## 4. 对正式行解释的影响（不改分数，只收紧解释）

1. **dabstep reward=0 的成因**：7/10 正确 < threshold 0.8。三失败题中 q49/q70 属「题面口径/前提陷阱」性质（模型数字正确但口径错、或答了不该答的题），q2697 属复杂计算错误。**11 轮零例外**说明该题组对当前模型（deepseek-flash 家族）构成稳定失败模式。
2. **归因纪律**：失败跨 DSH/Codex/WorkBuddy 三形态一致 → **不可归因为任何单一 Harness 的缺陷**；更接近「任务构造×当前模型能力」的交互。A 轨（同模型）分轨结论不受影响，且本证据强化了「dabstep 三失败题不构成 Harness 区分度来源」。
3. **回应 Week3「五题区分力」追问**：dabstep 的区分力实际来自 weighted（70.00/60.00 等的断言级差异），而非 reward 二值（全部 0）。q49/q70 属于**对五款产品同时失效的题**（现有 11 轮覆盖 3 款，其余两款未测、不外推）。
4. **不做什么**：不改正式 25 行；不把 11 轮外推为「五款全部如此」；不据此改题或改判卷（题目保留原样供历史可比）；q2697 的 gold 推导复核留作后续可选事项。

## 5. 复算方法

- 数据：`2-用例/dabstep-payments-10/inputs/`（payments.csv 138,236 行、manual.md、fees.json 1000 条、questions.jsonl）与 `truth.json`（gold 如上）。任何读者可在公开仓克隆后用同口径复算（口径：`has_fraudulent_dispute=="True"` 计 fraud；比率分母=该国 ip_country 全部交易）。
- 运行答案来源：公开 `3-表现现场/r1030-formal-a1/runs/*__dabstep-payments-10/workspace/answers.jsonl` 与 `3-表现现场/r1109-mech-n3/runs/*__dabstep-payments-10*/workspace/answers.jsonl`；WorkBuddy 原批三轮的三题答案文本由作者自私档归档（wb-n3-20261101/runs/）读出并**仅披露这三题答案值**（合成任务答案文本，无其他轨迹内容；完整原件仍为私档，本文不宣称其公开）。
- 本分析全部数字由脚本机械复算（payments.csv 直接读），无手工转录。

## 6. 变更记录

- 2026-11-09：初版（lead，AI Agent；事后探索性派生分析，非预注册）。
