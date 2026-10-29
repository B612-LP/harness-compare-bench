# L3 独立验收（judge 双验，2026-10-29）

- 验收基准：[PREREGISTRATION.md](<../../1-评测方案/自动循环L3-2026-10-29/PREREGISTRATION.md>) §三条款 A1–A6/B1–B8/C1–C4 + §四/§五；封印 `72edb51`；裁定台账见同目录 README.md
- 逐条款机械证据与疑点钉死：[verify-receipt-l3.json](<verify-receipt-l3.json>)
- 纪律：未改任何既有文件（仅本目录新建）；未写 work-registry-live.json；git 仅只读（log/show/diff）；`--spec` 类一律 `--out`/tmp；未读 2-用例 truth/solution；全部哈希/时刻由脚本生成后粘贴

live_doc_drift: []（none）——2026-10-29 实测 `freeze.py verify`（v3 与 v2 均 exit=0, ok=true），summary.live_doc_drift==[]；本行即 ⑧b 状态行。

## Dogfood（⑧b/C3 首次真实使用）

- 证据行由 evidence_line.py 生成（工具 sha256 前 8 位 9b00febf，自测 11/11）：
5-评测报告/L3独立验收-2026-10-29/verify-receipt-l3.json · 569d86bb · 12920B · 2026-10-29T18:45:20+08:00
- receipt_check.py（97b3be0b，自测 10/10）对本验收两文档执行：预期 all_ok=true（本文件含状态行与合规证据行；JSON 收据含顶层 live_doc_drift 键）；实测结果与命令见下节。

## 逐包裁定

| 包 | 裁定 | 要点（全部 judge 自跑复现） |
|---|---|---|
| 包A（DF-1+⑧a/c） | **pass** | A1 schema（registered_at 必备+时区 pattern；kind 6 值含 correction）+ judge 独立校验器 11/11 事件 0 fails；A2 stdlib schema 校验并入不变量测试；A3 变更框 dated 18:01:09（lock_before 544a7f96 入框、lock_after bf7f9aa3 外置台账，实测两哈希吻合）；A4 读取面机械归类 judge 直调 0 违规、本地读取面 29/29 contract、3+1 新测试；A5 tripwire 保留+「报告制≠免检」声明；A6 48/48（44+4，0 删除）、v3/v2 verify 双 exit=0、v2 零字节（git diff 空）、lock 17→38（31c/7l） |
| 包B（DF-2+C-1+⑦） | **pass**（附新发现 D-L3-1 → L4 池） | B1/B2/B3 三 enum+伴随约束由 fixtures 实证（spec 10/10）；B4 fail-closed（T2 exit=1 fail:unsealed）+ opt-in 仅 --retro 带 seal 标记（judge 同输入两跑唯一差异=seal.policy）；B5 fixtures 10、新收据 6048ad41、原三收据字节未动（5c6177fd/22332412/12cd3354 实测）；B6 judge 亲测二跑拒写+字节不变+裸 --spec 不落盘；B7 SCHEMA 披露必要非充分+合成对账正/负例独立复现（ok/exit0、violation/exit1）；B8 收据字段脚本生成。**⚠️ 新发现：`--reconcile --git` 模式缺陷（D-L3-1）**——:460 行 `"...%cI %s" % commit` 的 Python %-format 与 git 占位符冲突 → commit-time-source 步骤恒假（subprocess 本身成功、时刻已正确解析），且 `verdict="ok"` 与 `ok=false` 自相矛盾；exit=2（fail-closed 未破）。L3 披露诚实（SCHEMA 明示未行使）+ U1 留 L4，故不入本条款裁定，但 **U1 执行前必修** |
| 包C（⑥+⑧b） | **pass** | C1/C2 双自测绿（11/11、10/10）+ judge 以本验收两文档真实 dogfood；C2 的证据行机械复算与「--out 已存在即拒」实测一致；C3 铁律在案并已践行；C4 联合自测 2/2（r4=a95631d5）；修正链 r1→r4（d951ba4a/74b989e7/e9a14c17/a95631d5）同 commit 落盘、之后零改动、双活台账事件披露 ✓ |

## 疑点钉死（六项全闭环）

1. **live_doc_drift 语义**：同一语义、不同渲染。verify 顶层无该键，实际在 `summary.live_doc_drift==[]`；包A 报「[]」走对路径，包B 打印「None」系顶层 get——非真不一致，建议示例统一引 summary 路径。
2. **⑧b 适用范围（judge 定性）**：适用于本轮 judge/auditor 产出的**验收/审计收据**（机器可核文档）；builder 叙述/规格文档（v3 README 属此类）不适用——其 drift 语义由 verify 的 pin 分类与 live_doc_drift 输出管理。包C 对 v3 README 的 all_ok=false 属范围外运行的披露性结果：①README 提及 live_doc_drift 但同行无状态记号；②`dab2697` 是 hex 记号规则的真实命中（大写形似、案件名非哈希）。工具的 `--no-drift-require` 即两类文档的区分开关。非 builder 缺陷。
3. **38 pin 无遗漏**：成立。judge 直调 check_pin_classification 违规=[]；本地读取面 29/29 contract；live ledger 按 design 非 contract 且有 tripwire；2-用例字节经 pinned config case_snapshots 哈希传递锚定。
4. **--allow-unsealed**：实证成立——`--spec` 携带即 exit=2；仅 `--retro` 生效且输出带 seal.unsealed=true/policy 标记。
5. **--reconcile --git 零行使**：披露充分（SCHEMA 明示）、U1 如实留 L4；但 judge 以只读 git 身份亲测发现 **--git 代码路径缺陷**（见上 D-L3-1）——实质不可用，L4 真实对账前必修。
6. **修正链**：包C r1→r4 字节保留 ✓（四文件同 commit、零后续改动、双事件披露）；**包A「4 起」在仓库内无可考修正链/披露记录**（单 commit、无 corrections 条目、无链文件）——「修复前字节是否真保留」在仓库证据上不可核，需 lead 澄清所指（observation N-1）。

## 新发现（§五 U3 → L4 池）

- **D-L3-1（defect，包B）**：`--reconcile --git` 的 src 字符串 %-format 冲突（`%cI` vs `% c`）→ 源步骤恒假 + verdict/ok 矛盾。影响/下一步/停止条件：L4 真实对账的 --git 模式会产出自相矛盾收据，以 verdict 为键的机读消费会被误导 / 一行转义修复 + verdict 语义对齐 / **U1 执行前必修，未修复前 --git 输出不得作为闭项证据**。
- **N-1（observation，包A）**：「4 起修正」仓库内无留痕（见疑点 6）。
- **N-2（note，包B）**：retro 行为字段级 delta、无 per-run classify；unsealed 语义在矩阵级 seal 块，与 SCHEMA §三.3 一致。

## 复现

```bash
cd <仓库根>
python3 -B "4-打分细则/可信冻结-2026-10-29-v3/test_freeze.py"        # Ran 48, OK
python3 -B "4-打分细则/可信冻结-2026-10-29-v3/freeze.py" verify      # exit=0, live_doc_drift=[]
python3 -B "4-打分细则/可信冻结-2026-10-29-v2/freeze.py" verify      # exit=0
python3 -B "1-评测方案/工具链/runner-schema-v2/cli-selftest-l3.py" --out /tmp/x.json   # 6/6
python3 -B "1-评测方案/工具链/evidence-kit/kit_selftest.py" --out /tmp/y.json          # 2/2 (11/11+10/10)
python3 -B "1-评测方案/工具链/evidence-kit/receipt_check.py" \
  "5-评测报告/L3独立验收-2026-10-29/README.md" \
  "5-评测报告/L3独立验收-2026-10-29/verify-receipt-l3.json"                            # ⑧b dogfood
```

*judge 出品 · 全部哈希/时刻脚本生成 · 逐条款证据见 verify-receipt-l3.json · 总结论归 lead 验收报告*
