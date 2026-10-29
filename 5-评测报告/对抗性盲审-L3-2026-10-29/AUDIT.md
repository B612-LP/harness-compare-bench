# 对抗性盲审报告（L3）——机读对齐与证据机械化，2026-10-29

- 审计角色：敌意复核者（第三轮连任）。立场：hostile；预注册是唯一基准；builder/judge 陈述一律当作待证主张；目标是找 judge 条款级验收会漏掉的东西。
- 方法与铁律：全只读（仓内零写入，本目录除外）；git 只读可用但本轮**未行使**（全部判定以磁盘字节+可离线重放为准，与 U1 口径一致）；零模型调用；`--spec` 类一律 /tmp 或新路径；2-用例 truth/solution 未读；哈希/时刻由脚本生成（本文全部证据行由 `evidence_line.py` 生成、并经 `receipt_check.py` 回验，见 §7）。
- 依据：`1-评测方案/自动循环L3-2026-10-29/PREREGISTRATION.md`（封印 `72edb519`）；L2 缺陷原文 `5-评测报告/对抗性盲审-L2-2026-10-29/AUDIT.md`。
- 时点：审计执行 18:25–18:5x +08:00（实钟）。

**live_doc_drift: none（0 项）**——`freeze.py verify`（v3）于 18:26 实测 `ok=true, live_doc_drift=[]`；本文件自身经 `receipt_check.py` 核验通过（§7）。

## 0. 总判定

**0 blocking。** L2 遗留缺陷 DF-1/DF-2/O-1 与 unknown-2 三条件的闭合**经攻击性实验逐条证实为真闭合**（非声称闭合），其中 A4 经本审计构造逃逸样本实测：**生产路径 verify_seal 硬拒**（非测试专属）。发现 3 项 defect（两处新工具的实现-承诺缺口、一处 B4 措辞-行为偏差）、2 项 observation、4 项 note。停止条件判定见 §6。

分级计数：**blocking 0 / defect 3 / observation 2 / note 4**。

证据行（脚本生成，18:46:20+08:00）：

```
4-打分细则/可信冻结-2026-10-29-v3/freeze.py · 3896e6aa · 45117B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/test_freeze.py · dd941b44 · 23401B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/config-schema.json · c8a06024 · 6229B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/freeze.lock.json · bf7f9aa3 · 8264B · 2026-10-29T18:46:20+08:00
4-打分细则/可信冻结-2026-10-29-v3/work-registry-live.json · a6c09fe3 · 11223B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py · 8c81e9a4 · 29316B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/spec-selftest-receipt-l3-20261029.json · 6048ad41 · 5226B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/cli-regression-receipt-l3-20261029.json · db65c68c · 7215B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/runner-schema-v2/reconciliation-synthetic-l3-20261029.json · a4dbe315 · 1856B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/evidence-kit/receipt_check.py · 97b3be0b · 11464B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/evidence-kit/evidence_line.py · 9b00febf · 5758B · 2026-10-29T18:46:20+08:00
1-评测方案/工具链/evidence-kit/kit_selftest.py · 383a70f8 · 3688B · 2026-10-29T18:46:20+08:00
```

---

## 1. 发现清单

### DF-C1【defect】receipt_check 的 hex 记号正则对「CJK 前贴哈希」与超长串全盲——C2 的核心场景失效

- **证据**（本审计构造样本实测，`receipt_check.py:50` `HEX_TOKEN_RE = re.compile(r"\b([0-9a-fA-F]{7,64})\b")`）：
  - `哈希5c6177fd68a74ab9…（64 位小写，前贴中文无空格）` → **0 命中**（Python `\b` 为 Unicode 词边界，CJK 与 hex 同为词字符，无边界可依）；
  - `假哈希deadbeefdead…` → 0 命中；70 位超长 hex 串 → 0 命中（`{7,64}` 上限 + `\b` 双侧不可满足）；
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
