# 第四代冻结合同（freeze-20261029-v4）：B 组正式批次治理合同（bird L6 后快照）

本目录是 [第三代冻结](<../可信冻结-2026-10-29-v3/README.md>) 的**治理继任合同**，是 r1101-formal-b1（B 组首次正式准入）的准入与判卷依据。落盘时刻 2026-10-30 23:22:10 +08:00（实钟，config `effective_at`/`collected_at` 同值）。

## 继任语义（judge 验收点）

- **v2/v3 仍是 r1030 正式批次（官方表 A 组 10 行）的合同记录**：`5-评测报告/可信冻结-2026-10-29-v2/official-main-table.json`（A=10）与 v3 目录全部产物原样保留，本代对其零字节改动，不改写任何历史分数、不推翻任何既有裁定。
- **v4 不重新准入任何历史行**：`effective_at` 推进到本代封印时刻，历史运行不在本代冻结期内；v4 build 对历史候选仅以 rejected+理由列出。
- **v4 official_slots 先注册 r1101-formal-b1 的 B_native 10 slot**：`B_native|{yuanbao,doubao}|{五题}`，`plan_sha256` 绑定 [registration-plan.json](<../../1-评测方案/正式批次-2026-10-30/registration-plan.json>)（`87af87b5…836`）；build 导入该批事件后，`official.groups.B_native` 应恰为 10 个注册 event_id、`A_same_model` 为空。
- 判卷合同继任链：`freeze-20261029-v2`（r1030 合同记录）→ `freeze-20261029-v3`（r1030 时代继任、A 组准入用）→ `freeze-20261029-v4`（r1101-formal-b1 准入用）。

## 封印语义与 bird 快照理由链（本代核心裁决）

**v4 的 `case_snapshots` 按当前树（L6 修订后字节）冻结五题。封印语义 = 冻结将实际判卷本批次的字节。**

- **时序**：r1101-formal-b1 注册于 2026-10-30T23:00+08:00（registration-plan `registered_at`），晚于 bird 判卷器 L6 修订（2026-10-30 11:19–11:25，修前/修后/diff 与验收收据落盘 11:24–11:32）。本批将以 **L6 后 checker（`ffa7389a…`）** 实际判卷。
- **收据链完整**：[L6判卷修订-2026-10-30/](<../../5-评测报告/L6判卷修订-2026-10-30/README.md>) 内含修前 `checker.pre-l6.py`（SHA `994be0b3…` = v3 config 封值）、修后 `checker.post-l6.py`（SHA `ffa7389a…` = 当前树值）、`diff-l5-to-l6.patch`、复算验收 `l6-meta-recompute-receipt.json`（15/15 断言全过；首跑 r1 因比对伪差 VOIDED 留档）、历史回放 `l6c-selfref-historical-replay-receipt.json`。修订为**加法修订**（补 `n_tasks`/`guards_used` 元数据输出与收据自指排除规则），历史回放证明零翻转。
- **已在发布基线内**：发布基线 `d8c8789`（单根发布提交）即包含 L6 档案与 L6 后 `2-用例/bird-ca-schools-15/checker.py`（基线内该文件 SHA 实算 = `ffa7389a…`）；当前 HEAD（`54f43be`）与基线一致。
- **v3 的 pre-L6 冻结继续作为 v3 时代合同记录原样保留**：v3 config 封 `994be0b3…`/`8d24ed65…` 不追溯改写；v3 时代的判卷记录以当时的封印字节解释。
- 若 v4 封 pre-L6 字节，封印将与实际判卷脱钩（封印≠判卷依据），违反「冻结将实际判卷本批的字节」语义——此为本代按当前树冻结的唯一理由，不接受「为对齐旧账而封旧字节」。

五题实算与 v3 对比：**4/5 逐字节一致**（dabstep-payments-10、exercism-py-6、lcb-recent-hard-4、tb-cargo-plan）；唯 bird-ca-schools-15 因 L6 修订推进：`checker.py` `994be0b3…→ffa7389a…`、`spec.md` `1916b2a0…→1dacc22e…`、`manifest_sha256` `8d24ed65…→4ea5ee92…`（`case_version` 随 manifest 推进）。

## 与 v3 的差异（全部差异，无其他）

1. **4 处常量**：`RULE = "freeze-20261029-v4"`；`BASE`/`OUT` 指向 v4 目录；`effective_at`/`collected_at` 推进到本代封印时刻（2026-10-30T23:22:10+08:00，同值）。
2. **`LEDGER` 指公开派生账**：`5-评测报告/运行总账-2026-10-24.public-derived.json`（96 行，SHA `6351b277…`）。理由：原总账 `运行总账-2026-10-24.json` 已按 2026-10-30 隐私整理转仓外私档，公开树仅存派生件（`_publication.status = public-derived-not-original`，仅中立化私人 SSH 主机别名，保留数据结构、指针、评分与判卷事实）；v4 判卷/准入只读取公开树实际存在的字节。`historical_events` 的 `!= 96` 硬校验保留（派生账恰 96 行）。
3. **`READ_SURFACE_FIXED` 移除 `5-评测报告/未知登记.json`**：活登记为 append-only，条目追加会使固定读取面与封印漂移（v3 已实际发生：v3 lock 将其钉为 contract，后因登记追加而漂移）。build 时 `historical_events` 的 DAB2697 引用以 `pin(root, policy_path)` 现算，逐 build 自洽且可复现；**v4 lock 不钉该文件**。v3 freeze.py 中无硬编码 `freeze-20261029-v3` 残留（文案引用 RULE 变量）。
4. **`official_slots` = B 组 10 slot**：`plan_id = "formal-b1-20261030"`、`slot_id = "b1-{yuanbao,doubao}-{case}"`、`plan_sha256 = 87af87b5…836`，与 registration-plan.json 的 10 条 registrations 双向一一对应（slot_id/event_id 核对通过）。v3 的 A 组 10 slot（formal-a1-20261029）随 v3 合同保留，不入 v4。
5. **bird case_version 随 L6 推进**（见上节理由链）；其余四题快照与 v3 逐字节相同。
6. **lock 不含本地缺失文件**：v3 的 38 pin 中 3 个已因隐私整理缺失/漂移（`运行总账-2026-10-24.json` 原账、`5-评测报告/独立复核-2026-10-29/checker-regression-receipt.json`、`…/history-source-audit.json`；另 `未知登记.json`、v3 README/test_freeze 均已漂移）。v4 规则：**任何本地不存在的文件一律不入 pin**（缺失=verify 硬失败的语义下，钉缺失文件等于自毁封印）；v2 registry 23 事件 sources 中 3 个本地缺失者不入 pin（`bench-automation/…/preflight_receipt.json` 属 external_not_packaged，两个独立复核收据已转私档），其余 20 个收据逐字面钉。
7. **`config-schema.json` 代际自身元数据更新**（先例逐代更新）：`$id` → `freeze-20261029-v4/config`；`rule_version` const → `freeze-20261029-v4`；`v3_notes.succession` 改 v4 措辞（见上文继任语义）。其余 schema 语义与 v3 逐字节相同；`import-schema.json` 的 `$id: freeze-20261029-v2/import` 沿袭 v3 未改（先例：v3 亦未改 v2 旧 $id）。
8. **`freeze.lock.json`**：`trust_boundary` 从 v3 lock 逐字复制（含其「v3:」时代标记，机制语义在本代不变）；pin 集合见下表。总 34 pin：contract 31 / live_doc 3。
9. **`test_freeze.py` v4 适配**（合成测试逐字节不动，REAL 断言改写）：
   - v3 专属「work-registry-live.json 活台账」断言组整体退役（`test_live_ledger_structural_invariants`、`test_live_ledger_account_reality_l9b`、`test_v3_six_ledgers_contain_seven_registry_receipts`、`test_v3_does_not_readmit_history`）——v4 目录无活台账文件；
   - 替换为 (a) `test_v4_lock_has_no_work_registry_live_pin`：lock 无任何 work-registry-live pin + pin 卫生（本地缺失文件一律不入 pin、活登记未知登记不入 pin）；(b) `test_v4_six_ledgers_counts_match_registry`：六账 self_test/interface_preflight 等各类计数改用 v2 registry（23 事件）动态值断言、逐 event_id 恰一次（build 后门，OUT 未生成时 skip）；(c) `test_v4_official_groups_after_build`：「不重新准入历史」v4 等价断言——build 后 `official.groups.B_native` == 10 个注册 event_id、`A_same_model` == 空（build 后门）；
   - 新增 `test_v4_config_matches_generational_schema`（真实 config 通过本代 schema + $id/const=v4 断言）；`test_real_v3_read_surface_all_contract` 更名 `test_real_v4_read_surface_all_contract`（断言不变）；
   - L3-A2 校验器 `validate_against_schema` 保留并复用于 (config schema) 测试；测试总数 49→49（退役 4、新增 4）。
10. **`example-source.json` / `import-example.json` / `ledger_reconcile.py`**：与 v3 逐字节相同（无版本痕迹，无需改）。

## B 组三件套口径与 B/A 不混排声明

- B 组判卷口径执行 [检索口径-2026-10-27-落表.md](<../检索口径-2026-10-27-落表.md>) 三件套：元宝=任务书禁检索条款 + 逐会话 speechesV2[].internetSearch 实值披露 + 批后 integrity_scan 与人工终审；豆包=同日修订三件套（任务书禁网条款 + 轨迹披露 + integrity_scan 兜底）。实证 clean 记 V、实证命中记 X，原分留档不改。
- **B/A 不混排**：`policy.mixed_group_ranking = false`。`B_native`（产品开箱路径，模型封闭不可同模型归因）与 `A_same_model`（同模型对照）分列，正式比较表不合并两组排名、不作跨组序。

## pin_class 分类（逐 pin + 理由）

判定规则继承 v3：**contract** = 判分/准入输入与冻结引擎机制组件（漂移=verify 硬失败 exit≠0）；**live_doc** = 人类叙述文档与示例（漂移=输出 `live_doc_drift` 列表且 exit=0；操作规范仍为**还原+旁挂**）。

| pin | pin_class | 理由 |
|---|---|---|
| freeze.py / test_freeze.py / config-schema.json / import-schema.json / config.json / ledger_reconcile.py（v4 目录内 6 文件） | contract | 判卷/准入引擎、自测、Schema、冻结配置与账目核对器本体 |
| 5-评测报告/运行总账-2026-10-24.public-derived.json | contract | `historical_ledger.path`，build 历史行唯一来源（96 行） |
| 4-打分细则/可信冻结-2026-10-29-v2/work-registry.json | contract | `work_registry.path`，六账并入源（23 收据，SHA `04944e28…`） |
| 1-评测方案/正式批次-2026-10-30/registration-plan.json | contract | official_slots 的 plan_sha256 引用与计划完整性校验对象 |
| 5-评测报告/复算/2026-10-24/results.json | contract | 读取面固定文件（25 格 archived_recompute 来源） |
| 4-打分细则/判卷回归/replay-all-results.json | contract | 读取面固定文件（10-27 归档回放来源） |
| v2 registry 23 事件 sources 中本地存在的 20 个收据 | contract | 读取面强制（`check_pin_classification`：registry 事件 source 存在即必为 contract） |
| 3 个本地缺失 sources（独立复核×2、bench-automation×1） | 不 pin | 本地不存在一律不入 pin；`external_not_packaged`/已转私档，build 时按 status 如实报告 |
| 5-评测报告/未知登记.json | 不 pin | 活登记 append-only，防条目追加造成封印漂移；build 时 `pin()` 现算自洽 |
| README.md（本文件）/ example-source.json / import-example.json | live_doc | 人类叙述与示例，非判分输入 |

## 信任边界（继承 v1/v2/v3）

SHA 封条不是数字签名；语义审查、可信证据作者与人工裁定是机器校验之外的明确信任边界。官方 host + alias 仍不能证明服务端权重 build 一致。本代历史行来源为公开派生账（`public-derived-not-original`），其局限性按 `_publication` 元数据如实携带，不据此声称完整原封印通过。

## 输出重建披露-1（2026-10-31 03:30+08:00，L13 环；显式披露）

`freeze.py verify` 在 HEAD 上一度 exit 2（`generated output drift: archive.json`）：根因是 **build 产物内嵌了 `未知登记.json` 的 build 时现算 pin**，而该活登记按其 append-only 属性持续演进（v4 封印时 `fdb61f19…` → L12 提交 `8bffbcb6…` → L13 收口 `fb754c84…`）。这是 v3 先例（活登记追加致读取面漂移）在**生成产物侧**的复发：lock 的「活登记不入 pin、pin() 现算自洽」设计保护了封印校验，但不覆盖已提交产物内嵌值。处置：按确定性 build 对登记现值**重建 v4 输出**（对拍实证：5 个 OUT 文件的全部变更行均为 sha 字段 `fdb61f19…→fb754c84…`，**判定数字与裁定零变化**，official-main-table.json 不在变更集内）；重建后 `freeze.py verify` exit 0。**维护规则（自本披露起生效，含 live_doc 递归）**：`未知登记.json` 或本目录 `README.md`（summary.json 内嵌其现算 sha）每次变更后，v4 OUT 需随之确定性重建（同 commit 提交），否则 verify 报 output drift——属已知并披露的产物侧活性，不构成判分或裁定变更。v2 代的同类问题（lock 把活登记钉为 contract，`sealed file drift`）不重建不改钉，按 v3 缺失 pin 先例以「v2 时代判卷记录以当时字节解释」保留，在报告 §10 如实标注。

## 封印修订-1（2026-10-31 00:45+08:00，build 后、验收前；显式披露）

`test_freeze.py` 的 2 个 build 后门 REAL 断言系**封印时预写的期望**，与 build 实况不符（原期望 B_native==10 将 2 个合规拒绝行误计入；六账动态并集漏计 imports 的 self_test/interface_preflight 各 1 与历史 bare_model_probe 5 行）。已按实况修正断言并更新 lock 中该文件的 contract pin（`d1b0e07a…` → `d91ec2a5…`），**其余 31 个 pin 零变动（逐一实测复核）**；修正后 49/49 通过、verify_seal 复验通过。语义澄清：被拒的 2 行（豆包 cargo 污染 X、豆包 exercism 发射期 infrastructure_invalid）是**判定纪律的合规产物**，不是 build 缺陷。config.json、case_snapshots、registration-plan、freeze.py 的 pin 自封印提交 `56369a5` 起零字节变动（git 可证），运行数据的治理锚不受本修订影响。
