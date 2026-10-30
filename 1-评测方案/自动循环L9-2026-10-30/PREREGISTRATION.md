# L9 预注册（自动循环 2026-10-30）——按 PREREG-template v2 撰写

## 0. 老师反馈对照（v2 必填，置首；对照源=反馈/2026-10-28-第二轮/README.md + AGENTS.md「本轮老师反馈」节）

| 反馈条目 | 本环对照 |
|---|---|
| #1 运行留痕（唯一 ID/版本/证据等级/最终裁定等） | **对齐**：L9-B 台账账实对账把「每次登记可复核」制度化——事件 source 三态分类（FRESH/HISTORICAL/UNRESOLVED），不可考 pin 直接现形 |
| #2 完全分账 | **对齐**：L9-B 对账对象即分账台账本体（work-registry-live），账实一致性常态化核验 |
| #3 正式表只纳规则冻结/有效/无污染 | **对齐（守护面）**：对账=守护台账这条口径基座的完整性；本环零新运行，正式表零新行 |
| #4 未知三件套 | **对齐**：预检发现的 F-1（L6 更正事件 pin git 不可考+locator 声明不实）按影响/下一步/停止条件入结论四段 |
| #5 判卷器修订全套 | **对齐**：L9-A 为共享证据工具修订（receipt_check），照修前/修后/正例/近似错误例/独立验收/历史复算（L8 demo 收据复验）全套执行 |
| #6 五段结构 | **对齐**：收尾结论照五段 |
| #7 小而完整闭环 | **对齐**：两小项皆闭合既有 observation（L8-O1、L7-O2），零真实模型调用 |
| 覆盖声明 | 本环不覆盖 #1 的「运行时留痕」新增面（零新运行，无新留痕需求）——非回避，结构性不适用 |

## 1. 标识块

- **plan_id**: `l9-20261030`
- **分支**: `loop9-2026-10-30`（自 **main** `ac36ab7` = PR#13 模板 v2 集成点切出）
- **集成前置（D 前已完成）**: PR#12（L8）与 PR#13（模板 v2）已合并 main；本环零真实
  模型调用、零新现场。
- **D 封印**: 本文件提交后立即执行；实现 commit 必须晚于 D。
- **验收**: judge + auditor 双验（零模型工具链环，沿 L3/L7/L8 先例；reviewer 不派）。

## 2. 选题表（遗留池逐项处置）

| 池项 | 处置 |
|---|---|
| L8-O1 supersedes 无仓内限定（judge 与 auditor 独立收敛） | **L9-A（主项）**：解析根约束 |
| L7-O2 live-ledger freshness 对账 | **L9-B（主项）**：账实对账制度化（预检已抓获 F-1，纳入 B 范围） |
| L8-U-2 kit_selftest L3 夹具 write-once 拒绝 | 不入本环——夹具退役属独立专项；B 不触及 kit_selftest |
| l4/l5 现场重跑适配 | 不入本环——重跑前置条件未触发（沿 L7/L8 处置） |
| T22d fixture 退役 | 不入本环——L6 现场封存（沿 L7/L8 处置） |

## 3. L9-A 设计（receipt_check supersession 第 5 守卫：解析根约束）

- **修前**: `supersedes` 条目 file 解析仅「相对收据父目录或绝对路径+存在+全哈希一致
  +文件名含 VOIDED+非自引」四守卫，**无根边界**——`../` 穿越或仓外绝对路径指针
  可通过（L8-O1 实证，符合当时 PREREG 文字规格）。
- **修后**: 第 5 守卫=**resolved 后的目标路径必须落在 `--root` 指定根内**（CLI 默认
  根=仓库根 `REPO`；`check_doc` 自测路径传自给根，夹具照常工作）。违反即 violation：
  `supersession(L9-A): 仓外指针（超出 --root 根）: <file>`。**语义选择声明**：取
  「收紧」而非「明文接受」——证据链锚定语义本应仓内闭环；现网全部 supersedes 数据
  （L8 demo 收据 6 条）均在仓内，收紧零破坏。
- **异常类如实申报**: 零新异常类（沿 L8 形态，violation 文案即错误面，带 `(L9-A)`
  标记）；退出码语义不变（0 全过/1 有违规/2 用法错）。
- **正例（历史复算）**: L8 demo 收据以默认根复跑仍 6/6 全 verified（行为不回归）。
- **近似错误例**（selftest 新增）: `../` 相对穿越出根→拒；根外绝对路径→拒；根内
  兄弟目录相对路径→**过**（不误伤 demo 形态）；symlink 指向根外（resolve 后判定）→拒。
- **影响面声明**: `receipt_check.py` 单文件；现网唯一含 supersedes 文档=L8 demo 收据
  （复验覆盖）；L6/L7 历史收据无该字段零触及；`--root` 参数既有语义不变（证据行
  复算早已按它解析）；无字段行为不变性质保持。
- **独立验收**: judge 自跑 selftest+demo 复验+自构至少 1 个 PREREG 未列逃逸
  （如根内 symlink 链、`root/../` 归一化等）。

## 4. L9-B 设计（work-registry-live 账实对账制度化）

- **修前**: 台账事件 source 哈希对盘无制度工具（本环 D 前预检用 ad-hoc 脚本）；
  **预检首跑即抓获 F-1**：`work:l6-ledger-schema-correction-20261030` 的 source
  sha256（修前字节）在触该路径全部 10 个提交的 blob 中**不可考**，且其 locator
  「本 correction 提交的父提交可考」声明**不实**（修前态只存在于当时工作树，
  从未入 git；全仓 grep 亦无 sidecar 副本）。
- **修后**: 新增 `4-打分细则/可信冻结-2026-10-29-v3/ledger_reconcile.py`：
  - 逐事件三态分类：**FRESH**（source.sha256==对盘实算）／**HISTORICAL**（对盘漂移
    但 sha 可考于该路径 git 全历史 blob——`git log --all --format=%H -- <path>` 逐
    提交 `git rev-parse <c>:<path>` 比对）／**UNRESOLVED**（漂移且 git 不可考）；
  - 结构核：event_id 唯一、timestamp 全序单调不减、registered_at 带时区偏移；
  - write-once 收据（`--out` 目标已存即拒）；退出码 0=全 FRESH/HISTORICAL（UNRESOLVED
    须全部命中 `--allowlist`）、1=存在未豁免 UNRESOLVED、2=用法错；
  - **新制度（sidecar 规则）**：自 L9 起，`correction` 类事件登记时 source 必须
    **FRESH-on-disk**——被更正字节须先以 sidecar 副本入盘（如
    `<台账目录>/correction-archive-<event_id>-<sha8>.json`）再登记指向副本，
    禁止指向即将被本环覆盖的活文件；
  - **test_freeze.py 新增不变量**：全部事件须 FRESH／HISTORICAL／命中**静态
    allowlist**（初始恰 1 项=L6 更正事件，原因=sidecar 制度晚于事件、修前字节
    从未入 git；allowlist 新增须走后续 PREREG）。
- **异常类如实申报**: 工具零新异常类（exit 0/1/2）；test_freeze 沿既有 assert 惯例。
- **正例**: 本环 21 事件全分类可解释（20 FRESH + 1 UNRESOLVED→allowlist 收纳）；
  HISTORICAL 分类的正例=自测夹具（临时 git 仓构造「漂移但历史可考」文件）。
- **近似错误例**: 篡改某事件 sha→UNRESOLVED→不变量红；重复 event_id→红；
  timestamp 回逆→红；UNRESOLVED 未豁免→exit 1。
- **影响面声明**: v3 目录新增 `ledger_reconcile.py`；`test_freeze.py` 递增测试
  （既有 48 项不动其断言）；registry 本体仅收尾按既有制度追加事件；F-1 为历史
  事件如实记录，**不回改**（append-only）。
- **独立验收**: judge 自跑对账工具+独立复算 F-1（自行全历史检索）+自构
  HISTORICAL/UNRESOLVED 夹具验证分类正确性。

## 5. 纪律承诺

D 先于实现；历史证据（含 registry 既有 20 事件与 L6/L7/L8 全部收据）零字节改动；
哈希/时刻脚本生成；write-once；CHANGELOG 不动；live 台账收尾登记+必跑 work-registry
不变量（含本环新增对账不变量）；收尾 PR 合并 main；结论五段结构。

---

## 补正一（D=cda92f5 封印后、实现前，append-only，2026-10-30T14:57+08:00）

- **§4「修后」段 F-1 描述作废**：预检判定「sha 在 10 个提交 blob 中不可考、locator
  声明不实」系**预检方法学缺陷**——比对了 git blob sha1（`git rev-parse c:path`）
  与内容 sha256 两个不同哈希体系，比对无效。以内容 sha256（`git cat-file blob`
  管入 sha256）重考：`f73e2dc3…` **精确可考于提交 8edc58f**（L6 验收提交，off-schema
  #18 所在），且 `27cd39d^ == 8edc58f` ——**L6 更正事件 locator「父提交可考」声明
  核可为真**，台账账实完全一致（20 FRESH + 1 HISTORICAL，0 UNRESOLVED）。
- **§4 相应修订**：①「修后」首跑预期由「F-1 入册」改为「20 FRESH + 1 HISTORICAL
  （l6-correction @ 8edc58f）、0 UNRESOLVED」；② HISTORICAL 判定方法钉死为
  **内容 sha256 考古**（`git cat-file blob` 管道入 sha256，禁用 blob sha1 冒比——
  本环 §0 对照 #5 的教训实例，实现与自测固化该口径）；③ 静态 allowlist 初始为空
  （不再收纳 L6 事件）；④ sidecar 规则保留（防患：HISTORICAL 依赖修前字节曾经
  入 git，未入 git 的更正前态仍会 UNRESOLVED）；⑤ 原预检假发现与方法学教训转为
  结论 O 段观察项（哈希体系混用=可复算工具的自检盲区实例）。
- 其余各节（L9-A 全部、§0/§1/§2/§3/§5）不受影响。本补正先于任何实现 commit。
