# L5 综合结论（2026-10-30）——E3 批 6 槽正式判定与四份独立产物合成

- 数据基座：judge 独立验收收据 `5-评测报告/L5独立验收-2026-10-30/verify-receipt-l5.json`（sha256 `a05dafca6b7f5bb36f55ab770f1db4e51aea630ce9e4a38ca12f7561dff97d05`）与 `canonical-gate-admission.json`（sha256 `1f91a24be2fbe308c72c383b0ecac53d8a8450f8651c6ac26ee99f57e3d3a50e`）；合成对象另含 auditor 对抗性盲审（AUDIT.md，sha256 `672a3910ef8ac9b4f437ce9955e6ac7784dd41c8938c09a7d3d47ee0803561ea`）、independent-reviewer 干净环境独立复核（README sha256 `8845bda94112f7487adfff133db978631b6dcdffca888efbb38d0e818217963a`；主收据 independent-check-02.json sha256 `3354fc528d85ec0583917455dc78adf369b80ce6abe7298f0586acdc8b3566ed`）、lead 六账 `six-ledger.json`（sha256 `0ff7a90c595078ba135820ad9dbfc1d8bb593fbae72222fce6640003196af5ef`，本结论所引全部 sha 均为撰写时实算）。
- 分账声明：本文档属「判卷回归/离线复算」类合成结论；正式比较表只纳入规则冻结、证据有效、题面有效、无污染的运行（即 5 个 formal=True 槽）。

## 一句话结论

**E3 单封印批 6/6 槽 executed，canonical 准入 formal 5/6；wb-bird 因 checker 判分文档缺 guards_used/n_tasks 缺省字段按「unknown 不折满」如实不给 formal（raw 100.00000000 保留为 observed，判分缺省非基础设施问题）；封印链 D=8b1043d→E3=d8366da3 内部一致，两次中止重封动机为封印一致性而非分数驱动，已由三方独立证实；全部已知未知均有影响/下一步/停止条件，无阻塞项。**

## 一、观察

1. **产品运行（正式）**：E3 批（binding registered_at=2026-10-30T02:16:07+08:00，preregistration_commit==execution_seal_commit=`d8366da32694713d4f77c740f935229f9e298df4`）6 槽全部 executed，canonical gate v2（sha256 `38b42a87c30c87d277f0a8984c4300919da3867826790a01fd24af6766b05ce9`）判定 **formal 5/6**：

| 槽 | 独立复算分数（8dp） | formal | 判定依据 |
|---|---|---|---|
| codex-dabstep-payments-10-r1 | 70.00000000 | True | fails=[] |
| codex-tb-cargo-plan-r1 | 74.07407407 | True | fails=[] |
| dsh-dabstep-payments-10-r1 | 70.00000000 | True | fails=[] |
| dsh-tb-cargo-plan-r1 | 70.37037037 | True | fails=[] |
| wb-dabstep-payments-10-r1 | 60.00000000 | True | fails=[] |
| wb-bird-ca-schools-15-r1 | raw 100.00000000（observed 保留） | **False** | guards_used 缺失→无法按 guard 重算；partial 记账（unknown 不折满） |

builder 自报分数与 judge 独立复算全部一致。bird 判分缺省系 checker 文档字段缺省（judge.correct=15 有值而 n_tasks/guards_used 缺省），非基础设施故障。

2. **封印链与中止**：D=`8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825` → E3=`d8366da3…df4`，binding/manifest/plan/contract 哈希互证一致；两次中止重封——E=`7474b84…`（WB adapter 仍 pin l4-execution gate，WB 首槽 REFUSED **零调用**，fail-closed 先于 claim 生效）与 E2=`02a4cac2…`（DSH lab.py:1119 `ev.mkdir` 缺 exist_ok，dab-r1 实证 FileExistsError，已完成 4 槽将被 E3 失格）——**动机均为封印一致性而非分数驱动**：E2 观察分与在档 receipt 逐一吻合，E3 终局分有升有降（codex cargo 70.37→74.07 升；wb dab 70→60 降，降分直接否证分数驱动假说，auditor §2 独立核时序戳）。E1/E2 全部真实消耗（E1 codex/dsh 首槽在途 kill -9；E2 codex×2 ok、wb×2 ok、dsh dab partial(error)、dsh cargo not_executed）单列披露、**无 formal 资格**。

3. **修复验收点逐项**（R 系）：
   - **R1 发射字段**（judge 六槽）：inputs_verification.ok=true、meta.judge{checker_sha256==contract, guards_used, correct, n_tasks}、score.checker_sha256==contract、reported/meta.weighted 全 8dp——bird 缺省项如实记录；
   - **R2 中途修复**：DSH 1119 exist_ok 1-token dated 修（E2 dab-r1 教训），auditor 判最小性成立；
   - **R3（DSH×2）**：session_capture.match_method=**exact×2**、capture 非空、usage 非整线 null——L4 整线空捕缺陷修复确认（池项 L5-4）；
   - **R6（WB×2）**：renderer_ready 在 meta（均 ready/0.0s/1poll）；
   - **R7（WB）**：slot-accounting-frame（at=02:23:11）两槽 frame actual 非 null（executed+真实 score）、write-once 副本 6 件；wb bird insufficient_fields → gate 语义 partial，judge 不补值不放水。

4. **判卷修订复算影响（R4/R5）与双确认**：gate v2 对 L4 冻结 17 行复判 **17/17、唯一差异=bird 白名单 fail 消失**（与 L4 L5-8「gate 过严误报」裁定互证，formal 仍 0/17 如实）；cache-mapping-v2 复算 18 槽+28 断言+6 单元例全过、responses erratum 逐槽比对成立。**双独立确认**：independent-reviewer 原样脚本复跑 exit 0（r4-acceptance/r4-history/r5-mapping 三案）并逐字段等于在档收据；auditor 独立核封印链与中止档案。

5. **对抗性盲审计数**：blocking 0 / defect 0 / observation 2 / 受限声明 2（零 git 所致）。486 文件凭据扫描真实 key 零命中；ps 误印 Bearer 专项零入库（全 L5 仅披露语句本身命中）；config-snapshot PII 0 命中。

6. **干净环境独立复核**：**401/402 成立**，唯一失败=同一 E2 abort-receipt 自引哈希（记录 57ccffe1… vs 实算 d8c176ef…、24063B）——与 auditor AUD-L5-O1 **双独立互证同一 wart**；E3 绑定 D/E3/磁盘三方一致（reviewer 经 git 只读命令核到 committer 时刻==registered_at，输出哈希在案）；输入保护 815 项起止重哈希无变化。

## 二、证据

- judge：`L5独立验收-2026-10-30/`（README+verify-receipt-l5+canonical-gate-admission+u1-sealed-content-check+per-slot-emission-checks；evidence-kit 自检全绿）。
- auditor：`对抗性盲审-L5-2026-10-30/AUDIT.md`+l5-audit-mech-receipt.json+scan-report-l5-full-r1.json+pii-min-check-report-l5-configsnap-r1.json。
- reviewer：`L5独立复核-2026-10-30/`（README+independent-check-01/02+三案复跑收据+whitelist 负例）。
- lead：`L5综合结论-2026-10-30/six-ledger.json`（六账：product_run 6/6 executed·formal 5/6、judge_independent 引本验收收据、grading_regression、offline_recompute、self_test、interface_preflight、bare_model_probe 0/0、incidents 2 项处置、aborted_attempts_disclosure）。
- 封印与计划：binding sha256 `7ee8b689b002b222e7d8faf15d83f57395ad7b290486287dc3b8f381a9fe446a`；R4 收据 sha256 `a980fdc7069988187cd2ed2a2afe1e063dc9d59ecaf99b8be48ffe81e05d5149`；R5 收据 sha256 `895e2657ddacdbaac8886b79e4c1f6a364ab9a55ded471504248e85aa55fe7ae`。

## 三、解释

bird 的 formal=False 是合同「unknown 不折满」语义的机械执行：checker 输出缺 guards_used/n_tasks 缺省字段时，gate 无法按 guard 重算 earned/possible，任何补值或按已评部分折满都会破坏预注册判据——故 raw 100.00000000 保留为 observed 而正式资格不给，且该缺省属判分文档字段问题而非基础设施或执行故障。两次中止重封在 gate 逐槽绑封印的设计下是**唯一保批一致的选择**（中途换封使在途槽失格）；其动机独立性由「E3 分数有升有降+观察分与在档 receipt 吻合+时序戳独立核」三角证据支撑。R4 唯一投影差异（bird 白名单 fail 消失）恰好验证了 gate v2 修复的正确方向，同时 formal 0/17 不变说明修复未改变历史批判定实质。

## 四、未排除因素（未知，含影响/下一步/停止条件）

| # | 未知 | 影响 | 下一步 | 停止条件 |
|---|---|---|---|---|
| U-1 | **bird checker 文档缺 guards_used/n_tasks 缺省字段** | wb-bird 无 formal 资格，raw 100 不可计入正式比较表 | builder 补 checker 判分文档缺省字段输出→重封新批复跑 bird 槽 | 新批 gate 判定 formal=True 且 guards 重算与 raw 一致；或明确放弃该槽并保持 observed 单列 |
| U-2 | **R7 cmd_accounting 覆盖事件修复后置**（runner :2075 write_json_atomic 覆盖 E2 frame；E2 版可经 git b32d844 恢复） | 仅 E2 档案 frame 新鲜度，不影响 E3 判定 | 一行修复 write_json_once 随下次重封 pin（lead post-admission 提交）；有 git 权限方执行恢复并留证 | 修复版 runner 重跑后 receipts 全部 write-once 且 E2 版恢复件哈希在案 |
| U-3 | **AUDIT 受限声明 2 项**（E3 commit 对象级核、E2→E3 中途工具 diff 重放均需 git） | 两项以落盘收据+磁盘树吻合为限采信 | 有 git 权限方按 reviewer check-02 的 git 只读命令清单复算（输出哈希在案可直接比对） | 复算输出哈希与 reviewer 记录一致即闭项 |
| U-4 | **E2 abort-receipt 自引哈希 wart**（AUD-L5-O1，双独立互证：记录 57ccffe1… vs 实算 d8c176ef…） | 不等于中止证据失效（其余 213/214 项吻合）；但「哈希即终态」直觉被破坏 | 未来收据不列自身或显式 self-excluded 字段（收据设计 wart，入池）；不改写原收据 | 新收据模板含 self-excluded 且 receipt_check 增对应规则 |

另如实记录：L5 plan 结构（每产品 2 槽）与 L4（每产品 6 槽）不同，本文不做跨轮样本量推断；E1 WB 首槽 REFUSED 先于 claim，无残留调用。

## 五、可复现实验

```bash
cd /Users/b612-lp/Documents/harness-compare-bench
# ① canonical 准入复跑（示例 codex；dsh/workbuddy 同理）
python3 -c "import importlib.util;from pathlib import Path;s=importlib.util.spec_from_file_location('g','1-评测方案/工具链/l5-execution/gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);print(g.gate_admission(Path('1-评测方案/自动循环L5-2026-10-30/runtime-binding.json'),'codex',repo=Path('.'),plan_dir=Path('1-评测方案/自动循环L5-2026-10-30')))"
# ② judge 机器收据自检（应全绿）
python3 1-评测方案/工具链/evidence-kit/receipt_check.py 5-评测报告/L5独立验收-2026-10-30/verify-receipt-l5.json
# ③ 判卷修订复算收据复核（R4/R5，原样脚本复跑见 reviewer 目录三案）
python3 5-评测报告/L5独立复核-2026-10-30/run_reproductions.py --help
# ④ E2 自引哈希差异复现（唯一 402 分歧点）
python3 -c "import hashlib;from pathlib import Path;print(hashlib.sha256(Path('3-表现现场/中止重封档案E2-20261030T0207/abort-receipt.json').read_bytes()).hexdigest())"
```

## 附：L5 池结转项

| 池项 | 内容 | 建议处置 |
|---|---|---|
| L5-P1 | bird checker 文档补 guards_used/n_tasks 缺省输出 | builder 修复+重封复跑（对应 U-1） |
| L5-P2 | WB runner cmd_accounting 改 write_json_once（lead post-admission 提交） | 一行修复随下次重封 pin（对应 U-2） |
| L5-P3 | AUD-L5-O1 收据自引设计 wart（双独立互证） | 收据模板 self-excluded+receipt_check 规则（对应 U-4） |
| L5-P4 | ps 操作规程加固（ps 误印 Bearer 事件，零入库已证实） | 运维规程条目化，杜绝敏感命令行打印 |
