# L3 自动循环 · 机读对齐与证据机械化

- 分支 `loop3-2026-10-29`（自 main `22cc6ac`）；预注册封印 `72edb519` @ 2026-10-29T17:52:27+08:00（先于一切包工作）。
- 性质：零模型调用卫生闭环。目标：把 L2 双验遗留（DF-1/DF-2/O-1、live_doc 三条件）与循环内教训（哈希手打、`--spec` 覆盖）全部转成机器强制，为 L4 生产轮解除机读消费停止条件。
- 池项处置与分账、包条款、停止条件：见 [PREREGISTRATION.md](<PREREGISTRATION.md>)（封印后只允许 dated 勘误框）。

## 包与执行

| 包 | 范围 | 执行 | 状态 |
|---|---|---|---|
| A：DF-1 + ⑧a/c（v3 活台账对齐 + pin 机械归类 + tripwire） | `4-打分细则/可信冻结-2026-10-29-v3/` | builder-codex | 进行中（2026-10-29 17:54 派发） |
| B：DF-2 + C-1 + ⑦（validator 补齐 + 非破坏化 + 溯源机制） | `1-评测方案/工具链/runner-schema-v2/` | builder-dsh | 进行中（同上） |
| C：⑥ + ⑧b（evidence-kit 证据行/收据检查器） | `1-评测方案/工具链/evidence-kit/`（新建） | builder-dsh（B 后） | 待 B |

双验：judge（对照预注册条款独立验收）→ auditor（敌意盲审）→ lead 汇总修复 → PR squash 合并 → 合并后 sweep → ACCEPTANCE → 停等放行。

## 裁定台账（追加式）

- 2026-10-29 17:51（lead）：L3 组合裁定——③④⑤⑥⑦⑧ 入本环；①（cache 消融，需 API）与 ②（WB 正式批次）留 L4 生产轮，理由：生产运行与卫生闭环混排破坏分账纯度，且 DF-1/DF-2 对齐是活台账/validator 作机读准入门的停止条件前置。
- 2026-10-29 17:51（lead）：派发裁定——包A 归 builder-codex（L2 v3 原班），包B/C 归 builder-dsh（B→C 串行，同文件归属防写冲突）；freeze-engineer/mechanism-engineer 因 L2 多次静默启动失败本轮不指派（预注册范围外披露）。
- 2026-10-29 17:52（lead）：登记时序裁定——活台账追加须待包A schema 对齐落地（A1），避免登记事件在过渡态被现行 schema 判非法。
