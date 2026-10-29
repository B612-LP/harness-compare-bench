# L5 WB Runner（R6/R7/R1-WB）实现与自检报告

批次：l5-20261030-wb-gateway ｜ 生成：2026-10-30T01:45:42+08:00
D 封印：8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825 ｜ model_calls=0（零真实 app/零发送）
写界：仅 3-表现现场/l5-20261030-wb-gateway/** ｜ live_doc_drift=[]

## 1. 来源与文件

| 文件 | 来源 | 现 sha256_8 |
|---|---|---|
| runner/l5_wb_runner.py | L4 runner/l4_wb_runner.py 复制后修改 | d7445659 |
| runner/safe_driver.py | L4 同名复制后修改（+R6 等待函数） | 5a3a5203 |
| runner/verify_execution.py | L4 同名复制，仅路径适配 | a2d5b242 |
| runner/runner-config.json | L4 复制后改 D 封印/批名/R6 配置 | bc92bacc |
| driver-snapshot/* | **L4 原字节复制，未修改**（R6 落在 safe_driver 包装层与 runner，不动 driver 快照） | f9d4b076 |

路径适配：plan/contract/binding → 1-评测方案/自动循环L5-2026-10-30/；gate →
1-评测方案/工具链/l5-execution/gate.py（任务中途已由 freeze-engineer 落地，
本报告 T17/T18/T19 即对**真 l5 gate** 实跑）；工作区根 ~/bench-workspaces/l5-20261030-wb-gateway；
批次形状=WB 2 槽（order 5/6：bird→dab，timeout 各 1800）。

## 2. R6（池 L5-2）renderer 就绪等待

- `safe_driver.wait_page_target_ready(port, timeout_s, poll_s, fetch_fn)`：非生成式轮询
  `/json/list`，就绪判据=type==page 且含 webSocketDebuggerUrl（可 attach）；transport 可注入
  （mock）。
- run_impl 在 ensure 成功后、**任何 new_task/sendPrompt 前**调用；超时 ⇒ not_executed
  （reason/stop_source 必填），不重试不兜跑；配置 runner-config.json
  `renderer_ready_timeout_s=120 / renderer_ready_poll_s=2`（随 meta.renderer_ready 逐场披露）。
- mock 自检：T21a 伪 CDP 延迟就绪被等待捕获（polls≥3 后 ready）；T21b 超时返回 not-ready；
  T21c run_impl 级 page_ready=False → not_executed 落盘且驱动零 new_task/sendPrompt。

## 3. R7（L4 收尾）frame 路径解析 + receipts write-once

- frame 修复：accounting_frame 现真实解析 evidence_dir（notexecuted.json → not_executed；
  meta.json → executed/partial 含 started/session/usage/score/timed_out；slot-accounting.json
  兜底），身份/封印引用齐（T22b/c/d）。
- write-once：`write_json_once` 用于全部 receipts 写（selftest/preflight/accounting-frame/
  evidence-index）——目标存在即拒写并另存带时间戳副本（T22a 重跑不覆盖负例；实测
  preflight 重跑产生 preflight-static-<ts>.json，原件未动）。

## 4. R1-WB 发射（对齐 CLI/gate 契约）

- `meta.inputs_verification={ok, checked, method}`：真实模式逐输入 sha256 机械比对
  contract.case_snapshots.files；checked=实比输入数（T23d）。
- `meta.judge={checker_sha256, guards_used, correct, n_tasks(+method/candidates/conflict)}`：
  guards_used 按「索引序首个 reconciling 组合」推导——k=len(checks)-n_tasks，
  guard 通过数=npass-correct，combinations 原序首个和匹配即取，无解 conflict 标记
  （T23a/b/c）。
- score.checker_sha256 + reported 8dp；meta.weighted 8dp；receipt.earned 镜像 reward
  （reward∈{0,1} 时 earned 与 weighted 并列，互不覆盖）。
- R2 原则：ws 归档无 meta（T24；模型可见域仅 inputs+TASK）。

## 5. 自检与预检结果

- selftest：**71/71 全过、0 跳过**（gate v2 已就位，T17/T18/T19 端到端对真 l5 gate 实跑；
  含 R6 三例、R7 四例、R1 四例、T24 ws 无 meta）；receipt=
  selftest/selftest-receipt-l5-wb-v1-20261030T0144550800.json（write-once 生效：更早轮次
  副本带时间戳并存），receipt_check all_ok。
- preflight：all_pass（批次形状断言已按 L5 事实改写：2 槽/order 5/6/bird→dab）；
  receipt=preflight/preflight-static-20261030T0145070800.json。

## 6. 状态与边界

- E 未放行：runtime-binding.json 尚未生成；本报告零真实 app、零发送；真实 2 槽由 lead
  另行通知执行。
- E 后 runner/ 整树 pin（写满不再动）；selftest/receipts 位于批次根。
- 已知边界：guards_used 推导是算术回归（非语义护栏命名）；frame 不替代 judge 独立验收；
  wb_run_ids 前缀 l5-20261030-wb-gateway（不撞 r1030/r1031/l4）。


---

## v5.1 dated 备注（2026-10-30T02:00:04+08:00）：E 后授权修复——verify_execution.py gate 路径

- **事件**：E=7474b84a 首槽 bird REFUSED（plan-disk-sha disk=e8dfb73f≠binding=469a43df）。
  根因=runner/verify_execution.py:21-22 仍 pin **l4-execution/gate.py**（其 DEFAULT_PLAN_DIR=L4），
  适配遗漏；fail-closed 生效，零调用，bird 无 claim/registration 残留（REFUSED 先于 claim）。
- **lead 授权最小修复已施行**（同文件 3 处）：l4-execution→l5-execution、
  alias l4_common_gate→l5_common_gate、docstring 同步。修后 disk 计划读取正确
  （L5 plan 469a43df 过 plan-disk-sha），现 REFUSED 项=**E manifest 对本文件的旧哈希锚定**
  （want=a2d5b242，disk=904bb6d1）——即待 lead 统一重封的预期状态；fail-closed 链路全程工作。
- **新哈希冻结**：verify_execution.py sha256=904bb6d11e058bd19410ef7af681bc571c9fba90b62a45a3a9487cc9614a9b58
  （sha256_8=904bb6d1）；l5_wb_runner.py=d7445659；
  safe_driver.py=5a3a5203。
- selftest 重跑 71/71 全过（receipt=selftest/selftest-receipt-l5-wb-v1-20261030T0159340800.json）；
  T17/T19 端到端对真 l5 gate 实跑（经 runner 模块 GATE_PATH）保持通过；经 adapter 的
  verify-execution CLI 现达 manifest 检查层（plan/contract/释放检查全过）。
- 等待 lead 重封新 E（runner 树哈希更新）后执行 WB 2 槽；新 E 前不启动任何真实槽。


---

## v5.2 执行记录（2026-10-30T02:07:45+08:00）：E2=02a4cac2 WB 2 槽真实执行完毕

| 槽(order) | 状态 | earned | weighted | 时长 | R6 就绪等待 | 原生DB model | drift | integrity |
|---|---|---|---|---|---|---|---|---|
| bird(5) | ok | 1 | 100.0 | 74s | ready 0.0s/1poll | deepseek-v4.1-flash | 无 | clean |
| dab(6) | ok | 0 | 70.0 | 192s | ready 0.0s/1poll | deepseek-v4.1-flash | 无 | clean |

- 会话：bird=f096fa9d / dab=dc9a6ea3（各自独立，attempts 恒 1）；R1 发射全过——dab 的
  guards_used 在真实 checker 输出上推导成功（['answers_format','input_integrity']，
  first_reconciling_in_order，correct=7/n_tasks=10）；bird 的 checker 不发射 n_tasks ⇒
  guards_method=insufficient_fields（诚实缺省，如实入 meta 供 judge 裁定）。
- earned 镜像 reward（bird=1/dab=0），weighted 为 checker 原发射 8dp（100.0/70.0），
  两键并列不覆盖；score.checker_sha256 与 meta.judge 绑定一致。
- R7 验收：accounting frame 逐槽 actual 非 null（executed+真实 score），frame 收据为本批
  首写（write-once 无覆盖）；selftest/preflight 收据时间戳副本并存。
- 纪律：复用 9332 单实例（用户进程零终止）、未改网络/版本、无 git、无截图录屏；
  app_asar 前后哈希记录（upgrade_drift=None×2）；执行中一次 ps 误印产品进程命令行
  （含会话级 Bearer）——未入库未复述，收据/REPORT 零凭据，已核。
- evidence：runs/l5-20261030-wb-gateway-{bird-ca-schools-15,dabstep-payments-10}-r1/
  （trace 3 件/prompt.txt/agent.stderr.txt/agent-session/workspace 快照/meta/score-receipt/
  checker.stdout/native-terminal/registrations）。
