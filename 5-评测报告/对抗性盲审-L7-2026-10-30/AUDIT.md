# 对抗性盲审报告（L7）——gate 语义默认显式化+逃逸面+VOIDED 链+运维规程+集成动作，2026-10-30

- 审计角色：敌意审计（板任务 task-20；lead 消息称 task-23，板上无该号，按 lead 委托范围建 task-20 并 claim——板号差异如实声明）。纪律：零模型/零网络；只读+离线复算；git 全程可用；写界仅本目录；truth/solution 未语义阅读。
- 对象：loop7-2026-10-30 三提交 a186ff3(D1 预注册)→47bd685(D2 实现)→d704440(L7-B r1 VOIDED 留档)。

**live_doc_drift: none（0 项）**

## 0. 总判定

**安全 blocking：0；defect：0；observation：2。** gate.py 修订（38b42a87→25dbf52e）22 变更行逐 hunk 对账 PREREG 全部授权内：DEFAULT_PLAN_DIR **零残留**（grep=0）、API None 即 GateError、CLI 双参必填、判分语义零改动、--selftest 豁免合法（自测仅 tmp 合成世界，不触真实 binding）；全仓逃逸面复核=其余 `自动循环L5` 引用均为批自有脚本或 declared known-impact（l4/l5 冻结现场），共享验证器已无隐式锚定；r1-r6 VOIDED 链六版全档保留+设计-note 论证成立（跨批重演按封印钉定设计不可满足）；L7-B 规程与 L5 ps 事件链对齐、9 处 env-passthrough 分类正确（抽验 0 字面量）；PR#10 合并树与 loop6 侧零差异（merge 零新改动实证）；main test_freeze 全绿（19 events schema 全过）；L7 新增文件凭据/PII 零命中。

## 1. gate.py 修订审计（AUD-L7-S1）

- **修前/修后字节双证**：gate.pre-l7.py sha256==`git show c8710fb:gate.py`==**38b42a87**（lead 声明修前值独立证实）；gate.post-l7.py==现行磁盘 gate.py==**25dbf52e** ✓。
- **22 变更行（15+/7-）逐 hunk 对账**（lead 称 24，实计 22，以实计为准）：①DEFAULT_PLAN_DIR 常量拔除（dated 注释保留修前行为指针 c8710fb+跨批错位实证=L6 E2 REFUSED）；②verify_execution `plan_dir=None`→GateError；③load_execution_seal `(plan_dir or DEFAULT)`→None 即 GateError；④gate_admission 同；⑤CLI `--binding/--plan-dir` 默认删除→必填（`ap.error`）。
- **默认值拔除彻底性**：grep DEFAULT_PLAN_DIR 现行 gate.py=**0 残留** ✓。
- **判分语义零改动**：diff 全部为默认值/参数校验/注释面，准入判定函数体零触碰（逐 hunk 复核）✓。
- **--selftest 豁免合法性**：`if a.selftest: return selftest()` 先于必参校验——selftest 体无 DEFAULT_PLAN_DIR 引用、仅 tmp 合成世界、不触真实 runtime-binding（逐项核）→ **合法豁免非绕过** ✓（PREREG:36「selftest 如依赖默认目录则同步适配（实现期核）」的实现期核结论=自测本不依赖）。
- 正例=历史复算改「基线收据引用固定+自身行为验收 r7 12/12 PASS」（见 §3）。

## 2. 显式化逃逸面（AUD-L7-S2）

- 共享验证器 gate.py：隐式锚定**已清零**（§1）。
- 全仓 `自动循环L5-2026-10-30` 引用面（grep --include=*.py）：剩余命中= ①l4/l5 冻结现场自有 runner（l5_wb_runner.py/l5 lab.py×2）= **PREREG:34-35 declared known-impact**（现场封存不重跑，重跑须先适配记池）✓；②各批自有脚本（L6 prepare_design.py 设计推导、L5/L6独立复核脚本）=批自有非共享验证器 ✓。**无其他共享模块隐式锚定批目录**。

## 3. r1-r6 VOIDED 链（AUD-L7-S3）

- **六版全档**：r1 跨pin复算设计误 / r2 冻结副本错位 / r3 部分世界复判设计误 / r4 树内binding代际错位 / r5 证据缺位 / r6 跨批重演设计废弃——六份收据+design-note+README+diff-main-to-l7.patch+gate.pre/post 全在 `5-评测报告/L7验证器修订-2026-10-30/`；r7 终版=l7-gate-recompute-receipt.json **12/12 PASS**。
- **VOIDED 未篡改**：各收据如实记录自身失败断言（all_ok=false+断言明细），VOIDED 状态按仓例编码于文件名（沿 L6 VOIDED 先例）；gate.pre/post 双字节锚使任何事后改写可检。
- **设计-note 论证成立**：跨批重演不可行的结构根源=每批 admission 要求「manifest 钉值==E blob==磁盘」三方一致，共享工链演进后历史批三方一致在当前盘**按设计不可满足**——这正是封印钉定目的（历史裁定由封印时刻字节+收据永久固定，不随 HEAD 漂移）。论证与 L4→L6 逐步实证（r1-r6 各自结构发现）自洽 ✓。终态验收面=基线收据引用固定+修订版自身行为验收（selftest+近似错误例 N1-N4+r7），与本审计对 gate diff 的独立核互补。

## 4. L7-B 运维规程（AUD-L7-S4）

- **OPERATIONS-hygiene.md 与 L5 ps 事件链对齐**：规程开头即引 L5 ps 误印事件（源=对抗性盲审-L5 AUDIT，零入库实证）；硬规则覆盖 argv 禁凭据/@file-env 注入/禁 set -x 回显/日志只存尾 8 位/泄漏先轮换后清理（顺序不可反）/入库禁令——与 L5 事件教训逐条对应 ✓。
- **bearer 扫描口径**：bearer-scan-receipt-l7.json=hits 9 全部 `--ae VAR="$VAR"` env 透传形态、literal_violations=0——**$VAR 引用非字面量，放行口径正确非漏报** ✓（恰为规程第 1 条允许形态）。
- **抽验**：run-dsh-xiaomi.sh 实文件 grep 字面量模式=**0** ✓（其余同构）。

## 5. 集成动作（AUD-L7-S5）

- **PR#10（c8710fb merge loop6→main）零新改动实证**：c8710fb 为双亲 merge（main f40c75e + loop6 42ecf72）；`git diff 42ecf72 c8710fb` = **0 行**——merge 树与 loop6 侧完全一致，零新改动 ✓（main 侧净增=L5+L6 全部交付 715 文件）。注：loop6 侧 42ecf72 含 L6 收尾三提交（acceptance/ledger schema repair/auditor polish），早于 L7 D1——时序正常。
- **main test_freeze**：现行树实跑 **OK，events=20，schema=live_registry_entry 全过（exit 0）** ✓。过程注记：本审计首查曾捕得 L7 索引事件瞬态 off-schema（带 live_doc_drift，恰为 L6 27cd39d 同类教训复现瞬态），lead 提交 e087a3c 时已净、终态 48/48 全绿；收尾清单制度（必跑 invariant）已在 27cd39d 立制，本次为提交前窗口期瞬态，非终态缺陷。

## 6. 凭据/PII 与红线（AUD-L7-S6）

- **L7 新增文件扫描**：自动循环L7+工具链新文件+gate.py+L7验证器修订 = 17 文件真实 key **0**/generic **0**；PII（15 文件）**0** ✓。
- **历史批零改动红线**：D1→HEAD 变更仅 gate.py（授权修订）+工具链新文件+L7 新目录；L4/L5/L6 证据/报告/收据零异动 ✓。

## 7. 结论与计数

**blocking 0 / defect 0 / observation 2**：
- **AUD-L7-O1**：r1-r6 VOIDED 状态仅文件名编码，收据体内无 status/superseded 字段（沿 L6 VOIDED 先例，可发现性尚可）——建议未来 VOIDED 收据增加机读 `superseded_by` 字段。
- **AUD-L7-O2**：l4/l5 冻结现场 runner 调 gate 仍为无显式参形态（PREREG declared known-impact）——重跑前必须先适配（池项），本审计确认该声明与盘面一致。

## 8. 机器收据与本文件自证

- l7-audit-mech-receipt.json（本目录机械核）；scan-report-l7-full-r1.json；pii-min-check-report-l7-full-r1.json。
- live_doc_drift: none（0 项）；证据行见 §9。

## 9. 证据行（evidence_line.py 生成，2026-10-30T13:52:22+08:00）

```
5-评测报告/对抗性盲审-L7-2026-10-30/l7-audit-mech-receipt.json · 394ed4a1 · 2036B · 2026-10-30T13:53:32+08:00
5-评测报告/对抗性盲审-L7-2026-10-30/scan-report-l7-full-r1.json · 39946d2e · 4876B · 2026-10-30T13:52:22+08:00
5-评测报告/对抗性盲审-L7-2026-10-30/pii-min-check-report-l7-full-r1.json · 548f48a7 · 441B · 2026-10-30T13:52:22+08:00
```
