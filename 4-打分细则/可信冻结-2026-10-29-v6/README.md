# 第六代冻结合同（freeze-20261029-v6）：b3 补跑批治理合同

本目录是 [第五代冻结](<../可信冻结-2026-10-29-v5/README.md>) 的**治理继任合同**，是 r1104-formal-b3（formal-b1 唯一残留非合规终局槽位豆包×tb-cargo-plan 的配额制作废重跑）的准入与判卷依据。继任语义、封印语义、pin_class 判定规则、信任边界与三件套口径均继承 v4/v5（README 逐节适用，本文件只写差异），落盘时刻见 config `effective_at`/`collected_at`（同值，实钟）。

## 与 v5 的差异（全部差异，无其他）

1. **4 处常量**：`RULE = "freeze-20261029-v6"`；`BASE`/`OUT` 指向 v6 目录；`effective_at`/`collected_at` 推进到本代封印时刻（同值）。
2. **`official_slots` = B 组 1 slot**：`B_native|doubao|tb-cargo-plan`，`plan_id = "formal-b3-20261031"`、`slot_id = "b3-doubao-tb-cargo-plan"`、`plan_sha256` 绑定 [registration-plan-b3-20261031.json](<../../1-评测方案/正式批次-2026-10-31/registration-plan-b3-20261031.json>)（**独占新路径**：v5 lock 已钉 b2 计划文件字节，绝不回写原文件——v3 台账教训同型），与该计划 1 条 registration 双向一一对应。前代语义不变：v5 仍是 r1102-formal-b2（官方表 B_native 1 行）的合同记录；**v6 不重新准入任何历史行、v4 行或 v5 行**（历史候选仅以 rejected+理由列出）。
3. **`case_snapshots` 逐字节继任 v5**：自 v5 封印以来公开树 `2-用例/` 零改动（封印时 diff 实证，verify_seal 现算复核），五题快照哈希与 v5 config 相同；无判卷器推进事由。
4. **`historical_ledger`/`work_registry` 引用与 v5 相同**（公开派生账 + v2 registry，sha 未漂移）。
5. **`config-schema.json` 代际自身元数据更新**（先例逐代更新）：`$id` → `freeze-20261029-v6/config`；`rule_version` const → `freeze-20261029-v6`；succession 措辞改 v6。其余语义与 v5 逐字节相同；`import-schema.json` 沿袭未改（先例同 v3/v4/v5）。
6. **`test_freeze.py` v6 适配**（合成测试逐字节不动，REAL 断言改写）：
   - pin 卫生断言与六账动态并集断言继承 v4 封印修订-1 定型逻辑，仅换 v6 命名；
   - official 表 build 后门断言维持 **结果鲁棒式**（v5 定型）：`B_native` 只能是空或恰 `formal-b3-doubao-tb-cargo-plan-01` 一行、b3 产品行必居 groups/rejected 之一、两个非产品事件（预检/自测）必按类别拒绝、96 条历史行全 rejected、`formal-b1-`/`formal-b2-` 行不得出现在 v6 候选——封印时不预写运行结果，三种合规终局（准入/污染 X/发射期 infra 拒绝）下断言均成立；
   - 测试总数 49→49（仅改名与 REAL 断言改写）。
7. **`freeze.lock.json`**：`trust_boundary` 从 v5 lock 逐字复制；pin 集合继承 v5 构成，其中 b2 计划 contract pin 换为 b3 计划（独占新路径）、引擎 6 文件与 3 份 live_doc 换 v6 路径并全部现算 sha；总 32 pin：contract 29 / live_doc 3。本地缺失文件一律不入 pin（v4 规则继承）。
8. **`example-source.json` / `import-example.json` / `ledger_reconcile.py`**：与 v5 逐字节相同（无版本痕迹，无需改）。

## 本批特别声明

- **产品环境披露**：b1 前承（r1101）与 b2（r1102）跑于豆包 v2.33.7；本批 app 已两连跳自动更新至 **v2.34.11**（2026-10-31 01:28/10:55，用户已关闭自动更新）。v2.34 引入 composer 权限模式选择器（始终询问[新版默认]/按需确认/全部允许）与 saman 沙箱运行时，trajectory 改为任务结束一次性落盘。本批批前将权限模式设为「**全部允许**」（与 v2.33 时代 b1/b2 的实际行为面等价：外部写/联网无逐次确认门），driver 固化该设置并在运行记录披露 app 版本与权限模式；产品版本差异按老师第 1 条（产品版本字段）如实入账。
- b3 机械形态承 L13 PREREG §3 事项①（经其 §0.5 修正）+ L14 PREREG §0.5/§0.6 承前声明：新 plan 新 slot、kind=first、parent_id=null，SAFE_POLICY `invalid_only_next_registered_max_1` 政策层兑现（前承=formal-b1 豆包×cargo 污染 X 场，原分 100 留档不采用，1 次重跑不择优）。
- 桌面工作区边界判定线与豆包检索三件套同 formal-b1/b2（任务书硬条款+禁网条款 + 轨迹披露 + integrity_scan 兜底）；实证 clean 记 V、实证命中记 X。
- 配额制：本 slot 仅 1 次发射（kind=first），发射失败即停不重试不补跑；probe 绿但会话无效仍按 `infrastructure_invalid` 合规拒绝。**三种终局均为合规终局，本代封印不预设结果。**

## 输出重建维护规则（L13 教训定型，前瞻披露）

本代 build 产物同样内嵌 `未知登记.json` 的 build 时现算 sha 与 live_doc README 现算 sha；活登记/本目录 README 任何变更后需**同 commit 确定性重建**：`python3 freeze.py build --imports 3-表现现场/r1104-formal-b3/formal-b3-events.json`（**必须带 --imports**，裸 build 丢 b3 导入行）。重建对拍纪律：变更行应全部为 sha 字段，判定数字与 official 表零变化。
