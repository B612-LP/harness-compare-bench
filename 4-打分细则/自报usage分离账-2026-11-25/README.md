# 自报 usage 分离账（2026-11-25）

第五周观测口径的 usage 层条目：对 r1109 固定 30 槽（5 案例 × 3 run × DSH/Codex）的**自报 usage** 做双侧分账，回答三个问题——自报数内部是否自洽、增量还是累计、字节账能否换算成 token 账。零新运行，纯离线复算；非作者独审后发布。

## 数据与绑定

- 载体：DSH `session.v4` 事件 `assistant/message` 的 `data.usage`（338 条）；Codex rollout 顶层 `token_usage_record.payload.usage`（406 条）。合计 744 条，全部来自同一批 DeepSeek V4.1-Flash、low 档、r1109 冻结原档。
- 绑定：30/30 槽与[钉定 evidence.json](<../机制重复口径澄清-2026-11-12/evidence.json>)（SHA `925470d3…`）的 identity SHA 逐一相符。**口径注**：DSH identity 的 SHA 是 `session.v4.jsonl.zstd` 压缩文件本身。
- 公开账本 [usage-ledger.json](usage-ledger.json)（schema `r1109-usage-ledger-v1`）：免 id（无 thread/session/response UUID），保留 DSH 的 turn/step 序与每条记录的 `text_chars`（内容无关计数）。**字段口径（独审 N2 订正）**：`text_chars` = 该消息所有带 `text` 字段内容块的 UTF-8 字节和——实测 **99.6% 来自 reasoning 块**（reasoning 1,229,076 B vs 可见 text 4,835 B）；账本内嵌 note 串的「visible text blocks」系误标，按本口径为准（账本字节保持独审核验原样，不重写）。档案正文不外发。
- Codex 会话级闭合：档案内每条 `token_usage_record` 另带 `thread_token_usage`/`turn_token_usage`（406/406），末条 thread 总量与逐条 usage 之和的对账见 [thread-closure.json](thread-closure.json)（内容无关计数）。
- 复算：`python3 recompute.py`；测试 `python3 -m unittest test_recompute.py`（含缺字段/非整数/负数/错绑/累计陷阱五类近错）。

## 裁定

| 预测（[PREREG 私档封印]） | 裁定 | 要点 |
|---|---|---|
| P1 结构五字段俱全 int≥0 | PASS | 338/338 |
| P2 `total = input+output` | **FAIL → 分支登记** | 仅 1/338 成立（恰 cacheRead=0 的退化等值）。实际 **DSH 归一口径：`totalTokens = inputTokens + outputTokens + cacheReadTokens + cacheWriteTokens`（338/338）**；cacheWrite 恒 0；inputTokens 与 cacheReadTokens 互斥分量（input≥cacheRead 仅 10/338）→ **inputTokens 是未命中（miss）专用字段** |
| P3 逐响应增量（非累计） | PASS | DSH：input 非单调 15/15 槽、`sum(total) >> last(total)`。Codex：**直接判据 = 末条 `thread_token_usage` 总量 == Σ逐条 usage（15/15 精确相等，input/output 分量同样闭合）**（独审 N1 升格）；原 `n×first > last`（bird r1：277,443 > 67,414）只是算术观察，不能排除累计：如有效累计序列 `[10,11]` 也满足。程序保留历史名称 `is_cumulative_impossible` 和输出字段 `impossible_cum` 以兼容旧结果，但其 True 不表示累计不可能 |
| P4 档案无会话级总量 | PASS（DSH-scoped） | assistant/message 之外递归扫描零 usage 载体；唯一双载体 = `data.usage` + `data.stream` 末块 `chunk.usage`，两者逐事件相等（338/338，键形一致）。**结构不对称（独审 N1 登记）**：Codex 档案**有**会话级总量（`thread_token_usage`），DSH 档案没有——「无/有」是双 harness 分离账的实质差异，见 [thread-closure.json](thread-closure.json) |
| P5 Codex 对照 | PASS | 15/15 槽 token_usage_record（各 5–66 条，共 406）；同案例三 run 自报总量互异 10/10 个案例×harness 组合 |
| P6 byte≠token | PASS | `text_chars / outputTokens` 中位数 per case（按 `text_chars>0` 且 `outputTokens>0` 过滤；本数据全部 338 条 outputTokens 均大于零，淘汰 dabstep 3 / exercism 1 / lcb 4 / tb 3 条）：bird 2.28 / dabstep 2.57 / exercism 1.87 / lcb 2.14 / tb 3.17，跨案例散布 1.70×（70% > 10%）；不过滤口径中位 bird 2.28 / dabstep 2.49 / exercism 1.43 / lcb 1.78 / tb 3.13、误差区间 21.7%–64.2%。`chars/4` 朴素估中位误差（过滤口径）20.9%–53.2%（max 99.8%）→ **字节门不能替代 token 账** |

P6 口径注（独审 N2 订正）：分母 `outputTokens` 是自报输出总数，可能涵盖 reasoning 与 tool-call 参数等，但账本不能拆出各成分的 token；分子 `text_chars` 是带 text 字段内容块的 UTF-8 字节和，**几乎全是 reasoning 块字节**（99.6%），与输出总数的内容覆盖面不一定一致。跨案例比率及朴素估算误差是描述性观察；它们不能单独区分分词密度、工具参数和其他内容组成、阶段等因素的影响。此前将差异及误差直接归因于分词密度的说法证据不足，现予订正。

## 核心发现（预注册外，独审重点区）

1. **同一 provider（deepseek-official）、两种相反的 harness 归一口径**：
   - DSH：四分量和；input 专指 miss，cacheRead 单列，cacheWrite 占位恒 0；
   - Codex：`total = input + output`（406/406）；`cached_input_tokens` 是 input 的内嵌 detail（input≥cached 406/406），`reasoning_output_tokens` 是 output 的内嵌 detail（reasoning≤output 406/406）。
   - → **usage 字段是 harness 归一值，不是 provider 原始值**；跨 harness 的 usage 比较必须逐格式映射，不能直接比字段名。这是观测规范 v1.4 候选的 usage 条款核心。
2. **首条自报 usage 对照（订正）**：每案例三个 run 的首条 DSH 自报输入分量之和相同，`totalTokens` 三 run 散布 0.35%–0.91%，全部 <1%（如 bird 输入分量和均为 7289，输出为 127/175/188，总量为 7416/7464/7477）。总量还包含输出，输入数相同也不证明请求内容或字节相同。此前「R1 已证首请求字节逐字节相同」「token 层独立印证」的说法错误：R1 检查的是特定事件内容，并明确未绑定本组客户端首请求正文，不能升级为请求侧等值。
3. **冷/热缓存状态在自报数中可见**：DSH r1 冷（input 6278–7289 / cacheRead 0–256）→ r2/r3 热（input 134–249 / cacheRead 6400–7040），total 近恒——miss/hit 分量搬家、总量不动；Codex 侧 `cached` detail 同型（r1 ∈ {3584, 7808} → r2/r3 ∈ {8576–9344}），且 input_tokens 逐 case 三 run 恒（9567/9319/8923/9033/8809）。
4. **写缓存分量双侧恒 0**（744/744）：语义（未上报 vs 真零）登记 unknown。
5. **单调性镜像**：Codex input 单调不减 15/15（整包口径随上下文增长）vs DSH input 非单调 15/15（miss 口径随命中波动）——同一会话现象在两种口径下呈相反单调性。
6. **会话级总量载体不对称（独审 N1）**：Codex 档案自带会话账本且精确闭合（末条 thread 总量 == Σ逐条，15/15，input/output 分量同闭合）；DSH 档案只有逐响应记录、无任何会话级总量载体。后果：Codex 的会话总量可从档案**内部对账验证**，DSH 的会话总量只能外部求和——跨 harness 汇总 token 账时，两者的「总」不是同一验证等级的量。

## 事后探索：工具块与字节／自报输出数比率

对同一批 DSH 15 槽原档事后按消息内容分层：含 `tool-call` 块与不含工具块；没有新运行，也不是预注册或独立试验。338 条 usage 中 327 条的 `text_chars` 和 `outputTokens` 均大于零，11 条文本字节为零；无工具块仅 15 条，每槽 1 条。按案例合并三槽消息计算各组比率中位数：

| 案例 | 有工具块（有效 n） | 无工具块（n=3） |
|---|---:|---:|
| bird | 2.223（62） | 3.364 |
| dabstep | 2.487（114） | 4.525 |
| exercism | 1.235（21） | 4.178 |
| lcb | 1.832（66） | 3.812 |
| tb | 3.131（49） | 4.271 |

五题均见组间差异，支持**内容组成是值得考虑的竞争解释**，不证明工具参数或分词密度是原因：各组并非随机分配，阶段、任务、语言和内容等可能混杂，无工具组每槽仅一条。将工具参数对象按固定 Python JSON 规则重编码并计代理字节后，有工具有效组的整体比率中位数由 2.291 变为 3.398；该代理不是原始请求字节或参数 token，也不代表补齐了分母内容。工具块存在不证明工具实际执行。

项目内非作者独立读取与既有 identity SHA 绑定的 15 个原档，逐行对表公开账本 338 条并复核分层；原档未公开，因此本段不声称仅凭公开账本可独立复算工具分层，内部独审亦不等于受控第三方核验。结论限于该批样本，不改历史成绩、成本或因果判断。

## 与既有结论的关系

- 对 [DSH 事件类型消融](<../DSH事件类型消融-2026-11-25/README.md>) R1 独审发现（N1）的路径订正：字段级 usage 的权威载体是事件 `data.usage`；`data.message.usage` 是恒 null 字段（R1 页已加订正注记）。
- 与老师反馈对照（#17）：本环只分账自报数，兑现「逐格式声明可归一字段与未知条件」；**不宣称服务端摄入**，不做成本/费用/排名推断；「字节 ≠ token/费用/服务端实际摄入」由 P6 与恒 0 的 cacheWrite 直接支撑。
- 校准例不充当独立试验；旧门不重开；正式 25 格与冻结分数不动。

## 边界与 unknown

- 服务端实际摄入未知：自报数 ≠ 计费/摄入；cacheWrite 恒 0 语义未知；字节→token 无事件级通用换算（P6 即证据）。
- P4 的递归载体扫描、P6 的 text_chars 计数依赖私有原档（30/30 SHA 绑定已记录）；账本内部关系全部可由本页脚本公开复算。
- 本页经非作者独审（audit-r2，**PASS-with-notes**，作者全部数字 100% 独立复现零分歧）。独审发现 N1–N6 已按登记式整改并入：N1 thread 闭合判据升格为主判据 + 会话级载体不对称入 finding（新增 [thread-closure.json](thread-closure.json) 承载，不动已审账本字节）；N2 `text_chars` 语义标签三处订正（账本内嵌 note 误标以披露代改写）；N3 过滤口径补声明；N4 措辞精度订正；N5（r2/r3 缓存态逐 case 全同可作冷/热佐证）与 N6（SHA 口径与自报≠摄入边界表述确认）仅登记。无新增产品运行，不改历史成绩。
