# L3 修复轮复验（judge，dated 2026-10-29T19:08:48+08:00 实钟脚本生成）

- 对象：commit `15d9d62a`（相对 `281ab3e2` 的 diff）；修复项 = D-L3-1（judge 发现）+ DF-B1/DF-C1/DF-C2（auditor 发现），共 4 defect
- 复验纪律：git 只读；`--spec`/`--out` 全部指向 /tmp 或新路径；逐项亲测（不采信 harness 输出为结论，harness 收据仅作对照）
- 工具新哈希实测：validate_runner_meta.py `e71f28fb…`、cli-selftest-l3.py `76551873…`、receipt_check.py `effda0ed…` ✓（与 lead 清单一致）；新收据 82393b1f（spec-l3-fix）/17a3c053（cli-regression-l3-fix）/b356ce9f（reconciliation-l3-fix）/29ce9062（kit r5）/c396bb40（kit r6）✓ 全对上

## 逐项证据

### (a) T8 `--git` 回归（D-L3-1）——亲测通过

- `L3_ALLOW_GIT=1` 下回归套件 9/9（6 旧 + 3 新：T7 DF-B1 / T8 D-L3-1 / T9 verdict 语义）
- **judge 亲测**（非 harness 代跑）：`--reconcile --ledger fixtures/reconcile/synthetic-ledger.json --pointer /registered_at --commit 72edb519 --git --out /tmp/...` → exit=0，**verdict=ok、ok=true、六步全绿**（`commit-time-source: True`——修复前恒假）、对账时刻=2026-10-29T17:52:27+08:00（L3 封印提交时刻）✓

### (b) verdict/ok 语义四态对齐——亲测通过

- 正例（T8 上）：verdict=ok、ok=true ✓
- 早于封印（T5 亲测）：exit=1、**verdict=violation、ok=false** ✓
- 垃圾来源（T9 亲测：commit-time-file 内容非时刻）：exit=1、**verdict=error、ok=false**、source 步骤 false ✓
- 不可判定态（inconclusive）不再与 ok/violation/error 混用；「verdict=ok 而 ok=false」自相矛盾形态不可复现 ✓

### (c) DF-B1 `--retro` fail-closed——亲测通过

- 无 `--seal-at` 且无 `--allow-unsealed`：**exit=3**、stderr 响亮（含 B4 指引与两种合法口径说明）、**矩阵不落盘**（mktemp 临时目录逐一核验：仅 stdout/stderr 捕获文件，无 m1.json）✓
- `--allow-unsealed`：exit=0、`seal.policy=allow-unsealed-disclosure`、`unsealed=true` ✓
- `--spec` 面 10/10 复跑 all_match=true（B1–B4 已验行为零改动）✓

### (d) DF-C1/DF-C2 receipt_check 新规则——探针全过

- CJK 前贴 64 位小写合规串：**命中且 0 违规**（修复前 `\b` Unicode 边界下 0 命中）✓
- 12 位（`deadbeefdead`）与真 68 位（`deadbeef`×8+`cafe`）越界串：均记 violation（长度 ∉ {7,8,40,64}）；65 位串亦记 ✓。**勘误自查**：我首轮探针误写 64 位串标「68 位」，检查器判其合规为**正确行为**（64 ∈ 合法集），已以真 68 位串复测纠正
- judge 自构中文叙述样本（含合法 8 位哈希）：0 误报 ✓
- DF-C2：JSON `"live_doc_drift": "none"`（字符串糊弄值）→ fail ✓；`[]` 列表值 → pass ✓

### (e) 字节守护 + v3 基线——全过

- 五收据实哈希：`5c6177fd`/`22332412`/`6048ad41`/`db65c68c`/`12cd3354` 全部原值 ✓
- v3 test_freeze：Ran 48 OK（exit=0）✓；v3 verify：exit=0、ok=true、live_doc_drift=[] ✓
- 活台账 events=12：judge 独立 schema 校验器（同初验口径）0 fails；第 12 事件 = `work:l3-fixround-dlb1-dl31-dfc1-dfc2-20261029`（修复轮登记，属 §二.6 执行者登记职权，judge 未代写）✓
- 修正链 r1→r6 六文件全在（d951ba4a/74b989e7/e9a14c17/a95631d5/29ce9062/c396bb40），r1→r4 与初验字节一致 ✓

### (f) 修复轮收据过 receipt_check——**附带口径发现 N-3**

- kit 联合收据 r6=`c396bb40`：默认口径（require_drift）下 **all_ok=false——因 r6 及全部 builder 收据（L3 与修复轮共 7 张）均未携带 `live_doc_drift` 键**；`--no-drift-require` 下 all_ok=true、exit=0（哈希/证据行规则全净）
- **N-3（observation，提请 lead 裁决口径）**：⑧b 条文（C2）目标是 judge/auditor 验收/审计收据；builder 自检收据是否也须携带 drift 状态键属口径选择。建议：L4 起 builder 自检收据统一内嵌 `live_doc_drift` 键（成本≈0，DF-C2 语义已可机判），并写入 SCHEMA/⑧b 文档；在此之前 builder 自检收据按 `--no-drift-require` 口径核对。r6 在其自身语境（self_test 收据）下判定：**合规**（哈希/证据规则 0 违规；drift 键缺失按 N-3 口径处理）

## 最终裁定

| 缺陷 | 裁定 |
|---|---|
| D-L3-1（--git 拼接+verdict 语义） | **closed**（fixed in-loop `15d9d62a`；judge 亲测 T8 全步绿 + 四态语义对齐 + T9 error 态正确） |
| DF-B1（--retro 无 seal 可产出矩阵） | **closed**（exit=3 + stderr 响亮 + 不落盘亲测；opt-in 标记正确；--spec 基线零改动） |
| DF-C1（CJK 前贴 0 命中 + 越长漏检） | **closed**（环视正则生效：CJK 前贴命中、12/65/68 位均记违规、合规 64 位不误报） |
| DF-C2（字符串糊弄值可过） | **closed**（非 null/list 值记 violation 判 fail；judge 自身收据已迁移为 list 形态并复检通过） |

四 defect 全部闭项。U1（真实批次 registered_at 对账）维持 L4；其执行前置（--git 修复）已就绪。

## 本轮收据状态

- 本验收两文档按 DF-C2 新口径复检：**all_ok=true**（README 状态行 + JSON `live_doc_drift: []`（list 合规）+ 证据行 `…verify-receipt-l3.json · 343e0df3 · 13848B · 2026-10-29T19:08:29+08:00` 机械复算通过）
- 原 [verify-receipt-l3.json](<verify-receipt-l3.json>) 除 drift 值迁移（dict→list+旁挂 note）与 D-L3-1 标注 closed 外未改判词；[README.md](<README.md>) 同步更新状态行与证据行

*judge 出品 · 全部哈希/时刻脚本生成 · 复验留痕 /tmp/judge-l2/（t8-git-judge.json、t5-judge.json、t9-judge.json、dfb1.*、dfc/*、v3-test-fix.log、v3-verify-fix.json、fix-cli-rerun.json、r6-check*.json、l3-receipt-check3.json）*
