# 对抗性盲审报告（L2 收尾）——契约与证据链卫生，2026-10-29

- 审计角色：敌意复核者（连任；L1 揪出 D2/D3 的同一审计线），目标：独立重放重算、不信任任何在案主张。
- 方法与铁律：只读审计 + 离线复算；零模型调用；零 git 操作（judge 已做 git 面检查，本报告只引用并标注不可自证部分）；除本目录外零写入；时间均为实钟（本轮取样 17:06–17:26 +08:00）。
- 依据：`1-评测方案/自动循环L2-2026-10-29/PREREGISTRATION.md`（封印 `ae36f67`，git 面不可自证，见 §6 限制）+ `AMENDMENT-L2-1.md`。
- 独立重放/复算清单：①包A 24 场 B13a 合同回放**完整重跑**（输出 /tmp，与在案收据逐场比对）；②v3 `freeze.py verify`；③v2 `verify`；④v3 `test_freeze` 44 测；⑤v3 六账 7 收据+去重逐条核对；⑥活台账 5 事件 source SHA 逐条复算；⑦r1031 20 场 meta 独立扫描（retro 矩阵全量复算）；⑧收据 canonical `620cd322` 按其声明规则重算；⑨覆盖事件 bare 字节 `0f62d42a` 重算；⑩artifacts 四项哈希、judge 两收据哈希、lock/test/README 哈希复算。

## 0. 总判定

**0 blocking。** 四包交付的实质主张经独立重放/复算**全部成立**；发现 2 项 defect（均在证据链卫生层，不影响任何已判分数或准入裁定）、4 项 observation、4 项 note。预注册 §九 unknown 2（live_doc 报告制）评估结论：**设计可保留、不构成封印力实质弱化，附三项 L3 条件**（详见 §5）。

分级计数：**blocking 0 / defect 2 / observation 4 / note 4**。

---

## 1. 发现清单

### DF-1【defect】活台账 schema 三方矛盾：`registered_at` 被测试强制、被 schema 禁止、被全部实例携带；kind enum 矛盾坐实（judge B-3 确认+扩展）

- **证据**：
  - `4-打分细则/可信冻结-2026-10-29-v3/config-schema.json` `$defs.live_registry_entry`：`additionalProperties: false`，properties 仅 `{event_id, kind, executor, timestamp, source, locator, description, pin_class}`，**无 `registered_at`**；`kind.enum` = 5 值（无 `correction`）。
  - `work-registry-live.json`：**5/5 条目**携带额外字段 `registered_at`（按 schema 即全部非法）；首条 `work:l2-r1030-readme-erratum-20261029` 的 `kind="correction"` 不在 enum（judge B-3 已登记，`aeec36f` 提交信息明示「kind enum 扩列留 L3」——本审计确认为真）。
  - `test_freeze.py::test_live_ledger_structural_invariants`（B-1 修复后）：测试自建的 required 元组**含 `registered_at`**——测试在强制 schema 禁止的字段。44/44 因此通过的同时，把矛盾固化成了「结构不变量」。
- **影响**：活台账当前不被 build 消费（无分数影响），但 L3 任何按现行 schema 的机读校验会**拒收全部 5 条 L2 事件**；且测试与 schema 的矛盾意味着「测试全绿」不能作为「实例合 schema」的证据。这是本轮「收据准确性」主题下的同类缺陷（schema/test/instance 三方不一致）。
- **下一步**：L3 三选一对齐并把 schema 校验并入结构不变量测试：(a) schema 增加 `registered_at` 属性（推荐——它是 D4 教训的时点字段）；或 (b) 测试与实例删除该字段；或 (c) 显式声明实例层 superset 并在 README 标注 schema 宽松化。kind enum：扩列 `correction` 或将首条改类；二者均需 dated 勘误。
- **停止条件**：L3 若引入活台账机读校验而未对齐 → 升级 blocking（全部 L2 事件失效）；本轮以披露闭项（B-3 义务不变）。

### DF-2【defect】validate_runner_meta.py 对 SCHEMA「约束」列的实现缺口（enum 约束、selection-null 伴随诊断、seal 校验静默可跳过）

- **证据**（SCHEMA 承诺 vs validator 实现，逐条对照）：
  - SCHEMA §一：`status∈{ok,timeout,error,transport-error,…}`、`integrity_verdict∈{clean, benign-reviewed, violation}`（benign-reviewed 须附 corrections）、`selection` null 时必须伴随 `diagnostic`——validator 的 `REQUIRED_FIELDS` 对三者分别只查 `str`/`str`/`dict_null`，**enum 与伴随关系均未实现**；fixtures 亦未覆盖这三条约束（`fixtures/manifest.json` 六个用例无一触发）。
  - SCHEMA §三.3：`registered_at ≥ 封印时刻`——`--seal-at` 为可选参数；未提供时 `temporal.seal="not_evaluable"` 且**不产生任何 issue**，`classify()` 照常可返回 `pass`。经 `--retro` 不带 `--seal-at` 即可绕过 seal 校验而无任何标记（`seal_at_provided` 字段只是旁注，不参与判定）。
- **影响**：下一真实批次若直接采用本 validator 作为合规门槛，`status`/`integrity_verdict` 可填任意字符串、null selection 可无诊断、调用方忘传 `--seal-at` 即静默失去 D1 的一半保障。D1/D2/D5 的**核心**字段（registered_at 存在性与时序、8dp 精度、dsh 六字段、transport_retries 整型）不受影响。
- **下一步**：L3 lab.py 集成时（预注册 §五 已列）一并实现：两个 enum、null→diagnostic 伴随校验、`--seal-at` 缺省时 classify 输出 `pass:unsealed` 类的响亮标记（而非静默 not_evaluable）；fixtures 补三用例。
- **停止条件**：若 L3 真实批次以本 validator 为唯一合规门而未补齐 → 该批证据链按未校验处理，升级。

### O-1【observation】`registered_at` 的溯源保障是自证性的：只有顺序约束，没有出处绑定

- SCHEMA §三.4 自述「值=预注册封印提交时间戳的引用……不得事手写未来时刻」，但该引用无机器绑定：validator 无法（也不试图）核对 `registered_at` 与 `preregistration_commit` 的真实提交时刻（需 git），`--seal-at` 亦是调用方传入的裸参数。一个不诚实的 runner 写 `registered_at = started_at − 1s` 即可通过全部机读校验。SCHEMA 未显式披露「顺序检查是必要非充分」。
- 影响：D1 的「逐场机器可查」只做到了「逐场机器可查**格式与时序自洽**」，未做到「可查真」。下一步：L3 集成时让 runner 落盘 registered_at 的**读取来源**（预注册台账文件路径+字段位置），审计侧离线对 git 提交时间；SCHEMA 补一句显式披露。停止条件：真实批次完成一次「registered_at ↔ git 提交时间」对账即闭。

### O-2【observation】AMENDMENT-L2-1 自身缺少 git 锚与实钟标签——用本循环自己的标准衡量不合格

- 全文时间标签仅「2026-10-29 16:5x+08:00（实钟）」两处模糊值，无任何提交哈希自锚；对照预注册 §二.5「关键时间点以 git 提交哈希锚定」与 L1 D4 教训（本循环自己立的规矩），该修正案是本轮唯一未达此标准的时点文书。其**内容**经本审计独立核验全部为真：v1 台账=`27974b75…`、v2 台账=`04944e28…`（两哈希均在 L1 审计实测过，本轮复核一致）、v3 config path/sha 自洽、7 收据入账结果（8→13、11→13）与六账实测一致。
- 影响：程序文书质量瑕疵，非事实错误（judge X-1 已记其 write-scope 特例）。下一步：lead 在 L2 ACCEPTANCE.md 中给该修正案补提交哈希锚。停止条件：补锚即闭。

### O-3【observation】L1 问题池 ⑦ 的「O6 命名撞名」半边被静默排除

- L1 ACCEPTANCE §四 第 7 条打包了「WB 正式批次」与「O6 r1030/r1031 前缀与历史 yuanbao run_id 撞名」；预注册 §输入/§九.3 的排除声明只写了 WB 批次理由，O6 半边无任何去向语句，L2 也未做消歧注（L1 O6 建议的「两批 README 消歧注」未执行）。
- 影响：极小（L2 未新增批次，撞名未恶化），但「逐条有去向」的池子纪律破了一处。下一步：L2 ACCEPTANCE.md 或 L3 预注册补一行 O6 去向（建议：一行消歧注 + 池子续挂）。停止条件：补去向即闭。

### O-4【observation】builder 回执哈希误报闭环：`086f52af` 已闭环留痕，`0f1157f7` 只闭环了「真值」未闭环「误报」

- `086f52af`（被覆盖前补全版收据的哈希，作废）：`spec-selftest-receipt.json` corrections `pkgc-receipt-completion-20261029` 明确记载作废原因与覆盖链路（bare at=16:11:16 → `receipt-overwrite-evidence-20261029.json`，其内嵌 bare_content 重算 SHA=`0f62d42a…` 与声明一致，覆盖运行被字节钉死）——**闭环质量高**。
- `0f1157f7`：全仓检索仅命中 v2/v3 `output-manifest.json` 中 `build-recipe.json` 的**正确**哈希（本审计实测 match=True）。所谓「manifest 0f1157f7 误报」——错误主张本身（哪份回执、把该哈希安到了哪个文件）在仓库内**无任何留痕**；循环台账 L2 README 只以「canonical=字段=b347b6c2（一次哈希误标澄清修正中）」侧写。真相已被钉住（文件字节=`5c6177fd`、canonical=`620cd322`，均本审计重算吻合），但「曾有人误报过什么」不可复核。
- 影响：无误判风险（真值唯一且已验证），但违背「收据准确性可复核」的自我要求。下一步：lead 在 ACCEPTANCE.md 补一张误报闭环小表（误值→误安对象→真值→证据指针）。停止条件：表落盘即闭。
- **收据准确性模式评估（lead 问）**：L2 全部哈希类差错（086f52af 无对应物、canonical 误标为文件哈希、b347b6c2 过渡值、提交信息 0.44、AMENDMENT 时钟标签）均为**手工转写哈希/时刻进叙述文本**所致，无一是「文件与收据不符」。建议定为机制整改：哈希与时刻一律由脚本生成落盘、叙述文本引用而不手打；验收收据增加「claimed vs recomputed」机械对照节。

---

## 2. 包A：B13a 合同回放补证 —— ✅ 通过（独立重放逐场全等）

- **独立重放**：本审计以在案脚本 `replay_b13a_2026_10_29.py` 完整重跑（17:10:39 落盘 /tmp，exit 0）：`n_replayed=24 / n_flipped=0 / n_ledger_match=15`，与在案收据 `13d2ef97…`（实测吻合）**逐场 before/after/flip/ledger_match/artifact SHA 零差异**。
- **「实质差异是否只有 after 轨」**：不止。与原脚本实质差异共四处：after 轨改现行字节（含三 SHA 前缀自证，不符拒跑 exit 2）、行集冻结（旧收据 41 行口径）、环境漂移中止（冻结行 run_dir 缺失即 exit 2，不静默 skip）、ledger_match 改按**现行总账值**计算+漂移入 corrections。前一处是任务本体；后三处均为**收紧**而非放松，无操纵面。评分管线（/tmp 副本 canonical 重组、逐场双轨判分）逐字节继承。
- **行集冻结裁决 B 可操纵性**：排除规则文本在脚本常量、收据 `corrections[0].exclusion_rule`、`rowset_freeze.rule` 三处**逐字一致**（本审计程序化比对 True/True）；排除实例唯一（`r20261027-wb-lcb-sandbox/workbuddy/lcb-recent-hard-4`）且由脚本动态计算（现行同口径合格 25 − 冻结 24）。锚定文件 `replay-results.json` mtime 仍为 10-27 19:28（未被触碰）。**实质无关性**：B13a 只改 cargo checker（`70acdbb7→d84b1111`），被排除行属 lcb——其现行 after 字节与旧收据 after 轨相同，排除它不可能掩盖任何 B13a 翻转；冻结集内 10 场 cargo 全部重放。裁决 B 站得住。
- **数字复算**：24/0/15 重现。ledger_match 15 vs 旧收据 16 的唯一差异行=r1029 doubao lcb 负载超时抖动（本日 before=after=75.0，旧日侥幸 100.0），收据 `post_run_annotations` 与 2026-10-27 收据逐行对照披露，flip=False 正确（before=after，硬闸门不看登记分）。
- **勘误框**：两处 dated `2026-10-29 16:06:56 +0800`，原句保留、勘误增量；「15/24 初版口径 vs 19:28 刷新 16/24 vs 本收据 15/24」三层口径各自说清，无静默改写。

## 3. 包B：冻结合同 v3 —— ✅ 通过（附 unknown 2 评估见 §5）

- **verify/test**：v3 `verify` exit 0（`live_doc_drift=[]`）；v3 `test_freeze` **44/44 OK @HEAD**（B-1 修复后）；v2 `verify` exit 0。
- **② v2 零字节主张**：v2 目录文件清单与 L1 审计时一致（10 文件）、v2 lock 17 pin 经 v2 verify 内部全过 = 字节未动（git 面由 judge `status --porcelain` 空佐证，本审计不 git）。
- **③ 7 收据入账**：逐条在账（5×`work:r1030-selftest-*`→self_test、`work:r1030-cli-preflight`、`work:wb-admission-preflight-20261029`→interface_preflight）；self_test 8→13、interface_preflight 11→13、其余四类不变；**event_id 零重复**、`wb-sandbox` 恰 1 次（v1→v2 台账继承+去重正确）。
- **④ 测试等价性**：v2→v3 diff 实测 = 38 继承（0 删除）+ 6 新增；仅有的两处同名测试改动（fixture 时刻动态化、`test_outcome_based_registration` 的 registered_at 字面量→`_t(61)`）语义等价（两者都构造 registered≥started 的违规样本）。B-1 重写（空断言→六点结构不变量）是**有意的非等价**：原断言与 append-only 生命周期自相矛盾（`ae6b37d` 时真、`aeec36f` 后必假），新不变量保护的对象（结构合法性+非 contract pin）才是活台账需要的——judge addendum 九点复验成立，本审计独立认同。**残留缺口见 DF-1**（不变量未做 schema 校验，反而固化了 registered_at 矛盾）。
- **⑤ official v3 恒空**：groups={A:0,B:0}、128 行全 rejected 带理由（`not_in_freeze_period` 31 等）；README「继任语义」节明确「v2 仍是 r1030 合同记录、v3 不重新准入任何历史行」，`test_v3_does_not_readmit_history` 机器断言兜底。下游误读残险：`official-main-table.json` 文件**内部**无「r1030 见 v2」指针（→ note N-3）。另核：v3 保留的 official_slots 无法被新事件注入（计划 event_id 固定+重复导入即 duplicate ID 硬失败），无准入后门。
- **⑥ 活台账 5 事件**：source 路径全部存在、SHA 5/5 复算吻合；kind 归账与预注册 §二.6 分账一致（包A→grading_regression、包B/包C→self_test、包D→correction）；事件不进 v3 六账属设计（README 明示「进六账走未来代显式注册」）。kind="correction" 的 schema 矛盾见 DF-1。
- **pin_class 实现核验**：`freeze.py` v3 与 v2 的 diff 仅含声明改动（RULE/BASE/OUT、`lock_drifts`、verify_seal 返回 drifts、summary 增 `live_doc_drift`）——「其余逐字节相同」属实。contract 漂移 raise（exit≠0）、live_doc 漂移进列表且 `summary.json` **持久化** `live_doc_drift` 字段（非仅运行时打印）；缺文件 live_doc=drift 非 crash（单测覆盖）。lock 17 pin = 10 contract + 7 live_doc，归类逐条有理由；build/verify 消费的全部文件（config、v2 台账、plan、两预检收据、未知登记）均为 contract，**归类的机械正确性成立**。

## 4. 包C：runner-schema-v2 —— ✅ 通过（附 DF-2/O-1）

- **44 字段覆盖裁定**：D1→`registered_at`（必备，§三时序双规则）+`preregistration_commit`；D2→§五机读 8dp 唯一精度+展示层 2dp 隔离+validator 收据 canonical 层；D5→dsh 六字段必备化、`transport_retries` 整型+`transport_retry_events` 明细分离、`archived_stdout` 降为 dsh 特有可选映射且不豁免四 canonical 字段（§四映射表与 r1031 实测 `archived_stdout` 键集逐项吻合）。D1/D2/D5 缺口**全覆盖**，每字段带动机锚点。
- **retro 矩阵 `12cd3354` 独立复算**：本审计自扫 20 场——registered_at 缺 20/20、dsh 六字段各缺 10/10、transport_retries dsh=list 10/10 与 codex=int 10/10、收据 2dp precision_error 恰 2 场（codex cargo r2/r3）、meta.weighted 8dp delta 恰 4 场（双产品 cargo r2/r3）——**与在案矩阵逐项一致**；`tool_sha=ac2e4b7c` 与 validator 文件实测一致；`seal_at_provided=2026-10-29T13:22:39+08:00` 有提供。矩阵首部「披露非追溯判定」声明在位。
- **收据闭环真实性**：`spec-selftest-receipt.json` 文件字节=`5c6177fd` ✓；canonical `620cd322` 按声明规则（去 `receipt_sha256` 字段、ensure_ascii=false、indent=2+尾换行、文件键序）**重算吻合**；artifacts 四项（SCHEMA/validator/矩阵/manifest）哈希 4/4 实测一致；corrections 两条含自验失败两次的透明记录；`receipt-overwrite-evidence-20261029.json` 内嵌 bare_content 重算=`0f62d42a` ✓、`at=16:11:16` 把覆盖运行钉死——C-1 存证闭环**真实**（C-1 根因 `cmd_spec :230` 无条件重写本目录收据，代码确认；「--spec 活动目录禁令至判卷收口」已由流程执行，本审计的 --spec 相关核验均以只读方式进行，未触发重写）。
- **--spec fixtures 覆盖**：6 用例含 temporal-order/temporal-seal 两规则的正反例 ✓（缺 enum/selection-diagnostic 用例 → DF-2）。

## 5. 包D 与预注册 §九 unknown 2 裁决输入

**包D（r1030 勘误框）—— ✅ 通过**：dated 15:59:56 实钟、原句原段保留、双重指针（`tools-dsh/README §批内发现并修复`、`meta.corrections id=r1031-archiver-log-loss`）实测可达；`:308 rmtree 先于 :317 staging` 行序主张经 judge 源码复核成立（本审计复核 r1031 README 同一定性+lead 已核验的记载一致）。nit：小节标题「（r1030#1，**已修正**）」保留原词,与勘误框「『已修』声明不成立」形成标题层残余误导（→ N-2）。

**unknown 2（live_doc pin 报告制）独立评估结论：保留报告制——不构成封印力实质弱化，附三项 L3 条件。**

理由：
1. **分类机械正确**：判分/准入的全部输入与引擎组件（10 项）仍为 contract 漂移硬失败;降为报告制的 7 项均未被 build/verify 消费（逐项核对 freeze.py 读取面属实）。L1 的实际事故（合并 sweep 抓到准入预检 README 漂移致 verify 硬红）恰是报告制要消除的churn——该文件根本不影响任何分数。
2. **弱化的真实边界**：报告制弱化的是「叙述文档被静默改写」的发现速度，不是「合同字节被改」的防御力——后者分毫未动。且漂移列表持久化进 `summary.json`（非转瞬打印），任何后续 verify 都能重放检出。
3. **风险实存但被 tripwire 覆盖**：叙述文档承载语义（如裁定 md）时，静默改写仍可能误导人类读者;预注册 §九.2 已设「一次证据链断裂→收紧为硬失败」的触发器。本轮未观察到该触发器应触发的情形。
4. **三项 L3 条件（建议照单采纳）**：(a) pin_class 部分机械化——凡路径出现在 config/registry/sources 读取面的文件强制 contract，由 verify_seal 自检而非人工归类（防未来分类漂移）; (b) 每份验收/审计收据强制附 `live_doc_drift` 状态行（本轮所有收据事实上已这么做,升为规范）; (c) 维持 tripwire 并在 ACCEPTANCE 里明示「报告制≠免检,还原+旁挂仍是操作规范」。

---

## 6. 流程面核验

- **AMENDMENT-L2-1 程序**：§二.1 要求「勘误动机+时间线 git 锚定」——动机充分且为事实转写（双哈希实测留痕，v1=`27974b75`、v2=`04944e28` 均经本审计复核）;但自身无提交哈希锚、时间标签模糊（"16:5x"）→ O-2。内容侧全部核验为真（含 7 收据入账结果 8→13/11→13）。
- **L1 问题池去向**：①→包C ✓（registered_at 必备+8dp+跨 builder 对齐）; ②→包B ✓（v2 台账指向+7 收据入账）; ③→包A ✓（B13a 回放+15/24 勘误链）; ④→包D ✓; ⑤→包B ✓（pin_class）; ⑥⑦排除声明在位且理由成立（需真实运行/批次规划）。**唯一遗漏：⑦ 内含的 O6 半边无去向语句 → O-3**。
- **judge 两收据**：`verify-receipt.json`=3de0dfa2…、`addendum-b1-closed`=0dd54e00… 哈希实测吻合;其关键实测 10 项经本审计独立复跑**全部一致**（§0 清单）。judge 的 B-2 拆分对账（38+6）、B-3、X-1、X-2 及 addendum 第 8 项「manifest 不变才是正确行为」的实测更正,本审计均独立认同。
- **builder 回执哈希误报闭环**：086f52af ✓ 已闭环（收据 corrections 内作废+存证）;0f1157f7 → O-4（真值已钉、误报未留痕）。
- **L2 README 台账**：与产物实况逐行核对未见失实;一处计数笔误 → N-1。

## 7. Notes

- **N-1**：L2 README :19 称包C收据「corrections 三条」,实测文件为 **2 条**（「补全披露+误标澄清」合并在一条 note 内）。计数笔误,建议随 ACCEPTANCE 更正。
- **N-2**：r1030 README 勘误框所在小节标题仍含「已修正」原词（原句保留纪律的副作用）,扫读标题层有残余误导;可在下一轮文档巡检时一并处理。
- **N-3**：`5-评测报告/可信冻结-2026-10-29-v3/official-main-table.json` 文件内部无「r1030 准入见 v2」指针,README 有守卫;建议未来代在输出 JSON 增 `note` 字段（需改 freeze.py 输出 schema,留 L3）。
- **N-4**：`import-example.json`/`example-source.json` 归 live_doc（judge X-2）:本审计复核二者非 build/verify 消费面,分类可接受;若未来测试将其作 schema fixture,应升 contract。

## 8. 覆盖与限制

- 不可自证（git 面）：封印 `ae36f67`、`c0994d9`/`fe9f788`/`6c9c010`/`ab4be14`/`999d345`(L1) 等提交的先后关系,依据仓库内台账与磁盘 mtime 旁证采信;v2 零字节的 git 双命令证据引自 judge 收据（本审计以 v2 verify 17 pin 全过为字节面证据）。
- 本审计零模型调用;`--spec` 相关核验未在工作目录执行（只读代码+既有收据复算）,避免触发 C-1 覆写。
- 包A 独立重放输出在 /tmp/audit-l2-b13a-replay.json（仓库外）,未触碰审计目录。

## 附录A：复算命令要点

1. 包A：`python3 -B "4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay_b13a_2026_10_29.py" /tmp/<out>.json` → 与收据逐场 JSON 比对（本审计 diff=0）。
2. 包B：v3/v2 `freeze.py verify`（仓库根）;`test_freeze.py`;six-ledgers 与 7 event_id 计数/去重脚本;`work-registry-live.json` 逐条 source SHA;lock pin_class 计数。
3. 包C：20 场 meta 独立扫描器（自写,无 validator 依赖）对照 `retro-r1031-matrix.json`;canonical 按 `receipt_sha256_rule` 重算;bare/evidence/manifest 哈希重算;SCHEMA §一约束 vs `REQUIRED_FIELDS` 逐条对照。
4. 哈希锚实测值：lock `544a7f96…`、test_freeze `aa374cba…`、v3 README `61fb267d…`、收据 `13d2ef97…`、矩阵 `12cd3354…`、receipt 字节 `5c6177fd…`、canonical `620cd322…`、bare `0f62d42a…`、judge `3de0dfa2…`/`0dd54e00…`、AMENDMENT 重发版 `542e4a7b…`（L1）。
