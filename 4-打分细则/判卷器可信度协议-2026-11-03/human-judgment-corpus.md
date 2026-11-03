# 人工判定语料盘点（L38 主项 D）

- 生成时间：2026-11-03T14:50:29+08:00（Asia/Shanghai）
- 任务：对既有评测记录中全部「人工判定事件」建立机器可读盘点。**零发射**：只读公开仓与私档注记、零模型调用、零联网、零判分重算、未改动公开仓任何文件。
- 机器账：`human-judgment-corpus.json`（write-once 生成；本 md 与其同源同批生成，计数一致）。

## 1. 盘点方法

- **封闭清单**：按任务给定 9 源照单全查，不做开放搜索（注记：PREREG 原列 8 源，源 9=源 3 目录内收据子集的显式拆分，封闭范围未扩大）。源→物理路径：

| 源 | 路径（公开仓相对） | 条目数 |
|---|---|---:|
| 源1 | 4-打分细则/裁定-2026-10-26-dab-q2697.md | 7 |
| 源2 | 4-打分细则/裁定-2026-10-28-b13-legs-维持现状.md | 1 |
| 源3 | 5-评测报告/L5判卷修订-2026-10-30/ 与 L6判卷修订-2026-10-30/（另涉 evidence-kit 收据） | 11 |
| 源4 | 4-打分细则/判卷审计-2026-10-27/ | 14 |
| 源5 | 4-打分细则/判卷回归/ | 3 |
| 源6 | 3-表现现场/r1101-formal-b1/ 与 r20261031-wb-formal/ | 15 |
| 源7 | 3-表现现场/r20261101-yuanbao-n3/ 与 r20261101-doubao-n3/ | 8 |
| 源8 | 5-评测报告/验证器修订证据-2026-10-30/ | 9 |
| 源9 | 5-评测报告/L6判卷修订-2026-10-30/（两收据+VOIDED） | 3 |

- **只读**：全部证据仅读取；SHA-256 为脚本对本仓文件实测（`sha256` 字段：路径→完整十六进制）。
- **字段口径**：`availability` 判定政策——direct_test_item=标签与重判输入均在仓内可直接组 prompt；needs_construction=标签明确但需重组判分环境；context_only=政策/限制/未决背景。
- **条目原则**：如实盘点、不凑数不虚构；一条 = 一个可指认的人工判定事件（裁定/核定/终审/更正/金标收据/自测库），文件级 locator 到章节、行号或 JSON 键。

## 2. 逐条盘点（共 71 条，按 type 分组）

### ruling（口径/合同裁定） — 18 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-001 | 源1 | case | needs_construction | **q2697 判分口径维持官方兼容分**：人工裁定 dabstep q2697 记分维持官方兼容轨口径：通过值取『E:13.57』首数值≈13.57，严格轨按 signed-aci-v1 全串判定；不改金标、不改已发布分数、不重判历史（ADJ-DAB-2697-20261026-r1 生效）。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L7–L57（§0 裁定要点 / §3.1 判分口径：维持兼容分）） |
| HJ-002 | 源1 | case | context_only | **q2697 及两轨分差不用于能力归因**：人工裁定 q2697 因兼容轨挡不住多类负例（§6 实测），其兼容/严格两轨分差不进入任何产品能力归因结论，只在披露层单列。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L58–L61（§3.2 能力归因口径）） |
| HJ-003 | 源1 | assertion | needs_construction | **输出字段按 ACI（A–G）理解，guidelines {card_scheme} 为题面笔误占位**：人工裁定题面 guidelines 中 {card_scheme} 为占位笔误，输出字段集合按 manual 的 ACI 分类（A–G）解读，判分实现不受笔误影响。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L62–L65（§3.3 输出字段口径）） |
| HJ-004 | 源1 | assertion | needs_construction | **无匹配费率不得静默按 0 计**：人工裁定 checker 对无匹配费率输入不得静默按 0 计：合规处置为 covered-only 披露或 full-cost 记未知。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L66–L69（§3.4 未匹配交易处理口径）） |
| HJ-005 | 源1 | assertion | needs_construction | **多规则聚合 min/mean/max/sum 显式声明即等价可接受**：人工裁定四种聚合口径在输出方显式声明下等价可接受，且不得反向凑金标。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L70–L73（§3.5 多规则聚合口径）） |
| HJ-007 | 源1 | case | context_only | **q2697 停止追查=受控未知及重开条件**：人工裁定该题歧义按受控未知管理：停止追查并写明影响/下一步/停止条件；重开条件为官方口径变化、官方修题面或新独立证据。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L85–L94（§5 停止追查条件与下一步）） |
| HJ-008 | 源2 | tool | needs_construction | **B13 legs 精确键集维持现状（合同外延不收紧）**：用户拍板：legs 诊断字段在题面合同中合法，B13 精确键集校验不并入（历史 3 场合法输出会翻车）；判卷合同无新修订，并确立后续判卷器修订一律走六件套（老师要求⑤）。本裁定即该项关闭记录。 | [4-打分细则/裁定-2026-10-28-b13-legs-维持现状.md]（L1–L11 全文（裁定行 L9、后续六件套 L10）） |
| HJ-009 | 源3 | tool | needs_construction | **gate v2 not_executed 白名单修订并入**：人工核定 execution gate 的 not_executed 判定改为恰名白名单（registrations、whitelisted_entries），随 L5 批并入修后 l5-execution/gate.py（sha16 38b42a87c30c87d2）。 | [5-评测报告/L5判卷修订-2026-10-30/README.md]（L6–L15（gate v2（R4，池 L5-8））） |
| HJ-015 | 源3 | tool | needs_construction | **L6-A bird checker 增补 n_tasks/guards_used 元数据合同修订**：人工核定 bird checker 判分合同纯增两键元数据（n_tasks=15、guards_used=[input_integrity,answers_file,answers_schema,answers_coverage]），CONTRACT_REVISION=l6-meta-fields-2026-10-30，判分语义不变。 | [5-评测报告/L6判卷修订-2026-10-30/README.md]（L5–L26（L6-A：bird checker 元数据完备）） |
| HJ-018 | 源3 | tool | needs_construction | **L6-C 收据自引排除规则（self-referenced hash entry）**：人工核定新规则：evidence 收据 files_sha256 含自身哈希条目即构成 violation『self-referenced hash entry』，堵住收据自我背书（AUD-L5-O1 修正）。 | [5-评测报告/L6判卷修订-2026-10-30/README.md]（L27–L38（L6-C：收据自引排除）） |
| HJ-020 | 源8 | tool | needs_construction | **gate l7 显式计划目录+binding 修订并入**：人工核定 gate 调用契约改为显式计划目录+binding、缺参报 GateError（修前 sha16 38b42a87c30c87d2 → 修后 25dbf52e46404）；预注册旧文称 ValueError 的偏差如实保留，不以摘要消除。 | [5-评测报告/验证器修订证据-2026-10-30/README.md]（L5–L20（观察/证据/解释）） |
| HJ-032 | 源4 | tool | needs_construction | **收紧批 B2 并入（行精确键集 + SQL 禁注释符）**：人工核定 B2a（行级精确键集）与 B2b（SQL 禁 -- 注释符）并入 bird checker 合同（contract_revision=b2-tighten-2026-10-27）。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L69–L78（### B2 bird-ca-schools-15）） |
| HJ-033 | 源4 | tool | needs_construction | **收紧批 B8 并入（stderr 披露式，行为不变）**：人工核定 B8 以披露式 stderr 报告并入 lcb checker（v0.1 行为不变）。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L79–L87（### B8 lcb-recent-hard-4）） |
| HJ-034 | 源4 | tool | needs_construction | **收紧批 B12 并入（距离容差 0）**：人工核定 B12 距离容差收紧为 0 并入 cargo checker（contract_revision=b12-b14-tighten-2026-10-27）；24 场回放 0 翻转。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L88–L96（### B12 tb-cargo-plan）） |
| HJ-035 | 源4 | tool | needs_construction | **收紧批 B14 并入（补 cargo_on_board_lbs）**：人工核定 B14 契约补 cargo_on_board_lbs 键并入 cargo checker。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L97–L108（### B14 tb-cargo-plan）） |
| HJ-036 | 源4 | tool | needs_construction | **B13 整项硬闸门否决（候选回放翻转 3 场）**：人工判定 B13（legs 精确键集硬闸门）整项不并入：候选回放翻转 3 场（doubao/yuanbao/ablation 的 cargo 场），legs 多出 4–5 键均为合法诊断字段；最终以裁定-2026-10-28 关闭（HJ-008）。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L44–L66（## 2. 硬闸门：B13 触发）） |
| HJ-037 | 源4 | tool | needs_construction | **B13a/B13b 拆分裁决（顶层 PLAN_KEYS_TOP 并入、legs 不并入）**：Lead 复核后裁决拆分执行：B13a 顶层 PLAN_KEYS_TOP 精确键集并入 cargo checker（配自测 b13a_top_extra_keys），B13b legs 部分维持不并入。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L187–（补充并入：B13a（2026-10-27 晚，Lead 复核后裁决））） |
| HJ-042 | 源4 | tool | needs_construction | **lcb389g 重放夹具受控替换为独立参考解（Lead 授权，历史影响=0）**：2026-10-27 Lead 授权受控替换 2-用例/lcb-recent-hard-4/solution/abc389_g.py：重放夹具（sha16 0c61e2bc…）→ 独立参考解（sha16 1755f0b5…）；selftest 11/11 前后一致，四点论证历史分数影响=0，旧夹具留档 abc389_g.replay-fixture.bak.py。 | [4-打分细则/判卷审计-2026-10-27/lcb389g-oracle-替换/README.md]（L1–L79 全文） |

### revision_fixture_positive（修订正例） — 2 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-010 | 源3 | tool | needs_construction | **gate v2 正例世界验收（plain / registrations-dir）**：人工核定两个正例世界（plain、registrations-dir）下 gate v2 必须放行；验收脚本 8 项断言全过（receipt all_pass=true）。 | [5-评测报告/L5判卷修订-2026-10-30/gate-v2-acceptance-receipt.json]（worlds=[plain,registrations-dir]（assertions 8/8, all_pass=true）） |
| HJ-016 | 源3 | tool | needs_construction | **L6-A 修后 selftest 正例 29/29（含元数据不变量两分支）**：人工核定修后 checker selftest 29/29 全过，含新增『L6-A 元数据不变量』满分/空产物两分支。 | [5-评测报告/L6判卷修订-2026-10-30/README.md]（L14（正例：checker selftest 29/29）） |

### revision_fixture_near_miss（修订近似错误例） — 3 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-006 | 源1 | case | needs_construction | **q2697 兼容/严格两轨正反例期望判定表（1 正例 + 9 负例探针）**：人工核定 10 个探针在兼容/严格两轨下的期望判定：正例 E:13.57 双轨通过；负例 NexPay:13.57、纯数字、E:13.6、Z:13.57、E:-13.57、E:14、B1 E:41.66、B2 E:16.63、B3 C:131.20 各有明确期望；实测兼容轨挡不住 N1/N2/N3/错 ACI/符号翻转——该题不得归因的直接技术依据。 | [4-打分细则/裁定-2026-10-26-dab-q2697.md]（L95–L124（§6 正反例，现行 checker 实测 2026-10-26）） |
| HJ-011 | 源3 | tool | needs_construction | **gate v2 近似错误例验收（typo-variant / reg-plus-extra / fabricated-extra）**：人工核定三种近似错误世界（拼写变体注册目录、多注册目录、伪造 extra 产物）必须被 gate v2 拒绝。 | [5-评测报告/L5判卷修订-2026-10-30/gate-v2-acceptance-receipt.json]（worlds=[typo-variant,reg-plus-extra,fabricated-extra]（assertions 8/8, all_pass=true）） |
| HJ-017 | 源3 | tool | needs_construction | **L6-A 近似错误例：篡改 n_tasks / 漏 guards_used 必拒**：人工核定两类近似错误必须被修后 checker 拒绝：n_tasks 篡改为 14；guards_used 漏 answers_schema（canonical 收据断言 D/E 实证）。 | [5-评测报告/L6判卷修订-2026-10-30/README.md]（L14–L26（近似错误例 a/b）） |

### correction_chain（更正链/勘误/废止） — 13 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-013 | 源3 | tool | needs_construction | **cache mapping v2 修订并撤销『responses 协议缺 cache 字段』finding**：人工判定 L4 期『responses 协议缺 cache 字段』finding 实为 v1 映射缺陷：v2 改为 wire_key+嵌套 input_tokens_details.cached_tokens（别名不求和）后复算通过，finding 自 mapping v2 起撤销。 | [5-评测报告/L5判卷修订-2026-10-30/README.md]（L16–L21（cache mapping v2（R5，池 L5-5））） |
| HJ-022 | 源8 | tool | needs_construction | **l7 复算收据 跨pin复算设计误（VOIDED 废止登记）**：人工判定 r1 复算设计跨封印 pin、结果无效，废止重做；收据内保留失败断言作为设计误的证据。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r1-VOIDED-跨pin复算设计误.json]（全文（含失败断言）） |
| HJ-023 | 源8 | tool | needs_construction | **l7 复算收据 冻结副本错位（VOIDED 废止登记）**：人工判定 r2 复算使用错位的冻结副本（代际/来源不符），废止。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r2-VOIDED-冻结副本错位.json]（全文（含失败断言）） |
| HJ-024 | 源8 | tool | needs_construction | **l7 复算收据 部分世界复判设计误（VOIDED 废止登记）**：人工判定 r3 仅复判部分世界的设计不满足全量复判口径，废止。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r3-VOIDED-部分世界复判设计误.json]（全文（含失败断言）） |
| HJ-025 | 源8 | tool | needs_construction | **l7 复算收据 树内binding代际错位（VOIDED 废止登记）**：人工判定 r4 树内 binding 取错代际，废止。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r4-VOIDED-树内binding代际错位.json]（全文（含失败断言）） |
| HJ-026 | 源8 | tool | needs_construction | **l7 复算收据 证据缺位（VOIDED 废止登记）**：人工判定 r5 复算证据缺位、不可复核，废止。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r5-VOIDED-证据缺位.json]（全文（含失败断言）） |
| HJ-027 | 源8 | tool | needs_construction | **l7 复算收据 跨批重演设计废弃（VOIDED 废止登记）**：人工判定跨批重演设计废弃；历史复算口径改走各批封印基线引用（与 HJ-021 衔接）。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt-r6-VOIDED-跨批重演设计废弃.json]（全文（含失败断言）） |
| HJ-031 | 源9 | tool | needs_construction | **l6-meta 复算收据 r1 VOIDED（比对伪差）**：人工判定 r1 收据 13/15 中两条 false 为 answers_file.note 路径未归一的伪差（detail 实为 reward frozen=1 rerun=1），非判分差异；废止并以 canonical 收据重出（11:24:19 → 11:25:31）。 | [5-评测报告/L6判卷修订-2026-10-30/l6-meta-recompute-receipt-r1-VOIDED-比对伪差.json]（全文（13/15，两条伪差）） |
| HJ-038 | 源4 | batch | needs_construction | **收紧批 README 双勘误（2026-10-29：ledger 16/24 与 b13a 收据指向）**：两处勘误（原句保留、勘误行更正）：① L2 包A ledger_match 15/24 系初版快照口径，按 19:28 刷新版 replay-results.json 应为 16/24（逐 case bird 2/10、lcb 4/4、cargo 10/10，差异即 r1029 doubao lcb 一行）；② 盲审 D3 澄清 replay-results.json 的 after 轨实为 B12/B14 合同（cargo 70acdbb7…），B13a 合同回放以 replay-b13a-results.json 为准（24 场 flipped=0、ledger_match=15/24，行集冻结 41 行排除 r20261027-wb-lcb-sandbox）。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/README.md]（L121（勘误 L2 包A）） |
| HJ-044 | 源4 | tool | needs_construction | **cargo 上游前提更正（『自研无上游』不成立）**：人工查明 tb-cargo-plan 与 harbor-framework/terminal-bench 的 tasks/cargo-flight-dispatch 完整对应，truth.json source 声明被 9/9 字节级证实；更正父任务『自研、无上游』前提。 | [4-打分细则/判卷审计-2026-10-27/upstream-third-party-samples/README.md]（§4 ### ⑤ 更正：cargo 有上游） |
| HJ-064 | 源7 | batch | needs_construction | **yuanbao-n3 装配缺陷判分更正链（bird r2c / dabstep r1c 误判 0 → v2 重判）**：人工查明并更正：v1 装配存在后缀槽位寻址缺陷（suffix-blind 误读基础槽目录、丢弃已交付 answers.jsonl），致 bird r2c / dabstep r1c 被误判 0；v2 修复装配后重判 bird r2c=86.67（reward 1）、dabstep r1c=20.0（reward 0，值更正、裁定不变）；v1 收据以 reassembly-v2 标记保留，更正后完整哈希清单收据（corrected-after）私档留档；其余槽位判分不受影响（交付物目录为空是事实不是缺陷产物）。 | [3-表现现场/r20261101-yuanbao-n3/README.md]（L21–L23（## 更正链（本批内一处判分更正））） |
| HJ-065 | 源7 | scene | needs_construction | **yuanbao bird r2c 判分更正（0→86.67，reward 0→1）**：单场更正记录：grading_id=reassembly-v2、reward=1、weighted=86.67，execution_receipt_sha256=49d87fa7…；correction={reason:'v1 assembly used base slot dir (suffix-blind) and dropped harvested answers.jsonl; v2 assembles with suffix fix', superseded_v1_reward:0}。 | [3-表现现场/r20261101-yuanbao-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r2c.json]（grading(grading_id=reassembly-v2) + correction） |
| HJ-066 | 源7 | scene | needs_construction | **yuanbao dabstep r1c 判分更正（值 0→20.0，reward 仍 0，裁定不变）**：单场更正记录：v2 重判 reward=0、weighted=20.0（值更正、判废裁定不变），execution_receipt_sha256=274813a6…；correction 字段同更正链。 | [3-表现现场/r20261101-yuanbao-n3/runs/dabstep-payments-10/run-dabstep-payments-10__r1c.json]（grading(reassembly-v2, reward=0, weighted=20.0) + correction） |

### final_adjudication（人工终审） — 19 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-049 | 源6 | scene | direct_test_item | **doubao/bird 终审 V（5 findings 全误报）**：人工终审 V（clean）：5 条 findings 全部误报——assignment.md 为任务书副本、q26 合同措辞与 bird-bench.github.io/arxiv URL 均为 instruction.md 题面自带（豁免口径同 r20261026）、trajectory L5 为题面回声；0 检索步骤、0 题解接触。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=doubao/bird-ca-schools-15（adjudication/verdict/integrity）） |
| HJ-050 | 源6 | scene | direct_test_item | **doubao/dabstep 终审 V（零命中）**：人工终审 V（clean）：扫描零命中。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=doubao/dabstep-payments-10（adjudication/verdict/integrity）） |
| HJ-051 | 源6 | scene | direct_test_item | **doubao/lcb 终审 V（零命中，产物 4 项）**：人工终审 V（clean）：扫描零命中；产物 4 项（4 题 sample 自测提交），轨迹无检索无越界。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=doubao/lcb-recent-hard-4（adjudication/verdict/integrity）） |
| HJ-052 | 源6 | scene | direct_test_item | **doubao/tb 终审 X（污染坐实，整场排除）**：人工终审 X（contaminated，findings=24）：污染坐实——trajectory L62–75 出工作区全盘检索 cargo 材料，L67 列出私档树中 r1029 场 truth.json/checker.py 路径，L68 自述读 oracle/checker，L74–75 实读 checker 源码，L82 自述『The output matches the expected truth』；属桌面 agent 全盘文件访问的结构性越界；处置=1/100.0 留档不采用、整场排除主表、不按子题豁免（session/memory/MEMORY.md 为空，非跨会话记忆泄漏）。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=doubao/tb-cargo-plan（adjudication/verdict/integrity/score_disposition）） |
| HJ-053 | 源6 | scene | direct_test_item | **doubao/exercism 终审 infrastructure_invalid**：人工终审 infrastructure_invalid（integrity=not_applicable）：发射期基础设施失败（点『新工作任务』后 5 次重试仍未达全新任务页），未创建会话、零模型暴露；按预注册配额制（每 slot 仅 1 次 kind=first 发射、失败即停不重试）该 slot 本批无 primary。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=doubao/exercism-py-6（adjudication/verdict/integrity）） |
| HJ-054 | 源6 | scene | direct_test_item | **yuanbao/bird 终审 V（0 检索+0 题解 URL）**：人工终审 V（clean，findings=0）：search_usage_audit 0 检索步骤+0 题解 URL；发送档位 auto（产品设置不可关闭，批后审计兜底）。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=yuanbao/bird-ca-schools-15（adjudication/verdict/integrity）） |
| HJ-055 | 源6 | scene | direct_test_item | **yuanbao/dabstep 终审 V（clean）**：人工终审 V（clean，findings=0）：审计口径同上，clean。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=yuanbao/dabstep-payments-10（adjudication/verdict/integrity）） |
| HJ-056 | 源6 | scene | direct_test_item | **yuanbao/exercism 终审 V（六文件全回收）**：人工终审 V（clean，findings=0）：六文件全回收（zipper 本批到位）。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=yuanbao/exercism-py-6（adjudication/verdict/integrity）） |
| HJ-057 | 源6 | scene | direct_test_item | **yuanbao/tb 终审 V（0 分系产物未达标非污染）**：人工终审 V（clean，findings=0）：0 分系产物未达标（诊断列另记），非污染。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=yuanbao/tb-cargo-plan（adjudication/verdict/integrity）） |
| HJ-058 | 源6 | scene | direct_test_item | **yuanbao/lcb 终审 V（driver suspect 改判 V，B22 同形态先例）**：人工终审 V：完成判定 v3 于 8min 冻结无答案块，无有效产出；会话证据完整（conv API dump），检索口径不适用且零命中；与 B22（r20261027）同形态先例一致，人工终审裁定运行有效、结果可判（无产物=0 分），非污染非运行失败——driver 保守提示 suspect 被终审改判 V。 | [3-表现现场/r1101-formal-b1/integrity/integrity-adjudication-r1101.json]（adjudications[] run=yuanbao/lcb-recent-hard-4（adjudication/verdict/integrity）） |
| HJ-059 | 源6 | scene | direct_test_item | **wb/bird 终审 valid（10 调用 0 违规；预训练记忆不作泛化归因）**：人工逐调用终审 valid/contamination_free=true：10 次工具调用逐条审阅均局限工作区（every_tool_call_reviewed=true），0 边界违规；.baseline.json 仅输入大小/mtime 不含答案；真实隔离 checker 15/15、reward1；独立来源复核确认。原生推理自述回忆 gold 完整保留不证明外读——预训练记忆仍不能排除，故不作泛化因果归因。 | [3-表现现场/r20261031-wb-formal/runs/bird-ca-schools-15/adjudication.json]（final_adjudication / boundary_violations[] / review_confirmation.basis） |
| HJ-060 | 源6 | scene | direct_test_item | **wb/dabstep 终审 invalid（12 处 /tmp 写执行）**：invalid/contamination_free=false：12 处边界违规（原始/派生 L23 及 L25/28/31/34/46/52/61/64/67/73/79 写入并执行 /tmp 脚本，违反只在工作区活动的预注册硬条款）；整场 X；原始真实 checker 3/10、30、reward0 完整保留不因判废改写；DAB2697 不作能力归因。 | [3-表现现场/r20261031-wb-formal/runs/dabstep-payments-10/adjudication.json]（final_adjudication / boundary_violations[] / review_confirmation.basis） |
| HJ-061 | 源6 | scene | direct_test_item | **wb/exercism 终审 valid（40 调用 0 违规）**：valid/contamination_free=true：40 次工具调用逐条审查均工作区内；六份实际冻结实现全文安全审查后在 OS 隔离执行原 checker 6/6、100、reward1；无外读或主动联网证据（预训练记忆与底层网络不作排除声明）。 | [3-表现现场/r20261031-wb-formal/runs/exercism-py-6/adjudication.json]（final_adjudication / boundary_violations[] / review_confirmation.basis） |
| HJ-062 | 源6 | scene | direct_test_item | **wb/lcb 终审 invalid（L50/L53 /tmp）**：invalid/contamination_free=false：2 处违规（L50 写并读 /tmp/t387.txt、L53 删除外部文件）；后续改用工作区 _scratch 不抵消违规，整场 X；真实隔离 checker 4/4、100、reward1 原分保留，不准入。 | [3-表现现场/r20261031-wb-formal/runs/lcb-recent-hard-4/adjudication.json]（final_adjudication / boundary_violations[] / review_confirmation.basis） |
| HJ-063 | 源6 | scene | direct_test_item | **wb/cargo 终审 invalid（L75/L78 /tmp）**：invalid/contamination_free=false：2 处违规（L75 复制到 /tmp/_a.json 并运行 dispatcher 写 /tmp/_b.json、L78 删除外部文件）；整场 X；真实隔离 checker 22/27、81.48、reward0 原分保留，不准入。 | [3-表现现场/r20261031-wb-formal/runs/tb-cargo-plan/adjudication.json]（final_adjudication / boundary_violations[] / review_confirmation.basis） |
| HJ-068 | 源7 | scene | needs_construction | **yuanbao tb r3 内容门定性并停止尝试（判别探针收据）**：人工定性 tb 任务书遭产品侧内容门静默拦截（判别探针：中性文本+同附件约 3 秒建会话成功，同附件+题面文本被门控），据此决定 tb r3 第 5 槽不再尝试、不改题面绕行（避免破坏题面冻结）；tb 列 0 有效运行如实入账。 | [3-表现现场/r20261101-yuanbao-n3/runs/_diagnosis/probe-tb-content-gate.json]（判别探针收据） |
| HJ-069 | 源7 | batch | needs_construction | **yuanbao 11 槽 launch_invalid 逐槽判定聚合（零筛除）**：人工逐槽判定 11 次发射失败为 launch_invalid（launch_verdict=launch_infra_invalid×10、launch_failed×1），全部带逐槽证据文本（前端改版期发送失效、浏览器自动更新期页签崩溃、网络抖动、发送吞没门），零 agent 交互、零筛除入账。 | [3-表现现场/r20261101-yuanbao-n3/batch-summary.json]（rows[] 23 行（launch_verdict/launch_failure_evidence）） |
| HJ-070 | 源7 | scene | direct_test_item | **doubao exercism r2 额度中断改期（quota_interrupted_U → r2b）**：按额度改期协议人工判定 exercism r2 为额度中断（quota_event.verdict=quota_interrupted_U），本行不判分，final_adjudication=quota_interrupted_superseded_by_exercism-py-6__r2b；重试槽 r2b 判 100。 | [3-表现现场/r20261101-doubao-n3/runs/exercism-py-6/run-exercism-py-6__r2.json]（quota_event + final_adjudication + status） |
| HJ-071 | 源7 | scene | direct_test_item | **doubao tb r3 额度拒发射改期（quota_rejected_U → r3b）**：按额度改期协议人工判定 tb r3 发射被产品额度拒绝（quota_event.verdict=quota_rejected_U、launch_verdict=launch_failed），final_adjudication=launch_invalid、零 agent 交互不判分；重试槽 r3b 判 70.37（落历史波动带内：81.48→70.37→70.37）。 | [3-表现现场/r20261101-doubao-n3/runs/tb-cargo-plan/run-tb-cargo-plan__r3.json]（quota_event + final_adjudication + launch_verdict） |

### replay_golden（回放/复算金标） — 9 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-012 | 源3 | batch | needs_construction | **gate v2 历史复算金标（17/17 槽，L4 formal 0/17 不变）**：复算金标：17/17 槽按 gate v2 复判，bird 白名单 fail 消失且 record_valid=True，L4 formal 判定 0/17 保持不变（修订不翻历史）。 | [5-评测报告/L5判卷修订-2026-10-30/gate-v2-history-recompute-receipt.json]（17/17 槽） |
| HJ-021 | 源8 | tool | needs_construction | **l7 复算验收收据（12 项通过，含封印 pin 拒绝 P4）**：复算金标：12 项验收全过，其中 P4 为『封印 pin 拒绝』的期望失败项（跨 pin 复算被正确拒绝）；历史复算口径改为引用各批封印基线（正式纳入 0/17、5/6、1/1）。 | [5-评测报告/验证器修订证据-2026-10-30/修订与复算/l7-gate-recompute-receipt.json]（12/12 项通过） |
| HJ-029 | 源9 | batch | needs_construction | **L6 元数据修订 canonical 历史复算金标（15/15 断言 A–E × 2 工作区）**：复算金标（2026-10-30T11:25:31+08:00）：冻结工作区可复现（reward frozen=1 rerun=1）、修后零翻转、键集恰增 ['guards_used','n_tasks']、篡改 n_tasks=14 与 guards_used 漏项均被拒；覆盖 l5-e3-wb-bird 与 e2-aborted-wb-bird。 | [5-评测报告/L6判卷修订-2026-10-30/l6-meta-recompute-receipt.json]（assertions 15/15（A–E × 两工作区）） |
| HJ-030 | 源9 | tool | needs_construction | **L6-C 自引排除历史回放金标（E2 自引被抓获）**：回放金标：四文档期望全中（all_expectations_met=true）——E1 abort-receipt 无自引 ok；E2 abort-receipt 自引 found=true 被抓获（hash_violations=9）；supplement 1/2 ok。 | [5-评测报告/L6判卷修订-2026-10-30/l6c-selfref-historical-replay-receipt.json]（4 docs 回放） |
| HJ-039 | 源4 | batch | needs_construction | **收紧批回放金标（24 场 0 翻转，ledger_match 16/24）**：回放金标：B2/B8/B12/B14 合同对 24 场历史产物重判，reward 0 翻转；账面一致 16/24，9 场差异已查因（8 场 bird q26 版本重判偏移、1 场 lcb r1029 doubao 负载超时抖动 before=after=75.0）。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay-results.json]（n_replayed=24, n_flipped=0, n_ledger_match=16, n_skip=17） |
| HJ-040 | 源4 | batch | needs_construction | **B13a 合同回放金标（24 场 0 翻转，行集冻结 41 行）**：回放金标：after 轨=现行 checker 字节（含 B13a，三 SHA 自证 bird 994be0b3…/lcb 63845361…/cargo d84b1111…），24 场 flipped=0、ledger_match=15/24；rowset_freeze 固定 41 行并排除 r20261027-wb-lcb-sandbox；after_track_selfcheck sha 前缀校验通过。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay-b13a-results.json]（n_flipped=0, n_ledger_match=15, rowset_freeze） |
| HJ-041 | 源4 | batch | needs_construction | **B13 候选预检回放金标（翻转 3 场的否决证据）**：回放金标：B13 整项候选合同的预检回放翻转 3 场（n_flipped=3，doubao/yuanbao/ablation cargo），构成否决 B13 的量化依据。 | [4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay-b13-candidate-precheck.json]（n_flipped=3（n_replayed=24）） |
| HJ-045 | 源4 | batch | needs_construction | **官方口径正例判分记录（六行全 reward=1）**：官方/本地口径正例金标（现行 checker 只读判分、temp run_dir、判后即删）：lcb 4/4=100.0、dabstep 10/10=100.0、bird 纯官方 14/15（q26 登记差异）reward=1=93.33、bird 官方14+本地q26 15/15=100.0、exercism 6/6=100.0、cargo 27/27=100.0 关键5项全过；判分前后 checker/truth SHA 未变（§7）。 | [4-打分细则/判卷审计-2026-10-27/upstream-third-party-samples/README.md]（## 5. 官方口径正例判分记录（六行表）） |
| HJ-048 | 源5 | batch | needs_construction | **全量只读重判管线首跑金标（95 行：57 可重判/47 一致/10 已知偏移/0 不一致）**：回放金标（2026-10-27T19:56:24+08:00）：总账 runs[] 全部 95 行按现行 checker 只读重判，57 场可重判中 47 场逐分一致、10 场为 bird q26 v1.1→v1.2 已收据合同迁移偏移（非翻转）、0 场未查因不一致；38 skip（归档 23/判定X 11/产物不齐 4），退出码 0。 | [4-打分细则/判卷回归/replay-all-results.json]（summary n_rejudged=57 n_match=47 n_known_offset=10 n_unexplained_mismatch=0） |

### selftest_positive（自测正例库） — 3 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-014 | 源3 | tool | needs_construction | **cache mapping v2 unit selftest 六例全过**：人工设计六用例（nested positive/nested zero/parent_missing/parent_non_object/child_missing/alias no-sum）全过，钉住 v2 映射语义边界。 | [5-评测报告/L5判卷修订-2026-10-30/cache-mapping-v2/recompute-receipt.json]（unit_selftest：6/6 pass；slot_count=18） |
| HJ-019 | 源3 | tool | needs_construction | **L6 evidence-kit 联合自测（evidence_line 11/11 + receipt_check 16/16）**：人工核定 evidence-kit 与 L6-C 规则联合自测全过；E2 abort-receipt 自引被抓获（hash_violations=9）即规则实效实证。 | [1-评测方案/工具链/evidence-kit/selftest-receipt-l6-20261030.json]（evidence_line 11/11 + receipt_check 16/16） |
| HJ-046 | 源5 | tool | needs_construction | **五题 checker selftest 正例库（首跑 2026-10-26 全过）**：人工核定五题 checker --selftest 退出码 0 且逐 fixture 期望标签全中：bird 25/25、dabstep 23 组、exercism 16/16、lcb 11/11、cargo nop/oracle/6 负例全过；results.json stdout_tail 内嵌逐 fixture reward 期望（负例如『每行多余键 status/verified』期望 reward=0）。 | [4-打分细则/判卷回归/results.json]（summary selftest_total=5 passed=5；selftests[].stdout_tail） |

### other（限制登记/未决/清单维护） — 4 条

| ID | 源 | scope | availability | 判定（title：label_semantics） | evidence |
|---|---|---|---|---|---|
| HJ-028 | 源8 | batch | context_only | **独立验收原收据不可用限制登记（results=null；24/22 行口径未消解）**：人工登记限制：独立验收原收据不公开且逐项 results=null，公开摘录不能独立证明原件真实性/完整性/时序；差异行数 24 与 22 两口径不一致保留为未消解，不得当已消解。 | [5-评测报告/验证器修订证据-2026-10-30/独立验收与分账/独立验收公开摘录.md]（全文） |
| HJ-043 | 源4 | case | context_only | **BIRD 上游两包不一致定责与口径建议（Lead 裁决未决）**：人工查明同一官方 gold SQL 在三个 california_schools.sqlite 上执行：dev.zip 主发布与本地 15/15 一致，minidev.zip V1 在 q17/q24/q27 三题不一致；根因 satscores.cds 前导零（minidev V1 打包件 211 行带前导零）；定责=上游发行件之间不一致，非本地改库。建议（供裁决）维持主发布 dev.zip 口径并在 truth/spec 补注；Lead 裁决在封闭清单内无已决记录，登记为未决项。 | [4-打分细则/判卷审计-2026-10-27/upstream-third-party-samples/README.md]（§4 ### ①【高价值】BIRD 上游自身两包数据不一致 → q17/q24/q27 结果集分叉） |
| HJ-047 | 源5 | batch | context_only | **47 条审计收据 SHA pin 清单回归（47/47 ok）**：人工维护的判卷资产 pin 清单：47 条历史审计收据的存在性+SHA-256 校验全过（results.json 生成于 2026-10-27T19:29）；判断本体是『哪些判卷资产必须字节冻结』的清单维护，无逐项重判标签。 | [4-打分细则/判卷回归/results.json]（summary sha_checks_total=47 ok=47；sha_checks[]） |
| HJ-067 | 源7 | scene | context_only | **yuanbao bird r3 预注册补发射（PREREG l21-20261102，私档）**：人工决定对首批发射遗漏的 bird r3 槽按预注册 PREREG l21-20261102（SHA-256 5bf84dff…，私档）补发射一次并判分（86.67、reward1）；执行方当时操作失误如实披露（bird 列暂记 n=2 后更正）。 | [3-表现现场/r20261101-yuanbao-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r3.json]（status/grading（v1, 86.67, reward1）） |

## 3. 按 availability 分级小计

| availability | 条数 | 占比 | 说明 |
|---|---:|---:|---|
| direct_test_item | 17 | 23.9% | 可直接进发射阶段测项池（r1101 十条终审、wb 五场终审、doubao 额度两事件） |
| needs_construction | 48 | 67.6% | 需发射阶段重组 checker/夹具/回放管线/收据拼装 |
| context_only | 6 | 8.5% | 政策、限制登记、未决事项或 pin 清单维护，不设逐项重判标签 |

**direct_test_item 合计 17 条——这是发射阶段测项池的直接规模**；HJ-069（11 槽 launch_invalid 聚合）与 HJ-006（10 探针表）若在发射期拆分为逐槽/逐探针测项，池可再扩约 20 项（已在 judge_input_needs 注明）。

## 4. 局限（哪些人工判断只存在于过程叙述、不可结构化）

- 源3 的 5-评测报告/L8证据链修订-2026-10-30/ 目录存在但为空（0 项），无人工判定事件可盘点，不立项。
- 源8 补充核验/ 目录为空。
- 独立验收原收据不公开且逐项 results=null（HJ-028），该人工验收过程只存在于公开摘录叙述。
- r1101 原始 trajectory 不在公开仓场景目录（HJ-052 等仅有裁决行号引文与引文、event-evidence.json），污染判定不能逐行复核原始轨迹。
- yuanbao PREREG l21-20261102（bird r3 补发射）与 corrected-after 更正收据在私档；公开仓只有结果记录与 correction 字段（HJ-065/067）。
- BIRD 上游两包不一致（§4-①）的 Lead 裁决在封闭清单内无已决记录（HJ-043 登记为未决）。
- 过程性判断只存在于叙述：9 场 ledger 差异查因过程、wb 预训练记忆不能排除的判断、B13 Lead 复核讨论、lcb389g 影响四点论证——有结论收据但推理过程不可结构化。
- doubao-n3 run_id 产品段沿用 W 批模板 workbuddy 段名（写入后不可改），产品身份以目录为准、17 会话经产品收据证实 DoubaoWork 2.34.12——登记注记，非缺口。

补充说明：
- 24 场回放协议（HJ-039/040/041）的判断结论与逐场数据可复核，但回放时点的 /tmp 工作区副本按协议判后即删，不在仓内。
- type=other 的 4 条（HJ-028 限制登记、HJ-043 未决裁决、HJ-047 pin 清单维护、HJ-067 预注册补发射）是「人工判断事件」但无逐项可重判标签，均标 context_only。

## 5. 自检

### 5.1 类型 × 数量对账

| type | 条数 | direct_test_item | needs_construction | context_only |
|---|---:|---:|---:|---:|
| ruling | 18 | 0 | 16 | 2 |
| revision_fixture_positive | 2 | 0 | 2 | 0 |
| revision_fixture_near_miss | 3 | 0 | 3 | 0 |
| correction_chain | 13 | 0 | 13 | 0 |
| final_adjudication | 19 | 17 | 2 | 0 |
| replay_golden | 9 | 0 | 9 | 0 |
| selftest_positive | 3 | 0 | 3 | 0 |
| other | 4 | 0 | 0 | 4 |
| **合计** | **71** | **17** | **48** | **6** |

scope 分布：assertion=3、batch=12、case=5、scene=21、tool=30。

### 5.2 evidence 路径存在性校验（脚本实测）

- 校验范围：71 条语料引用的 64 个独立文件路径（均解析到公开仓根下）。
- 结果：全部 64 个路径存在且为普通文件；SHA-256 实测覆盖 71/71 条。

**ERRORS: NONE**

### 5.3 机器账一致性

- JSON 顶层 `meta.counts` 与本 md 各表由同一份内存数据生成；JSON 数组 `corpus` 元素数 = 71。
- 输出为 write-once（`open(path,"x")`）：私档环目录 staging/human-judgment-corpus.json
