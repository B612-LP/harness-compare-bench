# L8 综合结论（2026-10-30）——废止收据链机器可读与预注册措辞防错

- 数据基座：judge 独立验收收据 `verify-receipt-l8.json`（sha256
  `e612e26ed5fee51d2a261c6de9b9f5cf5f0828b4df70e10a5d8d808f1d281d26`，8/8 PASS）与
  auditor 盲审 `5-评测报告/对抗性盲审-L8-2026-10-30/AUDIT.md`（sha256
  `cdcb0dcb`前缀，0 缺陷/2 observation/blocking 否，机械核 9 PASS/0 FAIL）。
- 分账声明：本环为零真实模型调用的证据链/规程环；无产品运行分账；最近真实批=L6
  （formal 1/1）。
- live_doc_drift: none（0 项）——本 README 证据行由 evidence_line.py 生成、
  receipt_check 复算通过；引用件哈希以实算为准。

## 一句话结论

**L8 双交付独立验收全过：L8-A 将废止链从「人读文件名后缀」升级为「存续收据
`supersedes` 后向指针+全哈希实锚」的机器可验证链（receipt_check 第 4 检查，selftest
16→25 全绿，demo 收据 6/6 实锚真实 L7 六废链，历史收据零字节改动，无字段行为 A/B
双独立实测逐字段一致）；L8-B 预注册模板立制「异常类如实申报」并自食（模板必填
1/2/3/4 在 L8 PREREG 逐字段指认全过，措辞 vs 实现零偏差，实现 0 新 raise）；
judge 11 个自构负例全拒（含 traversal/symlink/成环），auditor 对抗核声明语义 100%
落实。AUD-L7-O1 前向→后向的设计偏离在 D 封印内预先声明，双验收独立核可。**

## 一、观察

1. **时序与身份**：main `016dbfe`（PR#11 L7 集成点）→ `ccc357a`（L7 审计终稿补全
   入库，lead 代提交，provenance=合并后 auditor 13:52 重生字节）→ D1=`294aee6`
   （14:10:54，预注册封印）→ D2=`f50e31b`（14:17:45，实现）。D1 祖先于 D2。
2. **L8-A 落实**：`receipt_check.py` 新增第 4 检查 supersession——JSON 收据可选
   `supersedes=[{file,sha256}]`：恰两键、sha256 匹配 `^[0-9a-f]{64}$` 且与实算全
   哈希一致、file 相对收据父目录解析须存在、文件名须含 `VOIDED`（人机双载体）、
   禁自引/重复/成环（walk≤16）；任一违反→violation（文案带 `supersession(L8-A):`
   标记）→fail。**无该字段行为逐字节不变**（A/B 对照实测：origin/main 版 vs 修订版
   对无 supersedes 文档输出逐字段一致，judge ⑤ 与 auditor 独立各测一次）。
3. **正例（真实链实测）**：`l8-supersession-demo-receipt.json` 以 6 条
   `../L7验证器修订-2026-10-30/l7-gate-recompute-receipt-r{1..6}-VOIDED-*.json`
   全哈希实锚——`receipt_check --out` 全报告 `all_ok=true`、6/6 verified、0
   violation；`git diff 016dbfe HEAD` 于 L7/L6 两修订目录=**0 行**（历史收据
   「锚而不动」即设计意图）。
4. **独立验收**：judge 自跑 selftest 25/25、demo 复跑 ok、**自构负例 11/11 全拒**
   （路径穿越、symlink 内容寻址拒、大写/63 位 sha、多余键、缺 file 键、重复条目、
   非 VOIDED 名、非 list、自引、成环）；auditor 机械核 9 PASS/0 FAIL，对抗向量
   （恰有键/三形态自引覆盖/同文件异 sha/深度上限）逐项落实，**措辞 vs 实现偏差
   清单=零**（L7-O1 先例检查通过）；`git grep '^+.*raise'`=0 新增 raise。
5. **L8-B**：`PREREG-template.md` 立制必填清单 1 标识块/2 选题表/3 七要素（含
   **异常类如实申报**：与实现实际 raise 类逐字一致、不得猜测类名、报错文案含修订
   标记）/4 纪律承诺；L8 PREREG 自食核对 judge 逐字段指认全✓。
6. **设计偏离声明兑现**：AUD-L7-O1 原文建议废止收据上前向指针 `superseded_by`；
   L8 改存续收据后向指针 `supersedes`——终局收据文件名在废止时刻不可预知（L7 链
   r1-r6 全废、终局名无 r7 后缀实证），前向要么事后改已定稿字节（违 write-once）
   要么存空哈希（弱验证）。偏离在 D 封印 PREREG 内预先声明，judge ⑦/auditor §2
   独立核可。

## 二、证据

```text
5-评测报告/L8证据链修订-2026-10-30/verify-receipt-l8.json · e612e26e · 5077B · 2026-10-30T14:33:15+08:00
5-评测报告/对抗性盲审-L8-2026-10-30/AUDIT.md · cdcb0dcb · 8003B · 2026-10-30T14:33:15+08:00
5-评测报告/L8证据链修订-2026-10-30/l8-supersession-demo-receipt.json · 48c67684 · 1874B · 2026-10-30T14:33:15+08:00
5-评测报告/L8证据链修订-2026-10-30/l8-receipt-check-report.json · 1e5f1adc · 2568B · 2026-10-30T14:33:15+08:00
1-评测方案/工具链/evidence-kit/receipt_check.py · fde05e3f · 24933B · 2026-10-30T14:33:15+08:00
1-评测方案/工具链/PREREG-template.md · 3e99f5cd · 2640B · 2026-10-30T14:33:15+08:00
```

## 三、解释

废止链此前只有文件名后缀这一**人读载体**，机器只能靠 README 叙述+人眼比对维系链
完整性；L8 把它升级为**机器可验证的全哈希链**：存续收据单次写就锚定全部被废前置
（存在性+内容寻址+废止标记三重守卫），任何一处字节漂移即验证失败。方向选后向不是
对 O1 的折扣而是加强——前向指针在「终局名不可预知」的链上逻辑上不可全哈希化。
双工具独立验收在「仓内限定缺失」上**未经沟通收敛到同一条 observation**，说明对抗
审计的效力已覆盖规格级（实现忠实于 PREREG、而 PREREG 规格本身有欠约束处）——这类
缺陷恰是单靠实现级测试抓不到的。零新 raise 的实现形态让「异常类如实申报」条款在
L8-A 上以 violation 文案为错误面自然成立。

## 四、未排除因素（未知/观察，含影响/下一步/停止条件）

| # | 项 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| O-1 | **supersedes 无仓内限定**（judge O-1 与 AUD-L8-O1 独立收敛）：`../` 穿越/仓外绝对路径指针在四守卫（存在/VOIDED 名/全哈希/非自引）下可通过（符合 PREREG 文字规格） | 现数据全仓内零利用；内容寻址+VOIDED 双载体缓解 | 下环 PREREG 规格补「resolved 路径须在仓库根内」或明文接受（池结转） | 限定版 selftest 全绿+demo 复验 6/6 |
| O-2 | 校验器类固有窗口（AUD-L8-O2）：TOCTOU 单次校验、VOIDED 子串名检（真锚=sha 不受影响）、walk 深度≥17 理论逃逸（静默穷尽） | 单文件只读校验器不承载并发/对抗执行语义 | 不改，后续运行可检（池注释） | 类固有，记录即闭 |
| U-1 | 样本口径：本环零真实批 | L8 结论仅覆盖证据链/规程面，产品判定沿用 L6 | 后续正常批回归多槽结构 | 结构性事实，非待办 |
| U-2 | kit_selftest.py 对 L3 时代夹具 write-once 拒绝（exit 2） | 既有环境状态，非本环回归（本环 0 触及该脚本） | 夹具退役留池（沿 T22d 先例） | 未来证据-kit 夹具专项 |

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① receipt_check selftest（期望 25/25 PASS）
python3 1-评测方案/工具链/evidence-kit/receipt_check.py --selftest | tail -1
# ② demo 收据实锚真实 L7 六废链（期望 all_ok=true；--out 目标已存则去 --out 看stdout）
python3 1-评测方案/工具链/evidence-kit/receipt_check.py '5-评测报告/L8证据链修订-2026-10-30/l8-supersession-demo-receipt.json'
# ③ 历史收据零字节改动（期望空输出）
git diff 016dbfe HEAD -- '5-评测报告/L7验证器修订-2026-10-30/' '5-评测报告/L6判卷修订-2026-10-30/'
# ④ 负例速览：篡改 demo 副本 sha 后须 fail（副本放 /tmp 之外须注意 REPO 解析，直接看在档 selftest 负例组亦可）
# ⑤ 台账不变量
python3 -m unittest discover -s 4-打分细则/可信冻结-2026-10-29-v3 -p 'test_freeze.py' 2>&1 | tail -3
# ⑥ 时序
git log --format="%h %cI %s" -3 loop8-2026-10-30
```

## 附：池结转

| 池项 | 内容 | 去向 |
|---|---|---|
| supersedes 仓内限定 | O-1 规格级 observation | 下环 PREREG 候选 |
| l4/l5 现场重跑适配 | L7 U-1 结转 | 未来重跑前适配 |
| T22d 退役 | L5 锚定已知败随 L6 封存现场 | 未来 WB 新现场 |
| live-ledger freshness 对账 | L7 O-2 结转 | 专项环 |
| evidence-kit 夹具退役 | U-2（kit_selftest L3 夹具 write-once 拒绝） | 未来证据-kit 专项 |
