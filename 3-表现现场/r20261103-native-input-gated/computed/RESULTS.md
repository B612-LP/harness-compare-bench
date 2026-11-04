# Native 请求侧输入观察（只读离线分析）

- 真正live会话：1；上游请求：1；本执行器strict mock：2（另有独立native探针，不能算模型请求）。
- 确认计划/实到：0/0；有效原生观察block：0/3；正式新行：0。
- 预注册分支：`direct_observation_incomplete`。
- 这不是同schema/同输出预算的因果对照，更不是产品总排名。

| 会话 | 阶段 | 产品 | 请求侧Δ UTF8 bytes | 严格技术门 | 双键端点 |
|---|---|---|---:|---|---|
| offline-strict-codex-01 | calibration | codex | 12506 | True | True |
| offline-strict-dsh-01 | calibration | dsh | 2255 | True | True |
| pilot-codex-native-v3 | pilot | codex | 12825 | False | — |

## 已计划的三组原生观察

| block | 技术有效 | CodexΔ−DSH boundedΔ bytes |
|---|---|---:|
| 1 | False | — |
| 2 | False | — |
| 3 | False | — |

## 边界

- Actual reasoning tokens and provider-default Codex output cap are not controlled.
- Native tool menus and protocols differ. UUID/root normalization is only a control fingerprint, never the byte metric.
- Client bytes do not establish service-side final input, token use, cache causality, latency or cost.
- Information retained means only the two-key endpoint; bounded text is not full-content preservation.
- Internal calibration/review is not a genuine third-party witness.
