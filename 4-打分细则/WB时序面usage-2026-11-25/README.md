# WB usage 时序面：rawUsage 自报 prompt 数与 credit/quota 字段（2026-11-25，预注册）

> 状态：已验收（冻结 trace 重投影，零新增运行）。本页补齐三 harness usage 时序面对照的 WB 侧（DSH/Codex 见[自报 usage 分离账](<../自报usage分离账-2026-11-25/README.md>)），并与[WB锚点闭合性](<../WB锚点闭合性-2026-11-25/README.md>)共用同一冻结档案。

## 1. 判定（合同：wb-temporal-usage.json，内容无关）

| 预测 | 判定 | 数据 |
|---|---|---|
| PG1 输入侧恒定 | PASS | 首 fc 行 rawUsage prompt 三分量（prompt/hit/miss）同案例三 run 逐值恒定：dabstep=30980/27904/3076、tb=30452/27904/2548；hit+miss==prompt 复算器硬校验 |
| PG2 输出侧波动 | PASS | 首 fc completion_tokens 六槽全不同（228/163/162/175/136/190）；credit_sum 六槽全不同 |
| PG3 口径分裂 | PASS | 首 message 行 usage 三 run 互异且 inputTokens 量级（7.3–9.9 万）远超首 fc prompt（≈3.0–3.1 万）——message.usage≈会话累计口径 vs fc.rawUsage=单请求口径，同轨迹两载体分裂登记；第三载体佐证：message 行内嵌 rawUsage.prompt_tokens==inputTokens 六槽全符 |
| PG4 quota 时序 | PASS | 原档独审登记 quota.percent 槽内单调不减，按槽排列的首值为 0,0,1,2,3,3；公开复算器检查单调声明与首尾关系，不重算完整序列。与共享计数器相容，但不证明各槽共享同一计数器 |
| PG5 credit 关联 | PASS+分支登记 | credit>0 全载体成立；「completion_thinking_tokens 全 0」被证伪（非零行 24/22/24/19/15/27 逐槽登记，PREREG 预测仅据首行勘察） |

## 2. 三 harness usage 时序面对照（同 provider：deepseek-v4.1-flash）

- **DSH**：首条自报 totalTokens 三 run 散布 0.35%–0.91%（全 <1%）；输出分量也不同，原因无法仅从自报数确定。
- **Codex**：input_tokens 三 run 恒定、cached detail 随 run 变；输入 token 数相同不证明输入内容或字节相同。
- **WB**：rawUsage 的 prompt 三分量恒定（同 Codex 形）而 completion/credit 不同，quota 另有时序变化；这些是自报字段的观察，不能单凭它们将变化归因于采样机制或确定服务端实际输入。

## 3. 近错（Q0 正常接受，QH1–QH4 全拒；影子树真跑）

completion 均一化拒 / prompt 单值扰动拒 / quota 单调翻转拒 / credit 非法拒。

## 4. 复算与测试

```sh
python3 4-打分细则/WB时序面usage-2026-11-25/recompute.py
python3 4-打分细则/WB时序面usage-2026-11-25/test_recompute.py
```

`recompute.py` 机器重算 PG1（恒定集）/PG2（全异性）/hit+miss==prompt/credit 正性/thinking 双处登记等值/内容无关门，并校验 quota 单调声明及首尾关系；quota_monotonic 与 thinking 计数为 raw 绑定声明（公开件内不可从完整原始序列机器复算，独审双路独立证实）；`test_recompute.py` 接受 1 个正常合同、拒绝 8 个变异合同。

## 5. 结论边界

credit 和 quota 是轨迹中的自报字段，不等于已证实的实际费用或配额绝对量；quota 的观测与共享计数器相容，但未证各槽共享，其他解释仍可能。message.usage 的累计口径判断不回填 R2 分账（载体不同不混算）；不产生分数。
