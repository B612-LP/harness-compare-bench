# WB usage 时序面：raw 层输入侧恒定与计费字段（2026-11-25，预注册）

> 状态：已验收（冻结 trace 重投影，零新增运行）。本页补齐三 harness usage 时序面对照的 WB 侧（DSH/Codex 见[自报 usage 分离账](<../自报usage分离账-2026-11-25/README.md>)），并与[WB锚点闭合性](<../WB锚点闭合性-2026-11-25/README.md>)共用同一冻结档案。

## 1. 判定（合同：wb-temporal-usage.json，内容无关）

| 预测 | 判定 | 数据 |
|---|---|---|
| PG1 输入侧恒定 | PASS | 首 fc 行 rawUsage prompt 三分量（prompt/hit/miss）同案例三 run 逐值恒定：dabstep=30980/27904/3076、tb=30452/27904/2548；hit+miss==prompt 复算器硬校验 |
| PG2 输出侧波动 | PASS | 首 fc completion_tokens 六槽全不同（228/163/162/175/136/190）；credit_sum 六槽全不同 |
| PG3 口径分裂 | PASS | 首 message 行 usage 三 run 互异且 inputTokens 量级（7.3–9.9 万）远超首 fc prompt（≈3.0–3.1 万）——message.usage≈会话累计口径 vs fc.rawUsage=单请求口径，同轨迹两载体分裂登记；第三载体佐证：message 行内嵌 rawUsage.prompt_tokens==inputTokens 六槽全符 |
| PG4 quota 累计性 | PASS | quota.percent 会话内单调不减（复算器逐槽校验）且跨槽全局递增（首值序列 0,0,1,2,3,3）——共享配额计数器=环境状态 |
| PG5 credit 关联 | PASS+分支登记 | credit>0 全载体成立；「completion_thinking_tokens 全 0」被证伪（非零行 24/22/24/19/15/27 逐槽登记，PREREG 预测仅据首行勘察） |

## 2. 三 harness usage 时序面对照（同 provider：deepseek-v4.1-flash）

- **DSH**：首响应 totalTokens 三 run 散布 0.35%–0.91%（全 <1%，模型采样层波动可见）。
- **Codex**：input_tokens 三 run 恒定、cached detail 随 run 变（输入侧确定性+缓存层差异）。
- **WB**：raw 层 prompt 三分量恒定（同 Codex 形）+completion/credit 波动（采样层）+quota 全局累计（环境层）——三种时序形态并存于同一产品轨迹。

## 3. 近错（5 项：Q0 正常+QH1–QH4 全拒；影子树真跑）

completion 均一化拒 / prompt 单值扰动拒 / quota 单调翻转拒 / credit 非法拒。

## 4. 复算与测试

```sh
python3 4-打分细则/WB时序面usage-2026-11-25/recompute.py
python3 4-打分细则/WB时序面usage-2026-11-25/test_recompute.py
```

`recompute.py` 机器重算 PG1（恒定集）/PG2（全异性）/hit+miss==prompt/quota 单调/credit 正性/thinking 双处登记等值/内容无关门；quota_monotonic 与 thinking 计数为 raw 绑定声明（公开件内不可机器复算，独审双路独立证实）；`test_recompute.py` 9 项（1 正常+8 注入）全拒。

## 5. 结论边界

不解读 credit 定价规则；quota.percent 递增只证「存在共享计数器」，不测配额绝对量；message.usage 累计口径不回填 R2 分账（载体不同不混算）；不产生分数。
