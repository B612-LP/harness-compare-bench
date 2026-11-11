# 日志字节在量什么：S3 与 R3/R4 的有效性边界

## 一、观察

**判断前**：已有 30 次执行的日志字节重复性结果，尚不能把日志量直接解释为模型实际输入稳定性。**新增证据**：对指定 15 个 DSH 会话、15 个 Codex 真 rollout 独立静态解析，逐行闭合既有四列计量，并分解字段、角色、usage 分段及重复。**判断后**：S3 的稳定主要约束选中的声明与 user 事件；R3/R4 包含追加的推理、调用及多种角色消息，既非纯用户输入，也不是已经识别的完整请求副本。

| 既有量，按原定义保留 | 本次复算合计 bytes | 观察到什么／不代表什么 |
|---|---:|---|
| DSH S3 | 396065 | 15 槽声明与 user 事件；不覆盖工具返回 |
| Codex R3 | 4325070 | 15 真 rollout 的全部 response-item payload；逐槽 60064–789813 |
| Codex R4 | 2359347 | R3 中 message＋reasoning；并非严格 assistant-only 输出 |

DSH 的 5 个任务中，4 个任务的三个 S3 相等；唯一差异 956B 可完全绑定至两条异步 user 事件。**这只收窄日志层“4/5 重复”的含义，不改变既有主门结论**。本页是已见发现后的事后再分析设计与独立实现，不冒称未知结果的历史事前注册；69 个公开依赖及 30 个源提取均不是新增 trial。新产品／上游模型请求为 0。

## 二、证据

### 来源及隔离投影

源基线为 `52b5e81531f3171292240a01c4ef3e4cb4b84eb8`。选择身份来自[既有 B 派生证据](<../../4-打分细则/机制重复口径澄清-2026-11-12/evidence.json>)，其固定 SHA-256 为 `925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c`；Codex 必须匹配[会话核算](<../../3-表现现场/r1109-mech-n3/observe/trace-accounting-summary.json>)的 `true_rollout`，DSH 必须匹配其候选身份，不能把残留 rollout 混进来。

本次独立读取指定 30 份原件、核对当前源 hash／会话身份，并将 **5863 条事件逐条闭合到 B 的四列**；DSH 只作 zstd 静态解压，不运行产品、旧 observer／runner／checker／serializer。新增[安全证据](<evidence.json>)为**新派生投影而非基线原件**：固定 SHA-256 `48e197314d22bc2b49cedad7625ba3edd16f8c176643fb5e470d9ab550110e61`。只公开 type、role、source-kind、字段键、整数长度／计数及 hash；不公开消息、工具、任务、状态正文或真实私档路径。[结果](<result.json>)由[公开验证器](<verify.py>)实际产生，含全部逐槽字段、排除项、usage 段、重复签名和调用配对。

### A：DSH S3 的组成与排除

S3 是 `user/message`、`request/header`、`request/context` **完整日志事件**的 canonical JSON UTF-8 长度之和。不是只计正文，也不是 HTTP 请求体长度。以下正文列是 content 的 canonical 值；纯文本 UTF-8 列不与它重复相加。

| source-kind | 事件数 | 完整事件 B | content canonical B | source canonical B | 其余包装／字段 B | 纯文本 UTF-8 B |
|---|---:|---:|---:|---:|---:|---:|
| user | 15 | 61284 | 58644 | 225 | 2415 | 57195 |
| agent-instructions | 15 | 47265 | 37770 | 7080 | 2415 | 36660 |
| runtime-context | 15 | 15285 | 6345 | 6510 | 2430 | 5880 |
| tool-jobs | 1 | 424 | 154 | 107 | 163 | 127 |
| subagent-settled | 1 | 532 | 168 | 201 | 163 | 115 |

每行满足“完整事件＝content＋source＋其余”。47 条 user 事件合计 124790B；15 条 header 合计 268590B；15 条 context 合计 2685B；三者闭合 S3=396065B。两个异步事件仅在 dabstep r1 出现：**424＋532＝956＝28062−27106**；其中正文 canonical 仅 322B，其余 634B 为 source／包装，不能把 956B 称为新增纯任务文本。

15 槽的声明内层 hash 与长度一致：每个 header 完整事件 17906B，结构是 `data.header.{tools,config,adapterDefaults}`，含 **21 个静态工具声明**，不是 HTTP headers。字段分解为 tools 17656B＋config 100B＋adapterDefaults 18B＋header 键／分隔包装 39B＋data 包装／reason 30B＋事件外层 63B。每个 context 179B＝data 115B＋外层 64B，键为 `contextWindow/model/provider/systemPromptUpdate`，也只是声明。二者共 271275B，占 S3 约 68.49%；不据此推 token、成本或真正发送占比。

| 槽（省略共同 dsh 前缀） | S3 B | S4 B | 排除的 tool/result 数 | tool/result B |
|---|---:|---:|---:|---:|
| bird-ca-schools-15__r1 | 27738 | 551905 | 29 | 110480 |
| bird-ca-schools-15__r2 | 27738 | 193745 | 16 | 57149 |
| bird-ca-schools-15__r3 | 27738 | 517142 | 29 | 120242 |
| dabstep-payments-10__r1 | 28062 | 1449424 | 55 | 104971 |
| dabstep-payments-10__r2 | 27106 | 694996 | 36 | 123370 |
| dabstep-payments-10__r3 | 27106 | 666696 | 34 | 147956 |
| exercism-py-6__r1 | 25588 | 55727 | 15 | 190736 |
| exercism-py-6__r2 | 25588 | 189407 | 10 | 83508 |
| exercism-py-6__r3 | 25588 | 81097 | 9 | 122160 |
| lcb-recent-hard-4__r1 | 25837 | 256008 | 21 | 61175 |
| lcb-recent-hard-4__r2 | 25837 | 414828 | 28 | 41905 |
| lcb-recent-hard-4__r3 | 25837 | 412441 | 27 | 34355 |
| tb-cargo-plan__r1 | 25434 | 1320828 | 22 | 73264 |
| tb-cargo-plan__r2 | 25434 | 643922 | 20 | 55197 |
| tb-cargo-plan__r3 | 25434 | 404774 | 16 | 50669 |

S4 是 assistant/message＋tool/call，合计 7852940B，**同样不是已证 HTTP 输出**。以 bird 为例，三个 S3 均为 27738B，而工具返回分别为 110480／57149／120242B；S3 定义直接排除这些返回，稳定性不能约束它们，也不能反过来仅凭返回差异证明实际请求不同。

| S3 排除的事件类型 | 数量 | canonical 事件 B |
|---|---:|---:|
| agent/inbox/spliced | 34 | 64998 |
| approval/policy | 15 | 1215 |
| assistant/message | 338 | 7483653 |
| permission/preset | 15 | 1440 |
| sandbox/mode | 15 | 1335 |
| session | 15 | 3180 |
| session-log-deepseek/delivery-accepted | 347 | 65538 |
| session/title | 24 | 4756 |
| session/title-llm-request | 9 | 36585 |
| step/end | 338 | 26053 |
| step/start | 338 | 26706 |
| subagent/catalog | 1 | 229 |
| system/message | 15 | 38070 |
| tool/call | 367 | 369287 |
| tool/result | 367 | 1377137 |
| turn/end | 15 | 1466 |
| turn/start | 15 | 1020 |

### B：Codex R3/R4、排除字段与分段

R3 是全部 `response_item.payload` 的 canonical UTF-8 字节和；R4 只选其中 `message` 与 `reasoning`。R4 的 message **包括 developer 和 user**，不是只选 assistant。分解如下；“output-like”仅指 reasoning／function_call／assistant message 的日志分类，合计 3012814B，不是经验证的 HTTP 方向。

| payload.type | 数量 | R3 B | 对 R4 的贡献 B |
|---|---:|---:|---:|
| message | 166 | 142627 | 142627 |
| reasoning | 406 | 2216720 | 2216720 |
| function_call | 503 | 737637 | 0 |
| function_call_output | 503 | 1228086 | 0 |

| message.role | 数量 | 对 R3 及 R4 各自的贡献 B |
|---|---:|---:|
| developer | 15 | 10079 |
| user | 30 | 74091 |
| assistant | 121 | 58457 |

reasoning 的 content canonical 值合计 2117250B；`encrypted_content` 原字符串 UTF-8 合计 15428B。二者是 payload 内的不同字段层次，不等于已解密思考量，也不与完整 payload 重复相加。

| 槽（省略共同 codex 前缀） | R3 B | R4 B | message B | reasoning B | call B | output B | usage 段 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bird-ca-schools-15__r1 | 225170 | 102835 | 8009 | 94826 | 39381 | 82954 | 29 |
| bird-ca-schools-15__r2 | 379471 | 241296 | 7534 | 233762 | 45496 | 92679 | 41 |
| bird-ca-schools-15__r3 | 268786 | 141592 | 10765 | 130827 | 40153 | 87041 | 19 |
| dabstep-payments-10__r1 | 583317 | 318642 | 25297 | 293345 | 109720 | 154955 | 54 |
| dabstep-payments-10__r2 | 334724 | 135806 | 10617 | 125189 | 65049 | 133869 | 24 |
| dabstep-payments-10__r3 | 286469 | 128922 | 13625 | 115297 | 52273 | 105274 | 23 |
| exercism-py-6__r1 | 91495 | 12832 | 7239 | 5593 | 10475 | 68188 | 5 |
| exercism-py-6__r2 | 60064 | 12964 | 7246 | 5718 | 6318 | 40782 | 5 |
| exercism-py-6__r3 | 80553 | 14817 | 7200 | 7617 | 7174 | 58562 | 5 |
| lcb-recent-hard-4__r1 | 131074 | 64814 | 8582 | 56232 | 33865 | 32395 | 23 |
| lcb-recent-hard-4__r2 | 156316 | 83436 | 5741 | 77695 | 32511 | 40369 | 21 |
| lcb-recent-hard-4__r3 | 296612 | 184612 | 8301 | 176311 | 70381 | 41619 | 42 |
| tb-cargo-plan__r1 | 789813 | 500123 | 6087 | 494036 | 160148 | 129542 | 66 |
| tb-cargo-plan__r2 | 323290 | 214461 | 7189 | 207272 | 28542 | 80287 | 25 |
| tb-cargo-plan__r3 | 317916 | 202195 | 9195 | 193000 | 36151 | 79570 | 24 |

| R3/R4 均排除的事件 | 数量 | canonical 完整事件 B |
|---|---:|---:|
| session_meta | 15 | 328335 |
| turn_context | 15 | 9990 |
| world_state | 15 | 18210 |
| token_usage_record | 406 | 352367 |
| event_msg | 1489 | 5365782 |

`session_meta.base_instructions.text` 每槽 **20903 个 UTF-8 bytes**，15 槽同 hash，合计 313545B，嵌在被排除的 session_meta 中；这不是完整 session_meta 长度，也不能由“未入 R3”推出“未发送”。turn_context 同样被排除，不能据 R3 为全部开局等控背书。

406 个 usage marker 均闭合非空日志段，空闭段 0、未闭尾段 0；验证器仍保留尾段与空段的定义并用合成输入测试。503 对 function_call／function_call_output 均唯一匹配且调用在先，**503 对之间均夹有 usage marker**。例如 bird r1 的调用逻辑 L12／L14、usage L15、返回 L16／L18：分段切开了工具交换，usage 不是已经验证的发送边界。结果保留 payload 的键集合，但不把 usage 数值累加成请求 bytes，也不据此认证 reasoning/cache 等控。

重复按**每槽内部**计，不能把不同 trial 的共同控制当历史重放：

- canonical 完整 payload 精确重复：0；重复 item id：0。
- 仅剥除顶层 `id/internal_chat_message_metadata_passthrough/call_id` 后，额外重复 3 条，均为 function_call；这是指定规范化下的签名相等，不是语义等价或完整历史重放。

| 槽 | 逻辑事件行对 | 额外原 payload B | 剥元数据后的 SHA-256 |
|---|---|---:|---|
| bird-ca-schools-15 r1 | 60 / 67 | 1135 | `2de62b4c798313d44315ea59227f58e8b7005f2e7bb50c50517d4e38335338ef` |
| bird-ca-schools-15 r2 | 24 / 272 | 380 | `81362e5fde6c11d7c3fd829f1246b1cf1c748489b26207cc55c2691221a7d60b` |
| lcb-recent-hard-4 r1 | 80 / 86 | 362 | `adcd82db7c2508e1375d24e951ebf6dfbe5468fa6288b66b61bd2075ed7d0b54` |

初始控制由实际 `response_item` 类型筛选，不硬编码行号：全部 15 槽的前三条为逻辑 L3 developer、L4 user 环境、L8 user 任务；**L5 是 world_state，L6 是 turn_context**。同任务三次的这三项 role＋content hash 相同，后续无同 role＋content hash 副本；这只支持选中控制内容一致，不支持“全部开局／最终上下文相同”，更不证明 HTTP 不重放历史。逻辑行号指原 JSONL 事件顺序，不是本页或派生 JSON 的文本行号。

## 三、解释

| 竞争解释 | 本次裁定 |
|---|---|
| S3 充分跟踪全部实际发送输入 | **现有定义不足支持**：367 条工具返回在 S3 之外，声明占比和两个异步 user 已能解释本次日志量结构及唯一差异。支持 E_LOG，不能以 S3 稳定推出全部输入稳定。 |
| R3 是纯用户输入／每段完整请求副本 | **不符合该普遍解释**：R3 明确混有推理、调用、assistant 消息与工具返回；usage 还切开所有工具交换。支持追加日志解释 E_APPEND；并不把它提升为产品实际发送实现的证明。 |
| 未见精确 payload 副本即可排除 HTTP 历史重放 | **不能**：日志记录与序列化请求处于不同层；三个规范化调用重复也不能支持完整历史重放。 |

所有 bytes 的 canonical 定义一致：`ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False` 后 UTF-8 编码。DSH 计完整事件，Codex 计 payload；纯文本字段另列。源压缩文件大小、JSONL 文件大小、事件 canonical、payload canonical、文本 UTF-8、最终客户端 body 和后端上下文是不同层，不能混列排名或转换为 token／费用。

## 四、未排除因素

- 本页的有限来源未提供足以建立最终发送映射的逐次 body、序列化版本及逐消息来源／重试身份；这不是“全局不存在 serializer／HTTP 证据”的证明。world_state、usage、任务状态或另一批请求捕获不能替代本批最终请求。
- 公开验证器只能核 **固定公开源绑定、投影一致性与算术**。新投影携带原件 hash 不等于公开持有原文；不能认证提取陈述真实性、历史不可变性或原完整封印通过。原件当前附加复算与历史真实性分账。
- 精确重复只针对 canonical payload；规范化只剥指定顶层键。无副本不等无隐式／HTTP 历史重放；短签名／ID 相同也不等内容等价。初始控制 hash 只覆盖选中 content，不覆盖其余状态、菜单、服务端上下文。
- 不估产品总体因果、统一输入／输出方向、实际思考量、cache、token、成本或任务性能。正式 25 格、既有分数／失败、旧阈值与原主门不变。
- 改变上述判断至少需要同一会话／尝试的最终序列化请求体、与日志逐项映射、版本／配置及重试／发送身份；即使捕获到客户端 body，也不能据此认证后端最终上下文或真实性。

## 五、可复现与验收

Python 3.9+ 标准库；验证器不访问私档、不启动子进程或网络。默认 `--root` 为本仓库根，stdout；显式 `--root REPO` 可指定公开克隆。`--output NEW` 只以独占 `x` 创建，已存在即拒绝覆盖，不会先截断。源缺失／改字节、混槽、坏 schema、错误标量类型、重复键及非有限 JSON 拒绝；门使用显式异常，不依赖被 `-O` 移除的 assert。

```sh
python3 -I -S -B 5-评测报告/日志计量有效性-2026-11-12/verify.py --root .
python3 -I -S -B -O 5-评测报告/日志计量有效性-2026-11-12/verify.py --root .
python3 -I -S -B 5-评测报告/日志计量有效性-2026-11-12/verify.py --root . --output NEW.json
python3 -I -S -B 5-评测报告/日志计量有效性-2026-11-12/test_verify.py -v
python3 -I -S -B -O 5-评测报告/日志计量有效性-2026-11-12/test_verify.py -v
```

2026-11-12 实跑：[自测](<test_verify.py>)普通／`-O` 各 **40 tests / OK**，包括真实结果逐字节对账、默认／显式根、独占输出、改字节／缺源／混槽／坏 schema／bool 冒充 int／错误 role 或 source-kind／负包装／重复键、usage 空段与尾段、调用顺序与重复返回、956B 闭合、精确和剥元数据重复分账。公开 CLI 普通／`-O` 输出与[实际结果](<result.json>)逐字相同。**作者自测不是非作者独审**；发布及独审状态由上层索引另行登记，本页不预先宣称完成独审。
