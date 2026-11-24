# 豆包工具链锚闭合性：信封弱锚下的局部 id 锚（2026-11-25，预注册）

> 状态：已验收（冻结 trajectory 重投影，零新增运行）。本页把[轨迹面格式合同候选](<../轨迹面格式合同候选-2026-11-25/README.md>)的豆包「弱锚」判定深化为双层结构，并与[WB 锚点闭合性](<../WB锚点闭合性-2026-11-25/README.md>)（同日）构成桌面双侧对偶证据。

## 1. 研究问题

R3 判定豆包轨迹「弱锚=行号」（信封零 id/零 timestamp）。但其 OpenAI 形消息内嵌 `tool_calls[].id` 与 `tool.tool_call_id`。本研究问：该**局部 id 锚**是否在三槽全部闭合（可配对、可唯一化、行序后向引用），使豆包证据面从「仅行号可定位」升级为「信封弱锚 + 工具链局部强 id 锚」？不翻 R3 主结论，不产生分数。

## 2. 判定（合同：doubao-anchor-contract.json，内容无关）

| 预测 | 判定 | 数据 |
|---|---|---|
| PA id 形态/唯一性 | PASS | 3/3 槽 calls/refs 全 UUID、逐槽唯一 |
| PB 配对闭合 | PASS | 3/3 集合相等+序列相等+逐位配对+ref 在 call 后（27/27、21/21、25/25） |
| PC 跨 run 结构 | PASS（方差如实登记） | 行数 45/37/44、calls 27/21/25、role 序 SHA 三异、工具名序列三异——与 R12 中 WB tb 三槽工具名恒同恰成对照 |
| PD 信封弱锚复核 | PASS | 3/3 槽行级 `id`/`timestamp` 顶层键 0/0（R3 再证） |
| PE calls==refs | PASS（判据订正登记） | 3/3 非空 calls 总数==refs 总数；PREREG 字面判据「assistant 行数==tool 行数」不成立（18/15/18 vs 27/21/25，一条 assistant 可含多 tool_calls）——登记不回改 |

## 3. 近错（5 项全过；弱式如实登记）

NM-A 配对破坏（合成改 ref）翻转检出；NM-B id 碰撞破坏唯一性；NM-C 跨槽计数对表拒绝；NM-D 悬挂注入（tool 行引用不存在 call）检出；NM-E 信封伪造 id 键检出。NM-A/B/D/E 为合成演示类（弱式）。

## 4. 复算与测试

```sh
python3 4-打分细则/豆包工具链锚闭合性-2026-11-25/recompute.py
python3 4-打分细则/豆包工具链锚闭合性-2026-11-25/test_recompute.py
```

`recompute.py` 校验：schema、3 槽集、traj SHA hex64、信封 0/0、8 项布尔全 True、calls==refs、跨 run 恒同声明必须 false（如实性检查）、近错与 verdict 枚举、PE 订正登记在位。`test_recompute.py` 9 项（1 正常 + 8 注入）全拒。

## 5. 结论边界

豆包轨迹**无信封时间戳**→ 时序分块不可做（与 WB 对偶差异如实登记），行序是唯一时序证据；本页不解读 trace 旁证文件（见[旁证等值与活键图谱](<../旁证等值与活键图谱-2026-11-25/README.md>)），不产生任何分数、成本或召回率结论；合同逐 call id 明细只存私档，公开件内容无关。
