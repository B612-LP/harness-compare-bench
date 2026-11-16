# 执行记录（2026-11-17，系统提示与工具集跨版本对齐）

## 时间线
- 02:08 私立题 `loop11/DIRECTION.md`（仓外）；对归档 15 槽 `system/message` 原文与 `request/header` 工具、capture req1 wire 层实测。
- 02:10 常量全量实测落 `loop11/constants-probe.json`（私档）。
- 02:13 冻结本包 README（SHA `6875c18f5c66530f33b719b27712bb54873e3b3fdd121c3f747c3856409bb3c1`）。
- 02:14–02:18 verify.py/test_verify.py 实现与修复；evidence/result 构建成功并两次幂等重建逐字节同。
- 02:18 四档套件全绿（17 tests × 普通/-O × 有/无真档环境变量；真档分支激活时 skipped=0）。
- 待办：非作者独审（独占私档目录）→ v1.69 整合。

## 修复史（发生在真档证据构建前，SHA 链可复核）
1. verify 常量首稿含**未实测占位值**（ARCHIVE_SYSTEM_SHA256/HUNKS 行哈希/等值工具字节数 0）——立即以 `loop11/constants-probe.json` 实测值整体替换（G1/F-1 教训：常量必须当场测量）。
2. COMMON_TOOL_RESULTS 由 JSON dumps 引入小写 `false/true/null` 字面量 → 改 Python 字面量。
3. CLI 参数：`--archive-base`（capture/私档 until14 根）与 `--launch-base`（r1109 归档根）分离；重放模式不需要二者。
4. `loads` 增加 `parse_float` 非 finite 拒绝（1e999 溢出不触发 parse_constant）。
5. 套件 refresh 改为逐 task 真实解码（首版用字符串替换导致 env 字节错配）；test_03 改为冻结常量失配负例（合成 evidence 对冻结 pin 必然拒绝），正向 CLI 重放由真档分支覆盖。

## 结果
- 终点全过：P1 15 槽→5 组（每任务 3/3 逐字节同）、路径归一后 1 模板；P2 六块分类 {model_slot:1, template_evolution:4, path_line_relocated:1}、净 +323 与 2593−2270 对账；P3 工具 21→22（−2/+3，共同 19 中 12 等值、7 演进）；P4 对齐包 P2 层别错配确认（信封 canonical 2535–2541 vs 原文 2270–2271）。
- evidence SHA `fb27b261214cb90049c4daf697277d4c1ef1a21ad7acf60b17cf3cc4bad3d010`；result SHA `2c73c024a04a6286f00f971aec7c950557c80f1061f64f37baca5c54cf31e6dd`；verify SHA `c6d4440f449adc76ba54f0c0ca20c761e6dba09c75d130fdb6e9ad3d314d77ad`；test SHA `0f07bf02c4d97ef2b23d06d2ad3d3ceb7cb7890293f1d9b52e50c2ee5eaaeccf`。

## 诚实披露
- 探索后冻结：作者在冻结前已见全部数值（见 README 先验曝光节）。
- 公开重放只校验 evidence 与冻结常量/README pin 一致性，不能认证私档真实性；`--archive-base`/`--launch-base` 路径为 CLI 契约（先例：跨模型包 G2）。
- 归档侧仅取每槽 r1 的 session 档（r2/r3 system 与 r1 同任务同文本已由分组数=5 隐含，未逐一显式比对——分组本身即以全文文本为键）。
- 模型槽行也随 provider 变化（见跨模型捕获包），本包只对齐 build 间差异。
