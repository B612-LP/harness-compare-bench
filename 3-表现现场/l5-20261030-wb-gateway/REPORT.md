# L5 WorkBuddy 网关评测摘要（事后脱敏）

> 本文是事后脱敏摘要，不是历史封印原件；不能证明旧验收时序，也不表示重新验证。真实运行、自检、拒绝和废弃批次分别记账。

## 准备及失败

原记录载零模型自检 71/71、静态预检通过；这不是产品真实运行。初次放行后，bird 首槽因校验器读取错误计划而 fail-closed 拒绝，零调用；修复后旧清单哈希不再匹配，须重封。guard 由计数调和推导，不等同语义护栏验证。

## E2 与 E3 实际运行

| 批次 | 槽 | 状态 | earned / reward | weighted | 时长 | 原记录完整性 |
|---|---|---|---:|---:|---:|---|
| E2 | bird | ok | 1 | 100.0 | 74 秒 | clean |
| E2 | dab | ok | 0 | **70.0** | 192 秒 | clean |
| E3 | bird | ok | 1 | 100.0 | 88 秒 | clean |
| E3 | dab | ok | 0 | **60.0** | 230 秒 | clean |

两批各槽单次尝试，原记录的原生模型均为 deepseek-v4.1-flash，renderer 均 ready；E2 dab 为 7/10，E3 dab 为 6/10。E2 是中止重封档案中的历史尝试，不与 E3 合并或取代。可核对 [E2 bird 收据](<../中止重封档案E2-20261030T0207/wb__bird-r1/score-receipt.json>)、[E2 dab 收据](<../中止重封档案E2-20261030T0207/wb__dab-r1/score-receipt.json>)、[E3 bird 收据](<runs/l5-20261030-wb-gateway-bird-ca-schools-15-r1/score-receipt.json>) 和 [E3 dab 收据](<runs/l5-20261030-wb-gateway-dabstep-payments-10-r1/score-receipt.json>)。

bird checker 当时未发射 n_tasks，guard 方法记 insufficient_fields；不能推断 guard 已被语义验证。E3 记账重跑覆盖了固定路径的 E2 accounting frame，原记录称旧版可从历史版本恢复；这是证据完整性限制，不应视作未发生。原记录 clean 不自动证明无污染或正式准入，最终裁定须独立核对；未核实部分为未知。
