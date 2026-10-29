# 自动循环 L1 预注册（var-n3 × v2 盲审 × WB 请求级补证）

- 注册时间：2026-10-29 13:22 +08:00（生效以本文件提交哈希为准，见每场 meta `preregistration_commit`）
- 授权依据：用户 2026-10-29 授权自动化循环全自动运行（含真实评测批次 API 消耗与结论产出）；预注册仍先提交后运行，但无需逐批批准。节奏：本闭环完成后停止，交验收报告，等用户放行。
- 用户保留项（本循环不得触碰）：**周报只在用户明确叫写时才写；CHANGELOG 不改。**

## 总则（三个工作包共同纪律）

1. **预注册先于运行**：任何新运行开始时本文件提交必须已存在；先跑后补注册视为无效场。
2. **无重试**：运行级失败不补跑，记 `selection=null` 诊断事件，该 rep 记 failed；仅传输层错误（429/断连）允许指数退避至多 3 次，且属同一逻辑运行。
3. **判卷合同冻结**：一律使用 freeze-20261029-v2 checker（现行准入合同）。若包B盲审对合同判出 blocking 缺陷，本循环**提前整体停止**，合同修订留给下一轮，绝不在本循环内边跑边改。
4. **完全分账**：产品运行（r1031）/ 工具自检 / 离线盲审 / 预检探针（WB）各记各账，不混。
5. **结论五段结构**（观察—证据—解释—未排除因素—可复现实验）；n=3 只作描述，不作任何排名声明。
6. **工作区在仓库外**（~/bench-workspaces/）；严禁读取 `2-用例/` 下 truth/solution/checker 内容；凭据不入库、不打印。
7. builder 一律不执行 git 命令；提交/合并由 lead 统一做。

## 包A：r1031 n=3 可重复性（20 场）

- **问题**：r1030 正式批 headline 双 3/5、weighted 444.81/414.07 为 n=1，重复性方差未知，存在对噪声过拟合风险。
- **设计**：product ∈ {codex, dsh} × case ∈ {bird, dab, exercism, lcb, cargo} × rep ∈ {2, 3} = 20 场；r1030 各场记为 rep 1。
- **条件**：模型 `deepseek-flash` @ api.deepseek.com；思考档 low；工具/权限（TOOL_FACTS）与 r1030 同产品一致；workspace `~/bench-workspaces/r1031/<product>/<rep>/<case>/`（仅 inputs+TASK.md）；event id `var-n3-<product>-<case>-r<rep>`。
- **随批工程项（在本批内验证）**：
  - a. stdout 归档去除 8192 截断：完整流落盘，meta 记字节数（回应未知登记「stdout 8192 截断」）；
  - b. 逐调用 usage（含 cache_read / cache_creation）入库，供 provider-cache 语义观察（回应未知登记同名项）。
- **分析计划（预先声明，判据锁定）**：
  - 每 case 3-rep 结果分布与翻转计数；每 rep headline（全对 case 数）分布；
  - 每产品 weighted 总分极差 `spread = max − min`（3 reps）；
  - 判定：`gap₀ = 30.74`（= r1030 两产品 weighted 差的绝对值，444.81−414.07）。若任一产品 spread ≥ gap₀ → 结论「r1030 产品差与重复性方差不可区分」；否则报告 gap₀/spread 比值。两种结果均不产生排名。
- **停止**：20 场全部完成；或两产品同时基建硬故障（以失败报告收包）。
- **产物**：`3-表现现场/r1031-variance-n3/`（runs+receipts+adjudications+integrity，schema 同 r1030）；验收报告 `5-评测报告/可重复性-n3-2026-10-29/RESULTS.md`（五段）。

## 包B：v2 全交付对抗性盲审

- **问题**：敌意复核者（模拟评分方/第二名选手）能在 v2 交付中找到什么缺陷？
- **范围**：freeze-20261029-v2（代码/配置/lock/schema/tests）；r1030 十场证据链（注册→产物→裁定→正式表）；机制复制证据与结论；判卷 GUARDS/权重一致性；未知登记一致性；报告五段结构完整性；历史锚点哈希。
- **方法**：只读 + 离线复算，禁 live API 调用；逐项核对哈希、时序（registered_at < started_at 等）、污染痕迹、从 checker 原始输出独立重算分数、主张与证据差。
- **独立性**：auditor 不读 lead/builder 的过程叙述，只读仓库产物与预注册。
- **产出**：`5-评测报告/对抗性盲审-2026-10-29/AUDIT.md`，发现分级 {blocking, defect, observation, note}；每条 defect 附影响/下一步/停止条件并进问题池；本循环内不自动修复（纯文档笔误除外，须披露）。
- **停止**：清单跑完；或出现 blocking（→ 本循环提前整体停止并报告）。

## 包C：WorkBuddy 请求级补证

- **问题**：受管未知 wb-upstream-route-host-undisclosed / wb-model-alias-equivalence 能否以请求级证据推进？
- **方法**：对 WB 桌面端做**预检级探针**（非评分运行）：本机代理/本地监听捕获请求 URL 主机、TLS SNI、请求体模型字段、响应头可证字段；最多尝试 3 种机制。
- **红线**：不改判卷、不进正式表；任何系统代理改动先快照、结束后必须还原，不得影响 Clash（7897）；捕获物存 `1-评测方案/准入预检-2026-10-29/evidence-r2/`。
- **产出**：`wb-preflight-r2.json` + 准入预检 README 增补。两种收场：(a) 证据补齐 → 更新预检裁定与未知状态（WB 是否进 A 组仍留待未来正式批次，**本循环不自动准入**）；(b) 3 种机制全败 → 负结果披露，未知保留并更新下一步/停止条件。
- **停止**：出结果或 3 机制用尽。

## 循环收束

- judge 独立验收包A：验收工具必须先对 r1030 十场自检、复现 known weighted 值（以 `official-main-table.json` 为准）后方可用于 20 场；
- lead 汇总三包 → 五段总结 → PR → 循环停止，交验收报告等用户放行。
