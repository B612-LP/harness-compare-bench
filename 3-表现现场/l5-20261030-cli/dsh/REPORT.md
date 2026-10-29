

## L5 E2 批次中断记录（2026-10-30 02:04–02:09）

- **E1 已废弃**：lead 统一 kill（WB adapter pin 缺陷重封）；我的在途首槽证据+仓外 ws 由 lead 移入 aborted-attempts-20261030T0152seal/（abort-receipt 在案，无 formal 资格）。E1 残留 dispatch claim 由我改名隔离为 `dispatch/e1-aborted-l5-20261030-cli-dsh-dabstep-payments-10-r1.json`（字节未动，sha 63fc27d4caacdc3d）。
- **E2 slot1**：真实执行成功（单 attempt/exit 0/316.8s/组证实/residual false；stdout 269319B sha b09780d2）；后处理在 runner :1119 `ev.mkdir(parents=True)`（缺 exist_ok，与 R2 pre-run prepare 自撞）抛 FileExistsError → **partial 记账**（status=error/class=runner-exception/unscored-diagnostic；无 session_capture、usage 无）。R3 验收点本次未到达。
- **E2 slot2**：未派发（fail-fast），按 runner 设计记 not_executed（绑定 E2 prereg 02a4cac2）。
- 纪律：未改冻结源、未重跑、无 git；等 lead 裁决 E3 后按新公告执行。


## L5 E3 最终批执行记录（2026-10-30 02:16 release；E2 尝试见中止重封档案，前节中断记录保留）

**执行**：`run --all` 2 槽（dab-r1 1800s 限 / cargo-r1 2400s 限）单次串行，restart=0、无 halt、exit 0、无补跑、无 git、冻结源未动（lab E3 pin）。R3 验收全过：

| 槽 | status | 时长(s) | reward | weighted | integrity | session_capture.match_method | usage.requests | per_call | cache_read | cache_creation |
|---|---|---|---|---|---|---|---|---|---|---|
| dabstep-payments-10-r1 | ok | 376.4 | 0 | 70.0 | clean | **exact** | 49 | 49 | 2680960 | 0 |
| tb-cargo-plan-r1 | ok | 223.2 | 0 | 70.37037037 | clean | **exact** | 17 | 17 | 582528 | 0 |

- **session_capture=exact**（两槽），agent-session 非空；usage 各字段为 API 原值实测（含 per_call 逐调用），无整线 null、未知不填 0；cache_creation=0 为该协议原字段观测值，不作跨 wire 结论。
- 归档链全：agent-session / agent.jsonl（原流）/ agent.jsonl.full（重建流另列 sha c4a01bef / 9726088e）/ checker.stdout / score-receipt（8dp 全分母）/ termination-receipt / workspace / config-snapshot（PII 安全派生）/ integrity-rescan。
- E1 中止（aborted-attempts-20261030T0152seal/）与 E2 中断（中止重封档案E2-20261030T0207/，含 dab partial 与 cargo notexec）均为独立档案，无 formal 资格，不计入本批。
- 双归档/准入如需，按 lead 后续指令执行（本轮验收范围以本批 runs/summary 为准）。
