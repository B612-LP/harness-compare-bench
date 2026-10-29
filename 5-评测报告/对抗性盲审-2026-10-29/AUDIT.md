# 对抗性盲审报告（包B）——v2 全交付，2026-10-29

- 审计角色：敌意复核者（模拟评分方/第二名选手），目标是在 v2 交付中找真实缺陷。
- 方法与铁律：只读审计 + 离线复算；零 live API 调用；未执行任何 git 命令；未改 CHANGELOG；未读 lead/builder 过程叙述（只读仓库产物与 PREREGISTRATION）；本目录外零写入。
- 预注册依据：`1-评测方案/自动循环L1-2026-10-29/PREREGISTRATION.md` 总则与包B。
- 复算环境：`/usr/bin/python3 3.9.6`，仅标准库；复算方法在附录A，可独立重放。
- 时点：首轮审计完成于 13:24–13:52 +08:00；对循环内修正（AMENDMENT-1）的核验完成于 13:52–13:58；对 D4 处置（AMENDMENT-1 重发 `999d345`）的复验完成于 14:03 前后，AUDIT.md 随即定稿。

## 0. 总判定

**无 blocking。** 首轮唯一的 blocking 候选（r1030 DSH weighted 总分发布值 414.07）经重分类为 **defect（报告链数字错误）**：判卷合同本体经审计无缺陷（17 pin / 10 slots / 220 指针 / 逐场重算全过），数字错误已在循环内按预注册修正案程序修正（核验见 D1）。lead 依据总则#3 裁定不提前停止，循环继续；本审计员原有的「建议整体停止」与 lead 裁决均如实保留于 D1（机制透明）。

分级计数：**blocking 0 / defect 4 / observation 3 / note 2**。
- D1：报告链数字错误 414.07→444.07（**已在循环内修正**，AMENDMENT-1）
- D2：v2 registry 7 条收据未进机读六账（问题池，留下一轮；条目已含影响/下一步/停止条件，老师④格式）
- D3：B13a 验收回放收据与实并合同不符（问题池，留下一轮；条目已含影响/下一步/停止条件，老师④格式）
- D4：AMENDMENT-1 时间戳早写（**已修正**，`999d345`，时点改锚 git 记录）
- O4/O5/O6、N7/N8：见正文（O5 勘误块已补「判读句待 r1031 n=3 检验」声明，`999d345` 一并提交）。

**包B收束**：0 blocking，四 defect 处置如上（D1/D4 已修正、D2/D3 问题池留下一轮）。本文件定稿即为包B最终交付。

三方独立收敛（judge 自检 13:40 → 包B盲审 13:52 → AMENDMENT-1 采纳）是本轮最重要的机制结论之一：报告链曾存在一个传导性数字错误，且被两个互不知情的独立机制抓住。

---

## 1. 发现清单（defect 级）

### D1【defect · 已在循环内修正】DSH weighted 总分发布值 414.07 错误，实为 444.07；gap₀=30.74 锚定失真 → AMENDMENT-1 修正

- **证据（独立重算，非引用）**：
  - 十场 `checker.stdout.json` 按 `3-表现现场/r1030-formal-a1/tools/build_import.py:22-27` GUARDS 与 `:21` 分母 (15,10,6,4,27) 逐场重算，10/10 与 stdout `weighted` 一致（codex 93.33/70.0/100.0/100.0/81.48；dsh 100.0/70.0/100.0/100.0/74.07）。
  - 总分：codex **444.81** ✓；dsh = **444.07** ≠ 原发布值 **414.07**；真实 gap = **0.74** ≠ 30.74。
  - 成因假说（本审计提出，AMENDMENT-1 已采纳为假说）：414.07 与 70+70+100+100+74.07 精确相等，疑为总行汇总时 bird 行误抄 dabstep 的 70.0。
  - 原内部矛盾：README 判读句称总分差由 bird（−6.67 对 codex）与 cargo（+7.41 对 codex）构成，净差仅 0.74，与 30.74 表值不可能同真。
  - 错误传播链（修正前）：r1030 README 总行 → `5-评测报告/阶段报告-v4.1.md` → `PREREGISTRATION.md:19,28` 包A锁定判据 gap₀=30.74。
- **循环内修正核验（本审计逐项落盘验证，非转述）**：
  - `1-评测方案/自动循环L1-2026-10-29/AMENDMENT-1.md`（磁盘 birth/mtime 13:50:09）：主判据 gap₀ 改 **0.74**（=|444.81−444.07|），30.74 降为敏感性对照；预注册原文与封印不改写；勘误「只修数字、不改叙述」。
  - `3-表现现场/r1030-formal-a1/README.md:15` 已改 444.07 且 `:19` 有显式勘误行（mtime 13:45:42）；`阶段报告-v4.1.md:9` 同（含勘误注）。
  - 参数化后验收矩阵 `5-评测报告/可重复性-n3-2026-10-29/verify-matrix-selftest-r1030.json`（13:46:22 生成）：`judgment_criteria.gap0_main=0.74`、`gap0_sensitivity=30.74` 并写明动机与时点；其 SHA `31534cec…` 与工具 `verify_var_n3.py` SHA `e6e9a6e5…` 与 AMENDMENT-1 权威哈希逐一吻合。
  - 残留口径（如实记录）：该矩阵的 claim 对照仍冻结原稿值 414.07（`all_match:false`）——作为「原主张已被推翻」的轨迹保留成立，但读者须结合勘误理解；判读句「这是单场方差而不是稳定差异」按「只修数字」原则未改（→ O5 继续成立）。
- **处置记录（机制透明）**：本审计员首轮基于「包A预注册判据 gap₀ 锚定失真」给出**建议本循环提前整体停止**（13:52 先报 lead）。lead 裁决（原话要点）：不停止——总则#3 的 blocking 停止条件限定于判卷合同缺陷；盲审已实证合同无缺陷；锚点缺陷已依预注册程序走 AMENDMENT-1（先于 judge 对 r1031 的任何聚合分析、动机为历史值勘误）补救，循环继续。本审计员接受该裁决并记录双方立场。
- **影响**：已消除（数字与判据均已修正并有独立收据）；残余风险为 O5 措辞与 N7 验收语义。
- **停止条件**：已闭（修正落盘+双口径声明）。下游文档再引用 414.07/30.74 为真实差即重开。

### D2【defect · 问题池，不自动修复】v2 config 的 work_registry 指向 v1 台账：v2 registry 追加的 7 条收据未进任何机读冻结产物

- **证据**：
  - `4-打分细则/可信冻结-2026-10-29-v2/config.json:132-135`：`work_registry.path = "4-打分细则/可信冻结-2026-10-29/work-registry.json"`（v1 路径，SHA 吻合）。
  - v2 版 `work-registry.json`（被 lock 封印）追加 7 条事件：5 个 r1030 判分器自测（`work:r1030-selftest-*`）+ `work:r1030-cli-preflight` + `work:wb-admission-preflight-20261029`；`README.md:7` 声称「工作台账追加本批自测与预检收据（5 自测 + 2 预检）」。
  - 实际产物 `5-评测报告/可信冻结-2026-10-29-v2/six-ledgers.json`：self_test=8（无任何 `work:r1030-selftest-*`）、interface_preflight=11（无上述 2 条）。
  - `1-评测方案/正式批次-2026-10-29/README.md:35-36` 写明 self_test/interface_preflight「(registry)」——与机读产物不符。
- **影响**：r1030 的 5 份判分器自测收据与 CLI/WorkBuddy 预检收据仅被 v2 registry 文件+lock pin 间接锚定，未进六类分账机读台账；「完全分账」在冻结产物层面缺账。**不影响 A 组 10 行准入与任何分数**（product_run 走导入通道）。
- **下一步**：下一版合同（v3 或勘误版 config）把 `work_registry.path` 指向 v2 台账并重封；或正式披露「该 7 条以 registry 文件+lock pin 为准，不进六账产物」。
- **停止条件**：合同修订留待下一轮（总则#3）；本轮以披露闭项。

### D3【defect · 问题池，不自动修复】B13a「历史回放重跑 flipped=0」的验收收据与实并合同不符；README §4 表与刷新后 JSON 不同步

- **证据**：
  - `4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay-results.json`（19:28 刷新）的 `after_contract["tb-cargo-plan"]` 指向 `after/tb-cargo-plan/checker.py` = SHA `70acdbb7…`（17:55，**B13a 并入前**字节）；现行 `2-用例/tb-cargo-plan/checker.py` = `d84b1111…`（19:26 并入 B13a，含 b13a 断言）。
  - 即 README 补充段（`README.md:185-192`）所称「B13a 并入后 24 场历史只读回放重跑 flipped=0（replay-results.json 已刷新）」实际重放的是 **B12/B14 合同**；B13a 合同从未直接跑过 24 场回放。
  - 同文件内不一致：README §4 表（`:114-119`）仍写 ledger_match 15/24，刷新后 JSON 为 **16/24**。
- **缓解（审计确认）**：① B13 硬闸门预检（`replay-b13-candidate-precheck.json`）显示 3 场翻转全部来自 legs 侧、顶层精确键集 0 场多余键——B13a（仅顶层）低风险，但属推断非执行记录；② 2026-10-29 00:53（+08）独立复核回归 `5-评测报告/独立复核-2026-10-29/checker-regression.json`（+receipt）：现行合同（含 d84b1111）五题自测 5/5、SHA 校验 47/47 通过；r1030 两场 cargo 由 d84b1111 判分，判分行为有现行收据。
- **影响**：收紧批五件套中 B13a 的「历史复算影响」环节引用了不对应实并合同的收据，验收表述失实（非判分错误）。
- **下一步**：用 d84b1111 对同一 24 场重跑 top-only 轨，另存 `replay-b13a-results.json`；更正 README 补充段与 §4 表（16/24）。
- **停止条件**：若补跑出现任一历史有效场翻转 → B13a 违反硬闸门，须回退或走版本决策。

### D4【defect · 已修正（`999d345`）】AMENDMENT-1.md 时间戳早写：内部时间线标签晚于文件创建时刻，时点声明可靠性受损

- **证据（首轮发现，2026-10-29 13:52:47 实测）**：
  - `AMENDMENT-1.md` 初稿磁盘 birth=mtime=**13:50:09**；本审计取当前时钟为 **13:52:47**（`date` 实测）。
  - 初稿文件头自称「2026-10-29 **13:55** +08:00」；正文含「权威哈希，2026-10-29 **14:05** 更新」「独立佐证与成因假说（2026-10-29 **14:20** 增补）」——三个标签均晚于文件创建时刻与当前时钟。
  - 涉事实体均可提前验证存在且早于标签：勘误行（README/阶段报告，mtime 13:45:42）、参数化工具与矩阵（13:46:10/13:46:22，SHA 与「14:05 更新」段所列权威哈希一致）、本审计的独立重算（先报消息早于 13:50）。**无证据伪造，但时间标签不可靠。**
- **裁定与处置（已修）**：lead 答复成立——初稿内嵌的 13:55/14:05/14:20 系撰写时**预估的时间标签，未实读时钟**，全部作废。AMENDMENT-1 重发（提交 `999d345`，文件 SHA-256 `542e4a7b65d818ad4fb6f52215d1087f160671a7c5ce5e5b0589d3ba444696d9`，本审计实测吻合）：移除全部手写时钟标签，新增「时间轴与 D4 勘重」节（本发现与裁定原文写入），一切时点只锚 **git 提交哈希+git 记录时间**。
- **锚定方案采纳记录**：本审计建议「改锚磁盘 mtime 链（13:45:42→13:46:22→13:50:09）+提交哈希」；lead 采**仅锚提交哈希**——理由成立：mtime 已被本次修正案编辑自身改变，不再可靠，git 记录才是稳定锚。重发版时间轴（13:45:51 `292cf18`、13:47:29 `474a8ed`）与磁盘旁证相互吻合，另披露 lead 提交信息曾误写「0.44」（正值 0.74，正文为准）。
- **影响**：已消除。时点主张「先于 judge 对 r1031 任何聚合分析」自 `999d345` 起只依赖 git 可验证记录，不依赖文件自述。
- **停止条件**：已闭。若任何时点主张再次脱离 git 记录自证，重开。

---

## 2. 观察与备注

### O4【observation】r1030 正式批结论未按五段结构呈现
- `3-表现现场/r1030-formal-a1/README.md` 判读段混合观察与解释，无「未排除因素」「可复现实验」节；`阶段报告-v4.1.md` §一.3 同。对照：机制复制 `RESULTS.md` 五段齐全。
- 影响：反馈第⑥条与预注册总则#5 在首批正式批这一关键结论上未满足。
- 下一步：补五段小结（可作附录，注明补记时间）。停止条件：补齐即闭。

### O5【observation · 已部分处置】n=1 表述越界：「这是单场方差而不是稳定差异」
- `r1030 README:17`、`阶段报告-v4.1.md:9`（数字修正后句子仍在，AMENDMENT-1「只修数字、不改叙述」）。n=1/格只能支持「与单场方差**不可区分**」；因果断言超出证据。
- 处置（lead，`999d345`）：r1030 README 勘误块已增补「另（盲审 O5）：判读句……为 n=1 时点的判断，现正由 r1031 n=3 重复运行直接检验，最终以 RESULTS 为准」（本审计已核验在盘）。
- 下一步：包A RESULTS 产出后以 n=3 结果回填该句结论。停止条件：n=3 检验声明落表即闭。

### O6【observation】批次命名空间与历史 run_id 冲突：r1030/r1031 前缀复用
- 历史冻结账 `运行总账-2026-10-24.json` 已有 `r1030/yuanbao/lcb-recent-hard-4`、`r1031/yuanbao/lcb-recent-hard-4`；本循环正式批 r1030-formal-a1、包A r1031；`未知登记.json` lcb-389g-oracle impact 的「r1030/r1031 元宝 35 候选」（指 2026-10-26 桌面批）现产生歧义。
- 机读无字面冲突（run_id 字符串不同，freeze.py 去重通过）；人类引用不再唯一。
- 下一步：两批 README 加消歧注；未来批次避开冲突前缀。停止条件：注记入即闭。

### N7【note】「以 official-main-table.json 为准复现 known weighted」不可执行；验收 summary 语义需区分
- `official-main-table.json` 仅含 rule_version/groups(事件ID)/rejected/ranking，无分值；循环收束条款的验收锚实际落在 r1030 README（B1 错误源）。参数化后矩阵 `summary.passed=10/failed=0` 与 `all_match:false`（对已作废原稿值的轨迹性比对）并存，只读 summary 会误读。
- 下一步：验收输出顶层加硬失败位/明确「anchor 比对对象为原稿值，仅作轨迹」；或循环收束条款改锚 README errata 后数值。

### N8【note】机制复制「6/6 场次观察正确」措辞含糊；SSE 分块使朴素 grep 失效
- DSH `02-response.sse` 按 `"AM"+"BER"+"-"+"731"` 分块流式输出，直接子串搜索 0 命中；按 delta 拼装后两场 call2 均正确报出 `{"HEAD_KEY": "AMBER-731", "TAIL_KEY": "COBALT-492"}`；codex rollout 7 处命中。6/6 = 3 份最终应答 × 2 键。两场响应 SSE 哈希不同、`raw_response_sha256` 与 analysis 吻合，无拷贝痕迹。
- 建议：RESULTS/审计工具注明「拼装文本」口径。

---

## 3. 逐项清单结果（7 项）

### 3.1 freeze v2 合同 —— ✅ 通过（合同本体），关联 D2
- 17 个 pin 逐一重算 SHA-256：**17/17 吻合**（`freeze.lock.json:3-72`）。
- config 10 个 official_slots：**10/10** 绑定 `plan_sha256=5e4452b5…`，与 `registration-plan.json` 实测 SHA 一致；slot_id 与 plan registrations 一一对应（`config.json:136-187`）。
- schema `$id`：`config-schema.json:3`、`import-schema.json:3` 均为 `freeze-20261029-v2/*`；`test_freeze.py` 经 `f.BASE/f.RULE` 引用 v2 常量，无 v1 残留路径。
- 离线执行 `freeze.py verify`：**ok**（A=10/B=0，96 历史行；来源 242 verified / 84 external_not_packaged）；`test_freeze.py` **38/38 通过**。
- config 引用的 v1 work-registry 与历史总账 SHA 均吻合；v2 registry 自身「封而不用」→ D2。

### 3.2 r1030 证据链 —— ✅ 通过
- 时序：10/10 场 `registered_at=02:10:00+08:00 < started_at`（02:12:00–02:29:17）；started_at ≥ `effective_at=02:12:00+08:00`。
- 结构：10/10 场 facts=15、gates=5，gates 全 true 且 refs≥1，无 unknown fact。
- 指针：**220 项** fact/gate/score/selection-plan 引用逐一解析比对，**0 失配**。
- integrity-rescan ↔ adjudication 一致：codex 5 场 0 命中→clean；dsh 5 场各 1 命中→clean-reviewed（benign 复核注记+行级证据）；`integrity-rescan-summary.json` 与逐场文件一致。
- `meta.corrections`：10/10 场如实披露 `r1030-archiver-log-loss`（r1030#1，`fixed_in` 指明 tools/lab.py 修复），未静默改写；批次 README §归档缺陷披露。

### 3.3 独立重算分数 vs 正式表 —— ⚠️→✅（D1 已修正）
- GUARDS 口径 10/10 场重算一致；A 组 10 行事件 ID 与 `official-main-table.json` 完全一致；headline 双 3/5 ✓。
- DSH 总分重算 444.07；原发布 414.07 为报告链错误（D1，已修正并有勘误行）。

### 3.4 机制复制 —— ✅ 通过
- 3 场（443→1514/+1071、443→1495/+1052、8610→15093/+6483）与 `replication-analysis.json` 及逐请求收据吻合；DSH 侧逐请求 request/response.sse/transport/capture-status/tool-process 齐全；夹具三方字节一致（35767 B，`fed5759…`×3）；codex 侧产品自报已披露。
- 「未内联/全量内联」主张在证据内（DSH 02-request 4289/4203 B 不含夹具正文探针串；codex 增量 ≈6.5K tokens 与 35767 B 相称）。
- 跨 Harness 绝对值不可比：已列为未排除因素#2，**被遵守**。
- 5 事件导入 v2：`replication-events.json` 在 build-recipe 内，`verify` 整体重建通过（含 validate-import）。

### 3.5 判卷历史 —— ⚠️ 见 D3，其余可追溯
- B2/B8/B12/B14：before/after 字节齐（bird `01447ab6→994be0b3`=现行 ✓；lcb `e07654d4→63845361`=现行 ✓；cargo `bac8cc61→70acdbb7`≠现行 `d84b1111`→D3）；正例/近似错误例（自测 #24/#25、#8/#9、b13a_top_extra_keys）与独立验收收据齐；历史复算影响（24 场 0 翻转 + B13 闸门 3 场翻转证据）固化于两个 JSON；B13 维持现状裁定归档 `4-打分细则/裁定-2026-10-28-b13-legs-维持现状.md`。
- 后置独立验收：2026-10-29 00:53 回归（现行合同 5/5 自测 + 47/47 SHA）入库并登记 `work:regression-20261029-lead`。
- 第三方样例集 `upstream-third-party-samples/`（四目录+manifest）在位；回归 SHA 快照三层（10-26/10-27/10-29）可追溯。

### 3.6 报告面 —— ⚠️ 见 O4/O5
- 五段结构：机制复制 RESULTS ✅；r1030 批次结论 ✗（O4）。
- 未知登记：主册 13 条 impact/next/stop 齐全；r2 册 6 条中 4 条内嵌齐全，2 条 WB 未知经 `registered_in` 指向 `wb-preflight.json`（impact/next/stop/reopen 2×4 字段实测存在，文件被 lock pin #15 封印）——合规，属间接引用。
- 无「未知被悄悄记成失败」（WB 不纳入≠记失败；机制混杂限 research）；无「按已评部分折算满分」（`no_zero_no_rescale` 机器强制，10 场全分母）。
- cli-stdout-display-truncation 以 accepted_limitation 结项且口径固化，与包A工程项(a)无矛盾。

### 3.7 挑战主张 —— ⚠️ 见 O5、D1；机制复制通过
- 443→1514 vs 8610→15093 解释**未超出证据**；n=1 处越界措辞（O5）与错误数字（D1，已修正）。
- 「失败格局与历史完全一致」对照 r1027（86.67/70/100/100/70.37 双款同分）成立。

---

## 4. 审计覆盖与限制

- 未验证（超出只读/离线边界）：Git 提交锚（`213013b`、`292cf18`、`474a8ed`、`999d345`、封印 `be39fc2`）的先后关系仅依据仓库内自述、重发版 AMENDMENT-1 时间轴与磁盘 mtime 旁证（13:45:42 勘误 → 13:46:22 矩阵 → 13:50:09 初稿 → `999d345` 重发），未执行 git 命令核验；修正案的时点主张已按 D4 处置改锚 git 记录，本审计对其的依赖以文件 SHA 实测（`542e4a7b…96d9` 吻合）为限。
- 包A（r1031）在跑产物未纳入审计范围；`~/bench-workspaces/` 仓库外工作区未读取。
- 独立复核员洁净室收据（`独立复核-2026-10-29/reviewer/final-0{1,2,3}.json`，sandbox 拒网+隔离 HOME）存在且自洽；本轮未重复其执行，仅抽验引用。
- 本报告不修复审计范围外任何文件；D2/D3/D4 按 lead 处置归档问题池，留下一轮。

## 附录A：复算方法（可独立重放）

1. 总分：`sum(checker.stdout.json["weighted"])`（每产品 5 场）；或按 `build_import.py` GUARDS 从 `checks[]` 重算 `round(100*Σpass/Σscored,2)`——两法 10 场结果一致。
2. 指针校验：对 `formal-a1-events.json` 每事件的 facts/gates/score refs 与 `selection.plan_pointer`，按 RFC 6901 JSON Pointer（含 `~0/~1` 转义）在 `sources[path]` 解析并比较值与类型。
3. 时序：`datetime.fromisoformat` 比较 `selection.registered_at < facts.started_at` 且 `facts.started_at ≥ config.effective_at`。
4. lock 校验：对 `freeze.lock.json` 17 个 pin 逐文件 `shasum -a 256`。
5. 全量合同校验：`python3 4-打分细则/可信冻结-2026-10-29-v2/freeze.py verify`（exit 0）；`python3 …/test_freeze.py`（38/38）。
6. 修正案核验：勘误行 grep（444.07/勘误）、`verify_var_n3.py` 与矩阵 SHA 比对 AMENDMENT-1 权威哈希、`judgment_criteria` 块读取、文件 birth/mtime 与 `date` 时钟对照（→D4）。
