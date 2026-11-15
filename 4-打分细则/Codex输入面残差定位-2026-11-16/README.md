# Codex 输入面残差定位（2026-11-16）

**预注册：把 [R3不稳定来源分解](<../R3不稳定来源分解-2026-11-16/README.md>)记录的 Codex developer/user 消息面跨重复残差（lcb developer 671vs672、dabstep user 5711vs5710、exercism user 4181vs4180）定位到 JSON 键路径——判定残差是封装元数据漂移还是消息内容漂移。** 动机：机制波已确立 Codex 输入侧 stable_core 与任务内容稳定（stable_core_ok/task_content_ok 全 True），但三处单字节级残差未定位；WB 复测已发现任务文本字节面漂移（[WB重复槽输入与交互量结构](<../WB重复槽输入与交互量结构-2026-11-16/README.md>)），Codex 侧须同口径闭合。纯事后算法定位，不新增运行、不改门判定与分数。

本页冻结于任何键路径计算之前。

## 1．范围与数据源（冻结）

- 五组 Codex 槽（bird/dabstep/exercism/lcb/tb 各 r1–r3，共 15 槽）中 role∈{user, developer} 的 message payload；与 v1.1 同一钉定归档。
- 硬等校验：逐组逐 role 逐槽 canonical 字节合计必须与 R3 分解包 `message_by_role_*` 数值一致，否则 exit 2。
- 对齐纪律：同 role 消息按流内序位 k 对齐（序位是结构量）；槽间该 role 消息**条数不同**的组/对 → 该 role 记 `count_mismatch` 单列（如实登记条数），超出公共前缀的尾部消息不参与定位、不猜测对应（与 v2 序列口径的 dabstep r1 自主分支发现一致）。

## 2．定义（冻结）

- 对每组每 role：k 从 0 到三槽最小条数−1，逐 k 跨三槽比较 canonical payload 字节：
  - 三槽全同 → 计入 `identical`。
  - 存在差异 → 记录逐差异**字节偏移**与该 payload 的 JSON 键路径（`payload.<key…>`；数组下标视为结构记录为 `[k]`），**不记录任何值**；键路径集合即定位结果。
- 分类（逐组逐 role，仅对存在差异的 k）：
  - 全部差异偏移落在**封装元数据键**（判据冻结：键路径仅触及 payload 顶层非内容键——`id`、`call_id`、时间戳类、`name` 之外的非 text/arguments/content 类键；实现方在读定实际 payload 键集后先列出「内容键集」候选清单（`content`、`text`、`arguments` 等承载文本的键），与本页判据合并钉入 verify.py，任何歧义键归入内容侧，宁可保守）→ `metadata_drift`（封装元数据漂移，输入面残差闭合为非语义）。
  - 任一差异偏移落在内容键 → `content_drift`（消息内容跨重复漂移——与 WB 同级的最重发现）。
- 内容无关纪律：只记录条数、序位、偏移、键路径、字节数、SHA；不记录值、不记录内容片段。

## 3．反证分支（冻结）

- **B-METADATA-ONLY**（三处残差全 metadata_drift）：Codex 输入面残差闭合——任务/环境文本逐字节稳定，漂移只在封装元数据；teacher 问题③的「输入重复性」在 Codex 侧全绿（字节面）。
- **B-CONTENT-DRIFT**（任一处 content_drift）：Codex 输入侧存在内容级跨重复漂移，与 WB 发现并列；只登记证据，不回写分数。
- **B-COUNT-MISMATCH**（定位被条数不齐阻断）：残差定位降级为结构登记，如实报告条数差异与已对齐部分结果。

## 4．老师反馈对照（Issue #16）

- **P1 机制解释优于加重复数**：零新运行，闭合 Codex 输入面最后残差。
- **P0 验收**：15 槽、3 处目标残差（lcb developer / dabstep user / exercism user）、分析脚本=本包 verify.py；交付含 result.json + test_verify.py + EXECUTION-RECORD.md（执行记录入包）。
- 与 WB 包互证：同一「信封外=内容侧」判定纪律跨产品一致。

## 执行记录（执行完成后写包内 EXECUTION-RECORD.md，不写本页）
