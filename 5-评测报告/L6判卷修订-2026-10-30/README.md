# L6 判卷修订档案（2026-10-30）

L6 闭环两项工具链修订的修前/修后/正例/近似错误例/独立验收/历史复算集中归档。
预注册：[自动循环L6 PREREGISTRATION](<../../1-评测方案/自动循环L6-2026-10-30/PREREGISTRATION.md>)。

## L6-A：bird checker 元数据完备（L5-P1）

- **修前**：`checker.py v1.2-q26-frpm`（`CONTRACT_REVISION=b2-tighten-2026-10-27`）输出无
  `n_tasks`/`guards_used` → WB runner `derive_guards` insufficient_fields → gate
  「无法按 guard 重算」→ L5 wb-bird `formal=False`（raw 100.0 保留 observed）。
- **修后**：输出**纯增量两键**——`n_tasks=15`、
  `guards_used=["input_integrity","answers_file","answers_schema","answers_coverage"]`；
  `CONTRACT_REVISION=l6-meta-fields-2026-10-30`；`CHECKER_VERSION` 不变（truth 冻结钉）。
  判分口径零改动。
- **正例**：checker selftest 29/29（含新增「L6-A 元数据不变量」满分/空产物两分支：
  计分项数=n_tasks、计分项 pass 数=correct、守卫 id 不与任务 id 相交）。
- **近似错误例**（gate 口径，证明新键参与重算）：
  (a) 篡改 `n_tasks=14` → `judge.n_tasks ≠ possible_raw` 必拒；
  (b) `guards_used` 漏 `answers_schema` → `possible_raw=16 ≠ 分母 15` 必拒。
- **历史复算**（L5 E3 wb-bird + E2 中止档 wb-bird 两处真实工作区，零模型）：
  - A 冻结证据可复现（修前复跑 == 冻结 checker.stdout；`answers_file.note` 内嵌
    run_dir 绝对路径按归一口径比对，r1 收据因未归一已废止留档）；
  - B 修后判分零翻转（reward/weighted/accuracy/correct/failed_questions/checks 逐值相等）；
    键集恰增两键；pre 字节 sha16 `994be0b3…` 与 L5 contract bird pin 逐位一致；
  - C gate 重算调和（possible_raw=15=分母、exp8==reported8）。
- **验收**：15/15 断言全过（脚本生成收据）。

## L6-C：收据自引排除（L5-P3 / AUD-L5-O1）

- **规则**（receipt_check.py）：JSON 收据含 dict 型 `files_sha256` 时，键含收据自身
  路径/文件名 → violation「self-referenced hash entry」。selftest 16/16（+2 用例）。
- **生成器**（manifest_receipt.py 新增）：write-once 清单收据，`files_sha256` 不含自身、
  显式 `self_excluded` 字段；selftest PASS。
- **历史复算**（真实收据回放）：E1 abort-receipt 无自引 ok；**E2 abort-receipt 的
  `abort-receipt.json` 自引条目被新规则抓获**（AUD-L5-O1 实证可检）；E2 supplement 1/2
  ok。E2 另有既有 hex 记号规则命中（trace 文件名内嵌 uuid 段，L3 既有行为，非本批引入）。
- **kit 联合自测**：evidence_line 11/11 + receipt_check 16/16 →
  `selftest-receipt-l6-20261030.json` PASS。

## 证据行（evidence_line.py 生成）

```text
5-评测报告/L6判卷修订-2026-10-30/checker.pre-l6.py · 994be0b3 · 31538B · 2026-10-30T11:33:55+08:00
5-评测报告/L6判卷修订-2026-10-30/checker.post-l6.py · ffa7389a · 34165B · 2026-10-30T11:33:55+08:00
5-评测报告/L6判卷修订-2026-10-30/diff-l5-to-l6.patch · e118f0e6 · 6920B · 2026-10-30T11:33:55+08:00
5-评测报告/L6判卷修订-2026-10-30/l6_meta_recompute.py · 1396af61 · 8141B · 2026-10-30T11:33:55+08:00
5-评测报告/L6判卷修订-2026-10-30/l6-meta-recompute-receipt.json · 5504cb45 · 3195B · 2026-10-30T11:33:55+08:00
5-评测报告/L6判卷修订-2026-10-30/l6c-selfref-historical-replay-receipt.json · a9686e74 · 2012B · 2026-10-30T11:33:55+08:00
1-评测方案/工具链/evidence-kit/selftest-receipt-l6-20261030.json · 2e7fbce4 · 785B · 2026-10-30T11:33:55+08:00
```

废止档：`l6-meta-recompute-receipt-r1-VOIDED-比对伪差.json`（13/15，比对口径未归一
`answers_file.note` 路径所致，非判分差异；修正后重出 canonical 收据）。

live_doc_drift: none（0 项）
