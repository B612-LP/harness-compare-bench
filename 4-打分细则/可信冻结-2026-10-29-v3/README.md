# 第三代冻结（freeze-20261029-v3）：治理继任者 + pin 分类封印

本目录是 [第二代冻结](<../可信冻结-2026-10-29-v2/README.md>) 的**治理继任合同**（L2 包B，[预注册 §四](<../../1-评测方案/自动循环L2-2026-10-29/PREREGISTRATION.md>)，封印 commit `ae36f67`，分支 `loop2-2026-10-29`）。落盘时刻 2026-10-29 16:31:12 +08:00（实钟）。

## 继任语义（judge 验收点）

- **v2 仍是 r1030 正式批次（官方表 10 行）的合同记录**：`5-评测报告/可信冻结-2026-10-29-v2/` 下 `official-main-table.json`（A=10）与全部产物继续作为 r1030 的准入与判卷依据，本代对其零字节改动。
- **v3 为后续批次的治理继任者，不重新准入任何历史行**：`effective_at` 推进到本代封印时刻（2026-10-29T16:31:12+08:00），历史运行不在冻结期内，故本代 `official-main-table.json` 的 groups 恒为空（A=0, B=0），全部历史候选仅以 rejected+理由列出。**v3 不改写任何历史分数、不推翻 v2 任何准入裁定。**
- 判卷合同继任链：`freeze-20261029-v2`（r1030 合同记录）→ `freeze-20261029-v3`（后续批次准入用）。

## 与 v2 的差异（全部差异，无其他）

1. `rule_version` → `freeze-20261029-v3`；`BASE`/`OUT` 指向 v3 目录；`effective_at/collected_at` 推进到本代封印时刻。
2. **`work_registry` 指源修正（D2 缺陷本体）**：v2 config 的 `work_registry.path` 指向 **v1** 台账（`4-打分细则/可信冻结-2026-10-29/work-registry.json`，16 事件，SHA `27974b75bd7533a58e75ab62b07ba1378789fab324ea28aed67eea47541bea15`），导致 v2 registry 追加的 7 条收据未进机读六账。v3 config 改指 **v2 台账** `4-打分细则/可信冻结-2026-10-29-v2/work-registry.json`。
   **字节勘误（2026-10-29 16:31+08:00，实钟）**：预注册 §四与任务指令写该文件 SHA 为 `27974b75…`；经实测该 SHA 属 **v1** 台账（16 事件），v2 台账（23 事件）实际 SHA-256 = `04944e28f243e06fd119a614c766f990c81813f4bce8a45958076e37796a93a6`。v3 config 按实况记载 `04944e28…`（若写 `27974b75…` 则 path/sha 不自洽，verify_seal 必失败）。此为预注册文本的转写勘误，不构成对预注册实质要求的偏离——实质要求（v2 registry 并入六账）照常实现。
3. **lock pins 增 `pin_class`**（见下节）。
4. 新增[活动台账](<work-registry-live.json>)。
5. `freeze.py` 其余逻辑与 v2 逐字节相同（含六账构建对 work_registry 的既有并入管道：category 直映，`product_run` 类拒绝入账，事件 ID 全局重复即失败）。

## pin_class 分类（逐 pin + 理由）

判定规则：**contract** = 直接作为判分/准入输入的文件，及冻结引擎机制组件（引擎/自测/Schema）——漂移=verify 硬失败 exit≠0；**live_doc** = 人类叙述文档与示例——漂移=输出 `live_doc_drift` 列表且 exit=0，操作规范仍为**还原+旁挂**（先还原字节，改动以旁挂文件+dated 勘误记录；封印纪律不因报告制放松）。

| pin | pin_class | 理由 |
|---|---|---|
| freeze.py | contract | 判卷/准入引擎本体，行为字节即合同执行语义 |
| test_freeze.py | contract | 引擎自测组件：其漂移=引擎行为漂移风险（按从紧归类） |
| import-schema.json / config-schema.json | contract | 导入与配置合同 Schema |
| config.json | contract | 冻结配置（case 快照/官方格/输入源指针） |
| 4-打分细则/可信冻结-2026-10-29-v2/work-registry.json | contract | 本代六账并入源（7 收据所在，SHA `04944e28…`） |
| 5-评测报告/未知登记.json | contract | build 读取（dabstep DAB2697 issue 引用锚） |
| 1-评测方案/正式批次-2026-10-29/registration-plan.json | contract | official_slots 的 plan_sha256 引用与计划完整性校验对象 |
| 1-评测方案/准入预检-2026-10-29/wb-preflight.json | contract | registry 收据 `work:wb-admission-preflight-20261029` 的 source |
| 3-表现现场/r1030-formal-a1/preflight/cli-preflight.json | contract | registry 收据 `work:r1030-cli-preflight` 的 source |
| README.md（本文件） | live_doc | 人类叙述 |
| import-example.json / example-source.json | live_doc | 示例文档，非判分输入 |
| 4-打分细则/裁定-2026-10-26-dab-q2697.md | live_doc | 叙述性裁定文档（未被 build 读取） |
| 4-打分细则/检索口径-2026-10-27-落表.md | live_doc | 叙述性口径文档 |
| 1-评测方案/正式批次-2026-10-29/README.md | live_doc | 叙述文档 |
| 1-评测方案/准入预检-2026-10-29/README.md | live_doc | 叙述文档；L1 sealed-drift 事件当事文件，本代起降为报告制 |

注意：`work-registry-live.json` **不在封印内**——活台账按设计 append-only（随执行持续追加），与 seal 的不变性要求矛盾；其条目进六账须走未来代显式注册。审计者可直接读取该文件核对 L2 事件。

## 六账预期变化（对照 v2 基线）

self_test 8→13（+5 `work:r1030-selftest-*`）；interface_preflight 11→13（+`work:r1030-cli-preflight`、+`work:wb-admission-preflight-20261029`）；其余四类不变。`work:wb-sandbox-preflight-20261027` 在 v2 基线 interface_preflight 已在账（源自 v1 registry 并入），按 event_id 去重后仍恰一次。product_run 110 / offline_recompute 7 / grading_regression 3 / bare_model_probe 5 不变。

## 活台账 schema

`work-registry-live.json`：`{schema_version: 1, coverage: {note, created_at}, events: []}`，条目按 `config-schema.json $defs.live_registry_entry`：`{event_id(work:*), kind ∈ 五类非 product_run, executor, timestamp, source{path,sha256}, locator, description, pin_class:"live_doc"}`，append-only，由执行者本人登记。

## 信任边界（继承 v1/v2）

SHA 封条不是数字签名；语义审查、可信证据作者与人工裁定是机器校验之外的明确信任边界。官方 host + alias 仍不能证明服务端权重 build 一致。

## 勘误（2026-10-29T17:00:17+08:00，实钟；judge 验收 B-1，lead 裁定）

corrections id=pkgb-test-live-ledger-fix-20261029：test_freeze.py 原 `test_live_ledger_exists_and_empty` 断言活台账 `events==[]`，与活台账 append-only 生命周期矛盾（commit ae6b37d 时点断言为真、44/44 成立；登记 5 事件后 HEAD 必失败，judge 实测）。已按 lead 裁定（采 judge 建议一）重写为 `test_live_ledger_structural_invariants` 结构不变量断言：(a) 存在且可解析；(b) 顶层 schema_version；(c) 逐条必备字段（event_id/kind/executor/timestamp/registered_at/source.path/source.sha256，ISO8601 带时区）；(d) event_id 无重复且时间非严格升序；(e) 该文件不是任何 contract pin；(f) 事件数仅写入测试输出不作数值断言。测试总数不变（44）。test_freeze.py 为 contract pin，已重建重锁（17 pin 重算）并刷新输出目录。原句（旧断言）以上述引述保留，未静默删改。
