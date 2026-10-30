# 对抗性盲审报告（L9）——假发现-补正事件链+账实对账+解析根约束，2026-10-30

- 审计角色：敌意审计（lead 委托 L9）。纪律：零模型/零网络；只读+离线复算；git 全程可用；写界仅本目录；truth/solution 未语义阅读；凭据仅批准 ref 内存比对，零值输出。
- 对象：loop9-2026-10-30 三提交 cda92f5(D 预注册，v2 模板首环含段 0)→5fcd3f2(D 补正一，实现前 append-only)→295f2c7(D2 实现)；基 main ac36ab7。

**live_doc_drift: none（0 项）**

## 总判定

**安全 blocking：否；defect：0；observation：0（对抗向量答问全部落实，无残留逃逸）。** 假发现-补正事件链成立且质量优于先例：D 封印内的假 F-1 在**实现前**经 append-only 补正作废（19 插入 0 删改、两提交间无夹层），补正前无任何修复类动作落盘；F-1 假发现的方法学根因（git blob sha1 冒比 content sha256）由本审计独立考古证伪其结论——**content sha256 f73e2dc3… 精确可考@8edc58f 且 27cd39d^==8edc58f，L6 locator「父提交可考」声明为真**。L9-A 第 5 守卫（resolved∈--root）关闭 L8-O1 逃逸面；L9-B 账实对账复现 20 FRESH+1 HISTORICAL@8edc58f/0 UNRESOLVED、考古口径钉死 content sha256、--repo .git 启动自检防深度错位；test_freeze 48 断言零改动纯追加至 49 全绿；段 0 反馈对照 7 条逐条真实；红线全净。

## 五段内省（观察—证据—解释—未排除因素—可复现实验）

### 一、假发现-补正事件链（本轮重点）

- **观察**：D 封印含假 F-1 声明（「sha 在 10 个提交 blob 中不可考、locator 声明不实」）；实现前出现补正一作废 F-1。
- **证据**：①时序独立核：D=14:53:56 < 补正=14:56:17 < D2=15:04:42（同区时字符串保序），且 D→补正间**无夹层提交**（恰 1 commit）；②append-only 机械证实：`git diff cda92f5 5fcd3f2` = **1 file changed, 19 insertions(+), 0 删改**；③补正前落盘面=零（全部 L9-B 修复类文件均在 D2）。
- **解释**：假发现源于预检方法学缺陷（哈希体系混用：`git rev-parse c:path` 的 blob sha1 ≠ 内容 sha256），非台账不实；补正以正确口径（`git cat-file blob` 管入 sha256）重考并作废假 F-1——**发现→作废→重考→实现**四步全部先于任何实现动作，假发现零落地。
- **未排除因素**：blob sha1 体系下 f73e2dc3 不可考是否可能为真——不可能：两哈希域不同，blob sha1 集合中不含 content sha256 值属必然，恰证混用无效。
- **可复现实验**：`git show 8edc58f:4-打分细则/可信冻结-2026-10-29-v3/work-registry-live.json | sha256sum` = f73e2dc3…（本审计独立实算）；`git rev-parse 27cd39d^` = 8edc58ff；`ledger_reconcile.py` 重跑 counts=**21=20 FRESH+1 HISTORICAL/0 UNRESOLVED** ✓。
- **先例质量评估**：vs L6 E1/E2 废封（实现中止+档案迁移+重封，成本=在途消耗披露）；本环在**实现前零成本**拦截——补正纪律（D 后 append-only、实现前定案）质量更高，且假发现本身被转为 §0-#5 教训实例与 O 段观察项（方法学自省入档）。

### 二、L9-A 解析根约束（第 5 守卫）对抗核

- **观察**：receipt_check.py +60 行：`validate_supersession` 增 root 参数，resolved 目标必须 `==root_r or root_r in resolved_t.parents`；CLI 默认根=仓库根；selftest 25→29（出根即拒/根内不误伤/symlink resolve 后判）。
- **证据**：diff 逐 hunk；--selftest PASS exit 0；**L8 demo 默认根复验 6/6 全 verified、violations 空**（历史复算零回归）；无字段 A/B（ac36ab7 修前版）**function-level 对照全同**。
- **解释**：L8-O1（repo 内限定缺失，auditor 与 judge 独立收敛）被制度性关闭；守卫语义=「出根即拒、根内不误伤」。
- **未排除因素**：大小写=文件系统原生语义（resolve 返回真实大小写，同文件不构成旁路）；TOCTOU 类固有窗口（沿 L8-O2 口径，后续运行可检）。
- **可复现实验**：selftest 内含出根负例组（tempfile 仓外 absolute + ../ 穿越用例）；A/B 对照脚本与副本 receipt_check.pre-l9.ab.py 在本目录。

### 三、L9-B 账实对账制度化

- **观察**：ledger_reconcile.py（274 行，新）+ 对账收据（187 行）+ selftest 10/10 + test_freeze 账实不变量第 49 断言。
- **证据**：重跑复现 counts={total:21, FRESH:20, HISTORICAL:1, UNRESOLVED:0, waived:0}、all_resolved=true、structure_violations=[]；HISTORICAL 恰为 #18 L6 更正事件（source=f73e2dc3…=8edc58f 修复前完整字节）；结构核+sidecar 制度+allowlist 初始空（与补正一钉死口径一致）。
- **解释**：考古口径钉死 content sha256（禁 blob sha1 冒比）=把 §0-#5 判卷器修订全套的「历史复算影响」制度化到台账基座；`--repo` 必须含 `.git` 的启动自检直接防本工具自身 HERE.parents 深度错位（开发期实测教训，注释与代码在案）。
- **未排除因素**：allowlist 静态空+sidecar 防「更正前态未入 git」的 UNRESOLVED——机制保留（未用≠失效）。
- **可复现实验**：`cd 4-打分细则/可信冻结-2026-10-29-v3 && ledger_reconcile.py`（重跑输出与收据逐字段一致）；`--repo` 传非 .git 目录应拒（自检路径）。

### 四、PREREG v2 自食与段 0 对照真实性

- **观察**：v2 模板首环，段 0 对照 7 条全覆盖+覆盖声明（#1 运行时留痕=结构性不适用，非回避）。
- **证据**：段 0 表与 AGENTS.md「本轮老师反馈」#1-#7 逐条实质对应（运行留痕/完全分账/正式表/未知三件套/判卷器修订全套/五段结构/小而完整闭环）；对照源=反馈/2026-10-28-第二轮 归档+AGENTS.md 本轮节（引用路径有效）；**补正一显式呼应 §0-#5**（把假发现教训实例化「实现与自测固化该口径」）✓。
- **解释**：v2 自食成立；补正纪律与模板「D 先于实现/append-only」条款自洽。
- **未排除因素**：无。
- **可复现实验**：模板四段逐项指认 + 本节引用路径存在性核。

### 五、红线与扫描

- **观察**：L5/L6/L7/L8 证据路径与既有收据须零字节改动；registry 21 事件 D2 后不再变；CHANGELOG 未动；新增文件零凭据零 PII。
- **证据**：`git diff --name-only ac36ab7..HEAD` 过滤后**零额外路径**；`git diff 295f2c7..HEAD` = **0 文件**（registry 及一切未再变）；CHANGELOG diff=0；扫描 25 文件真实 key **0**/generic **0**、PII **0**。
- **解释**：本环全部改动收敛于 PREREG（含补正）/receipt_check/ledger_reconcile/test_freeze 追加/收据新文件——红线净。
- **未排除因素**：无。
- **可复现实验**：同上 git 命令；两扫描收据原样重放。

## 缺陷与观察清单

- **blocking：无。defect：0。observation：0。**
- 对抗向量全部落实或答问：根约束守卫关闭 L8-O1；A/B 等同；考古口径独立复核；深度坑由启动自检防再犯。

## 机器收据与本文件自证

- l9-audit-mech-receipt.json（12 PASS/0 FAIL，含 S1-S12 与 adversarial_findings）；scan-report-l9-full-r1.json；pii-min-check-report-l9-full-r1.json；receipt_check.pre-l9.ab.py（A/B 修前版副本）。
- live_doc_drift: none（0 项）；证据行见下节。

## 证据行（evidence_line.py 生成，2026-10-30T15:14:55+08:00）

```
5-评测报告/对抗性盲审-L9-2026-10-30/l9-audit-mech-receipt.json · 8f1b55e2 · 2463B · 2026-10-30T15:14:55+08:00
5-评测报告/对抗性盲审-L9-2026-10-30/receipt_check.pre-l9.ab.py · fde05e3f · 24933B · 2026-10-30T15:14:55+08:00
5-评测报告/对抗性盲审-L9-2026-10-30/scan-report-l9-full-r1.json · 63d8e472 · 6440B · 2026-10-30T15:14:55+08:00
5-评测报告/对抗性盲审-L9-2026-10-30/pii-min-check-report-l9-full-r1.json · a311419e · 388B · 2026-10-30T15:14:55+08:00
```
