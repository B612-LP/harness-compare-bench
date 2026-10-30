# L9 综合结论（2026-10-30）——台账账实对账制度化与废止链根约束

- 数据基座：judge 独立验收收据 `5-评测报告/L9台账对账与根约束-2026-10-30/verify-receipt-l9.json`
  （sha256 `09793d88cb44fd6653a90bdd6b612ff17c419897c7a6c7770acf212daae248d1`，8/8 PASS）
  与 auditor 盲审 `5-评测报告/对抗性盲审-L9-2026-10-30/AUDIT.md`（0 缺陷/0
  observation/blocking 否，机械核 12 PASS/0 FAIL）。
- 分账声明：本环为零真实模型调用的证据链/规程环；无产品运行分账；最近真实批=L6
  （formal 1/1）。
- live_doc_drift: none（0 项）——本 README 证据行由 evidence_line.py 生成、
  receipt_check 复算通过；引用件哈希以实算为准。

## 一句话结论

**L9 双交付独立验收全过：L9-A 以第 5 守卫关闭 L8-O1（supersedes resolved 目标须落
`--root` 根内，judge 自构归一化穿越/根外绝对/多级 symlink 链/unicode 变体 4/4 全拒，
L8 demo 收据默认根复验 6/6 历史复算零回归）；L9-B 把台账账实对账制度化
（`ledger_reconcile.py` 内容 sha256 考古口径，21 事件=20 FRESH + 1 HISTORICAL
@8edc58f / 0 UNRESOLVED——账实完全一致，L6 更正事件 locator「父提交可考」声明经
双工具独立考古核可为真），并以 test_freeze 第 49 项不变量常设化。过程中预检假发现
（F-1：blob sha1 冒比 content sha256 致误判「不可考」）在实现前经 D 补正一作废，
D→补正→D2 时序与 append-only 经双工具独立核验，实现零成本拦截。**

## 一、观察

1. **时序与身份**：main `ac36ab7`（PR#13 模板 v2 集成点）→ D=`cda92f5`（14:53:56，
   v2 模板首环含必填段 0）→ **补正一=`5fcd3f2`（14:56:17，实现前 append-only
   19+/0-，作废预检假发现 F-1）** → D2=`295f2c7`（15:04:42，实现）→ 收口。D→补正
   间无夹层提交（auditor 独立核）；补正前落盘面为零。
2. **v2 模板首环自食**：§0「老师反馈对照」8 行逐条（#1-#7+覆盖声明），judge ⑦ 与
   auditor §6 独立指认；#1 运行时留痕以「结构性不适用（零新运行）」如实声明。
3. **L9-A 落实**：`validate_supersession` 第 5 守卫——resolved 目标必须落在 `--root`
   根内（`==root_r or root_r in parents`；symlink 经 resolve() 判定）；selftest
   25→29 全绿；violation 文案带 `(L9-A)` 标记。judge 自构逃逸 4/4 全拒；仓内兄弟
   目录（demo 同形态）不误伤；无字段 A/B（修前版取 ac36ab7）逐字段一致。
4. **L9-B 落实**：`ledger_reconcile.py` 三态分类（FRESH/HISTORICAL/UNRESOLVED），
   HISTORICAL=**内容 sha256 考古**（`git cat-file blob` 管入 sha256，明文禁 blob
   sha1 冒比）；结构核（id 唯一/ts 单调/registered_at 时区）；`--repo` 非 git 根
   exit 2（防 HERE.parents 深度错位——工具自身开发期真实踩中一次并被该自检口径
   当场定位，修复留痕）；test_freeze 48→49（新增账实不变量，既有 48 断言零改动，
   auditor diff 纯追加核）。首跑 21 事件=20 FRESH + 1 HISTORICAL（l6-correction
   @8edc58f）/0 UNRESOLVED。sidecar 制度立：自 L9 起 correction 类事件 source 须
   FRESH-on-disk（被更正字节先以 sidecar 副本入盘再登记）。
5. **假发现-补正事件链（本环方法论核心）**：预检以 `git rev-parse c:path`（git blob
   sha1）比对 sha256 前缀——两哈希体系不可互比，「不可考」属必然产出；D 封印后
   lead 复核识破，内容 sha256 重考（`git show 8edc58f:… | sha256` 双工具独立实跑
   =`f73e2dc3…` 精确吻合）→ 补正一在实现前作废 F-1 并修订预期（20+1/0、allowlist
   初始空、考古口径钉死）。auditor 先例质量评估：vs L6 E1/E2 废封（实现中止+重封），
   本环实现前零成本拦截，且假发现转为 §0-#5 教训实例与观察项。
6. **双验收**：judge 8/8 PASS（含双 selftest 29/29+10/10、独立考古复算、临时 git
   夹具三态分类复现）；auditor 0 缺陷/0 observation、机械核 12 PASS/0 FAIL、红线
   全绿（CHANGELOG diff=0；registry 自 D2 后 0 再变；新增 25 文件凭据/PII 全零）。

## 二、证据

```text
5-评测报告/L9台账对账与根约束-2026-10-30/verify-receipt-l9.json · 09793d88 · 4056B · 2026-10-30T15:17:56+08:00
5-评测报告/对抗性盲审-L9-2026-10-30/AUDIT.md · 2595f388 · 8028B · 2026-10-30T15:17:56+08:00
4-打分细则/可信冻结-2026-10-29-v3/ledger-reconcile-receipt-l9.json · 1694e3e0 · 6096B · 2026-10-30T15:17:56+08:00
5-评测报告/L9台账对账与根约束-2026-10-30/l9-receipt-check-selftest-receipt.json · a2b9774f · 5213B · 2026-10-30T15:17:56+08:00
5-评测报告/L9台账对账与根约束-2026-10-30/l9-ledger-reconcile-selftest-receipt.json · f18b8c14 · 2285B · 2026-10-30T15:17:56+08:00
5-评测报告/L9台账对账与根约束-2026-10-30/l9-demo-recheck-report.json · c6d32baa · 2568B · 2026-10-30T15:17:56+08:00
1-评测方案/工具链/evidence-kit/receipt_check.py · ecfc07de · 28122B · 2026-10-30T15:17:56+08:00
4-打分细则/可信冻结-2026-10-29-v3/ledger_reconcile.py · 55ae5153 · 12595B · 2026-10-30T15:17:56+08:00
```

## 三、解释

L7-O2 提出「台账新鲜度对账」时，真正的风险不是漂移本身（live_doc 钉本就允许演化），
而是**漂移不可解释**——登记时刻的声明事后无法复核。L9-B 把「可解释」制度化：对盘
一致为 FRESH；漂移但内容 sha256 可考于 git 历史为 HISTORICAL（账实链完整）；两者皆
非即 UNRESOLVED（账实断裂，不变量红）。假 F-1 事件反而是本环最值钱的一课：lead 的
预检同样在对抗面内——跨哈希域比较是可复算工具的典型自检盲区，若未在实现前拦截，
会沿着错误发现修一台账、写一份错误的 sidecar 制度甚至回改历史事件。D 补正一的
append-only 处置（不改原 §5 字节、全文留痕）使「预注册错了」本身也成为可审计事实。

## 四、未排除因素（未知/观察，含影响/下一步/停止条件）

| # | 项 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| O-1 | L8-O2 残余逃逸面收窄为「根内 VOIDED 文件名+正确 sha」 | 理论面，现数据零利用（内容寻址为主锚） | judge 已闭项记录，无需动作 | 无（闭项） |
| O-2 | HISTORICAL 分类依赖修前字节曾经入 git | 从未入 git 的更正前态只能 UNRESOLVED | sidecar 制度已立（L9 起 correction 事件 source 须 FRESH-on-disk） | 下个 correction 事件按规则登记即证 |
| U-1 | 样本口径：本环零真实批 | L9 结论仅覆盖证据链/规程面，产品判定沿用 L6 | 后续正常批回归多槽结构 | 结构性事实，非待办 |
| U-2 | kit_selftest 对 L3 时代夹具 write-once 拒绝（exit 2） | 既有环境状态，本环 0 触及 | 夹具退役留池 | 未来证据-kit 专项 |

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① 双 selftest
python3 1-评测方案/工具链/evidence-kit/receipt_check.py --selftest | tail -1        # 29/29 PASS
python3 4-打分细则/可信冻结-2026-10-29-v3/ledger_reconcile.py --selftest | tail -1  # 10/10 PASS
# ② 台账账实对账（期望 20 FRESH + 1 HISTORICAL@8edc58f，all_resolved=true）
python3 4-打分细则/可信冻结-2026-10-29-v3/ledger_reconcile.py | tail -8
# ③ 独立考古一行（内容 sha256 口径；期望输出 f73e2dc3…）
git show 8edc58f:4-打分细则/可信冻结-2026-10-29-v3/work-registry-live.json | shasum -a 256
# ④ L8 demo 收据默认根复验（期望 all_ok=true）
python3 1-评测方案/工具链/evidence-kit/receipt_check.py '5-评测报告/L8证据链修订-2026-10-30/l8-supersession-demo-receipt.json' | tail -6
# ⑤ 台账不变量（期望 49/49 OK）
python3 -m unittest discover -s 4-打分细则/可信冻结-2026-10-29-v3 -p 'test_freeze.py' 2>&1 | tail -4
# ⑥ 时序
git log --format="%h %cI %s" -4 loop9-2026-10-30
```

## 附：池结转

| 池项 | 内容 | 去向 |
|---|---|---|
| l4/l5 现场重跑适配 | L7 U-1 结转 | 未来重跑前适配 |
| T22d 退役 | L5 锚定已知败随 L6 封存现场 | 未来 WB 新现场 |
| evidence-kit 夹具退役 | U-2（kit_selftest L3 夹具 write-once 拒绝） | 未来证据-kit 专项 |
| ~~live-ledger freshness 对账~~ | **L7-O2 已闭合（L9-B）** | — |
