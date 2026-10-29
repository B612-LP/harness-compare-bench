# 对抗性盲审报告（L5）——封印链+修复 diff+凭据扫描，2026-10-30

- 审计角色：敌意审计（task-15）。纪律：零模型/零网络/**零 git 操作**（lead 指令）；只读+离线复算；写界仅本目录；truth/solution 未语义阅读；凭据仅批准 refs.DEEPSEEK_API_KEY（ASCII）内存比对，零值输出。
- 方法：机械核查 l5_audit.py（本目录）+ credential_scan/pii_min_check（沿用 L4 工具）+ 定向人工复核。封印链 git 时点核验由 lead 的 post-execution-seal-check.json（18 步）承担，本审计记录其结果并完成全部无 git 可行的独立机械核验。

**live_doc_drift: none（0 项）**

## 0. 总判定

**安全 blocking：0；历史批回写：0（红线未触）。** 封印链 D=8b1043d→E3=d8366da32694713d4f77c740f935229f9e298df4 内部一致（binding/manifest/plan/contract 哈希互证 + 23 仓内文件与外部文件逐条实算吻合 + lead 18 步 seal-check 全过）；两次中止重封（E=7474b84/E2=02a4cac2）理由有实证、时序单调、动机非分数驱动（E3 分数有升有降，独立核时序戳吻合）；修复 diff 中途最小性成立（1119 exist_ok 1 token dated）；L4→L5 全量差异含两项 **PREREG 预注册池项**（L5-3/L5-4），无未披露行为差异；凭据/PII 全量扫描零命中（含 ps 误印 Bearer 事件专项：零入库实证）。

分级计数：**blocking 0 / defect 0 / observation 2 / 受限项 2（零 git 所致，如实声明）**。

## 1. 封印链敌意核验（S1/S5）

- **binding 互证**：design_commit=8b1043d0…、preregistration_commit=execution_seal_commit=d8366da3…df4（lead 消息中 df3 为笔误，df4 与落盘 binding 一致——独立实读证实）、registered_at=2026-10-30T02:16:07+08:00。
- **manifest**：sha=a653eacb…==binding 声明；files 23 条 + external 全部存在且 sha256 逐条实算吻合（A4/A5）。
- **plan/contract**：disk sha 469a43df/944093c7 == binding == lead seal-check 的 D=E blob 等值记录（prereg blob 21cabd1e 同）。
- **lead seal-check 18 步全 ok**（含 registered-at-equals-E-commit-time：binding=git=02:16:07；ancestor D→E→HEAD；manifest required n=23；external locked）。本审计零 git，该项依落盘收据采信并如实声明。
- **受限项-1**：E3 commit 的 git 对象级复核（commit id 真实性）需 git，本审计以 binding/manifest/seal-check 三方一致 + 磁盘树哈希吻合为限，如实声明。

## 2. 两次中止重封：合法性、档案完整性、动机独立性（S2）

- **时序单调（B1）**：E1 abort 01:58:08 → E2 archive（目录名 02:07）/E2 执行 02:07:45 → E2 abort 02:15:41 → E3 registered 02:16:07。全部实读收据/binding。
- **E1（7474b84）**：WB adapter 仍 pin l4-execution gate → WB 首槽 **REFUSED 零调用**（fail-closed 生效，REFUSED 先于 claim，无残留）；gate 逐槽绑 binding.registered_at/preregistration_commit → 中途重封使在途槽失格 → 统一重封裁决成立。codex/dsh 首槽在途被 kill -9，证据原样移入 aborted-attempts-20261030T0152seal/，**有真实消耗如实披露、无 formal 资格**。
- **E2（02a4cac2）**：DSH lab.py:1119 `ev.mkdir` 缺 exist_ok（lead R2 编辑与 L4 归档块冲突）→ dab-r1 实证 FileExistsError（**档案内错误证据独立核到**，B4）；E2 已完成 4 槽（codex dab/cargo+wb bird/dab）将被 E3 失格 → 6 槽全部重跑保单封印一致批。
- **动机独立性（B2/B3）**：E2 观察分与 receipt 记录逐一吻合（codex dab 70.0/cargo 70.37037037、wb bird 100.0/dab 70.0——"记录不入结论"如实执行）；E3 终局分**有升有降**（codex cargo 70.37→74.07 升；wb dab 70→**60 降**）——降分存在直接否证"分数驱动重跑"；时序戳独立核吻合。
- **档案完整性（E1/E2 对账）**：E1 收据 files_sha256 全量对账通过；E2 收据+supplement×2 共 **187 条目、186 吻合**——唯一不符条目见 AUD-L5-O1。E2 档案 187 文件（含 codex__ev3-voided-claim 弃用声明、dsh__cargo-r1-notexec-e2）。

### AUD-L5-O1【observation】E2 abort-receipt 自引哈希条目永不可匹配
- E2 收据 files_sha256 含自身路径 `abort-receipt.json`（listed 57ccffe1…，实际 d8c176ef…）——自引哈希逻辑上不可自证；列示值对应收据定稿前某版本（discipline_note 等字段系后补），其余 **186/187 条目全部吻合**。分类：收据设计 wart + 揭示哈希计算后发生过修改（无害内容，但违"哈希即终态"直觉）。建议：未来收据不列入自身或显式 self-excluded。

## 3. 修复 diff 最小性（S3）

- **gate v2**：diff-l4-to-l5.patch 触及文件 ≤3、hunks 计数在案（C1）；宣告三处（白名单/默认目录/seal loader）与 patch 范围相符。
- **DSH lab 1119**：中途修= `ev.mkdir(parents=True, exist_ok=True)` 1 token，带 dated 注释（E2 dab-r1 教训）✓（C2）。
- **L4→L5 lab.py 全量差异 15 hunks 逐块分类**：约 8 块为 cycle identity（L4→L5 字样/路径/batch 名/spec 串/slots 6→2= L5 计划结构）；1 块=1119 修复；**2 块=池项 L5-3（ws 模型可见元数据移除：pre-run meta 改写仓内 ev/meta.prepare.json，直接消解 L4 AUD-D2 暴露面）与 L5-4（capture_session 重写：精确名+后缀退化+match_method 收据，修 L4 整线空捕缺陷）——两者均在 L5 PREREGISTRATION.md:14-15 预注册声明（修前/修后/正例/近似齐全），非未披露**；其余为收据 spec 串。结论：**无未披露行为差异**（受限项-2：E2→E3 中途工具 diff 因零 git+E2 档案无工具副本无法独立重放，以中止收据声明的 1 token+dated 注释采信，如实声明）。
- **WB runner 逐文件 diff 清单**（C3）与 **codex tools 抽查**（C4）hunks 计数在收据中，供 judge 抽阅。
- WB adapter E1 缺陷（pin l4 gate）已由 E1 中止+重封闭环；L5 适配面 l5-execution 引用核到（diff hunk :151）。

## 4. 凭据/PII（S4）

- **全量扫描**：l5-20261030-cli + wb-gateway + 中止重封档案 + L5 计划目录 + L5 判卷修订 = **486 文件，真实 key 精确命中 0**（exit 0）。收据 scan-report-l5-full-r1.json。
- **generic 8 处全归类 benign**：6× payments.csv:79769（dabstep 任务输入数据值，跨 4 份 ws/档案副本同源）；1× dsh lab.py:1903 desensitize 自检占位串（沿 L4 已知类）；1× 同行 apikey-assignment（fixture 一部分）。
- **ps 误印 Bearer 专项**：WB REPORT.md:110-111 披露「执行中一次 ps 误印产品进程命令行（含会话级 Bearer）——未入库未复述」；全 L5 目录 grep "Bearer" 仅 **1 处=该披露语句本身**（无 token 值）；专项确认**零入库** ✓。
- **config-snapshot PII**：L5 dsh 逐槽 config-snapshot/AGENTS.md 派生（30 文件）pii_min_check **0 命中**——安全派生声明抽验通过 ✓（pii-min-check-report-l5-configsnap-r1.json）。

## 5. U1 与中止对账 / WB R7（S5）

- **E3 binding/register 链**：registered_at 02:16:07 = lead seal-check 的 git 时刻记录；released=True；E 早于 verification（02:16:26）。
- **中止收据对账**：E1 全量吻合；E2 187 条目 186 吻合+1 自引（AUD-L5-O1）；supplement 1/2 纳入对账。
- **WB R7 覆盖事件**：现(E3)版 slot-accounting-frame.json 在 l5 receipts（at=02:23:11，plan_sha/design_ref 与 binding 一致）；**E2 版（git b32d844）双在档声明=受限项-2'**（零 git 无法核 git 侧副本；E2 中止档案内未含 frame 副本——如实声明，采信 lead 声明+git 可核性留给有 git 权限方）。对验收影响：frame 为 R7 覆盖披露载体，E3 版内容完整、判定不受影响。

## 6. 未知与限制

1. 零 git 限制下的三类受限项（E3 commit 对象核、E2→E3 工具 diff 重放、E2 frame git 侧副本）——均以落盘收据+磁盘树吻合为限，如实声明。
2. E2 abort-receipt 自引哈希（AUD-L5-O1）。
3. L5 plan 结构（每产品 2 槽）与 L4（每产品 6 槽）不同——按 L5 plan.json 原样核算，未做跨轮样本量推断。

## 7. 结论与计数

**blocking 0 / defect 0 / observation 2（AUD-L5-O1 自引哈希；受限项声明集合）/ 事故 0（L5 无新事故；E1 消耗已披露并入账外单列）。**
历史批零改动红线：未观察到任何回写（全量扫描与逐槽 evidence 目录核均无 L4/更早批文件异动迹象）。

## 8. 机器收据与本文件自证

- l5-audit-mech-receipt.json（A/B/C/E 系 16 PASS/2 FAIL→已分流：E2 自引=O1、lab hunks=预注册池项，均非 defect；分流理由见 §1/§3）。
- scan-report-l5-full-r1.json / pii-min-check-report-l5-configsnap-r1.json。
- 本文件 live_doc_drift: none（0 项）；证据行见下方代码块（evidence_line.py 生成，receipt_check 回验）。

## 9. 证据行（evidence_line.py 生成，2026-10-30T02:40:01+08:00）

```
5-评测报告/对抗性盲审-L5-2026-10-30/l5_audit.py · 95bccff1 · 12152B · 2026-10-30T02:40:01+08:00
5-评测报告/对抗性盲审-L5-2026-10-30/l5-audit-mech-receipt.json · 158acc6c · 3489B · 2026-10-30T02:40:01+08:00
5-评测报告/对抗性盲审-L5-2026-10-30/scan-report-l5-full-r1.json · 509e7826 · 135168B · 2026-10-30T02:40:01+08:00
5-评测报告/对抗性盲审-L5-2026-10-30/pii-min-check-report-l5-configsnap-r1.json · 57a83fea · 339B · 2026-10-30T02:40:01+08:00
```
