# 对抗性盲审报告（L6）——三次废封+授权 diff+F1+真实槽+预注册符合性，2026-10-30

- 审计角色：敌意审计（task-18）。纪律：零模型/零网络；只读+离线复算；**本环 git 全程可用**（lead 解除 L5 零 git 限制）；写界仅本目录；truth/solution 未语义阅读；凭据仅批准 refs.DEEPSEEK_API_KEY（ASCII）内存比对，零值输出。
- 对象：loop6-2026-10-30 全链 8c3e4b9(D1)→f10881c(D2)→1211b5b(D3/F1修)→8583ce5(现场)→1c27a6b(E1废)→7f04b6b(E1→E2 适配)→[936615d E2 binding]→46d64ee(E2废)→36fe6b9(E2→E3)→aae5eda(E3)→c1d8970(binding)→52a1614(真实槽)。链与 lead 清单一致（另含 936615d E2 binding，清单未列，无实质差异）。

**live_doc_drift: none（0 项）**

## 0. 总判定

**安全 blocking：0；defect：0；observation：2。** 三次废封（E1/E2 两次 REFUSED+首版比对收据 VOIDED）零消耗实证成立；E1→E3 全部代码改动落在 dated 授权清单内（51 行/11 hunks+verify_execution 5 行，逐 hunk 对账无超界）；F1=超量满足非验证器放松（gate 自 L5 后字节零改动，git 独立证实）；真实槽证据链完整（contract 9/9 pin+checker ffa7389a 实算吻合、零污染、别名双证）；「按位拷贝零改动」声明被三次适配推翻的偏离已由 dated 废止纪要+授权补充如实入档；历史批零改动红线成立（历史证据零异动；共享用例 checker/spec 演进=声明内 L6-A 判卷修订，truth/inputs 零触碰，rule-5 修前/修后/正例/历史复算在档）。

## 1. 三次废封零消耗实证（AUD-L6-S1）

- **E1=1c27a6b（11:52:45 binding）**：废止纪要载明阻断在 runner 读计划阶段（`wb_slots()` 读 L5 plan→L6 slot 不存在→必然拒绝），fail-closed 零消耗。独立核：`3-表现现场/l6-20261030-wb-gateway/runs/` 仅含 E3 bird 一目录；全目录 grep E1/E2 seal 标识（1c27a6b6/46d64ee/84f54d94/0bc9401e）**零命中**；bench-workspaces 仅 1 个 l6 ws（mtime 12:24=E3 运行时）；registrations 恰 1 份（12:24，E3 期）。
- **E2=46d64ee（12:15:41 binding）**：第二次 REFUSED（gate `DEFAULT_PLAN_DIR` 硬编码 L5 计划目录→plan_sha 错配），REFUSED 先于 claim，零 claim/零 registration/零发送；`runs/ 空` 与盘面一致。
- **第三处废档**：`l6-meta-recompute-receipt-r1-VOIDED-比对伪差.json`——首版比对收据因比对伪差被 VOIDED 且原样保留（废而不删），与 l6-meta-recompute-receipt.json 并存在案。
- **时序戳独立核**：E1 binding 11:52:45 → E2 binding 12:15:41 → E3 binding 12:23:46 → 注册 12:24 → 运行 12:24:21–12:26:49（148s，meta 实读）——严格递增，无废封期活动痕迹。

## 2. E1→E3 授权 diff 全清单对账（AUD-L6-S2）

- **l5_wb_runner.py**：`git diff 1c27a6b..aae5eda` = 51 变更行/11 hunks，位置逐一对应废止纪要授权清单：:32 计划目录、:193 batch meta、:394 WORKSPACE_ROOT、:616 evidence_dir、:1021 批形状断言（授权补充 A：L5 双槽硬编码→按 L6 plan/contract 事实一致性断言）、:1087/:1148/:1368/:1468/:1714 自测架适配（授权补充 C：单槽别名/前置 reset/contract19 rule_version 标签镜像）——**11/11 hunks 全部授权内，零超界**。
- **verify_execution.py**：5 行（PLAN_DIR 站点常量+调用处显式 `plan_dir=`），与 E3 授权补充逐字吻合；gate 文件不在 diff 中。
- **runner 终态独立实算**：l5_wb_runner.py 磁盘 sha256=**06d171bbdf96…**（与 wb 侧自报一致，本审计独立实算）；verify_execution.py=**f0612ba6…**（E3 manifest 钉值吻合）；两值均已写入 E3 manifest 且实算一致。
- **SUMS（授权补充 B）**：driver-snapshot/SHA256SUMS.txt 终态重算机制在案（runner 定稿后重算）。

## 3. F1 处置审计（AUD-L6-S3）

- **gate 零改动证实（git）**：`1-评测方案/工具链/l5-execution/gate.py` 全历史仅 L5 两次提交（6aaf655/972cf96）；`git diff <L5 末次>..HEAD` 该文件 **0 行**——字节不变，L5 现场不受影响。
- **超量满足非放松**：F1 REFUSED 系 gate `EXTERNAL_REQUIRED` 硬要求 3 件环境身份（cordis.patch.yml/package.json/~/.dsh/AGENTS.md）；处置=L6 execution_seal.py 补回 REQUIRED_EXTERNAL_FILES 前两件（AGENTS 原已钉）+ WB 两件保留——**验证器零放松，封印侧超量满足** ✓（与应然判定一致）。
- **EXTERNAL_REQUIRED 3 件 vs manifest external 5 件一致性**：manifest external_files 恰为 gate-required 3 + WorkBuddy 2（Info.plist/app.asar），5 件全部实算 sha256 吻合 ✓。

## 4. 真实槽证据链（AUD-L6-S4）

- **全件在档**：runs/l6-20261030-wb-gateway-bird-ca-schools-15-r1/ = prompt.txt/agent-session/trace/native-terminal.json/score-receipt/checker.stdout/meta.json/registrations/slot-accounting.json/workspace（inputs+TASK）齐备。
- **contract pin 实算**：case_snapshots.bird 9 个文件 pin 与 `2-用例/bird-ca-schools-15/` 实际字节 **9/9 吻合**；checker.py 顶层 pin=ffa7389adef3…（checker_sha256/bird 与 files 双处一致）**实算吻合** ✓。
- **污染扫描**：模型可见轨迹（native-terminal+trace）中 truth.json/solution/harness-compare-bench/checker.py 计数全 **0**；网络动作动词 0；ws 外路径仅为产品自身 app-data（.workbuddy projects/personal——产品交付态固有，沿 L4/L5 度量卫生口径）。
- **别名证据**：driver 创建参数「DeepSeek V4.1-Flash」+ 会话库 model 字段双证（alias_evidence 在案）；actual_request_model=null=managed unknown（不可观测，不参与同路由归因）；app_asar before==after 无漂移；integrity_verdict=clean。

## 5. 预注册符合性与偏离处置（AUD-L6-S5）

- **冻结性（git）**：PREREGISTRATION.md/plan.json 自 D1(8c3e4b9) **0 diff**；contract.json 仅 D3(1211b5b) 一改（F-1 修：case_snapshots 冻结算法重算，首版仅刷顶层 checker_sha256 致 per-file 旧钉残留被 judge 独立验收抓出——D3 修复+judge 收尾在案），此后 0 diff。
- **「按位拷贝零改动」偏离**：PREREG:56-57 原声明被三次适配部分推翻（站点常量/批形状断言/自测架）——偏离处置=根因归 lead 预注册声明缺陷（可预见适配遗漏，E 后首槽前静态验证零成本暴露）+ dated 废止纪要逐条授权+补充（A/B/C）+ T22d 已知败保留为 documented known-state（70/71）——**如实入档 ✓**。

### AUD-L6-O2【observation】共享用例文件演进（声明内）
- `2-用例/bird-ca-schools-15/checker.py(+43/-3)/spec.md(+2)` 系 L6-A 判卷修订（输出纯增量 n_tasks/guards_used 两键，判分语义零改动，动机=L5-P1 wb-bird 缺 guard 元数据曾不得 formal）。独立核：**truth.json/inputs 零 diff**；CONTRACT_REVISION 修前值在案；rule-5 修前(checker.pre-l6.py)/修后(post)/diff/正例/历史复算/VOIDED 伪差收据全在 `5-评测报告/L6判卷修订-2026-10-30/`。历史批影响：L4/L5 契约钉旧 checker 字节（各自身 frozen contract 在档），历史证据完整性不受损。分类：声明内演进，非红线违反；登记为 observation 以固定「共享用例演进需 rule-5 全套+双向 pin 重算」的先例。

## 6. 凭据/PII（AUD-L6-S6）

- **全量扫描**：l6 现场+计划目录+判卷修订 = **91 文件，真实 key 精确命中 0，generic 0**（exit 0；scan-report-l6-full-r1.json）。
- **PII**：3 处 xingming-label 命中逐一定性=BIRD 任务题面自身词汇（「管理者完整姓名」question_zh/evidence_zh 及其在模型轨迹中的回显）；**轨迹全量无 韩之凡/学号 等任何真实身份值** → 任务内容类，非个人 PII ✓（pii-min-check-report-l6-full-r1.json）。
- **历史批零改动红线**：`git diff 79cebe0..HEAD --name-only` 剔除 L6 路径后仅剩 evidence-kit（L6-C 声明内工具演进+自检收据）与上述 L6-A 用例两文件（§AUD-L6-O2）；**L4/L5 全部证据/报告/收据路径零异动** ✓。

## 7. 结论与计数

**blocking 0 / defect 0 / observation 2（AUD-L6-O1: actual_request_model=null 等 managed unknowns 沿例登记并已双证别名；AUD-L6-O2: 共享用例演进先例固定）**。三次废封零消耗、授权 diff 全对账、F1 超量满足、真实槽证据链、预注册偏离如实入档——全部成立。E3 唯一真实槽 formal_admitted=1/1（raw=100.0 15/15）由 gate v2 机械裁定，本审计独立复核其证据前提无异议。

## 8. 机器收据与本文件自证

- l6-audit-mech-receipt.json（本目录，机械核 A–F 系）；scan-report-l6-full-r1.json；pii-min-check-report-l6-full-r1.json。
- 本文件 live_doc_drift: none（0 项）；证据行见 §9（evidence_line.py 生成，receipt_check 回验）。

## 9. 证据行（evidence_line.py 生成，2026-10-30T12:40:51+08:00）

```
5-评测报告/对抗性盲审-L6-2026-10-30/l6-audit-mech-receipt.json · 79a492dc · 1492B · 2026-10-30T12:40:51+08:00
5-评测报告/对抗性盲审-L6-2026-10-30/scan-report-l6-full-r1.json · 846e056a · 24215B · 2026-10-30T12:40:51+08:00
5-评测报告/对抗性盲审-L6-2026-10-30/pii-min-check-report-l6-full-r1.json · 4532c358 · 758B · 2026-10-30T12:40:51+08:00
```
