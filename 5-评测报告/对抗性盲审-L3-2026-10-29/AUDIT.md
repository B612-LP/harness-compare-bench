# 对抗性盲审报告（L3）——机读对齐与证据机械化，2026-10-29

- 审计角色：敌意复核者（第三轮连任）。立场：hostile；预注册是唯一基准；builder/judge 陈述一律当作待证主张；目标是找 judge 条款级验收会漏掉的东西。
- 方法与铁律：全只读（仓内零写入，本目录除外）；git 只读可用但本轮**未行使**（全部判定以磁盘字节+可离线重放为准，与 U1 口径一致）；零模型调用；`--spec` 类一律 /tmp 或新路径；2-用例 truth/solution 未读；哈希/时刻由脚本生成（本文全部证据行由 `evidence_line.py` 生成、并经 `receipt_check.py` 回验，见 §7）。
- 依据：`1-评测方案/自动循环L3-2026-10-29/PREREGISTRATION.md`（封印 `72edb519`）；L2 缺陷原文 `5-评测报告/对抗性盲审-L2-2026-10-29/AUDIT.md`。
- 时点：审计执行 18:25–18:5x +08:00（实钟）。

**live_doc_drift: none（0 项）**——`freeze.py verify`（v3）于 18:26 实测 `ok=true, live_doc_drift=[]`；本文件自身经 `receipt_check.py` 核验通过（§7）。

## 0. 总判定

**0 blocking。** L2 遗留缺陷 DF-1/DF-2/O-1 与 unknown-2 三条件的闭合**经攻击性实验逐条证实为真闭合**（非声称闭合），其中 A4 经本审计构造逃逸样本实测：**生产路径 verify_seal 硬拒**（非测试专属）。发现 3 项 defect（两处新工具的实现-承诺缺口、一处 B4 措辞-行为偏差）、2 项 observation、4 项 note。停止条件判定见 §6。

分级计数：**blocking 0 / defect 3 / observation 2 / note 4**。

证据行（脚本生成，18:46:20+08:00；其中 3 条于修复轮 19:17:16+08:00 刷新为现行字节——validate_runner_meta / receipt_check / work-registry-live，刷新原因见 §9；其余 9 条文件修复轮未变动、原行保留）：

```
4-打分细则/可信冻结-2026-10-29-v3/freeze.py · 3896e6aa · 45117B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/test_freeze.py · dd941b44 · 23401B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/config-schema.json · c8a06024 · 6229B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/freeze.lock.json · bf7f9aa3 · 8264B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/work-registry-live.json · 191474ca · 12780B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py · e71f28fb · 31277B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/spec-selftest-receipt-l3-20261029.json · 6048ad41 · 5226B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/cli-regression-receipt-l3-20261029.json · db65c68c · 7215B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/reconciliation-synthetic-l3-20261029.json · a4dbe315 · 1856B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/evidence-kit/receipt_check.py · effda0ed · 14041B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/evidence-kit/evidence_line.py · 9b00febf · 5758B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/evidence-kit/kit_selftest.py · 383a70f8 · 3688B · 2026-10-29T18:46:20+08:00
```

---

## 1. 发现清单

### DF-C1【defect】receipt_check 的 hex 记号正则对「CJK 前贴哈希」与超长串全盲——C2 的核心场景失效

- **证据**（本审计构造样本实测，`receipt_check.py:50` `HEX_TOKEN_RE = re.compile(r"\b([0-9a-fA-F]{7,64})\b")`）：
  - `哈希5c6177fd…（原字面为 64 位小写、前贴中文无空格；修复轮截短为 8 位前缀+省略号，原因见 §9 附注）` → **0 命中**（Python `\b` 为 Unicode 词边界，CJK 与 hex 同为词字符，无边界可依）；
  - `假哈希deadbeef…（原字面 12 位）` → 0 命中；70 位超长 hex 串 → 0 命中（`{7,64}` 上限 + `\b` 双侧不可满足）；
  - 纯数字 8 位（`12345678`）被 `:126` 显式跳过（设计取舍，可接受）；大写/怪长(7,8,40,64 之外的合法长度)可抓 ✓。
- **影响**：C2 的存在理由是抓「叙述文档手打哈希」，而本项目叙述语言是中文——**手打哈希最常见形态恰是前贴中文**。⑧b 若以本工具为机读闸，手打哈希可在「合规」判定下静默通过。README:11「大写/怪长 hex 记号会被逐条记 violation」的承诺对 >64 位不成立。
- **下一步**：改用显式环视 `(?<![0-9A-Za-z])([0-9a-fA-F]{7,})(?![0-9A-Za-z])` 并对长度 ∉ {7,8,40,64} 与 >64 一律记 violation；自检补 CJK 前贴/超长两用例。随 L4 前修复即可，不阻塞本轮交付。
- **停止条件**：若 L4 以本工具作为收据合规**唯一**闸而未修复 → 手打哈希可穿透，该批文档的哈希合规判定无效。

### DF-B1【defect】B4「默认非零退出」在 `--retro` 无 seal 路径未落实：exit 0 + 完整矩阵，与预注册措辞不符（SCHEMA.md 已另行收窄但预注册未走修正）

- **证据**（本审计 /tmp 副本三模式实测，绝对路径 runs 目录各 20 场）：
  - `--retro <codex/dsh runs> --out …`（无 `--seal-at`，无 `--allow-unsealed`）：**exit 0**，完整矩阵落盘；`seal={"provided":false,"policy":"fail-closed-unsealed","unsealed":true}`；
  - 同命令加 `--allow-unsealed`：exit 0，矩阵与前者**唯一差异是 policy 标签**（`allow-unsealed-disclosure`）；
  - `--retro` 全程不调用 `classify()`（`validate_runner_meta.py` cmd_retro 逐行核对：行对象无 classification/issues 字段），故「fail:unsealed」在矩阵中不存在——`--spec` 路径 fail-closed 真实成立（T2 实测 exit 1 + fixture-valid→fail:unsealed），但「默认非零退出」对 --retro 是**标签级**而非行为级。
- **对基准**：预注册 §三 B4：「未提供 --seal-at 时 classify 不得产出可消费为通过的 pass——**默认非零退出**；显式 opt-in 仅限披露模式且输出带 unsealed 标记」。SCHEMA.md §三.4/§六 把非零退出收窄到 `--spec`（"--spec 由此非零退出"）并把 --retro 定义为披露模式——**实现与 SCHEMA.md 自洽，但与预注册字面承诺有偏差，且预注册未走 dated 修正**。另：`cli-selftest-l3.py` T2/T3 均未覆盖「--retro 无 seal 默认行为」，该偏差无测试钉住。
- **影响**：下游把无 seal 矩阵当已验证输入消费时，唯一的拦截是一个字符串标签；机器不可见（矩阵行内无 fail 标记、退出码 0）。
- **下一步**：二选一——(a) `--retro` 无 seal 默认改非零退出（或行内嵌 `classification` 字段使 fail:unsealed 机读可见）；(b) lead 对预注册 B4 出 dated 修正框，把「默认非零退出」显式限定为 --spec。二选一后补一条 T7 回归。
- **停止条件**：L4 若以**无 seal** 的 retro 矩阵作为合规输入且 DF-B1 未处置 → 该批机读合规判定无效。

### DF-C2【defect】receipt_check 的 JSON 分支：`live_doc_drift` 值类型校验形同虚设（wellformed 计算后从不参与判定）

- **证据**：`receipt_check.py` JSON 分支对每个 `live_doc_drift` 键计算 `wellformed = v is None or isinstance(v, list)` 并记录，但 `rep["ok"]` 的合成式只看 `found`（`:140-141`）：字符串值（如 `"live_doc_drift": "none"`）→ found=True、wellformed=False、**ok=True**。docstring 自述「JSON 递归查键（值须 null 或 list）」——承诺与实现不符。selftest 未覆盖该反例。
- **影响**：JSON 收据可以用一个字符串值糊弄 ⑧b 状态要求；「wellformed」字段成了死数据。
- **下一步**：`drift_ok` 合入 wellformed（或把非 wellformed 记 violation）；自检补字符串值反例。
- **停止条件**：与 DF-C1 同批修复即可；本轮 JSON 收据（含 v3 产物）实测均为合法 list/null，无已发生的误判。

### O-1【observation】`registered_at` 溯源对账（B7/⑦）的 commit_time 三来源中，文件来源可被循环自证

- `--reconcile` 的 `--commit-time-file` 接受「审计侧粘贴 git log 输出」的文件，但工具无法区分真 git 输出与手写文件（格式正则即过）。`--git` 模式 L3 未行使（U1 如实披露，SCHEMA §三.5/§七 + 收据 binding_disclosure 三处一致）。合成对账正反例（ok/violation）本审计复核成立。
- 影响：机制级可用、实证级未达成（这正是 U1 的自述）。下一步：L4 真实批次对账必须走 `--git` 或由审计者独立提供 commit-time 文件并交叉核对提交哈希。停止条件：即 U1 本身。

### O-2【observation】活台账 source 哈希无新鲜度机制

- 11 事件 source SHA 5/5→11/11 复算吻合（本轮实测），但台账 append-only 且不在封印内：被引用文件未来合法变更（如 r1030 README 再勘误）后，旧事件的哈希**静默变陈旧**，没有任何机制区分「登记时为真」与「现已失配」。append-only 纪律本身正确；缺的是对账可见性。
- 下一步：L4 起每轮验收跑一次全量 source 复算并把结果行（11/11 或差异清单）写入验收报告；或在 receipt_check 加 `--check-live-ledger` 模式。停止条件：出现一次未披露的 source 失配即收紧。

## 2. 包A（v3：DF-1 + ⑧a/c）—— ✅ pass

- **A1** ✓：`config-schema.json` live_registry_entry 增 `registered_at`（required、format date-time、pattern 强制 `Z|±HH:MM` 后缀）、`kind.enum` 扩 `correction`（6 值）。**本审计攻击：naive 时刻直灌 validator → pattern 拒绝**（`2026-10-29T18:00:00` 被拒，实测）；11/11 现行事件全部过 schema（test 输出 `[live-ledger] events=11…全过`）。
- **A2** ✓：`test_freeze.py:18-50` `validate_against_schema` 关键字覆盖对**被校验子树完备**——本审计枚举 config-schema.json 全部 schema 关键字（$ref/enum/const/type/required/additionalProperties/pattern/format），与实现逐一对应；`maxProperties/minProperties` 仅出现于 case_snapshots 定义（不在 validator scope，且 freeze.py 以 `set(CASES)` 等价检查更强地强制）。**非自证 stub**：naive 拒绝实验 + enum 负例均真实触发。
- **A3** ✓：README「L3 变更框」dated 18:01:09（实钟脚本生成）、原语义保留、lock_before=`544a7f96…` 脚本生成入框，lock_after 以「无自引用不动点」为由外置到活台账登记事件（事件描述含前后哈希，本审计核验 lock_before 与 L2 末代 lock 一致）。
- **A4** ✓✓（**本审计核心攻击：被生产路径击退**）。接线确认：`freeze.py:536` 在 verify_seal 内 raise。逃逸样本实验（/tmp 合成仓 36MB，先基线 PASS 再攻击）：
  - 构造 `work_registry.path → 字节相同的新路径文件` 且同步重锁 config pin（模拟重锁后一致态）：**REJECTED** `read-surface path not pinned contract: {…, "pin_class": "not-pinned"}`；
  - 再把该路径钉为 live_doc：**REJECTED** 同上（pin_class=live_doc）；
  - 还原后 PASS。结论：机械归类不在测试里自证，生产 verify_seal 真拦截。
  - 边界（如实记录，非缺陷）：pin_class 读取面=config+两输入+固定四文件+registry sources；2-用例 case 文件（config manifest 绑定）与三份 import envelope（build-recipe pin+validate_event 哈希）在分类系统之外但各有独立字节绑定；README 变更框第 3 条已对 imports 显式披露。测试 `test_read_surface_*` 3 项 + 真仓绿 1 项在案。
- **A5** ✓：tripwire 断言原样；README 明示「报告制≠免检，还原+旁挂仍是唯一合规操作规范」。
- **A6** ✓：v3 test_freeze **48/48 OK**（44 继承 0 删除 + 4 新增，计数实报相符）；v3 verify exit 0 / `live_doc_drift=[]`；**v2 verify exit 0（本审计复跑）**；lock 17→38（31 contract/7 live_doc），21 项新增 pin 由 `check_pin_classification` 首跑机械产出（README 变更框第 4 条披露，含「上表为 L2 时代 17 pin 分类」的表陈旧性披露）。

## 3. 包B（runner-schema-v2：DF-2 + C-1 + ⑦）—— ✅ pass（附 DF-B1）

- **B1/B2/B3** ✓：`STATUS_ENUM`/`INTEGRITY_VERDICT_ENUM` 落地，`benign-reviewed→非空 corrections`、`selection=null→非空 diagnostic` 伴随校验实现，`fail:enum`/`fail:companion` 进 FAIL_PRECEDENCE；SCHEMA.md §一/§B1 把原「…」开放值域改为封闭四值（实现与文档一致 ✓）。fixtures 6→10（新增 4 项覆盖三条新约束+1 正例），本审计 /tmp 重跑 `--spec --out 新路径`：**10/10 match，PASS**。
- **B4**：--spec 路径 ✓（fail-closed，T2 实测；`--allow-unsealed`+`--spec` → exit 2 拒绝）；--retro 路径 ✗ → **DF-B1**。
- **B5** ✓：L3 收据全部新路径（`spec-selftest-receipt-l3-20261029.json`=6048ad41 等）；原收据 `5c6177fd` 与覆盖存证字节实测未动（本审计复算一致）；既有 fixtures 新语义行为披露在收据 `l3_disclosure.fixtures_behavior_change`。
- **B6** ✓：无 `--out` 不落盘（stderr 提示）；目标已存在 → JSON `refused:true` + exit 2 + 原字节不动（本审计实测三次，含对原收据的拒绝）；新路径正常写入。T1 机械复现 16:11:16 覆盖模式（第二次运行 exit 2、首文件字节不变）并在 /tmp 重放 6/6 全过。边界残留 → N-3。
- **B7** ✓：SCHEMA §三.4 显式披露「顺序检查必要非充分」；`--reconcile` 三种 commit_time 来源，合成对账正例（ok，6 步全过）+负例（early → violation，第 6 步 False）本审计复核；`--git` 未行使 = U1 三处一致披露 → O-1。
- **B8** ✓：validator/收据/矩阵哈希与计数全部脚本生成（receipt 内嵌 tool_sha256、validator_sha256 与现行字节一致，本审计实测吻合）。

## 4. 包C（evidence-kit：⑥ + ⑧b）—— ⚠️ pass with defects（DF-C1/DF-C2）

- **C1** ✓：标准证据行四元组、批量失败不产半截行（本审计实测触发 exit 2）、`--selftest` 11/11。半个 UX 注记（N-4）：相对输入路径按 cwd 解析、按 root 显示，从非仓库根目录调用会误报不可读。
- **C2**：设计对路（claimed vs recomputed、只读、--out 拒已存在、unverified 不计 pass），但两个实现缺口 → **DF-C1/DF-C2**。
- **C3** ✓：铁律成文；本轮 judge/auditor/lead 试用留痕——本审计即实际使用者（§0 证据行 + §7 自验）。
- **C4** ✓：kit_selftest 至新路径 PASS（counts 2/2/0）；**r1→r4 迭代链透明**（r1 REPO 层级/hex 过滤修复前、r2 counts=None、r3 断言 FAIL 如实落盘、r4 现行——四个收据字节全保留，活台账登记逐版哈希；符合「失败如实记录」而非悄悄重跑）。

## 5. 活台账（11 事件）与 38 pin 制度自洽 —— ✅

- 11 事件：source 路径 11/11 存在且 SHA 复算吻合；executor 与预注册 §七 指派一致（包A=builder-codex、包B/包C=builder-dsh）；timestamp/registered_at 带时区且非严格递增；pin_class 全 live_doc；append-only 顺序保持。L2 五事件的 L3 重登记语义（spec-selftest 条目内「620cd322 为 canonical 自哈希、本条记文件字节哈希」的澄清）准确——正是 L2 O-4 的澄清落账。
- 38 pin 构成：31 contract（含 v2 registry 23 事件 sources 中 18 个新钉收据）/7 live_doc；**活台账 11 事件的 source 全部未 pin**——与「append-only 不入封印」设计一致，无过度钉扎。
- **制度自洽评估（lead 问）**：自洽。v2 registry 是冻结的历史账（不可追加=正确）；新收据一律走活台账+新文件路径；corrections=新文件+新事件（C-1 教训已制度化）。一个长期张力点已被正确放置：被封印 registry 的 sources 永久不可变，意味着「修订历史收据」唯一合法形式是旁挂新收据——这不是缺陷，是设计;但要求未来所有执行者理解「绝不能动 38 pin 清单内的任何文件」。活台账 source 新鲜度缺对账机制 → O-2。

## 6. L2 缺陷闭合核对（逐条「真闭合」判定）与停止条件判定

| L2 条目 | 判定 | 依据 |
|---|---|---|
| DF-1 活台账三方矛盾 | **真闭合** | schema 增 registered_at+enum 扩列（A1）；测试并入 schema 校验（A2，本审计 naive/负例攻击被拒）；现行 11 事件 11/11 合 schema；三方立场唯一。DF-1 的 L3 机读消费停止条件**解除**。 |
| DF-2 validator 约束缺口 | **真闭合（--spec 面）/附 DF-B1（--retro 面）** | enum×2+两个伴随校验实现且 fixtures 覆盖；B4 在 --spec fail-closed。--retro 默认行为见 DF-B1，L4 用作合规门前必须处置。 |
| C-1 --spec 覆盖 | **真闭合** | 拒写/显式 --out/目录即拒；T1 机械复现覆盖模式；原收据字节未动（本审计三重实测）。停止条件「修复前禁止对证据目录跑 --spec」可解除。 |
| O-1 溯源自证 | **机制落地、实证留 L4（=U1，如实）** | §三.4 披露+--reconcile+合成正反例；真实对账未做，U1 停止条件未触发也未闭合——按预注册口径正确。 |
| unknown-2 条件 a | **真闭合** | A4 生产路径硬拦截（逃逸实验）。 |
| unknown-2 条件 b | **本轮落地（本审计即试用方）** | 证据行+drift 状态行+receipt_check 回验；**活台账登记留 lead**（auditor write-scope 仅本目录，如实声明）。 |
| unknown-2 条件 c | **真闭合** | tripwire 保留+「报告制≠免检」明示（A5）。 |

其余停止条件：§四.1 v2/v1 字节冻结 ✓（v2 verify exit 0 复跑）；§四.4「对齐前他包不得消费活台账」——包B/包C 交付物未读活台账（代码面核对）✓；§五 U2（重锁后 drift 非空须逐条定性）——drift=[] 无需触发；U3 本报告新发现即输入。

## 7. 本文件自证（⑧b）

- 证据行 12 条由 `evidence_line.py` 于 18:46:20+08:00 生成（§0 引用），全部可按 `--root` 复算。
- `receipt_check.py` 对本文件实跑（18:48:55+08:00）：**exit 0、all_ok=true**——live_doc_drift 状态行 ✓、哈希行违规 0、证据行 claimed=recomputed **12/12**（bad=0、unverified=0）；报告存 /tmp/l3-audit-receipt-check.json（仓库外）。
- 修复轮复跑（19:2x+08:00，§9 增补+§0 刷新后字节）：以修复版 `receipt_check.py`（effda0ed）实跑 **exit 0、all_ok=true**——证据行 **19/19**（12 条含 3 条刷新 + 7 条修复轮新增；bad=0、unverified=0）、哈希行违规 0；报告存 /tmp/audit-l3fix/audit-check-1.json（仓库外）。
- 审计者活台账登记（work:l3-auditor-*）因 write-scope 限制未由本人写入，留 lead 代登（与「使用者本人登记」原则的偏差在此声明）。

## 8. 覆盖与限制

- git 未行使：封印 `72edb519` 及各包提交哈希（`0e276a20`/`af703db`/`23a63fc`）的先后关系采信仓库台账+磁盘 mtime 链（与 L2 同限制）。
- 未复核 judge 并行验收的对错（按指令）;本报告独立发现以 §1 三 defect + §2 A4 实验为核心。
- /tmp 工件：合成仓 `/tmp/l3audit-root`、包B 副本 `/tmp/l3-pkgb`、三份 retro 矩阵与重放收据——均在仓库外。

## 附录A：复现命令要点

1. A4 逃逸实验：复制骨架（2-用例+v3+各 pin 路径+imports 源）到 /tmp → `verify_seal` 基线 PASS → 改 config.work_registry 指向同字节新路径+重锁 config pin → 期望 `read-surface path not pinned contract`（实测 REJECTED×2 变体）。
2. naive 时刻攻击：`validate_against_schema(entry_with_naive_registered_at, live_registry_entry)` → AssertionError pattern miss（实测）。
3. CJK 漏报：对 `receipt_check.HEX_TOKEN_RE` 输入 `哈希<64hex>` → 0 命中（实测）。
4. B4 三模式：`--retro <codex runs> --retro <dsh runs> [--seal-at|--allow-unsealed] --out …` → 三者皆 exit 0，仅 seal.policy 标签不同（实测，20 场）。
5. B6：`--spec`（无 --out）/`--out 已存在`/`--out 新路径` 三态 → 不落盘/refuse exit 2/写入（实测）。
6. 活台账：11 事件 source SHA 复算；`test_freeze.py` 48/48；v2/v3 `verify`。

---

## 9. 修复轮敌意复核（2026-10-29，修复提交 15d9d62a；实钟 19:01–19:2x +08:00）

- 任务：不替 judge 跑测试，找修复本身引入的新问题（lead 指定五面：DF-B1 拒绝路径语义、DF-C1 新正则盲区/误报、DF-C2 并入后 --no-drift-require 自洽、D-L3-1 verdict 四态矛盾组合、修复轮收据链+活台账 append-only）。
- 方法与铁律：仓内零写入（本目录除外）；git 只读本轮**已行使**（show/log/diff/status 及 `--reconcile --git` 触发的只读 `git log -1`）；全部探针在 /tmp（`/tmp/audit-l3fix`）；truth/solution 未读；零模型调用。

### 9.1 修复本体核验（核了什么，全部实测）

- **DF-B1 ✓**：`--retro` 无 `--seal-at` 且无 `--allow-unsealed` → **exit 3 + 响亮 stderr + 矩阵不落盘**（拒绝路径在 `main()` 写盘之前，无半截产物）；有 seal 的 retro 完全不受影响（`--seal-at` → exit 0 密封矩阵）；`--allow-unsealed` → exit 0 披露矩阵（unsealed=true/policy 正确）；回归 T7 钉住。SCHEMA.md 4b（修复轮注）与实现一致，预注册 B4 字面「默认非零退出」现被满足且更严。
- **DF-C1 ✓**：新环视正则实测——CJK 前贴与**后贴**均捕获；大写 8 位记违规；65/70/128 位超长记违规；下划线贴邻（`_…_`）现被捕获（严于旧 `\b`，行为拓宽、方向正确）；纯数字（日期/计数）与混字母数字记号（如 `deadbeefX`）按设计跳过；base64 团块实测零误报；URL 内 21 位 hex 记号记违规（「长度一律校验」的预期严格性，见 N-4）。自检 14/14 含 CJK 前贴/超长/JSON 字符串值三个新反例（本审计 /tmp 独立复跑全过）。
- **DF-C2 ✓**：JSON `live_doc_drift` 字符串值 → violation 并入 `hash_lines.violations` → 参与 `ok` 判定；**且 `--no-drift-require` 下依然 fail**（糊弄值 ≠ 状态行缺失）。
- **D-L3-1 --git ✓**：真执行为 `subprocess.run(list)` 无 shell——无注入面；修复实际落在收据 `src` 记录串（旧 %-format 会在 step 记录前抛 TypeError 被吞）。本审计以只读 git 对真仓封印提交实测 `--reconcile --git`：verdict=ok、6 步全真、src 串正确。
- **inconclusive 可达性/消费性 ✓**：`cdt/vdt` 任一缺失必先使某非比较步骤为假 → verdict=error，故 inconclusive 防御性不可达；且收据 `ok = ok and verdict=="ok"`，inconclusive 恒 ok=false，下游按 ok 消费不会误收 ✓。

### 9.2 修复轮收据链与活台账（r5 FAIL 留痕/r6 现行/events=12）

- **r5（18:59:26，all_pass=false）如实留痕**：receipt_check（中间版字节 c7e91bbe）13/14、exit 1；r6（18:59:52）以**与提交字节一致的现行版（effda0ed）**复跑 2/2 PASS——r6 所钉 script sha8 与提交后磁盘/提交字节实测一致，validator 面同（cli-fix 收据内嵌 validator sha8 e71f28fb = 现行）。修正链 r5→r6 符合「失败如实记录」。
- **活台账 11→12 纯尾部追加**（git diff 逐行核对，前 11 事件字节未动）；事件 12 `source` 钉 cli-fix 收据 sha256 `17a3c053…`（前 8 位）实测逐字节吻合；timestamp 链自洽（r6 18:59:52 < 登记 19:00:07 < 提交 19:01:27）。locator 披露准确（T8 pending-external 已如实注明）。
- 既有收据零破坏：`db65c68c`/`6048ad41` 两条旧收据实测字节未动；新收据全走新路径（C-1 纪律保持）。
- 本审计独立复跑（全部 /tmp 出新路径）：kit_selftest 2/2、cli-selftest 9/9、`--spec` 自检 PASS——与申报一致。

### 9.3 新发现

### FIX-D1【defect】`--reconcile` verdict 语义仍有一处违反自订不变量：非比较步骤假 + 比较通过 ⇒ `verdict="ok"`

- **证据**（/tmp 实测收据）：`--commit` 给大写 7 位假哈希（`commit-hash-format` 步骤实假）+ `--commit-time` 给合法时刻 → 收据同页并现 **`verdict: "ok"` 与 `ok: false`**，步骤列表第 4 步 False、第 6 步 True，exit 1。代码面：`comparison_ran` 分支内 verdict 仅由 `vdt>=cdt` 决定，未并入 `non_comparison_ok`——与 docstring/SCHEMA 4b 自订不变量「**任何步骤假 ⇒ verdict 不得为 ok**」直接矛盾。
- **影响**：`ok`/退出码仍 fail-closed（按 ok/exit 消费者安全），但 verdict 字段正是 D-L3-1 要治理的机读摘要；L4 真实批次对账报告若按 verdict 出「对账通过」，带坏提交哈希的对账会被标 ok。
- **为何漏网**：T9 只测「commit-time 来源失败→error」，T4/T5 只测全真两态——「非比较步骤假 + 比较可跑」组合无测试钉住。
- **下一步**：`comparison_ran` 分支补一行守卫（如 `if vdt >= cdt and non_comparison_ok` 才 ok，否则 error）+ 补 T10（坏哈希+好时刻 ⇒ verdict=error）。修前工具哈希见 §0 刷新行。
- **停止条件**：L4 真实批次对账（U1）若以 verdict 为唯一机读结论而未修 → 该对账报告的「ok」不可采信。

### FIX-O1【observation】seal 块标签与实际密封状态存在两处矛盾组合（一处系修复使显形）

- `--seal-at`+`--allow-unsealed` 同时给：门放行、exit 0，矩阵 `provided=true/unsealed=false` 但 `policy="allow-unsealed-disclosure"`——密封矩阵带披露口径标签，且 `--allow-unsealed` 静默成 no-op（无警告）；
- 仅 `--seal-at`：`provided=true/unsealed=false` 但 `policy="fail-closed-unsealed"`——**已密封矩阵带「unsealed」策略标签**（此标签逻辑系包B遗留，非修复引入，但 4b 把 --retro 语义抬为主语义后更显眼；4b 未写双旗组合行为）。
- 影响：无安全洞（unsealed 布尔始终准确），但 policy 是机读字段，下游按 policy 分流会把密封矩阵归入披露口径。
- 下一步：policy 改由实际状态派生（如 sealed=`provided` 优先），或在双旗时响亮警告。停止条件：下游出现按 policy 误归档的第一次实例即转 defect。

### FIX-N1【note】「回归 9/9」中 T8 为 pending-external 计 pass

- T8（--git 用例）在 builder 环境默认跳过且 `pass=true` 计入 9/9；locator 已如实披露、judge 以 `L3_ALLOW_GIT=1` 执行——口径透明，唯计数语义「9 执行 9 过」与「8 执行+1 外判」应予区分。

### FIX-N2【note】r5 留痕只有工具级粒度

- r5 收据记录 receipt_check 13/14、exit 1，但未落哪个用例失败（tools 级 counts+exit）。留痕成立、链路自洽；失败用例级明细缺失使「为何 FAIL→为何修复」须由 git diff 反推。

### FIX-N3【note】`--no-drift-require` 在文本/JSON 两分支行为不对称

- 文本分支：drift 行存在但无状态记号 + `--no-drift-require` → ok（只查哈希行，符合文案）；JSON 分支：字符串值 + 同旗 → **violation**（DF-C2 接线使其无条件入判定）。两者都可辩护（缺失≠畸形），但现行文档未写明该不对称；建议 SCHEMA/README 一句话言明。

### FIX-N4【note】新正则的行为拓宽清单（供下游与文档校准）

- 现在会被记违规的既有无害形态：任意 9–39/41–63/≥65 位 hex 形串（如 21 位 URL 追踪参数、128 位 sha3 摘要——凡引用非 {7,8,40,64} 长 hex 摘要的文档将恒不过检）；下划线贴邻 hex（snake_case 标识符内嵌段）。被放行的形态：小写 hex 词 7/8 位（deadbeef、acceded 类）、纯数字、混字母数字。均系「长度一律校验」的预期后果，但 {7,8,40,64} 白名单语义值得在 README 一句话显式化，避免 L4 文档引用长摘要时误踩。

### 9.4 分级计数（修复轮增量）

**blocking 0 / defect 1（FIX-D1）/ observation 1（FIX-O1）/ note 4（FIX-N1–N4）。** 主审三 defect（DF-B1/DF-C1/DF-C2）+ D-L3-1 --git 面修复本体经攻击实测**全部真闭合**；FIX-D1 为修复自身在 verdict 字面不变量上的残留缺口（ok/exit 面仍 fail-closed，不阻塞本轮交付，须随 U1 前修复）。

修复轮证据行（`evidence_line.py` 生成，19:17:16+08:00；新增 7 条，§0 另刷新 3 条）：

```
1-评测方案/工具链/evidence-kit/selftest-receipt-l3-20261029-r5.json · 29ce9062 · 786B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/evidence-kit/selftest-receipt-l3-20261029-r6.json · c396bb40 · 785B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/cli-regression-receipt-l3-fix-20261029.json · 17a3c053 · 10187B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/spec-selftest-receipt-l3-fix-20261029.json · 82393b1f · 5226B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/reconciliation-synthetic-l3-fix-20261029.json · b356ce9f · 1856B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/cli-selftest-l3.py · 76551873 · 12116B · 2026-10-29T19:17:16+08:00
1-评测方案/工具链/runner-schema-v2/SCHEMA.md · 66e7fc65 · 15897B · 2026-10-29T19:17:16+08:00
```

§9 附注（自证与历史字面）：修复后正则会把 §1 原 DF-C1 证据行中的 16 位/12 位字面样本记为违规——这恰是修复生效的直接证明；为保持本文件自证通过，§1 字面已截短为 8 位前缀+省略号，原字面见 git 历史（281ab3e 版本本文件）。§0 三条证据行按现行字节刷新（原 a6c09fe3/8c81e9a4/97b3be0b 为修复前字节，留此存照）。

/tmp 工件（仓库外）：`/tmp/audit-l3fix/`（四态 retro 矩阵、verdict 空洞收据、--git 收据、正则攻击样本、独立复跑三收据）。
