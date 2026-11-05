# 控制条件差异：公开记录紧凑视图

由同目录 verify.py 的 render_summary() 从固定公开源生成；不是新正式账或新成绩。
完整逐格 path / SHA-256 / JSON pointer 与差异展示见 [controls.json](<controls.json>)；A 第 3 行 home 前缀仅展示替换为 [HOME]，不是原字节。

| 尝试 event_id（固定来源身份） | 正式 | 版本披露值 | effort 声明 | route/protocol 声明 |
|---|---|---|---|---|
| [formal-a1-codex-bird-ca-schools-15-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | codex-cli 0.163.0 | low | responses |
| [formal-a1-codex-dabstep-payments-10-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | codex-cli 0.163.0 | low | responses |
| [formal-a1-codex-exercism-py-6-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | codex-cli 0.163.0 | low | responses |
| [formal-a1-codex-lcb-recent-hard-4-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | codex-cli 0.163.0 | low | responses |
| [formal-a1-codex-tb-cargo-plan-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | codex-cli 0.163.0 | low | responses |
| [formal-a1-dsh-bird-ca-schools-15-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | 0.2.0-rc.2 | low | anthropic-messages |
| [formal-a1-dsh-dabstep-payments-10-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | 0.2.0-rc.2 | low | anthropic-messages |
| [formal-a1-dsh-exercism-py-6-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | 0.2.0-rc.2 | low | anthropic-messages |
| [formal-a1-dsh-lcb-recent-hard-4-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | 0.2.0-rc.2 | low | anthropic-messages |
| [formal-a1-dsh-tb-cargo-plan-01](<../../3-表现现场/r1030-formal-a1/formal-a1-events.json>) | 是 | 0.2.0-rc.2 | low | anthropic-messages |
| [formal-b1-yuanbao-bird-ca-schools-15-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | yuanbao-expert-web;app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-yuanbao-dabstep-payments-10-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | yuanbao-expert-web;app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-yuanbao-exercism-py-6-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | yuanbao-expert-web;app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-yuanbao-lcb-recent-hard-4-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | yuanbao-expert-web;app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-yuanbao-tb-cargo-plan-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | yuanbao-expert-web;app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-doubao-bird-ca-schools-15-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | 2.33.7 | 未知 | 未知 |
| [formal-b1-doubao-dabstep-payments-10-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | 2.33.7 | 未知 | 未知 |
| [formal-b1-doubao-exercism-py-6-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 否（作废父场） | 豆包工作(本地电脑 runtime);app_build=undisclosed(closed)（构建不可直接比较） | 未知 | 未知 |
| [formal-b1-doubao-lcb-recent-hard-4-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 是 | 2.33.7 | 未知 | 未知 |
| [formal-b1-doubao-tb-cargo-plan-01](<../../3-表现现场/r1101-formal-b1/formal-b1-events.json>) | 否（作废父场） | 2.33.7 | 未知 | 未知 |
| [formal-b2-doubao-exercism-py-6-01](<../../3-表现现场/r1102-formal-b2/formal-b2-events.json>) | 是 | 2.33.7 | 未知 | 未知 |
| [formal-b3-doubao-tb-cargo-plan-01](<../../3-表现现场/r1104-formal-b3/formal-b3-events.json>) | 是 | 2.34.12 | 未知 | 未知 |
| [r20261031-wb-formal:workbuddy:bird-ca-schools-15](<../../3-表现现场/r20261031-wb-formal/formal-wb-events.json>) | 是 | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-formal:workbuddy:dabstep-payments-10](<../../3-表现现场/r20261031-wb-formal/formal-wb-events.json>) | 否（作废父场） | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-formal:workbuddy:exercism-py-6](<../../3-表现现场/r20261031-wb-formal/formal-wb-events.json>) | 是 | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-formal:workbuddy:lcb-recent-hard-4](<../../3-表现现场/r20261031-wb-formal/formal-wb-events.json>) | 否（作废父场） | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-formal:workbuddy:tb-cargo-plan](<../../3-表现现场/r20261031-wb-formal/formal-wb-events.json>) | 否（作废父场） | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-replacement:workbuddy:dabstep-payments-10](<../../3-表现现场/r20261031-wb-replacement/formal-wb-replacement-events.json>) | 是 | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-replacement:workbuddy:lcb-recent-hard-4](<../../3-表现现场/r20261031-wb-replacement/formal-wb-replacement-events.json>) | 是 | 5.9.3 | low | product-log-declared-chat-completions |
| [r20261031-wb-replacement:workbuddy:tb-cargo-plan](<../../3-表现现场/r20261031-wb-replacement/formal-wb-replacement-events.json>) | 是 | 5.9.3 | low | product-log-declared-chat-completions |

所有后端模型身份与实际思考预算均为未知；low / 产品标签仅是公开记录声明。
权限、skills、模型标签与 case/checker/truth/TASK 逐字段原值和来源保留在 JSON，不以标签推定隔离或因果相同。

| 唯一替代：父 → 子 | case / checker / truth | 版本记录 | TASK 公开表示比较 |
|---|---|---|---|
| formal-b1-doubao-exercism-py-6-01 → formal-b2-doubao-exercism-py-6-01 | same_recorded_value/same_recorded_value/same_recorded_value | not_directly_comparable | different_recorded_value |
| formal-b1-doubao-tb-cargo-plan-01 → formal-b3-doubao-tb-cargo-plan-01 | same_recorded_value/same_recorded_value/same_recorded_value | different_recorded_value | different_recorded_value |
| r20261031-wb-formal:workbuddy:dabstep-payments-10 → r20261031-wb-replacement:workbuddy:dabstep-payments-10 | same_recorded_value/same_recorded_value/same_recorded_value | same_recorded_value | not_directly_comparable |
| r20261031-wb-formal:workbuddy:lcb-recent-hard-4 → r20261031-wb-replacement:workbuddy:lcb-recent-hard-4 | same_recorded_value/same_recorded_value/same_recorded_value | same_recorded_value | not_directly_comparable |
| r20261031-wb-formal:workbuddy:tb-cargo-plan → r20261031-wb-replacement:workbuddy:tb-cargo-plan | same_recorded_value/same_recorded_value/same_recorded_value | same_recorded_value | not_directly_comparable |

WB 的父场是明确 public-derived 的 TASK 表示，子场是公开 TASK；保留差异文本，但两者不认证原私档提示。

## A 五对：有限文本展示（不是语义等价）

原字节计算的精确变更范围均为第 1、3 行；比较不删除任何行、不正则或换行归一化（LF/CRLF 不同）。JSON 保留 source SHA 与原行定位，但第 3 行仅展示 home→[HOME] 的派生文本，显式 not_original_bytes / display_transform；不是提示语义归一化。

| 用例 | 声明 effort | 协议记录 | TASK |
|---|---|---|---|
| bird-ca-schools-15 | low / low（非实际预算） | responses / anthropic-messages | 仅第 1、3 行不同；非等价证明 |
| dabstep-payments-10 | low / low（非实际预算） | responses / anthropic-messages | 仅第 1、3 行不同；非等价证明 |
| exercism-py-6 | low / low（非实际预算） | responses / anthropic-messages | 仅第 1、3 行不同；非等价证明 |
| lcb-recent-hard-4 | low / low（非实际预算） | responses / anthropic-messages | 仅第 1、3 行不同；非等价证明 |
| tb-cargo-plan | low / low（非实际预算） | responses / anthropic-messages | 仅第 1、3 行不同；非等价证明 |

相同/不同仅指所列公开记录值；unknown 不因 null == null 转成相同；不同表示域使用 not_directly_comparable。
正式仍 A10/B10/W5，每产品×用例 n=1；历史 5 缺件、40 个 B 观察版本未知、15 个正式成绩无身份信封边界均保留。
