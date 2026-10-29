# REPORT — l4-20261029-wb-gateway 阶段 I（实现 + 零模型预检/合成测试）

> **更正（2026-10-29T20:35+08:00，lead 源码审查后 dated 更正）**：首版报告所述「主运行器 ✅」
> 实为**框架版**——`run-slot` 真实执行体未实现（gate 通过即 return 0）、`verify_execution`
> 为弱化本地副本且接口方向反了、meta `tools` 误为 str、未接共同 gate validator。两项
> E-release blocker 已按审查意见在本版修复：①完整 send/poll/timeout/trace/archive/checker/
> accounting 实现并以 mock 驱动全路径干跑证实；②改为**调用共同 gate**
> （1-评测方案/工具链/l4-execution/gate.py）的薄适配层，缺共同 gate 或任一封印检查失败即
> 零调用；meta 经共同 gate 的 validate_meta+classify 机械验证（带 seal → pass、issues 空）。
> 首版收据原字节保留于 `receipts/v1-skeleton-archive/`（不覆盖）；v2 收据为本版产物。

- 执行者：wb-probe（task-6，in_progress 保留至运行结束）
- D 封印：`bb14897a7d1ac26c06697bb80a15d94158cd8ae0`；规则版本 `l4-20261029-batch-v1`
- 本阶段模型调用：**0**；未建任何题会话；未启动 WB；未改任何网络/代理/keychain/settings/更新配置

## 一、交付（v2，阻断项已清）

| 项 | 文件 | 状态 |
|---|---|---|
| 主运行器（完整 run_impl：workspace→登记→ensure→send→poll/timeout→collect→污染扫描→usage→checker→meta→accounting） | `runner/l4_wb_runner.py` | ✅ |
| 结构性禁用 SIGTERM 的 driver 包装 | `runner/safe_driver.py` | ✅ |
| 共同 gate **薄适配层**（方向已纠正：runner 调 gate；缺 gate/GateError 即零调用） | `runner/verify_execution.py` | ✅ |
| `verify_execution(binding_path)` 接口 | runner 内 `binding_gate()`；共同 gate `--admission` 为正式准入裁判 | ✅ |
| driver 快照 pin | `driver-snapshot/`（SHA256SUMS；E 时另核仓外原件） | ✅ |
| 零模型静态预检收据 v2 | `preflight/preflight-static.json`（29 检查全过，含 common_gate_present，receipt_check all_ok） | ✅ |
| 合成正反例收据 v2 | `selftest/selftest-receipt-l4-wb-v2.json`（24/24 过，receipt_check all_ok） | ✅ |
| R1 记账帧 | `receipts/slot-accounting-frame.json` | ✅ |
| 干跑全路径产物（mock） | `selftest/dry-ws-*/…`（meta/score-receipt/registrations/slot-accounting） | ✅ |
| 首版（骨架）收据存档 | `receipts/v1-skeleton-archive/`（3 件，字节不动） | ✅ |

## 二、selftest v2 覆盖（24 项，全部机械验证）

- T1 结构性禁用三分支（stub，零真实交互）：复用/干净启动/无端口 → `WBUnsafeState` 无 kill 路径。
- T2 共同 gate 适配 fail-closed：binding 缺失 → ok=false；**gate `--selftest` rc=0**（与 builder-dsh 机制联动）。
- T7 **mock 驱动全路径干跑**（fake-case 夹具，零真实 WB 交互零调用）：status=ok；attempts 恒 1（whole_execution_restarts=0）；weighted 8dp；usage 从 trace 解析（rawUsage 缓存 null 字段原样保留不填 0）；R3 调用登记先持久；污染扫描 clean；score-receipt 落盘；**共同 gate 的 validate_meta+classify 实测：无 seal → `fail:unsealed`；带 seal → `pass` 且 issue_classes=[]**。
- T8 R1 真值表四态：not_executed（started_at/session/usage/score 全 null 非 0、admission=false）；infrastructure（admission=false，不按能力失败记零）；timeout（timed_out=true、限时真实分、admission 由共同 gate 判定）；ok（admission 由 gate 判定，能力低分不是拒收理由）。
- T9 meta 语义：`tools` 为 **list**；`declared_alias`≠`actual_request_model`（null + not_observable_in_this_batch 状态，不可观测≠已证）；`route_verification=current_not_observed` + r2 历史依据路径；白名单四项管理未知（影响/下一步/停止条件）。
- T6 收据过 evidence-kit receipt_check（`live_doc_drift=[]` 在位）。

## 三、真实模式 fail-closed 实测（负例）

`run-slot`（真实模式，binding 尚不存在）→ **REFUSED**，收据 `receipts/release-refused.json`：
`GateError: binding 不存在或为软链`——共同 gate 检查链真实生效，零调用。

## 四、环境可安全运行评估（阶段 I 口径）

- WorkBuddy 5.9.3 + app.asar 哈希已入预检收据；正式跑前后各记一次，漂移即停剩余 slot 不补跑。
- 安全 driver 仅存两条无干扰路径（复用带端口实例 / 空闲干净启动）；`new_task` 内部 `ensure_app` 同被结构拦截。
- E 后顺序：lead release → `preflight --live` → 按 plan order 13–17 串行（每槽：登记→发送→等待→归档→checker→meta→accounting）→ 五槽后共同 gate `--admission --product workbuddy`。

## 五、给共同 gate（builder-dsh）的接口（已按正确方向接好）

```python
# runner/l4_wb_runner.py → binding_gate() → adapter_verify_execution(BINDING_PATH)
# runner/verify_execution.py → import 共同 gate.verify_execution（GateError → 零调用）
```
共同 gate 的 `--admission --product workbuddy` 为逐场 formal-admission 裁判；
runner 产出 meta.json / score-receipt.json / slot-accounting.json / registrations 供其消费。

## 六、停止点

实现与自测完备，**停待 E 封印与 lead 释放**。E 后只运行、不改冻结源码。
`selftest/SYNTHETIC-binding-*.json` 为合成夹具（带 `_synthetic_fixture` 标记），非 runtime-binding。

## 七、live_doc_drift

无（收据内 `live_doc_drift: []`）。

---

## 更正与补强（2026-10-29T21:00+08:00，v3：timeout/completion 阻断轮 + judge 复核轮）

**v3 dated 更正**：v2 版本在 timeout/completion 语义上仍不达标（lead 复核 driver 发现），且
judge 独立复核（judge 固定 v2 快照独立 harness，socket0，见 5-评测报告/L4独立验收-2026-10-29/）
另指出多项阻断。本轮全部修复，自检扩至 **37/37**（selftest-receipt-l4-wb-v2.json，
receipt_check all_ok）。零模型调用、零会话。

### 修复清单（对应 lead/judge 逐条）

| 阻断 | 修复 | 自检证据 |
|---|---|---|
| driver wait 把 active+20s 稳定当 completed | wrapper `wait_completion_strict`：完成仅认 DB 终态+trace 连续稳定；active-idle 永不早判 | T10a（active 静默直到 deadline 不完成）/T10b（终态+稳定才完成） |
| timeout 只 return 不停模型/工具 | 到限先调产品原生 `wb:conversations:cancel`（arg0=conversationId，静态定位见 runner/safe_driver.py 文档块）→ 15s 窗口验证 DB 终态+trace 稳定 → `stop_verified`；deadline-evidence.json 冻结 | T10a/T10c（验证不成立→stop_verified=False） |
| cancel 可能只是请求信号 | 三项验证（DB 终态+trace 稳定+无取消后活动）不成立即不视为已安全停止；首个真实超时就地验证；失败→剩余槽按已封规则诊断 not_executed | T10c；运行期证明留真实批（E 后） |
| 无可靠停止能力则不强跑 | stop_capability_failed 标志 + accounting diag；五槽 not_executed+准确原因属合法结果 | T10c 语义 |
| cmd_run_slot binding_values 未定义（NameError） | `binding_values()` 已定义（gate 通过后读取） | 语法+T2 适配链 |
| registration 可覆盖/二次外发 | registration.json 改 O_EXCL|O_NOFOLLOW，已存在即拒（attempt 已登记不重发）；claim 在任何 setup 前先行 | T11（重入拒绝且目录零变化） |
| 时间戳幂等不合规 | 固定 slot O_EXCL claim（receipts/claims/<slot_id>.claim）；拒绝不产生新文件 | T11 |
| setup/ensure 失败不落盘 | 所有早退路径持久 slot-accounting.json（真实模式 not_executed → notexecuted.json） | T12 |
| 版本漂移无比较/强制点 | 前后 version+asar 比较 `detect_upgrade_drift` → meta.upgrade_drift + upgrade_stop_remaining + acc diag | T15 |
| managed_unknowns dict / 缺顶层 slot_id | list-of-{item,impact,next_step,stop_condition}；meta.slot_id 顶层 | T7i3/T9d |
| 缺失 trace 冒充 clean+ok | canonical 缺失 → integrity.missing_trace=True + verdict=violation + status=error（不评分不冒充） | T13 |
| dry 写真实 runs / 陈旧 trace | dry 一律 selftest/dry-evidence+dry-ws；collect 前 rmtree 陈旧 trace | T14；T7（新布局） |
| checker exit1 语义 | 夹具 checker 错答 exit1 仍输出合法评分 JSON → status=ok + 合法低分（exit1≠基础设施） | T7l |
| v2 期 dry 误写真实 runs（污染） | 8 文件带 PROVENANCE.json（来源/sha/零调用证明）归档至 selftest/archive-real-runs-pollution-20261029T205000+0800/；解析绝对目标后 move，未静默删除；真实 runs/claims 现 0 文件 | 归档清单 |

### 与共同 gate（builder-dsh v1 契约，gate.py sha256_8=ca820479）对齐

- 适配层 `verify_execution(binding, require_release=True)`（TypeError=契约不符→零调用）。
- meta：顶层 slot_id；route.declared_alias / route.alias_evidence（指向本批存在的
  agent-session/session-row.json，gate 验存在）/ actual_gateway=unknown + validation 与
  route_verification 双写 current_not_observed + r2_history_ref；product_version/app_asar_sha256
  本批必填；managed_unknowns list；stratum 恒 wb_gateway_delivery；model=声明 alias，
  actual_request_model=null+not_observable 状态。
- 证据布局 §C：prompt.txt / trace/<session>.jsonl（evidence_paths.stdout）/ agent.stderr.txt
  （0 字节事实）/ agent-session/ / workspace/；score-receipt §D 固定格式（earned/possible=
  denominators/reported 8dp/raw_checker_output 对象）。
- §E：not_executed → notexecuted.json；E 前 binding 缺席不写任何记账（ refusal 收据只在
  receipts/，槽目录零文件——当前实测真实 runs/ 为空）。
- 共同 gate validator 机械实测：无 seal → fail:unsealed；带 seal（datetime）→ pass、issues=[]（T7g/h）。

### 停止能力结论（诚实边界）

通道存在性已证（静态）；运行期可靠性未证（需真实 session）。首个真实超时就地验证：
验证成功 → timeout 槽按 R1 可评分分支；验证失败 → stop_verified=false 不视为已安全停止，
剩余槽诊断 not_executed。五槽若全部正常完成则该能力无需触发。

### live_doc_drift

无。

---

## v3.1 补充（2026-10-29T21:10+08:00）：cancel 调用链静态定位与 stop_verified 升级

**已证调用链**（只读 5.9.3 解包副本，REA 范围；字节偏移可复核）：
1. `wb:conversations:cancel` — resources/extensions/edge-sync/server/index.cjs @4532764
   （localConversationMethod 描述符，arg0=conversationId）与 @4535903
   （sendPreparationGate.cancel(conversationId)，与 sendPrompt.begin 成对）。
2. main/server.js @1794921：conversation Proxy 将 `cancel` 与 `sendPrompt` 并列为一等方法。
3. main/server.js @1456198：`SessionManager.cancel(e) → cancelSessionRun(e,{kind:"user",
   reason:"cancelled"})`；`cancelSessionRun` 全文：withReadySession → `requestProcessingStop`
   → **`await r.backend.cancel(t)`（转发运行中会话后端/kernel——原生取消覆盖 active runner）**
   → `finalizeStaleToolCallsForDetachedCancel`（产品显式建模取消后工具调用可能 detach 存活）
   → 状态机 turn_completed / onProcessingStopped("interrupted")。
4. kernel 侧 main/acp.js：abort→requestCancelled(-32800) 协作式取消语义。

**止步边界（如实，不越证据）**：wb: 通道字面路由行在压缩 bundle 未定位（数据驱动分发）；
`backend.cancel` 对已 spawn 工具**进程**的终止效果静态不可证——stale-tool finalize 的存在
正是产品预期「工具可能比取消活得更久」。

**stop_verified 升级（三重验证，任一不成立即 false）**：①DB 终态 cancelled/stopped；
②trace 自 cancel 起零增长；③本 workspace 作用域（lsof cwd 匹配，仅限本批 workspace，
用户会话不受影响）内无可见 codebuddy kernel 进程（探测失败按可见处理=保守拒）。
stop_verified=false → timeout formal=false + 停后续槽。自检 T10a–d 四态（含进程判据），
总数 38/38。未发任何真实 session/cancel，零调用。

---

## v3.2 更正（2026-10-29T21:20+08:00，lead 复核 safe_driver v3 真实路径 bug 后）

1. **NameError 阻断**：v3 超时路径默认探针引用了不存在的 `_workspace_codebuddy_processes`
   （真实名 workspace_processes_still_active），自测因注入 process_probe 而掩盖。已修正；
   新增 **T16（a–e）不传 process_probe 的完整 deadline 路径**——mock 在 `_lsof` 间接层
   （非替换探针函数），真实默认入口被直接执行（原 NameError 即此路径回归）。
2. **探针作用域过窄**：`lsof -c codebuddy` 换为**全进程 cwd 扫描**——凡 cwd 为本 workspace
   或其任意子目录的进程均计入（含已 spawn 的 python/node/shell）；lsof 非零退出/超时/
   权限错误/不可解析 → `probe-error`，绝不当空列表（保守拒 verified）。T16a（子目录 cwd）、
   T16b（probe-error）。
3. **窗口提前 break**：DB 首次 cancelled 即 break 与「连续稳定」声明不符。改为**全有界窗口
   观测**：逐采样记录 statuses/max_bytes；stop_verified = 终态出现过 ∧ 终态后无非终态翻转
   ∧ trace 自 cancel 零增长 ∧ 作用域进程为空。T16d（窗内 DB 翻转→拒）、T16e（cancel 后
   trace 增长→拒）。
4. 静态 cancel 链不替代工具停止未知：stop_verified=false 语义不变（timeout formal=false +
   停后续槽）；backend.cancel 覆盖 active runner 与 detached-tool 边界陈述见 v3.1。

自检 **43/43**（selftest-receipt-l4-wb-v2.json，receipt_check all_ok）。零模型调用、零会话。

---

## v3.3（2026-10-29T22:00+08:00）：native_stop 原物信封 + 端到端真 gate 正反例（judge v3.2 快照固定后解冻实施）

1. **producer 落盘**（真实超时路径）：`evidence_dir/native-stop.json` 原物收据（b76208cf 契约：
   verified_stop 权威 bool + stop_kind("wb:conversations:cancel") + verified_at + checks
   {db_terminal, trace_stable, no_scoped_processes} 三键全 true 承认 + deadline_reached_at +
   cancel_invoked_at + slot_id/run_id/event_id/conversation_id/workspace 绑定字段）；
   `meta.native_stop={file:"native-stop.json", sha256}` **不含 verified_stop**（权威在 doc，
   不双写）；attempts[0].outcome="timeout"；verified_stop=false 照常写收据+信封（gate 区分
   「未验证」与「缺信封」两种 fail）；非 timeout 槽无 native_stop（豁免保持）。
2. **inputs_verification**：真实模式逐输入 sha256 对 contract.case_snapshots.files 机械比对。
3. **score-receipt**：score 对象内补 checker_sha256（gate 核对 contract）。
4. **端到端真 gate 自测（T17/T18，gate_admission 真入口 + _fake_git_env 注入，零 git 写）**：
   - T17a 正例：WB timeout + verified_stop=true → **formal_admission=True 且
     genuine_timeout=True**（全门清零，非仅 stop 门）；
   - T17b verified_stop=false → 拒（verified_stop≠true）；T17c 缺信封 → 拒（须 native_stop
     原物信封）；T17d verified_stop=true 但 checks 三键缺一 → 拒（atk17 语义）；
   - T18a/b 跨槽/跨 session 借用：生产者 validate_native_stop_binding 拒（slot_id/
     conversation_id 不符即 RuntimeError）。
5. 自检 **49/49**（receipt_check all_ok）。
6. **披露（builder-dsh 侧）**：gate b76208cf `--selftest` 当前 10/47 失败（其 baseline 夹具
   未跟上新校验：guards_used/timeout receipt 字段等，案例名 admit-baseline-*、atk1/3/5 等），
   已同步 builder-dsh；WB 集成证明由本侧 T17 真实 gate_admission 端到端承担，T2c 改为解析式
   事实记录（不掩盖 gate 红灯）。
7. 真实运行期未知保留：cancel=请求信号、工具进程终止不可静态证明 → 三重验证与
   stop_verified=false 分支不变；E 前零模型调用不变。

---

## v3.4（2026-10-29T22:15+08:00）：W13 completed 全门正例 + native_terminal 原物（gate 3987b172/b76208cf 契约）

1. **producer 补齐（W13 九项拒收逐条）**：meta 顶层 order；checker.stdout 原始全文落盘
   （gate 验存在/可解析/与 receipt.raw_checker_output 逐字一致）；judge 保留原始 checks 计数列表；
   score-receipt 的 score.checker_sha256（gate 核对 contract）；inputs_verification（v3.3 已有）；
   exit_code 保持诚实 None 不伪造 0（gate 已按 WB 原生终态证据改核）。
2. **native_terminal 原物**（builder-dsh completed 契约，与 native_stop 同构）：
   `evidence_dir/native-terminal.json` O_EXCL 落盘（terminal:true + state:"completed" +
   verified_at + slot_id/run_id/event_id/conversation_id/workspace + DB/trace 终态证据）；
   `meta.native_terminal={file,sha256}` 不双写权威状态；failed/error 终态如实记录（gate 拒，
   正确行为）；WB timeout 仍走 native_stop。
3. **T19 全门正例（lead 要求的核心）**：正常 completed 场景走**真 run_impl 全管线**
   （mock 驱动、零模型调用）→ 产物直进**真 gate_admission**（_fake_git_env 注入零 git 写）：
   `formal_admission=True 且 fails=[]`（27 分母 tb-cargo-plan 世界，含 order/inputs_verification/
   checker.stdout 绑定/score-receipt 计数重算/native_terminal 全链）。T17 timeout 正反例保留。
4. 自检 **53/53**（receipt_check all_ok；preflight 全过；真实 runs/claims=0）。
5. 澄清一处 gate 拼写疑点：3987b172 的 exit_code 检查出现重复 fail 行（无条件+WB 文案），
   由 native_terminal 路径实际短路未触发；以 builder-dsh 自测 W13-1 为准。

---

## v3.5（2026-10-29T22:50+08:00）：W6 纪律——stop 未验证不跑 checker（早退 partial + halt）

**代码分支（l4_wb_runner.py run_impl）**：
- `_on_deadline`（:578 区域）：deadline 到达**即时冻结** deadline-evidence.json
  （reached_at + pre_cancel_snapshot），后发 cancel——非事后补写。
- **6b 早退块**（collect/checker 之前）：timeout 时先落 native-stop.json（verified_stop
  按三重验证实况）+ 信封；`stop_verified != True` ⇒ **不 collect 不跑 checker 不冻结动态
  workspace**：selection=null + diagnostic{class:"stop_unverified"} + score/judge 置 null +
  meta.json/slot-accounting.json（partial，score=null）持久化 + `persist_halt`（O_EXCL
  receipts/HALT.json）→ return（checker_ran=False）。
- **0- halt 检查**（claim 之前）：HALT.json 存在 ⇒ 本槽零 send，真实模式持久
  notexecuted.json（§E），dry 落 slot-accounting，status=halted。
- verified timeout 路径照旧评分（R1：已验证超时可评分），accounting 收敛为 verified-only。
- 顺带修复：v3.4 native_terminal 插入时 timeout 的 native_stop 代码被误吞进 error 分支
  （本次重构归位）。

**测试（真 run_impl 分支级，T20a–f + T19 保持）**：
- T20a 未验证 stop：checker 0 次（无 checker.stdout/score-receipt/trace/workspace）；
- T20b partial 记账 score=null + native_stop.verified_stop=false + meta selection=null/
  diagnostic=stop_unverified；
- T20c deadline 证据冻结文件在；T20d 批级 halt 持久；
- T20e 后续槽 status=halted 且 mock driver 零调用 + not_executed 记账；
- T20f verified timeout：checker 跑通（checker.stdout+score-receipt）、meta.timed_out=true、
  accounting executed+timed_out、attempts[0].outcome=timeout；
- T19 completed 全门 formal=True 保持不变。
自检 **59/59**（receipt_check all_ok；真实 runs/claims=0；动态 workspace 残留语义=
  未验证 stop 不动它——dry 根每次自测通配清理，真实根永不清理）。
