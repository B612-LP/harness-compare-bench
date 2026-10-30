# 第五代冻结合同（freeze-20261029-v5）：b2 补跑批治理合同

本目录是 [第四代冻结](<../可信冻结-2026-10-29-v4/README.md>) 的**治理继任合同**，是 r1102-formal-b2（formal-b1 唯一非合规终局槽位的配额制作废重跑）的准入与判卷依据。继任语义、封印语义、pin_class 判定规则、信任边界与三件套口径均继承 v4（README 逐节适用，本文件只写差异），落盘时刻见 config `effective_at`/`collected_at`（同值，实钟）。

## 与 v4 的差异（全部差异，无其他）

1. **4 处常量**：`RULE = "freeze-20261029-v5"`；`BASE`/`OUT` 指向 v5 目录；`effective_at`/`collected_at` 推进到本代封印时刻（同值）。
2. **`official_slots` = B 组 1 slot**：`B_native|doubao|exercism-py-6`，`plan_id = "formal-b2-20261031"`、`slot_id = "b2-doubao-exercism-py-6"`、`plan_sha256` 绑定 [registration-plan.json](<../../1-评测方案/正式批次-2026-10-31/registration-plan.json>)，与该计划 1 条 registration 双向一一对应。前代语义不变：v4 仍是 r1101-formal-b1（官方表 B_native 8 行）的合同记录；**v5 不重新准入任何历史行或 v4 行**（历史候选仅以 rejected+理由列出）。
3. **`case_snapshots` 逐字节继任 v4**：自 v4 封印以来公开树 `2-用例/` 零改动（封印时 diff 实证，verify_seal 现算复核），五题快照哈希与 v4 config 相同；无 L6 式判卷器推进事由。
4. **`historical_ledger`/`work_registry` 引用与 v4 相同**（公开派生账 + v2 registry，sha 未漂移）。
5. **`config-schema.json` 代际自身元数据更新**（先例逐代更新）：`$id` → `freeze-20261029-v5/config`；`rule_version` const → `freeze-20261029-v5`；succession 措辞改 v5。其余语义与 v4 逐字节相同；`import-schema.json` 沿袭未改（先例同 v3/v4）。
6. **`test_freeze.py` v5 适配**（合成测试逐字节不动，REAL 断言改写）：
   - pin 卫生断言与六账动态并集断言继承 v4 封印修订-1 定型逻辑，仅换 v5 命名；
   - official 表 build 后门断言改为**结果鲁棒式**：`B_native` 只能是空或恰 `formal-b2-doubao-exercism-py-6-01` 一行、b2 产品行必居 groups/rejected 之一、两个非产品事件（预检/自测）必按类别拒绝、96 条历史行全 rejected、`formal-b1-` 行不得出现在 v5 候选——**吸取 v4 封印修订-1 教训（build 后门断言预写未知终局导致修订-1），封印时不预写运行结果**，三种合规终局（准入/污染 X/发射期 infra 拒绝）下断言均成立；
   - 测试总数 49→49（仅改名与 REAL 断言改写）。
7. **`freeze.lock.json`**：`trust_boundary` 从 v4 lock 逐字复制；pin 集合继承 v4 构成（6 引擎 contract + ledger/registry/b2-plan/固定读取面/20 份 v2 registry 收据 contract + 3 份引擎目录 live_doc），其中 b1 计划 pin 换为 b2 计划、引擎 6 文件换 v5 路径并全部现算 sha；总 32 pin：contract 29 / live_doc 3。本地缺失文件一律不入 pin（v4 规则继承）。
8. **`example-source.json` / `import-example.json` / `ledger_reconcile.py`**：与 v4 逐字节相同（无版本痕迹，无需改）。

## 本批特别声明

- 本批是**运行记录模板 schema v2 的首个执行批**（十字段强制），也是[桌面工作区边界判定线](<../../1-评测方案/正式批次-2026-10-31/判定线-2026-10-31-桌面工作区边界.md>)的首个适用批（任务书硬条款 + 越界即 X + 终审加查 find/ls）；两者均在注册计划 note 中预注册声明，先于运行封存。
- 豆包检索三件套与 formal-b1 相同（任务书禁网条款 + 轨迹披露 + integrity_scan 兜底）；实证 clean 记 V、实证命中记 X。
- 配额制：本 slot 仅 1 次发射（kind=first），发射失败即停不重试不补跑；probe 绿但会话无效仍按 `infrastructure_invalid` 合规拒绝。**三种终局均为合规终局，本代封印不预设结果。**

## 输出重建披露-1（2026-10-31 03:45+08:00，L13 环；与 v4 同款维护规则，显式披露）

本代 build 产物同样内嵌 `未知登记.json` 的 build 时现算 pin（封印时 `8bffbcb6…` → L12 `fb754c84…` → L13 收口 `b4a5e53c…`）与 live_doc README 现算 sha；活登记/本目录 README 变更后需**确定性重建**（同 commit 提交）：`python3 freeze.py build --imports 3-表现现场/r1102-formal-b2/formal-b2-events.json`（**必须带 --imports**，裸 build 丢 b2 导入行致 B_native 1→0）。重建对拍纪律同 v4：变更行应全部为 sha 字段，判定数字与 official 表零变化。首次触发=本披露提交（对拍 172 对 sha-only，verify exit 0）。

## 封印修订-2（2026-10-31 02:19+08:00，运行完成后、事件导入前；显式披露）

注册计划的 `registration[0].parent_id` 在封印时预写为 `formal-b1-doubao-exercism-py-6-01`，与机械契约冲突：`validate_event` 要求 selection 与计划条目**逐字段全等**，而 `select_events` 队列要求首事件 `kind=first` 且 `parent_id=null`——两者不可同时满足，validate-import 以 `queue must start at first` 拒绝。修正：计划该字段 → `null`（先承关系由 `design.predecessor` 与条目 `reason` 叙述保留，跨批作废重跑在本队列语义中=新 plan 新 slot 的 first）；级联更新 `config.official_slots.plan_sha256`（`d7f21136…` → `f050cbe8…`）与 lock 中 config、registration-plan 两个 contract pin（现算）。**其余 30 个 pin 零变动（逐一实测复核）**；运行操作严格按封印计划执行（单次发射、无重试），未受修订影响；修订后 validate-import / build / verify 全 exit 0、49/49 测试通过。修订时序：D 封印（`dec790a`）→ 运行（01:27–02:07）→ 修订-2（02:19）→ 导入与 build。
