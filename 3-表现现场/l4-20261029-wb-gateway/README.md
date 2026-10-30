# L4 WorkBuddy 独立网关正式五题批次（l4-20261029-wb-gateway）

层名（展示全称，CLARIFICATION-L4-1 R2）：**WB 产品交付态（历史证据指向网关；本批路由状态单列）**。
这不是本批网关已验证或同权重声明；`actual_gateway` 默认 `current_not_observed`，历史依据见
[1-评测方案/准入预检-2026-10-29/wb-preflight-r2.json](../../1-评测方案/准入预检-2026-10-29/wb-preflight-r2.json)。

## 槽位（plan.json 权威，order 13–17，全部 first，stratum=wb_gateway_delivery）

| order | run_id | case | timeout_s |
|---|---|---|---|
| 13 | l4-20261029-wb-gateway-bird-ca-schools-15-r1 | bird-ca-schools-15 | 1800 |
| 14 | l4-20261029-wb-gateway-dabstep-payments-10-r1 | dabstep-payments-10 | 1800 |
| 15 | l4-20261029-wb-gateway-exercism-py-6-r1 | exercism-py-6 | 2400 |
| 16 | l4-20261029-wb-gateway-lcb-recent-hard-4-r1 | lcb-recent-hard-4 | 3000 |
| 17 | l4-20261029-wb-gateway-tb-cargo-plan-r1 | tb-cargo-plan | 2400 |

## 目录

- `runner/l4_wb_runner.py` — 主运行器（preflight / selftest / verify-execution / run-slot / accounting）
- `runner/safe_driver.py` — driver 包装：**结构性禁用**快照 driver 的 `_quit_app`/SIGTERM 分支；
  仅允许「CDP 复用」或「进程未起时干净启动」，进程无端口一律 `WBUnsafeState` fail-closed
- `runner/verify_execution.py` — **薄适配层**：runner 调用共同 gate
  （1-评测方案/工具链/l4-execution/gate.py）的 `verify_execution`（E blob/漂移/manifest/
  registered_at==E git 时刻全查）；缺共同 gate 或任一封印检查失败 → 零调用（fail-closed）。
  runner 内入口 `binding_gate()`；formal-admission 裁判 = 共同 gate `--admission`。
- `driver-snapshot/` — 仓外 driver 的 pin 快照（SHA256SUMS.txt；runner 只导入快照副本，
  E 封印时另核仓外原件哈希一致）；取证边界：driver 仅 CDP+RPC 驱动与仓外 collect，
  无 hook/注入/代理/网络改动（本批无 r2 式任何注入手段）
- `preflight/`、`selftest/`、`receipts/` — 收据（含 `live_doc_drift`，过 evidence-kit receipt_check）
- 停止语义（v3）：完成=DB 终态+trace 稳定（active-idle 不算）；超时→`wb:conversations:cancel`
  （产品原生通道，静态定位见 runner/safe_driver.py 文档块）→15s 窗口验证 DB 终态+trace 稳定→
  `stop_verified`；验证不成立不得视为已安全停止，剩余槽按已封规则诊断 not_executed
- 槽位独占：`receipts/claims/<slot_id>.claim`（O_EXCL，任何 setup 前 claim，重入即拒）；
  registration O_EXCL 不二次外发；超时冻结 deadline-evidence.json；版本漂移即停剩余槽

## 命令接口

```bash
python3 runner/l4_wb_runner.py preflight            # 零模型静态预检（本阶段已执行，29 检查全过）
python3 runner/l4_wb_runner.py selftest             # 37 项合成正反例含 mock 全路径干跑（零真实交互）
python3 runner/l4_wb_runner.py verify-execution <binding_path>
python3 runner/l4_wb_runner.py run-slot <slot_id>           # E 释放前机械拒绝（fail-closed 零调用）
python3 runner/l4_wb_runner.py run-slot <slot_id> --dry     # mock 驱动全路径干跑（零调用零交互）
python3 runner/l4_wb_runner.py accounting           # R1 三态记账帧
python3 runner/l4_wb_runner.py preflight --live     # E 后：非干扰驱动预检（CDP 复用/空闲启动）
```

## 纪律要点（本批实现强制的）

1. **E 前零调用**：`run-slot` 先过 `verify_execution`，`released_for_model_calls != true` 即拒绝。
2. **不干扰用户会话**：无端口进程绝不 kill（结构禁用，非"先检查再调用"）；自动升级则停止剩余
   slot 不补跑；不改网络/代理/keychain/settings/更新配置。
3. **R1 两层判定**：每 slot 恰一条 slot-accounting（executed/partial/not_executed）；
   `not_executed` 不虚填 started_at/session/usage/score（null 非 0）；完整记账≠formal_admission。
4. **R2 未知管理**：`declared_alias`（本批原生选择证据）≠`actual_request_model`（本批不可观测，
   null）；alias 不可观察/选择失败 → 停该 slot 只诊断；effort/upstream/内部工具为白名单管理未知
   （逐项影响/下一步/停止条件内嵌 meta.managed_unknowns）；不跨路由排名。
5. **证据**：产品原生 trace + prompt + 产物 + 冻结 checker（不录屏）；真跑前后记录 app 版本与
   app.asar sha256；模型/路由/effort 未知不填已验证值。
