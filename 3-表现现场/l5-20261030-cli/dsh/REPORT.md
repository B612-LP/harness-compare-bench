# L5 DSH CLI 评测现场摘要（事后脱敏）

> 本文是事后脱敏摘要，不是历史封印原件；不能证明旧验收时序，也不表示重新验证。以下状态和数值沿用原记录，正式准入需另核原始证据与裁定。

## 中止及中断尝试

- E1 批次废弃，途中首槽无正式资格。
- E2 首槽真实执行，单次 attempt、退出码 0、316.8 秒；后处理因目录已存在抛出 `FileExistsError`，记为 runner 异常、partial、未评分诊断。未取得 session capture 和 usage，R3 验收点未到达；不能把未知用量记作零。第二槽因 fail-fast 未派发，记 not_executed。E2 不是 E3 正式结果。

## E3 两槽真实运行

| 槽 | 状态 | 秒 | reward | weighted | 原记录完整性 | 会话捕获 | requests / per-call |
|---|---|---:|---:|---:|---|---|---|
| dabstep-payments-10-r1 | ok | 376.4 | 0 | 70.0 | clean | exact | 49 / 49 |
| tb-cargo-plan-r1 | ok | 223.2 | 0 | 70.37037037 | clean | exact | 17 / 17 |

原记录称各槽串行单次运行、无补跑，会话非空；cache_read 分别为 2680960、582528，cache_creation 均为协议原字段观测的 0，不据此作跨协议结论。评分与轨迹可核对 [dab 收据](<runs/l5-20261030-cli-dsh-dabstep-payments-10-r1/score-receipt.json>)、[cargo 收据](<runs/l5-20261030-cli-dsh-tb-cargo-plan-r1/score-receipt.json>) 及同目录其他证据。

E1、E2 独立存档，不纳入 E3。原记录的 clean 是当时完整性检查结果，不自动证明无污染或正式比较准入；污染与最终裁定以独立证据为准，未核实部分为未知。
