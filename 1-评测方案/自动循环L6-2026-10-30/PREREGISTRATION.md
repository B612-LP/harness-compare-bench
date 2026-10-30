# L6 预注册（自动循环 2026-10-30）

- **plan_id**: `l6-20261030`
- **分支**: `loop6-2026-10-30`（自 `loop5-2026-10-30`@`79cebe0` 切出）
- **D 封印**: 本文件 + `plan.json` + `prepare_design.py` + `execution_seal.py`（+其测试）提交后立即执行；**任何实现 commit 必须晚于 D**。
- **真实预算**: WB 桌面 × 1 槽（`bird-ca-schools-15` rep1，timeout 1800s）。judge/auditor/reviewer 验收全程零模型。
- **模型**: 现行定案不变（A 组 WorkBuddy 桌面走其可用模型，按 L5 runner 既有路由）。

## 选题（源自 L5 池结转，2026-10-30 综合结论附表）

| 池项 | 处置 |
|---|---|
| L5-P1 | **L6-A（主项）**：bird checker 判分文档元数据完备（`n_tasks`/`guards_used`），修订后 E 封印真实重跑复判 formal |
| L5-P3 | **L6-C（次项，零模型）**：收据自引排除（AUD-L5-O1 wart 类）——receipt_check 规则 + self-excluded 收据模板 |
| L5-P2 | 已修（8f25d64，post-admission）：WB runner 五件套随 L6 现场按位拷贝自动纳入 pin，无新改动 |
| L5-P4、L3 尾项 | 留池，不入本环 |

## L6-A 设计（判卷器修订，全套纪律）

- **修前**：checker `v1.2-q26-frpm`（`CONTRACT_REVISION=b2-tighten-2026-10-27`）输出 JSON 无
  `n_tasks`/`guards_used` → WB runner `derive_guards` insufficient_fields → gate
  「meta.judge.guards_used 缺失（无法按 guard 重算）」→ L5 wb-bird `formal=False`
  （raw 100.00000000 保留 observed，非基础设施问题）。
- **修后**：输出 JSON **纯增量两键，判分语义零改动**：
  - `"n_tasks": N_QUESTIONS`（=15；gate 重算要求 `judge.n_tasks == possible_raw`）；
  - `"guards_used": ["input_integrity","answers_file","answers_schema","answers_coverage"]`
    （静态：恰为 checks 中四个非任务项 id，与 runner 索引序首调和组合的推导结果一致；
    gate 以该表划分守卫项/计分项）。
  - `CONTRACT_REVISION` → `l6-meta-fields-2026-10-30`；`CHECKER_VERSION` **不变**
    （truth.json 冻结钉 `1.2-q26-frpm`，交叉校验仍过）。
- **spec.md**：§2 dated 补记（修订动机=工具链元数据完备，不涉判分口径）。
- **正例**：oracle 全绿且新两键在案、值正确。
- **近似错误例**（证明新字段参与重算而非装饰）：
  (a) 篡改输出 `n_tasks` ≠ 15 → gate 计数不等拒绝；
  (b) 篡改 `guards_used` 漏一项 → gate `possible_raw` ≠ contract 分母拒绝。
- **独立验收**：judge 复算（修前/修后 diff + 正例 + 近似错误例 + 历史复算收据）。
- **历史复算**：L4 冻结 17 行中全部 bird 行 + L5 全部 6 行 raw 复判——
  断言 `reward`/`weighted`/`checks` 逐值不变，仅新增两键；**0 翻转**。
- **contract**：`prepare_design.py --plan-only` 先行（D 前）；`--contract-only` 于实现完成后
  生成（pin 修订后 bird checker sha；其余四 case 继承 L5 不变；
  `rule_version=l6-20261030-batch-v1`）。E 封印 manifest 钉 contract.json 终态。

## L6-C 设计（收据自引排除，零模型）

- **receipt_check.py 新规则**：JSON 收据含 dict 型 `files_sha256` 映射时，若其键含收据
  自身文件名/路径 → violation「self-referenced hash entry（AUD-L5-O1）」。
- **新增 manifest_receipt.py**：write-once 清单收据生成器——`files_sha256` 不含自身、
  显式 `self_excluded` 字段记录自身路径、`live_doc_drift: []`、目标已存在即拒（C-1 同款）。
- **selftest 正负例**：自排除收据 pass；自引收据 fail。
- **历史复算**：对 L5 关键收据 + evidence-kit 历史 selftest receipts 复跑 receipt_check——
  预期唯一新 fail = E2 `abort-receipt.json`（真实 wart 实证）；其余全 ok。

## 实批计划（plan.json 单槽）

- `l6-20261030-wb-gateway-bird-ca-schools-15-r1`（workbuddy，rep1，timeout 1800s）。
- 现场目录 `3-表现现场/l6-20261030-wb-gateway/`；runner 五件套自 L5 现场按位拷贝
  （diff=0 机器收据），零改动；输出全部落新现场，**历史批零改动红线不变**。
- 判定：gate v2 `--plan-dir` 本批目录，formal 判据与 L5 完全一致。
- **成功标准 = formal 准入链路修复**（证据链完备可 formal）；分数不作目标——
  真实作答若错，`reward=0` 亦是合法 formal 结果，如实记录。

## 边界与结论口径

- 本环结果**不回写** L5/L4 结论（历史批冻结）；跨批比较仅作观察性披露。
- 单槽复验不提供分数稳定性信息，不入横向结论表；横向表述仍以 L5 canonical 为准。

## 风险 / 未知 / 停止条件

- wb-bird 真实分数未知：不影响链路验证目标；若答错 → formal=True/reward=0 如实入账。
- derive_guards 非满分分支：L5 已验证，本环合成例覆盖满分与守卫失败两分支。
- WB 基础设施故障（renderer 未就绪等）→ 按 R6 就绪等待规程；E 后首槽 REFUSED →
  fail-closed 停批、零消耗保全、重封裁决（消耗单列，无 formal 资格）。
- 真实槽 checker 行为与合成例不一致 → 停，查清后按判卷器修订纪律处置（不得边跑边改）。

## 纪律承诺

D 先于实现；E 前不改判分语义；凭据零入库；哈希/时刻一律脚本生成；
CHANGELOG 不动（未获授权）；live 台账收尾登记 `work:l6-six-ledger-index-20261030`；
结论用五段结构；未知写明影响/下一步/停止条件。
