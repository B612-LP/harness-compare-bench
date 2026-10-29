# L3 自动循环 · 机读对齐与证据机械化

- 分支 `loop3-2026-10-29`（自 main `22cc6ac`）；预注册封印 `72edb519` @ 2026-10-29T17:52:27+08:00（先于一切包工作）。
- 性质：零模型调用卫生闭环。目标：把 L2 双验遗留（DF-1/DF-2/O-1、live_doc 三条件）与循环内教训（哈希手打、`--spec` 覆盖）全部转成机器强制，为 L4 生产轮解除机读消费停止条件。
- 池项处置与分账、包条款、停止条件：见 [PREREGISTRATION.md](<PREREGISTRATION.md>)（封印后只允许 dated 勘误框）。

## 包与执行

| 包 | 范围 | 执行 | 状态 |
|---|---|---|---|
| A：DF-1 + ⑧a/c（v3 活台账对齐 + pin 机械归类 + tripwire） | `4-打分细则/可信冻结-2026-10-29-v3/` | builder-codex | ✅ 交付（0e276a20）；judge pass / auditor pass |
| B：DF-2 + C-1 + ⑦（validator 补齐 + 非破坏化 + 溯源机制） | `1-评测方案/工具链/runner-schema-v2/` | builder-dsh | ✅ 交付（af703db）；judge pass / auditor pass（附 DF-B1→修复轮） |
| C：⑥ + ⑧b（evidence-kit 证据行/收据检查器） | `1-评测方案/工具链/evidence-kit/`（新建） | builder-dsh（B 后） | ✅ 交付（23a63fc）；judge pass / auditor pass with defects（DF-C1/C2→修复轮） |

双验：judge ✅（5-评测报告/L3独立验收-2026-10-29/，三包 pass+D-L3-1）· auditor ✅（5-评测报告/对抗性盲审-L3-2026-10-29/AUDIT.md，0 blocking/3 defect）。修复轮（D-L3-1/DF-B1/DF-C1/DF-C2，builder-dsh）→ judge 复验 + auditor 确认 → PR squash 合并 → 合并后 sweep → ACCEPTANCE → 停等放行。

## 裁定台账（追加式）

- 2026-10-29 17:51（lead）：L3 组合裁定——③④⑤⑥⑦⑧ 入本环；①（cache 消融，需 API）与 ②（WB 正式批次）留 L4 生产轮，理由：生产运行与卫生闭环混排破坏分账纯度，且 DF-1/DF-2 对齐是活台账/validator 作机读准入门的停止条件前置。
- 2026-10-29 17:51（lead）：派发裁定——包A 归 builder-codex（L2 v3 原班），包B/C 归 builder-dsh（B→C 串行，同文件归属防写冲突）；freeze-engineer/mechanism-engineer 因 L2 多次静默启动失败本轮不指派（预注册范围外披露）。
- 2026-10-29 17:52（lead）：登记时序裁定——活台账追加须待包A schema 对齐落地（A1），避免登记事件在过渡态被现行 schema 判非法。
- 2026-10-29 18:52（lead，转记时点实钟；4 起事件时点仅据 builder-codex 汇报区间 17:54–18:22，未逐一起实钟）：**包A 4 起预提交工作树迭代转记（N-1 处置，据 builder-codex 汇报转记，lead 署名；原始披露=派发通道 chat 汇报，仓内此前无留痕）**：①A4 首跑 verify exit 2——机械自检抓出 18 个 registry source 未 pin，机制按设计工作，全部补为 contract pin；②错标样本测试夹具缺合成根（BASE/config.json 未建）致断言落空，夹具补建；③重锁脚本 `../` 层级笔误（应为 `../../`）中途 FileNotFoundError，锁未写入、无文件副作用，从仓库根重做；④登记事件复核脚本 datetime 别名 NameError（写盘已完成，仅复核重跑）。定性：均确定性适配、无测量重跑，不违反无重试纪律；制度缺口（披露未仓内落盘）→ L4 池新增「builder 事实汇报仓内归档制度」。
- 2026-10-29 18:47（lead，双验结果裁定）：judge（三包 pass；六疑点钉死：①live_doc_drift=同义不同渲染，键在 summary 内 ②⑧b 适用=本轮验收/审计收据，叙述文档不适用 ③38 pin 无遗漏 ④--spec+--allow-unsealed=exit 2 实证 ⑤--git 披露充分但发现 D-L3-1 ⑥包C 修正链完整/包A 4 起仓内无痕→N-1）+ auditor（**0 blocking / 3 defect / 2 obs / 4 notes**；攻击面实证：自写 schema 校验器非 stub、A4 逃逸样本被生产路径硬拒、B6 三态全对、38 pin 制度自洽、L2 遗留 DF-1/DF-2/C-1/O-1/unknown-2 全部真闭合）。四 defect 循环内修复裁定：**D-L3-1**（--reconcile --git `%-format` 与 git 占位符冲突→自相矛盾收据；judge 发现）、**DF-B1**（B4「默认非零退出」在 --retro 无 seal 路径未落实，SCHEMA 自行收窄而预注册未走修正——裁定修代码就预注册字面，不做弱化修正框）、**DF-C1**（receipt_check `\b` 正则对 CJK 前贴哈希零命中——⑧b 闸门核心场景）、**DF-C2**（wellformed 死数据不参与 ok 判定）。修复执行=builder-dsh；复验=judge（含 --git 只读亲测）+auditor 确认。B6 边缘项（悬空 symlink 穿透写、write_text 非原子）auditor 定级 note → L4 池。
- 2026-10-29 18:52（lead）：L4 池增补：①builder 事实汇报仓内归档制度（N-1 制度化）；②receipt 写入硬化（symlink 检查+原子写）；③O-2 活台账 source 哈希新鲜度对账（auditor observation）；④U1 真实批次 registered_at↔git 对账（承 L2，D-L3-1 修复为前置）；⑤--retro 无 seal 矩阵下游消费规约（标签级拦截的消费者侧纪律）。
- 2026-10-29 18:52（lead）：auditor 活台账登记委托裁定——执行者因只读约束无法自登，由 lead 在修复复验收口后统一代登（judge 收据+auditor AUDIT 两事件，标注「lead 代登」），与 4 起转记同批。
- 2026-10-29 19:16（lead，修复轮复验结果）：judge 复验（fix-verification-20261029.md，T8 只读 git 亲测六步全绿、四 defect 全闭项、勘误自查一处）+ auditor 敌意复核（AUDIT §9：修复本体全真闭合；新分级 blocking 0 / defect 1 / observation 1 / note 4）。
- 2026-10-29 19:23（lead，FIX-D1 裁定）：auditor 抓出 --reconcile comparison_ran 分支残留「verdict:ok 与 ok:false 同页」矛盾（假哈希格式+合法时刻组合无测试钉住）——与 D-L3-1 同类，裁定**循环内修复**（守卫+T10，builder-dsh 执行、judge 闭项复验）：机读字段的类缺陷不带着合并。FIX-O1（seal 块 policy 标签与密封状态矛盾，无安全洞）与 N1（9/9 计数语义应区分 pending）、N2（r5 留痕无用例粒度）、N3（--no-drift-require 分支不对称未言明）、N4（新正则行为拓宽清单宜在 README 显式白名单）→ L4 池。
- 2026-10-29 19:23（lead，N-3 口径裁定）：采纳 judge 建议——L4 起 builder 自检收据统一内嵌 live_doc_drift 键（≈零成本，届时写入 ⑧b/SCHEMA）；过渡期自检收据按 --no-drift-require 口径核对（r6=c396bb40 在其自身语境判定合规）。
