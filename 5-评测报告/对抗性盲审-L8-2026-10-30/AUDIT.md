# 对抗性盲审报告（L8）——receipt_check 废止链机器可读（L8-A）+ PREREG 模板（L8-B），2026-10-30

- 审计角色：敌意审计（板任务 task-20 序列延续；lead 委托 L8）。纪律：零模型/零网络；只读+离线复算；git 全程可用；写界仅本目录；truth/solution 未语义阅读；凭据仅批准 ref 内存比对，零值输出。
- 对象：loop8-2026-10-30 三提交 ccc357a（L7 审计终稿补全，lead 代提交）→ 294aee6（D1 预注册）→ f50e31b（D2 实现，5 新文件）。

**live_doc_drift: none（0 项）**

## 总判定

**安全 blocking：否；defect：0；observation：2。** L8-A 废止链检查（+163 行）逐向量对抗核验：声明语义全部落实（形态严格/全哈希实测/VOIDED 名检/禁自引/禁重复/深度 16 环检测），「无字段行为逐字节不变」经 A/B 独立实测证实（origin/main 版 vs 修订版同输入输出全同）；对抗探得的**规格级缺口=repo 内限定缺失**（../与绝对路径仓外指针可过四守卫，AUD-L8-O1）与**类固有残留窗口**（TOCTOU/子串名检/深度穷尽静默，AUD-L8-O2），均非阻塞且现数据零利用。L7 审计终稿补全（ccc357a）provenance 如实（恰两文件、内容=本 auditor 13:52-13:53 终稿字节）。历史红线（L6/L7 含 VOIDED 零字节改动、gate/CHANGELOG 零触及）成立。

## 五段内省（观察—证据—解释—未排除因素—可复现实验）

### 一、L8-A 废止链检查（receipt_check +163 行）

- **观察**：新增 `validate_supersession` + check_doc 集成（仅当 doc 含 `supersedes` 键时激活）+ selftest 16→25（正例 1+负例 7+链环）。
- **证据**：`git diff 294aee6 f50e31b -- receipt_check.py` 逐 hunk 复核；--selftest 实跑 PASS exit 0（l8-receipt-check-selftest-receipt.json 在档可复现）。
- **解释**：每项对账 PREREG 声明——list/dict/**恰有 {file,sha256}**/64 位小写 hex/存在性/实算一致/文件名含 VOIDED/禁自引（bare 名、子路径、绝对路径三形态均被 resolve 等值覆盖）/禁重复（(file,sha) 对去重；同文件不同 sha 经 sha 实测不符被拒）/沿链深度 ≤16 环检测——**声明项 100% 落实，无类名/字段名/规则偏差**（L7-O1 先例逐条核通过）。
- **未排除因素**：①**repo 内限定缺失**（AUD-L8-O1）：`../` 穿越与仓外绝对路径指针在现规格四守卫下可通过——实现忠实于 PREREG（规格本身未声明仓内限定），但削弱「人机双载体在库」意图；现数据（demo 收据 6 指针全仓内 `../L7验证器修订-…`）零利用。②TOCTOU：sha 单次实测后、链跟随重读前的替换窗口存在（与证据行复算类工具同类固有；任何后续运行可检）。③文件名子串匹配：`NOT-VOIDED.json` 亦过名检（真锚=sha）。④深度 ≥17 的环理论逃逸（walk 穷尽即静默停止；实际链长量级 1-2，16 上限合理）。
- **可复现实验**：`receipt_check.py --selftest`（25 项含 supersedes 正/负例组）；A/B 对照——origin/main 版与修订版对无字段收据同输入输出**逐字节全同**（/tmp/l8ab 实测）；demo 收据 `--out` 全报告实跑 **supersedes 6/6 全 verified、violations 空**（实锚真实 L7 六废链，../ 相对解析正确）。

### 二、ccc357a provenance 与时序（D1 先于 D2）

- **观察**：ccc357a 携带恰 2 个 L7 文件（AUDIT.md + l7-audit-mech-receipt.json），声称「合并后 auditor 13:52 重生、lead 代提交」。
- **证据**：`git diff --name-only 016dbfe ccc357a` 恰该两文件；AUDIT.md 增量=证据行实填（394ed4a1 钉）+F1 终态 PASS 12/12——与本 auditor 13:52-13:53 实际重生字节一致；提交时序 ccc357a(14:10) < 294aee6(D1) < f50e31b(D2, 14:17)。
- **解释**：provenance 如实（代提交声明在 commit message）；D1 先于 D2 ✓。
- **未排除因素**：无（文件作者粒度 git 只到提交者；内容与 auditor 在场痕迹互证）。
- **可复现实验**：上述 git diff 命令原样可重放。

### 三、历史红线（L6/L7 零字节改动）

- **观察**：L6/L7 全部收据（含 6 份 VOIDED）须零改动。
- **证据**：`git diff --name-only 016dbfe..HEAD -- 5-评测报告/L7验证器修订-2026-10-30/` = 空；gate.py 与 CHANGELOG.md 不在 loop8 全量 diff 中；红线过滤（剔除 L7/L8/工具链声明内路径）后**零额外路径**。
- **解释**：demo 收据以 sha256 锚定 L7 VOIDED 六件而不改动它们——「锚而不动」正是 L8-A 设计意图的实证。
- **未排除因素**：无（git 全树 diff 已覆盖）。
- **可复现实验**：同上 git diff；`sha256sum 5-评测报告/L7验证器修订-2026-10-30/l7-gate-recompute-receipt-r*.json` 与 demo 收据 supersedes 列表逐条比对一致。

### 四、L8-B PREREG-template（自食声明与异常类条款）

- **观察**：PREREG-template.md（36 行）立制「异常类如实申报」（预注册异常类与实现 raise 逐字一致；不得猜测类名）+四段必填结构+自食核对段。
- **证据**：模板全文核读；L8 PREREG 结构对照（标识块/选题表五项处置/七要素/纪律承诺齐）；L8-A 实现 **0 个新 raise**（git grep `^+.*raise`=0）——异常面=violation 文案（已带 L8-A 前缀）✓；模板自食段如实声明「本文件即 L8-B 交付」。
- **解释**：无自我矛盾——模板约束结构完整性且自食核对显式披露 bootstrap 顺序；条款对 L8-A 本身成立。
- **未排除因素**：「模板自身修订须走预注册」的元-递归在更长序列上的操作性（本环无实例）。
- **可复现实验**：对照 `1-评测方案/自动循环L8-2026-10-30/PREREGISTRATION.md` 与模板四段逐项指认。

### 五、凭据/PII 与红线扫描

- **观察**：本环新增 5 文件须零凭据零 PII。
- **证据**：PREREG-template+evidence-kit 全目录 13 文件：真实 key **0**/generic **0**/PII **0**（scan-report-l8-full-r1.json、pii-min-check-report-l8-full-r1.json）。
- **解释**：新增面全部为模板/校验器/收据，无凭据形态内容。
- **未排除因素**：无。
- **可复现实验**：两收据工具原样重放。

## 机器核（l8-audit-mech-receipt.json，9 PASS/0 FAIL）

S1 时序/D1 先于 D2 ✓；S2 ccc357a 恰两文件 ✓；S3 终稿版本判据 ✓；S4 红线零额外路径 ✓；S5 gate/CHANGELOG 零触及 ✓；S6 VOIDED 零字节 ✓；S7 selftest PASS ✓；S8 demo 6/6（--out 全报告）✓；S9 无字段 A/B 全同 ✓。
（过程注记：S8 首查 FAIL 系审计侧两处失误——demo 实文件在 `5-评测报告/L8证据链修订-2026-10-30/`（diff stat 截断误导）；CLI stdout 为设计内投影不含 supersession 块、须 --out 取全报告。两因均系审计侧，非工具缺陷，如实留档。）

## 缺陷与观察清单

- **blocking：无。defect：无。**
- **AUD-L8-O1【observation·规格级】**：supersedes 校验无 repo 内限定——`../` 穿越与仓外绝对路径可过全部四守卫（存在/VOIDED 名/sha/非自引），削弱「双载体在库」意图；现数据零利用。建议：规格补「resolved 路径须在仓库根内」。
- **AUD-L8-O2【observation·类固有】**：TOCTOU 单次校验窗口、VOIDED 子串名检（NOT-VOIDED 过名检）、环检测深度 16 穷尽静默——同类文件校验器固有窗口，后续运行可检/真锚为 sha，实际链长量级下风险可忽略。

## 证据行（evidence_line.py 生成，2026-10-30T14:30:07+08:00）

```
5-评测报告/对抗性盲审-L8-2026-10-30/l8-audit-mech-receipt.json · eb0f69c1 · 2310B · 2026-10-30T14:30:07+08:00
5-评测报告/对抗性盲审-L8-2026-10-30/scan-report-l8-full-r1.json · 228048a9 · 3550B · 2026-10-30T14:30:07+08:00
5-评测报告/对抗性盲审-L8-2026-10-30/pii-min-check-report-l8-full-r1.json · 38a75194 · 386B · 2026-10-30T14:30:07+08:00
```
