# L8 预注册（自动循环 2026-10-30）

- **plan_id**: `l8-20261030`
- **分支**: `loop8-2026-10-30`（自 **main** `016dbfe` = PR#11 L7 集成点切出）
- **集成前置（D 前已完成）**: PR#11 已合并 L7 至 main；本环零真实模型调用、零新现场。
- **随环首提交**: L7 审计终稿补全入库（auditor 于 PR#11 合并后 13:52 重生机械收据
  F1 终态 PASS 12/12 + evidence_line 实填证据行）——合并后产生、未入库的 L7 材料
  随本分支首提交 `ccc357a` 入库，lead 代提交并注明 provenance。
- **D 封印**: 本文件提交后立即执行；实现 commit 必须晚于 D。
- **验收**: judge + auditor 双验（零模型工具链环，沿 L3/L7 先例；reviewer 不派）。

## 选题（源自 L7 池结转）

| 池项 | 处置 |
|---|---|
| AUD-L7-O1 废止收据机器可读指针 | **L8-A（主项）**：废止链机器可读，见下（含对 O1 原文方向的设计偏离声明） |
| PREREG 异常类型措辞（L7-O1 observation） | **L8-B（次项）**：预注册模板条文化「异常类如实申报」+ 本环自食 |
| l4/l5 现场重跑适配（U-1） | 不入本环——现场封存；跨批重演已按设计放弃（L7 history-replay-design-note），重跑前置条件未触发 |
| T22d fixture 退役（U-2） | 不入本环——runner 位于已封存 L6 现场，改动即破坏历史批零改动红线 |
| O-2 live-ledger freshness 对账 | 不入本环——收尾清单已含 invariant 必跑（27cd39d 立制）；freshness 专项对账留池 |

## L8-A 设计（共享证据工具修订——废止链机器可读）

- **修前**: 收据废止仅靠**文件名后缀** `-VOIDED-<reason>`（人读）维系；收据 JSON 正文
  无任何机器可读指针（唯一线索为 prose 附注，如 L7 终局收据 `tool` 字段内
  "r1-r6 voided chain in dir"）。链完整性目前只能靠 README 叙述+人眼比对。
- **修后**: 存续（非废止）收据 JSON 新增**可选**机器字段
  `"supersedes": [{"file": <被废止收据文件名或相对路径>, "sha256": <64 位小写全哈希>}, ...]`。
  `receipt_check.py` 新增第 4 类检查 **supersession**（仅对含该字段的 JSON 文档生效）：
  1. 形态严格：`supersedes` 必须为 list；每项必须为 dict 且**恰有** `file`+`sha256`
     两键；`sha256` 匹配 `^[0-9a-f]{64}$`；`file` 为非空字符串——违反即 violation。
  2. 指针验证：每项 `file` 相对**收据自身父目录**解析，文件必须存在、sha256 与实算
     **全哈希一致**、且文件名必须含 `VOIDED`（废止标记人机双载体）。
  3. 链卫生：禁止自引（指向收据自身）；禁止重复条目；沿链上行（被指文件若亦含
     `supersedes`）深度 ≤16 内不得回到自身（环检测）。
  4. 任一 violation → 该文档 `ok=false`。
  - **方向选择声明（偏离 AUD-L7-O1 原文）**: O1 原文建议在**废止收据**上加
    `superseded_by`（前向指针）。本设计改在**存续收据**上加 `supersedes`（后向指针），
    理由：终局收据文件名在废止时刻不可预知（L7 链实证：r1-r6 全废、终局名为
    `l7-gate-recompute-receipt.json` 无 r7 后缀），前向指针要么事后改已定稿字节
    （违 write-once 纪律）要么只能存空哈希（弱验证）。后向指针单次写、全哈希锚定、
    可同时机械验证被指文件名含 VOIDED；机器可读性等价、验证强度更高。
- **正例**: L8 收尾在 `5-评测报告/L8证据链修订-2026-10-30/` 以 write-once 新建
  demo 收据（kind=`l8-supersession-demo`），`supersedes` 引用**真实 L7 六文件废止链**
  （真实文件名+实算真实 sha256），以 `receipt_check.py` 实跑全过——证明验证器对
  真实链数据可用；**历史收据零字节改动**（新字段仅向后生效）。
- **近似错误例**（selftest 内新增负例组）: sha256 篡改→fail；file 不存在→fail；
  被指文件名无 VOIDED→fail；自引→fail；多余键→fail；sha 非 64 位小写→fail；
  supersedes 非 list→fail；链环→fail。
- **影响面声明**: `receipt_check.py` 为共享证据工具；现有 16 自测用例+48 test_freeze
  不受影响（新检查仅对含新字段文档生效，无字段=行为逐字节不变）；
  `manifest_receipt.py` 不涉及（目录清单与废止链正交）；gate 判分语义零触及；
  历史收据（L6/L7 全部 VOIDED 与终局收据）零字节改动。
- **独立验收**: judge 独立复跑 receipt_check selftest+demo 收据实跑+自行构造至少
  1 个 PREREG 未列的负例；auditor 对抗性盲审。

## L8-B 设计（预注册模板，纯文档+自食）

- 新增 `1-评测方案/工具链/PREREG-template.md`：预注册必填字段清单——plan_id/分支/
  集成前置/选题表（池项逐项处置）/各主项设计（修前/修后/正例/近似错误例/影响面/
  独立验收）/**异常类如实申报条款**/纪律承诺。
- **异常类如实申报条款**: 预注册所写异常类必须与实现实际 raise 的类**逐字一致**，
  实现期由 lead 复核、验收期由 judge 抽验；反例=L7-O1（预注册 ValueError vs 实现
  GateError，措辞级偏差被审计记 observation）。模板同时要求：报错文案含修订标记
  （如「L8-A」）、错误路径可被独立脚本断言。
- **自食**: 本 PREREG 即按模板必填字段撰写；验收时 judge 逐字段可指认。

## 纪律承诺

D 先于实现；历史收据零字节改动；哈希/时刻一律脚本生成；write-once（--out 目标已存
在即拒）；CHANGELOG 不动；live 台账收尾登记并**必跑 work-registry 不变量测试**
（v3 test_freeze 全绿，L6 新制度）；收尾 PR 合并 main；结论五段结构。
