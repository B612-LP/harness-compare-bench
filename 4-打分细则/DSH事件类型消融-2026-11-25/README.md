# DSH 事件类型消融与 dabstep 956 B 定源

**结论先行：dabstep 唯一过不了 S3 辅助诊断的 956 B 差额，定源为两条真实输入侧差异——DSH 后台机制注入的用户面通知（一条后台 bash 作业完成通知、一条后台 subagent 停止通知），r1 独有，r2/r3 全事件精确字节零命中。不是解析器或日志层假象。** 本页是 [11-24 计量层敏感性](<../旧主门计量层敏感性-2026-11-24/README.md>) DSH 侧的后续：那次只做了 Codex 消融并指出「dabstep 的 S3 失败全部落在一类」，这次把该单类切割补齐成矩阵，并用原档内容级复核定源。旧主门不变；无重跑、重判或补判；响应 [Issue #17 第 1/2 条](<../../反馈/2026-11-18-第五轮/验收条款-公开版.md#L36>) 的观测口径细化。

## 消融矩阵（5 组 × 4 切法，辅助门 ≤100 B）

对 15 个 DSH 槽（[v1.1 公开复核](<../机制重复口径澄清-2026-11-12/README.md>) 钉定投影）按 S3 = `user/message` + `request/header` + `request/context` 做单类扣除，重新求三槽极差：

| 场景 | S3 full | −user/message | −header | −context |
|---|---:|---:|---:|---:|
| bird | 0 ✅ | 0 ✅ | 0 ✅ | 0 ✅ |
| dabstep | 956 ❌ | **0 ✅（翻转）** | 956 ❌ | 956 ❌ |
| exercism | 0 ✅ | 0 ✅ | 0 ✅ | 0 ✅ |
| lcb | 0 ✅ | 0 ✅ | 0 ✅ | 0 ✅ |
| tb | 0 ✅ | 0 ✅ | 0 ✅ | 0 ✅ |

- **翻转 1/5，且仅由 `user/message` 单类承载**：扣掉它 dabstep 即过线；扣另两类不动。这证明该组的全部差额确在单类之内，与前页「差 956 B 全落 user/message」的字节合计互相印证。
- **敏感性限定（独审）**：五组三 run 的 `header+context` 合计恒为 **18085 B**（15 槽相同），即被保留层在 size 层从不变化——−user/message 切法在本数据集不可能 FAIL，「翻转」与「唯一会变的类型被移除」互为表里，须与 full FAIL 联合解读，不能单独当作 header/context 稳定性证据。另切割按类型合计，同类型内条目重排在合计层不可见（幸由下节逐条定源补足）。
- 辅助诊断只说明字节可分性，不参与旧主门，也不构成行为等值证明。

## 定源：956 B 是什么

对 dabstep 三槽的原始会话档案（zstd，SHA 已由钉定件 identity 逐一锚定：`3116d109…` / `190dd497…` / `d6733947…`）做内容级复核（数据层 = 事件 `data` 字段，排除 `time`/`seq`/`id`/`surfaceOp` 信封）：

1. **共同条目内容等值**：三条共同 `user/message`（真实任务输入 `source.kind=user`、`agent-instructions`、`runtime-context`）的 `content`/`source`/`role` 三槽逐字节相同；`request/header` 与 `request/context` 的 `data` 亦逐字节相同。
2. **两条 r1 独有通知**（整事件 424 B / 532 B，data 341 B / 449 B），原文为 Harness 生成机制通知、不含任务内容：

   > background job bash-54 (bash: sleep 60; echo done) finished [status: completed, exit code: 0]. Read its output with job_output.

   > Background subagent 0cd290d6-5a96-489a-9ebc-cbb0e30b119b was stopped before it finished. / It left no closing message.

3. **精确字节在 r2/r3 全事件任何类型零命中**；泛化短语 "background job" 在三跑的 `request/header`+`system/message`（工具目录能力文本）都有，"was stopped before it finished" 三跑唯一。能力三跑俱在，只有 r1 行使了（r1 步数 56 对 33/31，后台 splice 6 对 2/2）。
4. **任务正文的完整面（独审补验）**：dabstep 任务简报经 `agent/inbox/spliced` 注入（首条 4883 B，在 S3 之外）；掩 `id`/`time`/`seq` 后三槽任务简报字节等值。「同题输入等值」主张覆盖 spliced 层后才完整。

**归属**：同题重跑间 agent 是否行使后台机制造成了真实输入侧差异，Harness 忠实注入通知；旧门 dabstep S3 失败归真实输入侧，不是日志层分类假象。这是重复性口径内的事实，不构成机制因果（为何 r1 行使了后台作业不在本页范围）。

## 观测口径新事实（影响未来合同设计）

- **整事件规范字节含 `time`/`seq` 信封**：跨 run 的整事件字节等值原则上不可能；钉定门的「极差 0」本质是 size 诊断。真实标本：两槽 `turn/start` 同为 68 B 而内容不同。本例数据层复核证明共同内容确实等值，size 等值在此未掩盖内容差异。
- **每条消息 `data.id` 是每运行新 UUID**：按 id 对账的口径必然 100% 报差异。
- **`user/message` 类型内含 Harness 注入子类**：本三槽出现 5 种 `source.kind`（`user` / `agent-instructions` / `runtime-context` / `tool-jobs` / `subagent-settled`）；输入侧切割与未来 inline/spill 类干预设计须按此分型，不能把整类当「真实用户输入」。
- **15 槽事件类型并集无任何 usage/token/cost 类类型名**（对照 Codex 的 `token_usage_record`）；但**字段级计量数据真实存在（独审发现）**：`assistant/message` 事件 `data.message.usage` 内嵌 `{inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens, totalTokens}`，15 槽共 338 条。「DSH 无自报用量」仅在类型名级为真；自报 usage 分离账可在 session v4 事件内分账，另行推进。

## 边界与 unknown

- 本页经非作者独审（PASS-with-notes）：矩阵与定源 A–F 独立管道复现零数字分歧；上列敏感性限定、spliced 层补验与字段级 usage 发现均出自独审并已并入。
- 未绑定客户端首请求正文、未证后端实际摄入；无成本/token/排名推断；首请求正文、后端摄入、同控干预效果仍为 **unknown**。
- 钉定行核验是操作层重现（同口径同输入同数字），不是生成器代码级等价证明。
- 内容级复核读自私档原档，公开的只有裁定、字节量与 SHA 锚（档案 SHA 已在钉定件中公开）；任务正文不公开。

## 离线复算

仓库根目录运行（Python 3.9+ 标准库；只读钉定件，不读私档）：

```bash
scope='4-打分细则/DSH事件类型消融-2026-11-25'
python3 -B "$scope/recompute.py"
python3 -O -B "$scope/recompute.py"
python3 -B -m unittest discover -s "$scope" -p test_recompute.py
python3 -O -B -m unittest discover -s "$scope" -p test_recompute.py
```
