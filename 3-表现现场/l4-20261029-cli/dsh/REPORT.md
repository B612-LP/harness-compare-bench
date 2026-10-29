# L4 阶段 I 报告 —— DSH 六场运行器与共同严格准入工具（builder-dsh）

- 生成：脚本实钟见 `phase1/delivery-index.json`。分支 loop4-2026-10-29；设计封印 D=bb14897a7d1ac26c06697bb80a15d94158cd8ae0。
- 状态：**实现+零模型预检/合成自测完成；零真实模型/API 调用；停待 E 封印与 lead release。**
- 任务板 task-4 保持 in_progress（运行结束前不 complete）。

## 交付文件（哈希见 delivery-index，脚本生成）

| 文件 | 说明 |
|---|---|
| `tools/lab.py` | DSH runner：plan 驱动 6 槽（order 7–12：dab r1→cargo r1→cargo r2→dab r2→dab r3→cargo r3），单次派发无 whole-CLI 重启，原始流 O_EXCL 永不覆盖，dispatch/ 派发登记先持久，每槽派发前快核 external_files |
| `preflight/cli-preflight.json` | 零模型预检收据：6 槽唯一、冻结 checker 哈希==contract、外部文件基线（cordis.patch.yml/package.json/AGENTS.md）、CLI 0.2.0-rc.2、凭据 ref 在位（未打印）、workspace 根可写；`zero_model: true` |
| `selftest/runner-selftest.json` | 零模型自测收据 3/3：r1031 归档轨迹→完整流重建/逐调用 usage/完整性扫描全链路 + 脱敏函数 |
| `phase1/delivery-index.json` | 交付索引（含共享工具哈希） |

共享（`1-评测方案/工具链/l4-execution/`）：

| 文件 | 说明 |
|---|---|
| `gate.py` | 共同 gate：`verify_execution`（binding/E blob/祖先关系/manifest+external_files/必需成员集；require_release 默认 True）+ `gate_admission`（R1 真值表五层分层；先 verify 再逐场） |
| `receipts/gate-selftest.json` | gate 合成正反例 25/25（r1 留痕：hex 前缀 12 位不合规已改 8 位） |
| `replay_dual.py` + `selftest-replay-dual.json` | 双归档等价模拟 harness（母本不动；legacy r1030#1 缺陷副本内复现）自测 8/8 |
| `README.md` | 共享接口说明（已发 codex/wb，抄 lead） |

## 自测与收据合规

- gate 自测覆盖：正例全链；release 闸、缺键、registered_at≠E、D/E blob 漂移、祖先假、external 漂移、manifest 缺盘上文件、不安全路径、漏封必需成员；admission：ok+genuine-timeout 双准入（formal=2）、infra=partial 不准入、not_executed 完整记账不虚造、污染槽 0-formal 但 accounting_complete=true、虚造空流/缺记账/run_id 部分重号/admission 先 verify。
- 四份新收据全部过 evidence-kit `receipt_check.py`（all_ok=true）；`live_doc_drift` 恒 list；新路径 O_EXCL 拒写。

## 零调用证明（负面验证）

- `run --slot <真实slot>`：binding 缺席（E 前）⇒ `GateError: binding 不存在`，无进程派发；
- `notexec`：binding 缺席 ⇒ 拒绝记账（not_executed 须 D/E 引用，E 前不可记账）；
- preflight/selftest/report 路径无任何模型命令；无 `dsh <profile>` 运行调用发生。
- 纪律：测试期间曾误以 notexec 写入一个测试记账文件，已即时删除（`runs/` 现为空，无任何运行数据）；runner 随即加 binding 前置校验根除此路径。

## 行为要点（对合同）

- canonical stdout = 原始真实 `agent.jsonl`（O_EXCL 独占落盘+只读位）；`archived_stdout.full_*` 另列字段独立实算，不冒称原始流；8192/32KB 投影截断披露沿用。
- timeout=运行级结果（timed_out=true，保留首流，冻结 checker 全分母判分）；error/transport-error 保留首流+诊断（selection=null），无重试。
- 评分只机械执行冻结 checker（哈希对 contract 快照断言）；judge 计数对（correct/n_tasks）由 scored checks 推导，分母==contract.denominators 断言。
- AGENTS.md 快照脱敏（key/token/secret/password 赋值与 sk- 串替换 [REDACTED]）；凭据原值不入库。

## 待 E 后（不在本报告承诺执行结果）

1. lead release → `lab.py run --all`（plan order，单次派发/槽）；
2. 双归档重放：对每场 `replay_dual.py --run <ev>`（offline_recompute 分账）；
3. `gate.py --admission --product dsh` + runs-summary.json。


---

## v3 修复轮：timeout 停止证据原物化（2026-10-29T21:08:42+08:00）

Lead 判据收紧：genuine timeout 不得仅凭 duration+outcome/stop_source 字符串。修前 snapshot 首版记录=phase1/snapshot-pre-termination-gate.json（gate f8a4ca08 / lab e221c1fe）。

- runner：stop_process_group 返回 verified_stop（仅观察到受控退出=true；组消失等未观察=false）；ev/termination-receipt.json O_EXCL 原物落盘；meta.termination_receipt={file,sha256,verified_stop} 绑定；emergency_partial 同步携带。
- gate（cli 层）：termination-receipt.json 原物存在+sha==绑定+verified_stop is True+signal∈{SIGTERM,SIGKILL}+at/ack_at 时点，且 attempts[0].outcome=="timeout"、duration_s≥slot.timeout_s——四者合取才 genuine；verified≠true ⇒ formal=false（codex signal-0 权限受限场景自动落在拒收侧）。
- gate（wb 层）：只认 meta.native_stop 同构信封（file/sha256/verified_stop），CLI receipt 不被接受（防跨层穿透）。
- runner_formal_eligible（codex 内部字段）不为 gate 输入——gate 只认原物+绑定（已复函 codex）。
- 新增负例：atk9 伪造 timeout（无 receipt 原物）拒；atk10 receipt sha 篡改拒；atk11 WB 借 CLI receipt 拒。gate 自测 **39/39**；runner mockrun r2 **5/5**（timeout 世界经原物路径准入）。


---

## v4 修复轮：组级确认终止 + S6 replay 诚实重写（2026-10-29T21:27:09+08:00）

- **组级终止协议（lab.py c6366d94）**：TERM → 先收父（zombie 组长会使探活呈 EPERM）→ 轮询仅 ESRCH 计确认 → EPERM 歧义仅在 allow_escalate 时以 KILL 判别器消解（对空组 killpg(SIGKILL)=ESRCH 证实）→ 组级确认才 verified_stop=True。真实父子回归（父收 TERM 即退、子忽略 TERM 持续写）6/6：TERM-only 父退组活 verified=False（旧 proc.wait 实现的反例被钉死）、KILL 升级后组确认消失且子进程实测停写。termination-selftest r1–r6 留痕。
- **S6（replay_dual.py 61fcd9f0）**：current.full_stream 实际重建（events/bytes/sha 实测，不以目录存在冒充）；legacy usage=unknown（旧管线读已丢 log，不从会话补造）；双侧 score=not_evaluated（harness 不跑 checker，无任何分数不变声称）。自测 10/10（r3 收据；r1/r2 留痕）。
- codex close_process_group（42df0400）已只读参考（delivery/probe 分离）；未共享文件、无跨产品依赖；reviewer 真实父子判据以本方回归独立满足。
- 全套现行计数：gate 43/43（56a3f534）、mockrun 5/5（r7）、termination 6/6（r6）、replay 10/10（r3）、runner selftest 3/3（r3）、preflight r1（拒写复跑为预期）。收据全过 receipt_check。


---

## v5 修复轮：runtime 闭包 + receipt 身份绑定 + WB native checks（2026-10-29T21:43:28+08:00）

- **runtime 闭包（lead/reviewer runtime 条件）**：verified_stop=false ⇒ run_slot 立即早退——只冻结首流/prompt/termination receipt（workspace 疑似仍在写入，不冻结不称完整），score=null（checker 调用 0），持久 halt 标记 halt.json（跨进程拒一切后续 slot 派发）。真实 mock（mockrun 世界5）：verified=false 注入 → checker_calls=0、CLI 派发 Popen=1（无后续）、halt.json 在位、下一 slot cmd_run=3、gate formal=false + accounting_complete=false。mockrun 7/7（r13）。
- **receipt 原物身份绑定四项（gate 46→47 项电池）**：①doc.slot_id==meta/plan（挪用他场拒，atk14）；②doc.pgid==attempts[0].pgid（spawn 时 start_new_session 启动即取，pid 同核，atk15）；③doc.at≥started_at（时序起点）；④meta binding 与 doc 的 verified_stop 双说矛盾显式拒（atk16）——runner 侧 binding 已移除非权威 bool（权威在 doc 原物）。
- **WB native_stop 契约落 gate**：native-stop.json 信封（file/sha256）+ slot_id 绑定 + verified_stop=true 时 checks{db_terminal,trace_stable,no_scoped_processes} 三项全 true 才确认；双说矛盾拒；verified=false 仍写收据（区分"未验证"与"缺证据"）。atk17 负例在测。
- **replay 诚实命名**：partial_text_usage_projection（text/usage 部分投影，scope 明示缺 reasoning/tool 事件，非 full_stream）。自测 10/10（r5）。
- 现行全套：gate **47/47**（b76208cf）、mockrun **7/7**（r13，lab cf116ff8）、termination 6/6（r7）、replay 10/10（r5）、runner selftest 3/3（r4）。收据全过 receipt_check。


---

## v6 修复轮：组闭包扩展到全部已执行正式候选（2026-10-29T21:53:05+08:00）

- **runner（2a378846）**：正常/错误退出路径同样先组闭包确认再归档判卷——组已消失（ESRCH）⇒ normal_exit 探针证（signal=None 合法，不发无谓信号）；组仍活（父退子存）⇒ 有界清理 TERM→KILL→组级确认后才继续。任一 phase verified=false ⇒ 早退 partial（score=null、workspace 不冻结为完整产物）+ 持久 halt 拒后续 slot。
- **gate（3987b172）**：所有已执行 formal 候选（ok/timeout）须 termination receipt 原物 + verified 组闭包（normal_exit 允许 probe=verified_gone 且 signal=None；其余须合法 signal）；timeout 另守 duration≥时限+outcome。atk18（ok 无 receipt）拒。
- **termination-selftest r8：8/8**——新增场景 C（父正常 exit0+子忽略 TERM 活：清理后 verified=True、child 实测停写）、D（普通正常退出：探针证、无信号）。真实父子样本，非 stub wait。
- 现行全套：gate **48/48**、mockrun **7/7**（r14）、termination **8/8**（r8）、replay 10/10（r5）、runner selftest 3/3（r4）。收据全过 receipt_check；index v7。


---

## v7 修复轮：W13（2026-10-29T22:06:18+08:00）

judge W13：WB 正常 completed 产物被"status=ok 但 exit_code=None≠0"误拒。
- gate：exit_code==0 硬门仅限 CLI（slot.stratum 区分）；WB completed 须 meta.native_terminal={file,sha256} 绑定原生终态原物（doc：slot_id/terminal=true/state="completed"/verified_at）——活动态/错误态拒（W13-2/3 负例），completed+None 全门正例（W13-1）。gate 自测 **51/51**。
- 契约已同步 wb-probe（native-terminal.json 字段集）。全套回归：mockrun 7/7（r15）、termination 8/8（r9）、replay 10/10（r6）、runner selftest 3/3（r5）、gate-rc=0；收据全过 receipt_check；index v8（gate 77d8e8b4 / lab 2a378846）。


## v8（2026-10-29T22:4x+08:00）reviewer final-v4 后两处 runtime 分支修复 + lead 校准

- **normal-exit 组未证实分支（~:881）**：`dict(termination,…)` 在 termination=None 时 TypeError；且共用 partial 逻辑硬编码 status=timeout/timed_out=true 伪造正常退出。修复：以 effective_stop（timeout→termination，否则 closure）为 receipt 基对象；保留实际 phase/status/underlying returncode（exit_code）；仅真实 timeout 才 timed_out=true；组未证实的 normal 分支 = status=error + partial + score null（不假 timeout）。
- **Popen OSError 分支（~:853）**：proc/launched_pgid 未初始化即被 closure 段引用 → NameError 丢记账。修复：先初始化 None；Popen 抛出 = 进程从未存在 → 首槽 not_executed 记账（真实 reason+封印引用，无 started/session/usage/score，infra 分类不涉模型成败）。批级处置=政策选择（lead 校准 2026-10-29：停后续或继续其他固定槽均可，硬要求=首槽有效记账+不重复同 slot/不漏记）；本 runner 取保守 halt。
- 新增 mock 世界 6/7（真实错误支路）：6=正常退出+closure verified_stop=false（status=error、exit_code=0 保留、phase=post_exit_cleanup、receipt 原物、checker 0、Popen 1、halt、next 拒）；7=spawn OSError（notexecuted.json 有效性四要素、无 meta/无原始流文件、halt、next=3）。mockrun 9/9（r17）；termination 8/8（r11）；selftest 3/3（r7）；gate 51/51 未动。收据全过 receipt_check。


## v9（final，2026-10-29T22:5x+08:00）三项收尾 + PII 派生快照脱敏

- **OSError 捕获分流**：spawn 捕获仅围 Popen（抛出=进程从未存在→首槽 not_executed+保守 halt）；已启动后的运行期 OSError（proc 非 None）→ 必要组停止（有界）+ 真实 partial（class=runtime-oserror-post-launch、真实异常与 phase、score null、无 checker）；停止未证实⇒halt。不误记 not_executed、不把 spawn/运行期异常扩成模型成败声称。
- **setsid 覆盖边界披露**：judge S6 实证组确认≠所有脱组写者。meta 与 termination-receipt 增 residual_disclosure（group_coverage=仅被派发 pgid、host_guarantee=none、probe=workspace-growth-two-sample、policy=仍在写⇒conservative partial）；组确认后执行停后双采样增长探针，检出仍写⇒翻转 verified_stop=false 走 unverified partial（无 checker+halt）。原组 4/4 真实判据未动，未伪造 times。
- **公开派生快照 PII 脱敏**：desensitize_text 增 PII 标签行级规则（name/student-id/class/affiliation，标签词以 \u 转义写入源码，机械扫描字面标签 0 残留）；config-baseline/config-snapshot/AGENTS.md 以 snapshot_config 安全派生重写（真实运行将同样派生，非手改单文件）；raw_source_sha256=d343bcc3…（内存确定性重建，PII 派生物已销毁不留仓）；public_redacted_sha256=5786a0ef…；~/.dsh/AGENTS.md 原件与 external_files 哈希口径不变。pii_min_check 全批 0 命中（exit 0，46 文件）；台账 config-baseline/pii-redaction-log.json。
- **世界 8**：运行期 OSError mock（选择性包装 build_cmd 派发，_EioProc 补 wait/poll/send_signal 代理）。mockrun 10/10（r20）·termination 8/8（r15）·selftest 3/3（r10）·gate 51/51 ·replay 10/10（r9），收据全过 receipt_check。


## v10（2026-10-29T23:1x+08:00）JSON 收据字节展示适配（lead 指示，receipt_check 停写移交 lead）

- 触发误报定位：仅 DSH 侧三份现行收据的 JSON `evidence.lines[].line` 字段（r20:71/r15:61/r10:47，lab.py · 671630d5 · 105009 bytes 段）；JSON 内嵌行不走 checker canonical 解析，落入通用 hex 扫描。gate/replay 收据无此模式。
- 修复=lab.py 增 `ek_json()` 展示适配（JSON 内嵌 line 字节段改"N bytes"；结构化字段与 evidence_line.py canonical 原格式不动），4 处 embed 包装。receipt_check.py 的宽放豁免已停写移交 lead 回退。
- 收据重生成：mockrun 10/10(r21) · termination 8/8(r16) · selftest 3/3(r11)；按原规则（无豁免）模拟扫描全部现行收据/index/台账 PASS。
