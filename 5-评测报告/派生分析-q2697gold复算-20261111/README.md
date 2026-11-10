# 派生分析：q2697 gold 完整复算（2026-11-11，环2）

**性质**：判卷层（grading-layer）派生分析。零发射；不修改正式 25 行评分、历史判卷件与已发周报。本件由 2026-11-11 00:36–22:00 (+08:00) 授权窗口内的维护与派生分析环产出；数据来源全部为公开仓随包文件与已公开的既往派生分析。

## 1. 背景与问题

[派生分析-dabstep失败归因-20261109](<../派生分析-dabstep失败归因-20261109/README.md>) 确认 dabstep q2697 在全部 11 轮（a1 两形态 + r1109 机制批 DSH/Codex ×3 + WorkBuddy 原批 ×3）中 0/11 得分，并如实标注「gold 推导未完整复算」。该遗留项正好落在 Anthropic《Demystifying evals for AI agents》提出的原则上——恒败（0% pass）的题应先检查任务与判分器本身，而非只记模型失败。本件补齐该复算。

- 题面（`2-用例/dabstep-payments-10/inputs/questions.jsonl`，task_id 2697，hard）：「For Belles_cookbook_store in January, if we were to move the fraudulent transactions towards a different Authorization Characteristics Indicator (ACI) by incentivizing users to use a different interaction, what would be the preferred choice considering the lowest possible fees?」
- 随包 gold（`truth.json`，与 `solution/answers.jsonl` 一致，官方 dev 划分随包答案）：**`E:13.57`**。
- 判卷：`checker.py` 的 question_scorer 按字符串精确比对 gold。

## 2. 复算方法

[collect-q2697-gold-recheck.py](<collect-q2697-gold-recheck.py>)（公开件，私档镜像 `until22-20261111/collect-q2697-gold-recheck.py` 同 sha256 `428bd0f58d245433f319efef4d988294a7284ccd788b739c606c223c8b0ff44c`）从 `2-用例/dabstep-payments-10/` 机械重算：

- 欺诈集：Belles_cookbook_store、2023 年 1 月（day_of_year 1–31）、`has_fraudulent_dispute=True` → **94 笔 / 11680.62 EUR**，全部 aci=G、is_credit=True、未被拒；scheme 分布 GlobalCard 31 / TransactPlus 30 / NexPay 19 / SwiftCharge 14；商户月度总量 113260.42 EUR（natural month），金额比欺诈率 10.3131% → `>8.3%` 档；volume → `100k-1m` 档。
- 语义穷举：手册对若干关键语义未作定义，引擎在四个轴上取全组合（**216 组合**）——capture_delay 映射 3 种（'<3' / 'immediate' / 仅匹配 null）、多规则匹配择一 3 种（min / max / 按 ID first）、月度欺诈档口径 3 种（金额比 / 笔数比 / 仅 null）、空列表 `[]` 语义按字段独立取通配或死规则（2³）。候选 ACI 集合排除当前 G（题意为 "move towards a different ACI"）。无匹配规则的交易计 0 费（手册同样未定义，作为显式假设披露）。
- 复算可复核性：公开脚本仅以调用方传入的用例根路径工作，在公开仓内 `python3 collect-q2697-gold-recheck.py 2-用例/dabstep-payments-10 <out>.json` 复跑输出与随档 [q2697-gold-recheck.json](<q2697-gold-recheck.json>) 逐字节一致。

## 3. 结果

1. **216 个语义组合中 0 个复现 gold 费值 13.57**。最近值即 canonical 组合的 16.63（差 3.06）。
2. **canonical 语义**（手册可推导口径：capture '<3'、逐笔取最低匹配规则、金额比欺诈档、`[]` 通配）下候选 ACI 全费表：A 81.81 / **B 54.21** / C 81.04 / D 36.62 / **E 16.63** / F 33.56。**E 是最低费 ACI**——gold 的字母半段（E）站得住，费值半段（13.57）在任何已枚举语义下都不可复现。
3. **模型 11 轮答案与语义空间精确对应**（此前归因件只记「无对应」，本件修正）：
   - `B:54.21`（×2 轮）= canonical 语义下候选 B 的费值（54.21），逐字节一致；
   - `E:77.68`（×7 轮）= SwiftCharge ID183 组费 5.64 + TransactPlus ID924 组费 10.99 + TransactPlus ID454 组费 61.05 = **77.68**，即对候选 E「把每条匹配规则全部计费」的多规则求和语义（5.64+10.99+61.05=77.68）；
   - `NexPay:3.49`（×2 轮）在本空间无对应（NexPay 在全部 capture 映射下均无 ACI-E 匹配规则）。
4. 匹配规则明细（候选 E）：SwiftCharge 仅 ID183（fixed 0.05 / rate 43，全通配）；TransactPlus 为 ID924（0.02/17，credit=True+国际）与 ID454（0.12/94，account_type 含 R+volume 档）两条；GlobalCard 与 NexPay 在任何语义下均无匹配（其 ACI-E 规则或 credit=False、或 mcc 非空列表不含商户 MCC 5942——5942 不在任何规则的 mcc 列表中）。

## 4. 判卷层缺陷登记

1. **gold 费值不可复现**：`E:13.57` 的费值 13.57 在随包数据版本与全部 216 个合理语义组合下均无法推导；字母段 E 与 canonical 最低费一致。官方（Adyen+HF DABstep）只随包发布 gold 不发布推导；不排除官方内部口径与随包手册不一致或答案本身有误。
2. **guidelines 措辞 bug**：答案格式说明写 `{card_scheme}:{fee}`，而 gold 实形为 **ACI 字母**:`fee`（E = Card Not Present - Recurring Bill Payment）。模型若按字面理解格式会输出卡组织名（如 NexPay:…），与两种已知模型错误形态相符。
3. **多规则匹配择一未定义**：手册未规定一笔交易匹配多条费率规则时取哪条。这是模型答案分裂的直接来源——7 轮按「全计费」得 77.68、2 轮按「取最低」把同一语义应用到 B 得 54.21；两者都与 gold 不同。
4. **`[]` 空列表语义未定义**：手册只声明 `null` 通配；fees.json 中大量规则字段为空列表（account_type 720 条、mcc 127 条、aci 112 条），其语义只能外部推断。

## 5. 边界与不外推

- 本件只登记**判卷层**事实；q2697 所在 dabstep 场的正式评分行（含 a1、r1109、WorkBuddy/元宝/豆包各批）**保持原判不变**——0/11 是「按官方 gold 的精确比对得分」，该事实不因 gold 可疑而改写；本件改变的是对失败的解释归属（判卷层缺陷 + 模型语义分歧，而非单纯的模型能力缺陷）。
- 黑盒运行不能区分「模型推导错误」与「模型对官方隐含语义的不同猜想」的占比；77.68 的精确分解表明至少部分轮次是自洽语义下的计算，不是随机错误。
- 不据此修改 checker、gold、题面或 DABstep 任何随包文件；对上游 benchmark 的反馈不属本轮授权。

## 6. 复核入口

```
python3 collect-q2697-gold-recheck.py 2-用例/dabstep-payments-10 /tmp/out.json
diff /tmp/out.json q2697-gold-recheck.json   # 应逐字节一致
```
