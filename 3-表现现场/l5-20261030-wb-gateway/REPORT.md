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
