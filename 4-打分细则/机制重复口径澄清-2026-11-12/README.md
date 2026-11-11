# 机制重复口径澄清 v1.1（2026-11-12）

**回应 Issue #16 的 P0 / Q3：已有 30 槽、10 组、每组 3 次；这是 R 输入重复性检查，不是 M1 inline/spill 干预效果。** 本页是事后澄清与加性勘误，不是新预注册，也不追认旧门通过。绑定历史基线 `38b2e13f63c5aeacb58094d2e977980ab12e8041`；逐源 SHA 见[结果](<result.json>)及[无内容测量投影](<evidence.json>)。旧原文、正式 25 格及历史分数不变。

## 1．问题、历史目标与可推翻分支

[原预注册](<../机制独立重复预注册-2026-11-08/README.md>)的历史主门为：同一场景、同一臂的三次选定输入 bytes，`max−min ≤ 100 B` **AND** “turn 边界类型序列一致”；10/10 组通过才允许增强重复性表述。五场景 × 两臂 × 三次 = 30 槽，已于 [r1109 执行记录](<../../3-表现现场/r1109-mech-n3/README.md>)完成，并非待补跑。

它检验的是固定任务/配置下的**所选输入观测量是否稳定**。某组 bytes 差大于 100 B，或经有效定义取得的序列不一致，足以反驳该组通过；若序列定义/实现不足，则不能把缺证据当作通过。任一组未通过便不能作 10/10 升级。这里没有 inline/spill 随机或配对干预，故不支持 M1 效果、成本收益或普遍因果归因；首消息相同也不等于全输入、实际 reasoning/cache 受控。

## 2．证据、计量层与身份边界

按[请求侧观测定义](<../请求侧观测规范-2026-11-08/README.md>)逐槽从已归档真源重新选择并计算：DSH S3 是 `user/message`、`request/header`、`request/context` **完整事件**的 canonical UTF-8 JSON bytes；S4 是 `assistant/message`、`tool/call` 完整事件之和。Codex R3 是各 `response_item.payload` 的 canonical bytes，按 `token_usage_record` 分段并保留未闭合尾段；R4 只加其中 `message/reasoning` payload。canonical 均为键排序、无额外空格、非 ASCII 不转义。事件 wrapper 长度另列，usage 不充当 bytes；两产品观测层不同，不冒充统一 HTTP 输入、token 或费用。

公开版本只新增[逐事件类型/长度投影](<evidence.json>)，不公开原消息内容。其每条事件记录是 `[type, canonical_event_bytes, payload.type或null, canonical_payload_bytes]`；保留原件 SHA 和归档相对标识、15 份 Codex 首消息摘要哈希。公开[复算器](<verify.py>)重新选择、分段、求和，核 69 个公共源的相对路径/SHA，并与逐槽 aggregate、[采集对账](<../../3-表现现场/r1109-mech-n3/observe/trace-accounting-summary.json>)及[批次身份表](<../../3-表现现场/r1109-mech-n3/adjudications.json>)交叉检查。

**公开可核范围是投影算术、公共源绑定及公共记录间一致性，不是私档真伪认证。** 原始 canonical 长度、消息哈希和全部原件身份，仍需取得原件后独立核验。24 份公开 meta 沿用 `r1030-formal-a1` 标签且无 `a1_gate` 字段，不能拿该标签证明归属；脚本同时要求场景/臂/rep、r1109 run/event ID、采集时间及原会话标识相符。四份 DSH aggregate 的 run 字段仅为文件基名，不能单独证明槽位；脚本固定其具体路径/SHA并对账。上述均保留为缺口，不补写历史控制成立。

## 3．重算结果：字节子门与完整主门必须分开

下表为计划、槽位和分析脚本一致的 **10 组 × n=3 = 30 槽**。每次 S3/R3/S4/R4、序列与 SHA 均在[结果 JSON](<result.json>)；不另铺 30 槽长表。“不可核”指旧序列子门不足以裁决，不是零字节或运行失败。

| 场景 | 臂 | n | 输入 max−min（B） | ≤100 B 子门 | 历史 AND 主门 |
|---|---|---:|---:|---|---|
| bird-ca-schools-15 | DSH | 3 | 0 | 通过 | 不可核 |
| dabstep-payments-10 | DSH | 3 | 956 | 不通过 | 不通过 |
| exercism-py-6 | DSH | 3 | 0 | 通过 | 不可核 |
| lcb-recent-hard-4 | DSH | 3 | 0 | 通过 | 不可核 |
| tb-cargo-plan | DSH | 3 | 0 | 通过 | 不可核 |
| bird-ca-schools-15 | Codex | 3 | 154,301 | 不通过 | 不通过 |
| dabstep-payments-10 | Codex | 3 | 296,848 | 不通过 | 不通过 |
| exercism-py-6 | Codex | 3 | 31,431 | 不通过 | 不通过 |
| lcb-recent-hard-4 | Codex | 3 | 165,538 | 不通过 | 不通过 |
| tb-cargo-plan | Codex | 3 | 471,897 | 不通过 | 不通过 |

因此 DSH 仅能确认 **字节子门 4/5**；不能重申完整旧门 4/5 通过。10 组有 6 组已由字节子门反驳、4 组完整门不可核，不能作 10/10 升级，更不能把它当作独立机制效应。

## 4．序列歧义与加性数值勘误

- **历史语义诊断：** [最小纯函数](<verify.py#L78-L84>)固定旧白名单 `user/assistant/thinking/tool_call/tool_result/text/final/status/session`。在真 v4 类型上重演，15 份均只剩 `['session']`；而公共 aggregate 本身记录的是 `user/message`、`assistant/message`、`tool/call`、`tool/result`、`turn/start`、`turn/end` 等。白名单与真实类型不匹配，session-only 不构成充分 turn 语义证据。该函数说明缺口，不认证未公开旧实现的真实性。
- **两种事后诊断互相提示歧义：** 五组 DSH 的狭义 `turn/start` / `turn/end` 序列均相同（各恰一轮）；加入 step/tool/assistant 后五组均不同。两者都只列为诊断，不能选择更宽序列事后宣布“旧门 0/5”，也不能用更窄序列补授旧门通过。
- **Codex：** 15 份 canonical R3 均与逐槽 aggregate 和采集对账一致，范围 **60,064–789,813 B**；exercism r2 为 **60,064**，而[旧派生摘要](<../../3-表现现场/r1109-bw-retest/observe/codex-r3-summary.json>)为 62,854。旧范围摘要失准，称“派生摘要数值口径不一致”，没有证据归因为 serializer。
- **次要控制观察：** 五组 Codex 的首三条 `response_item` message 均为 developer permissions / user environment / user task，三者的 role+content canonical 哈希组内一致，任务 content 单独也一致。首 user 实为 environment，不是 task。这是事后次要观察，不替换 R 主门、不证明后续完整输入一致。
- **DSH 输出：** bird r2 真源 S4 为 **193,745**，不是[旧摘要](<../../3-表现现场/r1109-bw-retest/observe/dsh-s3-s4-summary.json>)的 551,905；bird 三次为 551,905 / 193,745 / 517,142，真实 max/min 为 **2.849**，旧执行页 1.067 是旧错配残留。dabstep 重算比为 **2.174**。逐项不一致保留在结果中，不改旧页或历史分数。

## 5．结论、置信与限制

**能确定：** 30 槽已完成，10 组分析一致；字节子门 DSH 4/5、Codex 0/5；所选 S3/R3 稳定性不能直接推出 S4 稳定性。**不能确定：** 旧序列子门充分成立、全输入等控，或 inline/spill 独立效果。对数值和公共记录间一致性的信心来自独立重算与 SHA 对账；对原件真实性、未公开控制及旧实现的公共可核性仍保留缺口。没有新增产品运行/请求，没有重判分数。

版本关系：原协议/执行页按绑定版本冻结保留；v1.1 是本页及脚本的新澄清版本，不是原协议的事后重注册，只澄清历史目标、错误与不可核分支。`≤100 B AND 序列一致`、10 组、30 槽都未改成更有利阈值。将来若另立序列定义或干预效应实验，必须另行事前定版，不能倒改本批历史。

## 公开复算与测试

Python ≥3.9，仅标准库；不调用网络、子进程、旧观测工具或判卷器。绑定基线指历史源版本及逐文件 SHA，并不读取/假定当前 Git HEAD。缺源、坏 schema、槽位缺失/重复/混入、SHA 不符、组数或阈值变化均报错（CLI exit 2），不默认零；已披露旧摘要差异作为诊断输出，不用它代替真身值。

```sh
python3 4-打分细则/机制重复口径澄清-2026-11-12/verify.py --root .
# 默认 stdout；只有显式给出全新路径才写文件，已有文件拒绝覆盖：
python3 4-打分细则/机制重复口径澄清-2026-11-12/verify.py --root . --output /tmp/r1109-clarification-new.json
PYTHONDONTWRITEBYTECODE=1 python3 4-打分细则/机制重复口径澄清-2026-11-12/test_verify.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -O 4-打分细则/机制重复口径澄清-2026-11-12/test_verify.py -v
```

[负例与回归测试](<test_verify.py>)普通模式和 `-O` 均为 28 项通过；覆盖 100/101 B 与 AND、退化 session-only、窄/宽序列差异、首 user 误标 task、payload/wrapper、槽位身份、源与投影 tamper、旧摘要冲突、组数/阈值改动、确定性及输出不覆盖。验收仅针对本澄清实现，不追认旧门。
