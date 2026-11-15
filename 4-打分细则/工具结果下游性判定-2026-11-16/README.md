# 工具结果下游性判定（2026-11-16）

**预注册：对 [R3不稳定来源分解](<../R3不稳定来源分解-2026-11-16/README.md>)定位出的环境/任务族主导组做逐项下游性判定——每个字节不同的 `function_call_output`，其配对 `function_call`（call_id 联结）的 canonical 参数字节是否也不同。** 回答「r1109 批次是否存在**不**下游于模型选择的工具非确定性」。纯事后算法判定，不新增运行、不改任何门判定；R3 与 v1.1 的结论不回写。本页冻结于任何判定值计算之前。

## 1．问题与范围

R3 分解已确立：Codex 五组 R3 不稳定中 4/5 组由模型生成族主导，exercism 唯环境/任务族主导（87.20%，净差集中在 `function_call_output` +27,406B；三对两两分解稳健）；dabstep r2vsr3 两两对环境族亦主导（59.26%）。既有解释守卫声明「`function_call_output` 内容下游于模型所选调用，E 主导不证环境独立漂移」——该守卫目前是**合理推断，未经逐项验证**。本页把它升级为可判定的分支问题。

范围（冻结）：exercism 三对两两比较（r1vsr2、r1vsr3、r2vsr3）+ dabstep r2vsr3 比较。共 4 个比较对。数据源与 v1.1 相同钉定归档；每槽 R3 总和与逐型分解必须与 [R3分解 result.json](<../R3不稳定来源分解-2026-11-16/result.json>) 硬等，否则 exit 2。

## 2．定义（冻结，执行前写定）

- 联结：按 response_item 流内 `function_call` 与 `function_call_output` 的 call_id 字段配对；联结缺失或一对多歧义 → 该项记 `unlinked` 单列，不得猜测配对。若归档流无 call_id 字段（以实际 payload 为准），整体转 `unlinked` 分支并在执行记录说明，不虚构联结。
- 对每个比较对，逐 `function_call_output` 分类：
  - **outputs_differ_calls_differ**：输出 canonical 字节不同，且配对调用的 canonical 参数（函数名+arguments）字节也不同 → 下游证据（模型选了不同调用，工具如实返回不同结果）。
  - **outputs_differ_calls_same**：输出不同但配对调用参数逐字节相同 → **工具非确定性证据**（同输入异输出，环境侧不稳定）。
  - **outputs_same**（无论调用是否不同）：不计入，只在计数表体现。
- 汇总指标（逐比较对）：三类计数 + outputs_differ 总数；全局判定：全部 outputs_differ 均为 downstream → D-ALL-DOWNSTREAM；存在 ≥1 项 calls_same → D-TOOL-NONDETERMINISM（逐项列出 call_id、两槽标识与两侧字节数）；存在 unlinked → 单列不并入前两类。
- 内容无关纪律：只记录事件型、call_id、函数名、canonical 字节数与 SHA；不记录参数或输出内容。

## 3．反证分支（冻结）

- **D-ALL-DOWNSTREAM**（全部 outputs_differ 均下游）：r1109 全部已观测字节不稳定收口为三类既有机制——模型输出回流（R3 分解 4/5 组 + bird S4 载体）、自主分支真实输入差异（dabstep r1 subagent 轮）、工具结果下游于模型选择（本页）；环境/工具侧非确定性在该检测面**未观察到**。表述按检测面限定，不改任何门判定。
- **D-TOOL-NONDETERMINISM**：至少一项同参异果——逐项列证据，作为后续批次观测设计的新反例输入；不改历史分。
- **全部 unlinked 或联结面与预期不符**：如实报告联结结构，本页降级为结构登记，不给下游性结论。
- R3 总和与逐型值和 R3 分解包硬等校验失败 → exit 2。

## 4．老师反馈对照（Issue #16）

- **P1 机制解释优于加重复数**：不新增运行，把既有守卫推断升级为逐项判定。
- **P0 验收=槽位/组数/分析脚本一致**：5 槽（exercism r1-r3、dabstep r2-r3）、4 比较对、脚本为本包 `verify.py`。
- 服务③「30 次重复的主要假设」：若 D-ALL-DOWNSTREAM 成立，输入重复性假设在检测面内无未解释残差。

## 执行记录（执行完成后写包内 EXECUTION-RECORD.md，不写本页）
