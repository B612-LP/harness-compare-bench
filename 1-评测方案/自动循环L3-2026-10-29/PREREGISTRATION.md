# L3 自动循环预注册 —— 机读对齐与证据机械化

- 循环分支：`loop3-2026-10-29`（自 main `22cc6ac` 分出）
- 本文件封印提交 = 本循环开工时点，提交时刻以 `git log` 为准（权威），行文时刻一律脚本生成
- 封印性质：本文件在**任何包开工前**提交；此后只允许 dated 勘误框（原句保留），不允许静默改写
- 模型调用声明：**本循环零模型调用**——不跑任何产品批次、不产生新分数主张、不调用评测 API

## §一 主题与动机

承接 L2 双验遗留（AUDIT `5-评测报告/对抗性盲审-L2-2026-10-29/AUDIT.md` DF-1/DF-2/O-1 + unknown-2 三条件）与循环内教训（哈希手打误报 ×3、`--spec` 覆盖收据事故 C-1）。L3 = **机读对齐与证据机械化**：把 L2 的披露性缺陷全部转成机器强制，为 L4 生产轮（真实批次）解除机读消费的停止条件。

**L3 池 8 项处置**：

| 池项 | 处置 |
|---|---|
| ③ DF-1 活台账 schema 三方矛盾 | 包A |
| ④ DF-2 validator 约束缺口 | 包B |
| ⑤ C-1 `--spec` 破坏性覆盖 | 包B |
| ⑥ 哈希/时刻脚本化 | 包C |
| ⑦ registered_at 溯源自证（O-1） | 包B（机制本轮落地，真实对账留 L4） |
| ⑧ live_doc 报告制三条件 | (a)(c)→包A，(b)→包C |
| ① provider-cache 消融（需 API） | **留 L4 生产轮** |
| ② WorkBuddy 正式批次 | **留 L4 生产轮** |

留 L4 理由：①② 均为生产运行，与卫生闭环混排会破坏分账纯度；且 DF-1/DF-2 对齐是「活台账/validator 作机读准入门」的停止条件前置。

## §二 分账声明（预期）

| 账目 | 预期 |
|---|---|
| product_run | 0 |
| bare_model_probe | 0 |
| interface_preflight | 0 |
| offline_recompute | 0 |
| grading_regression | 0（不重跑 B13a 回放） |
| self_test | N（各包测试/自检计数，验收时实报） |

API 调用 0 次。若循环内任何包需要打破上表，必须先出 dated 修正框并重走封印。

## §三 包定义与验收条款

### 包A（v3 侧：DF-1 + ⑧a/c）—— 执行：builder-codex

范围：`4-打分细则/可信冻结-2026-10-29-v3/`。**禁触**：`可信冻结-2026-10-29-v2/`（4/5 两处）与 v1，字节冻结。

- **A1** schema 对齐（AUDIT DF-1 方案 a）：`config-schema.json` `$defs.live_registry_entry` 增加 `registered_at` 属性（date-time、须带时区偏移）；`kind.enum` 扩列 `correction`。对齐后现行 5 事件**全部**合 schema。
- **A2** 三方一致并机械化：`test_freeze.py` 结构不变量并入 JSON Schema 校验（实例必须通过 live_registry_entry schema）——消除「测试全绿 ≠ 实例合 schema」；schema/实例/测试三者对 `registered_at` 与 `kind` 的立场唯一。
- **A3** dated 勘误：enum 扩列与 schema 变更在 v3 README 以 dated 变更框披露（原语义保留，附 lock 前后哈希，脚本生成）。
- **A4** pin_class 机械归类（⑧a）：`verify_seal` 自检「凡被 build/verify 读取面（config/registry/sources）引用的路径必为 contract」——lock 内人工归类与之冲突即 verify 硬失败；测试覆盖错标样本必被抓住。
- **A5** tripwire 保留（⑧c）：live-ledger 非 contract pin 断言不删；README 明示「报告制≠免检，还原+旁挂仍是操作规范」。
- **A6** 重建+重锁：全测试绿（44 继承 + 新增，计数实报）；`freeze.py verify` exit 0 且如实报告 `live_doc_drift`；v2 目录 verify 仍 exit 0（字节未动）；新 lock 哈希脚本生成入台账。

### 包B（runner-schema-v2 侧：DF-2 + C-1 + ⑦）—— 执行：builder-dsh

范围：`1-评测方案/工具链/runner-schema-v2/`。

- **B1** `status` enum 强制（值域以 SCHEMA.md §一 列举为准，实现与文档一致）。
- **B2** `integrity_verdict` enum = {clean, benign-reviewed, violation}；`benign-reviewed` 必须伴随非空 `corrections`，否则 issue。
- **B3** `selection` 为 null 必须伴随非空 `diagnostic`，否则 issue。
- **B4** seal 校验响亮化：未提供 `--seal-at` 时 classify **不得**产出可消费为通过的 pass——默认非零退出；显式 opt-in（如 `--allow-unsealed`）仅限披露模式且输出带 unsealed 标记。既有 fixtures 在新语义下的行为更新须在收据中披露。
- **B5** fixtures 补 ≥3 用例覆盖 B1/B2/B3；spec-selftest 收据**生成到新路径**，原收据（字节 `5c6177fd…`）与 `receipt-overwrite-evidence-20261029.json` 字节不动。
- **B6** C-1 非破坏化：`cmd_spec` 不再无条件写死路径——写入必须显式 `--out`，或目标已存在即拒绝（非零退出、原字节不动）；回归测试机械复现 16:11:16 覆盖模式（第二次运行必须失败且首文件字节不变）。
- **B7** ⑦ 溯源机制：SCHEMA.md 显式披露「顺序检查必要非充分」；提供 registered_at ↔ git 提交时刻的离线对账能力（对账子命令或脚本，输入=预注册台账路径+字段位置/封印提交）；以 L3 封印提交做一次**合成对账**作为 self_test 证据；真实批次对账为正式闭项条件（§五 U1）。
- **B8** 事实汇报：变更清单/测试计数/哈希全部脚本生成；B6 落地前 `--spec` 仍只对 /tmp 副本运行。

### 包C（工具包：⑥ + ⑧b）—— 执行：builder-dsh（包B 落地后开工）

范围：`1-评测方案/工具链/evidence-kit/`（新建）。**禁触** v3 与 runner-schema-v2（避免与 A/B 写冲突）。

- **C1** 证据行生成器：输入文件路径（支持多个），输出报告标准证据行（相对路径 · sha256 前8位 · 字节数 · 生成时刻 ISO8601+tz）；自带 `--selftest`。
- **C2** 收据规范检查器（⑧b）：机械核验收据/审计文档含 `live_doc_drift` 状态行与合规哈希行；供本轮 judge/auditor 起用；**不回改**历史收据。
- **C3** README 一条铁律：叙述文档中的哈希/时刻必须引用脚本输出，禁止手打；本轮 judge/auditor/lead 实际试用并留痕。
- **C4** 全部脚本自测绿（计数实报）。

## §四 冻结与不变量

1. `可信冻结-2026-10-29-v2/`（两处）与 v1：字节冻结，任何包不得改动；循环收口时 verify 仍须 exit 0。
2. r1030 仍是 v2 合同记录；v3 official 表恒空语义不变；本循环不产生任何新准入、不改任何历史分数。
3. 活台账 `work-registry-live.json` append-only：执行者本人登记，仅追加；登记须待包A schema 落地后进行（B/C 包时序约束），哈希用脚本生成。
4. 本循环不引入任何机读消费者打破 DF-1 停止条件——包A 本身就是对齐动作，对齐完成前其他包不得以 validator 身份消费活台账。

## §五 未知与停止条件

- **U1**（承 O-1）：registered_at ↔ git 提交时刻的**真实批次**对账未做（L3 仅合成对账）→ 影响：溯源仍是机制级而非实证级；下一步：L4 首个真实批次必做；停止条件：一次真实对账吻合即闭。
- **U2**：包A 重锁后若 verify 报非空 `live_doc_drift` → 如实报告并逐条定性，不得静默通过。
- **U3**：judge/auditor 新发现 → 入 L4 池，循环内只修 blocking。

## §六 防过拟合声明

- 无新运行、无分数表、无准入变更 → 本循环对评测结论的过拟合面为零；全部产出是约束与工具。
- 预注册先于一切包工作封印；无重试纪律不变（失败如实记录，不悄悄重跑）。
- **本循环自身即试点 ⑥**：lead 行文中的全部哈希/时刻由脚本生成后粘贴，禁止手打。
- builder 只报事实；分析结论归 judge/auditor/lead。
