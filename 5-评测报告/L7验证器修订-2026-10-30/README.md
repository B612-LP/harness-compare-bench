# L7 验证器修订档案（2026-10-30）

L7 闭环两项交付的集中归档。预注册：[自动循环L7 PREREGISTRATION](<../../1-评测方案/自动循环L7-2026-10-30/PREREGISTRATION.md>)；
历史复算设计变更：[history-replay-design-note](<../../1-评测方案/自动循环L7-2026-10-30/history-replay-design-note.md>)。

## L7-A：gate 语义默认值显式化（L6 池项）

- **修前**：`l5-execution/gate.py`（sha `38b42a87…`，L5 v2 后未动）5 处锚定 L5 默认计划目录
  （常量、`verify_execution`/`gate_admission` 签名、seal loader、`--binding` CLI 默认）——
  调用方漏传即静默读错批（L6 E2 REFUSED 实证路径）。
- **修后**：默认值全数拔除——CLI `--binding`/`--plan-dir` 必填（`--selftest` 例外）；
  API `plan_dir=None` → `GateError`；判分语义零改动（diff +24/−7 行，全部声明类）。
- **正例**：selftest PASS（合成世界全程显式传参）。
- **近似错误例**：CLI 缺参/N2 API None/N3 seal loader None/N4 坏目录——四类全拒（r7 收据）。
- **封印 pin 精确性（P4）**：修订版 gate 复判 L6 恰因 `gate.py sha-mismatch want=38b42a87`
  拒——失败=封印 pin 而非语义漂移。
- **历史复算口径变更**：跨批重演经 r1-r6 五版探索证明**按设计不可行**（每批由封印时刻
  全套工链字节+收据固定；共享工链演进后三方一致在当前盘不可满足=钉定系统目的），
  改为基线收据引用固定（r1-r6 全档 VOIDED 保留；五版结构发现见设计变更说明）。
  基线：L4 formal 0/17、L5 5/6、L6 1/1（各自封印时刻独立验收背书）。
- **验收**：r7 收据 12/12 全过。

## L7-B：运维卫生规程（L5-P4）

- 新增 [OPERATIONS-hygiene.md](<../../1-评测方案/工具链/OPERATIONS-hygiene.md>)：
  敏感命令行硬规则（凭据禁入 argv/日志/收据正文；env/文件传递；轮换先于清理），
  事件引用 L5 ps 误印 Bearer（零入库实证）。
- 首查扫描：155 文件，9 命中全数为 `"$VAR"` 环境变量透传允许形态，**零字面量违规**
  （r1 未分类误报 VOIDED 留档）。

## 证据行（evidence_line.py 生成）

```text
5-评测报告/L7验证器修订-2026-10-30/gate.pre-l7.py · 38b42a87 · 120157B · 2026-10-30T13:42:04+08:00
5-评测报告/L7验证器修订-2026-10-30/gate.post-l7.py · 25dbf52e · 120672B · 2026-10-30T13:42:04+08:00
5-评测报告/L7验证器修订-2026-10-30/diff-main-to-l7.patch · 9a7eecea · 4447B · 2026-10-30T13:42:04+08:00
5-评测报告/L7验证器修订-2026-10-30/l7_gate_recompute.py · 2ceaa120 · 7317B · 2026-10-30T13:42:04+08:00
5-评测报告/L7验证器修订-2026-10-30/l7-gate-recompute-receipt.json · 5c71bc56 · 3605B · 2026-10-30T13:42:04+08:00
1-评测方案/工具链/OPERATIONS-hygiene.md · 964d92de · 1864B · 2026-10-30T13:42:04+08:00
1-评测方案/工具链/bearer-scan-receipt-l7.json · 27f792aa · 3657B · 2026-10-30T13:42:04+08:00
```

废止链：`l7-gate-recompute-receipt-r1..r6-VOIDED-*.json`（设计演化全记录，见设计变更说明）。

live_doc_drift: none（0 项）
