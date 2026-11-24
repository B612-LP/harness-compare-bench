# WB 锚点闭合性：调用链配对、时序分块与父链悬挂（2026-11-25，预注册）

> 状态：已验收（冻结 trace 重投影，零新增运行）。本页把[轨迹面格式合同候选](<../轨迹面格式合同候选-2026-11-25/README.md>)的锚点分级条款从「字段存在级」深化到「闭合性实证」级，并补齐其跨 run **结构比较**半边。

## 1. 研究问题

R3 判定 WorkBuddy 轨迹有强锚（id/timestamp/callId 链），但只验证了字段存在，未验证引用可解析率与配对闭合。本研究问：WB 6 槽（dabstep×3 + tb×3）的调用链锚在**闭合性**上是否成立——callId 配对是否逐位闭合、时间戳是否严格递增并分块、消息父链是否可解析？不重判 R3 的掩蔽等值与锚点分级结论。

## 2. 判定（合同：wb-anchor-contract.json，SHA16 4dc374114f4c8745）

| 预测 | 判定 | 数据 |
|---|---|---|
| PA 信封形态 | PASS | 6/6 槽 fc/result 行 id+parentId 全 UUID 形、callId 全非 UUID 形；id/callId 逐槽唯一 |
| PB callId 配对 | PASS | 6/6 逐位相等且计数相等（fc=result 27/24/27/30/22/40）、result 在 call 之后；行级交替不作要求 |
| PC 时序 | PASS | 6/6 fc timestamp 严格递增；两案例三 run 区间互不重叠（disjoint_sorted） |
| PD 消息父链 | PASS（悬挂如实登记） | parentId ∈ message id 池仅 18/340（5.3%）——**轨迹面父链不闭合**，逐槽登记，不伪装闭合 |
| PE 结构比较 | PASS | 工具名集合跨 run 不稳定成立但强度分案例：dabstep 三槽互异（r2 无 present_files/Write）；**tb 三槽完全相同**（削弱因素如实登记，不改 PASS 判定，判据由 dabstep 支撑）；status 全 'completed' |

## 3. 近错（8 项全过；弱式如实登记）

NM1/NM3/NM5 为合成夹具承重演示（配对破坏可检/ts 判据非恒真/分块判据非恒真）+ 真实性对照（NM1c 真实槽全配对、NM3c 全递增、NM5c 真实分块成立）；NM2 悬挂瞒报探针（真实 18/340 证明「父锚全闭合」断言不成立）；NM4 跨槽错绑（r1/r2 计数互异可检）。合成演示类如实标注为弱式。

## 4. 复算与测试

```sh
python3 4-打分细则/WB锚点闭合性-2026-11-25/recompute.py
python3 4-打分细则/WB锚点闭合性-2026-11-25/test_recompute.py
```

`recompute.py` 校验：schema、6 槽集、fc=result 计数、11 项布尔全 True、ts 区间、悬挂瞒报硬拒（parent 池命中=全额即拒）、status 集、时序分块、近错与 PD verdict 枚举。`test_recompute.py` 9 项（1 正常 + 8 注入）全拒。

## 5. 结论边界

本页深化 R3 锚点分级条款（callId 锚闭合 + 时序分块 = 可配对可排序；消息父锚悬挂 = 轨迹导出不携带全部父节点），不翻案、不涉及豆包弱锚面、不产生任何分数或成本结论；合同内容无关（计数/布尔/区间/比例，无轨迹正文）。
