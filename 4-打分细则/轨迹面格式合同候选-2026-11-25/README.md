# 轨迹面格式合同候选（WB/豆包）· 2026-11-25

- **环**：当日第 3 环（前环：[DSH事件类型消融](../DSH事件类型消融-2026-11-25/)、[自报usage分离账](../自报usage分离账-2026-11-25/)）
- **模式**：零发射离线复算——不启动任何模型/产品/读取试验，只对 r1109 bw-retest 冻结原档（WorkBuddy 6 槽 + 豆包 3 槽轨迹 + 15 个旁证件）做派生统计与关系复算
- **公开件**：`trajectory-contract.json`（内容无关统计件：计数/SHA/关系判定/掩蔽集声明）、`recompute.py`（复算器）、`test_recompute.py`（7 测试）。轨迹正文与旁证内容不公开（原档为私有冻结档案，公开仅含派生统计；本页不写私有路径）

## 研究问题

桌面端（WorkBuddy / 豆包办公）的**轨迹面**此前从未被逐格式声明观测口径。CLI 侧（DSH/Codex）已有事件层同规格复算（R1/R2）；本环检验：桌面轨迹面能否达到同级可复算性，作为观测规范 v1.4 的**候选条款**（本环不冻结）。

## 预测对照（PREREG → 判定）

| 预测 | 判定 |
|---|---|
| P1 结构可枚举 | ✅ WB type union 恰 7 种（session-meta 12 / message 30 / file-history-snapshot 16 / ai-title 6 / function_call 170 / function_call_result 170 / reasoning 133，共 537 行）；豆包 3 槽各恰 1 个 agent mid，role 仅 {assistant, tool}（126 行） |
| P2 canon 重投影决定性 | ✅ 同文件两次规范投影逐字节相同 |
| P3 跨 run 首 user 掩蔽等值 | ✅ WB（完整掩蔽集下两案例三-run 整消息逐字节等值）；豆包**结构性不可核**——轨迹无任何 user 行，输入侧缺席，无等值对象（比预测更强的如实事实，未造伪对象） |
| P4 锚点分级 | ✅ WB 强锚（行 id+timestamp+callId/parentId 调用链）；豆包弱锚证实（126 行 0 id / 0 timestamp，行序锚=文件行号，重排不可检测） |
| P5 轨迹无 usage 载体 | ❌ **证伪→载体登记**：WB 每槽 22–34 条 function_call 行 + 每槽 1 条 assistant message 行，均带 `providerData.rawUsage` + `providerData.usage` 双层（合计 160 载体）；豆包 0 命中 |
| P6 字节账跨 run 互异 | ✅ WB 2 案例 + 豆包 3 槽全部三-run 互异 |

## WB 掩蔽集合同候选（P3 的核心产出）

WB 首 user 消息在**四元掩蔽**下跨三-run 逐字节等值（dabstep `77d5e2f6797f446e`、tb `2ce5784fc24f6d1f`）：

1. **行信封**：剔除 `id`、`sessionId`、`timestamp`、`_meta`（含 traceparent/baggage telemetry）
2. **providerData**：剔除 `conversationRequestId`（每 run 请求 id）
3. **文本内嵌槽位路径**：`__r<数字>` → `__rN`
4. **文本内嵌提交时刻**：`<current_time>…</current_time>`（DOTALL）→ `<current_time>`

掩蔽必要性已逐元素验证（近错 NM2）：省略任一元素，三-run 等值即翻转——四元掩蔽**每个元素都承重**，无冗余项。这是「输入侧恒量检验必须声明掩蔽集」的直接证据。

## WB usage 载体登记（P5 证伪的完整口径）

- **三层结构**：`providerData.rawUsage`（provider 原始混合形）+ `providerData.usage`（归一层：`inputTokens`/`outputTokens`/`totalTokens`/`inputTokensDetails`（**list 形**）/`outputTokensDetails`）+ message 行嵌套 `message.usage`（OpenAI 形）
- **rawUsage 键并集 14 键 = 多协议混合**：OpenAI 形（`prompt_tokens`/`completion_tokens`+details）、DeepSeek 形（`prompt_cache_hit_tokens`/`prompt_cache_miss_tokens`/`prompt_cache_write_tokens`）、Anthropic 形（`cache_read_input_tokens`/`cache_creation_input_tokens`）、`completion_thinking_tokens`、`credit`/`quota`（WB 计费字段，credit>0 全部 160 载体）
- **关系面 160/160 全绿**（证据强度分层，独审 N4：`hit+miss==prompt`、`details.cached_tokens==hit` 为真实数据关系；`归一层==raw`、`totalTokens==in+out` 属 WB 归一层**同层自洽**——归一层由 harness 自生成，非 provider 侧独立佐证）：`hit+miss==prompt`、`prompt_tokens_details.cached_tokens==hit`、`归一层==raw(prompt,completion)`、`totalTokens==in+out`、`details_cached==hit`、`nested cached==hit`（每槽 1 条 message 行）
- **口径家族归属**：WB 归一口径 `total==in+out`（与 Codex 同形），非 DSH 的 `in+out+cr+cw` 形——三 harness（DSH/Codex/WB）两种归一口径、usage 字段为 harness 归一值的结论获得第三数据点
- **provider 路由不可归一判定**：rawUsage 同时含多协议键形，真实 provider 路由无法从键形唯一确定（只登记键形，不猜路由）
- **语义注记（独审 N3）**：rawUsage 顶层 `cached_tokens` 对齐 **write 维度**（160/160 == `prompt_cache_write_tokens`，本数据全 0），`prompt_tokens_details.cached_tokens` 对齐 **hit 维度**（160/160 == 命中数）——两字段语义相反，不可互换；下游误读顶层 `cached_tokens` 会把缓存命中低估为 0

## 锚点分级候选条款（P4）

- **WB = 强锚**：行级 `id`/`timestamp` + function_call 的 `callId`/`parentId` 调用链 → 行可独立定位、链可验证
- **豆包 = 弱锚**：全部 126 行无 id/timestamp → 行序锚=文件行号，**重排不可检测**（登记为合同候选已知限制）
- 豆包输入侧旁证：`agents/<mid>/system/assignment.md`（任务说明落盘）等 15 个旁证件已登记 SHA/bytes（含 0 字节空文件=如实事实），内容级比对未做（超出本环范围，未公开内容）

## 近错对照（10/10）

NM1 错绑拒绝（r1 槽指 r2 文件 → 字节账 SHA 不符）；NM2a 全掩蔽等值 + NM2b–e 省略信封/conversationRequestId/槽位路径/current_time 任一 → 等值翻转；NM3 跨格式混淆拒绝（WB 行无 role、豆包行无 type，互喂校验器必拒）；NM4 豆包强锚声明被行事实反驳；NM5 未枚举类型报 unknown。

## 已知限制与 unknowns

- 豆包轨迹无 user 行 → 输入侧等值检验结构性不可核
- WB rawUsage 多协议键形并存 → provider 真实路由不可归一判定
- 豆包旁证件仅登记 SHA/bytes，内容级比对未做
- 本环产出为**候选条款**，不冻结；能否并入规范 v1.4 待独立环检验

## 复算入口

```bash
python3 recompute.py            # 校验 trajectory-contract.json 内部一致性
python3 test_recompute.py       # 7 夹具（正常 + 6 近错）
```

## 老师反馈对照（#17）

- **覆盖 1（唯一观测规范先行的对象扩展）**：桌面轨迹面首次获得逐格式声明+掩蔽集+锚点分级候选；不冻结，符合「反例达预期后才冻结」的次序
- **覆盖 3（部分）**：三例受控第三方核验仍以 CLI 三链为对象；本环为桌面面准备了同规格可核验统计件，第三方核验尚未完成，不以本环代替
- **不覆盖 2**：本环无任何干预（纯观测），不声称 Harness 效果
- **不覆盖 4**：读取检测不在本环范围

- 本页经非作者独审（PASS-with-notes）：重投影逐槽 SHA、掩蔽集逐元素翻转链与 160 载体关系独立复现零数字分歧；上列两 `cached_tokens` 语义注记与关系面证据分层注记出自独审并已并入；dabstep 省略任一掩蔽元素亦翻转由独审补测（作者臂仅测 tb）。
