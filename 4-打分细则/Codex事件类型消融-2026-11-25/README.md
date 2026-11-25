# Codex 事件类型消融与输入侧掩蔽等值（2026-11-25）

对 r1109 冻结批次的 **Codex CLI 15 槽 rollout**（5 案例 × 3 run）做事件类型层消融与前三条 message 的掩蔽等值分析，考察所声明类型分组中的跨 run 方差分布。这是对 [DSH 事件类型消融](<../DSH事件类型消融-2026-11-25/>) 的另一侧观测；两组并非同条件的控制实验，类型层比较不能单独完成真实输入变化与日志层差异的对称因果归因。

## 数据与绑定

- 数据面：`launch-r1109` 冻结原档 Codex rollout 15 文件（未压缩 JSONL）。
- 绑定链（错绑锚）：rollout 文件字节 SHA-256 == [机制重复口径澄清](<../机制重复口径澄清-2026-11-12/>) evidence.json 槽 identity == [自报 usage 分离账](<../自报usage分离账-2026-11-25/>) `usage-ledger.json` 的 `archive_sha256`，15/15 双对账；对账结果以合同 `binding_triple` 字段承载（slots_all_equal=true、slots_checked=15）。
- 口径：规范字节 = `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False)` UTF-8（与 DSH 侧 canon 同式）。

## 判定结果（PD1–PD6 全 PASS）

| 维度 | 结果 |
|---|---|
| 类型枚举 | top 6 型（session_meta / event_msg / response_item / token_usage_record / turn_context / world_state）；response_item 子型恰 4；event_msg 子型 5；`token_count` 与 `token_usage_record` 计数逐槽相等 15/15 |
| 输入侧恒量 | 每槽前 3 条 message 角色序恒 `[developer, user(<environment_context>), user(任务公告)]`；显式掩蔽集后三-run **逐行规范字节等值** 5/5 案例；developer 与 environment_context 两行掩蔽后**跨案例同 SHA**（任务无关常量），任务公告行逐案例恒定 |
| 方差面 | assistant message / reasoning / function_call(+output) / item_completed / task_complete / token_count / token_usage_record 跨 run 全互异（输出+工具产物+计量记录） |
| 结构头恒量面 | session_meta / turn_context / world_state / thread_settings_applied / task_started 掩蔽后等值；常量 `model=deepseek-flash`、`instructions=dfd53114f5f6f9f5fd7816370d0bf2847806246d`、`approval_policy=never`、`sandbox_policy=danger-full-access` 全 15 槽单值 |
| usage 复算 | rollout 重提 `token_usage_record.payload.usage` 与公开账本逐槽逐条（含顺序）精确相等 15/15 |
| 类型层分账 | 已枚举的 13 型在本合同分为恒量 5 型与方差 8 型，无未分组类型；其中没有名为 DSH `tool-jobs` / `subagent-settled` 的对应事件类目。此结果限定于类型名与本合同分组，不能据此断言其他载体不存在状态反馈或某类机制不存在。 |

**类型层结论**：在本合同所枚举的事件类型及分组下，跨 run 方差落在输出、工具产物与计量记录相关类别；每槽前三条 message 在声明掩蔽后逐行等值。这不等于证明全部输入、请求正文或服务端实际摄入等值。DSH dabstep 旧门的 956 B 定源为该记录中的两条通知事件，是另一数据面的既有观察；两侧类型和可见承载方式不同，本身不能区分真实机制差异与日志表达差异，也不能推断产品机制相同或不同。

## 工具输出的格式候选及未知（事后补充）

在同一批固定的 15 个 Codex 槽，对 503 组 `exec_command` / `write_stdin` 调用与输出作事件层离线复核：503 组均为同槽调用 ID 唯一配对且调用行在输出行之前。503 的分母仅限这两类调用，不代表所有产品操作或所有可能的反馈通道。

按固定严格前缀规则，5 个输出呈现“运行中”格式候选（`exec_command` 3、`write_stdin` 2）；另有 494 个“已退出”格式候选，4 个其他或未知。5 次 `write_stdin` 的参数值与同槽唯一、已返回的先前 `exec_command` 运行格式候选中的会话字段静态相等；两次运行格式返回还与调用参数自洽，另三次退出格式返回不包含可验证的会话字段。这只表示所定义字段和行序匹配，并非认证实际进程或会话身份。

上述状态文本位于输出字符串内部，不是独立认证的工具信封字段；命令输出可以仿造同样文本，来源不能判断时应保持未知。上述证据不证明自动通知、客户端请求正文或服务端实际摄入，也不证明能力高低。

对照的 DSH dabstep 三槽是按 `user/message` 的来源类别计数，而非按调用配对计数：三槽分别 5、3、3 条；其中首槽多出两种通知来源各一条。**两个产品并非同条件，且 15 槽的调用分母与 3 槽的事件分母不同**；这些观察不能说明两侧机制相同或不同。

固定私有原档的前后 SHA 与预定锚相等，仅支持本次本机错绑核查；公开材料不含原档，读者不能据此直接复算私档。项目内非作者独审不等同于老师所要求的受控第三方原档核验。该补充是事后离线探索，不改历史合同与分数。

## 掩蔽集声明（合同内逐条）

1. 行信封 `timestamp` / `ordinal` 字段去除；
2. payload 内嵌时间键按名掩蔽：`started_at` / `create_time` / `completed_at` / `timestamp`（与信封时间同类的日志层时间）；
3. 工作区路径 `/Users/…/bench-workspaces/…` → `<cwd>`；
4. UUID 形 id（含 `msg_…` 尾部）→ `<uuid>`。

承重性（省略即翻转）：UUID 与时间键使输入三行逐行不等；cwd 使 env 行跨案例恒一性从 5 塌缩到 1。

## 近错（8 组 14 断言全过）

错绑拒绝（r1 字节≠r2 钉定 SHA，检测器抛错）；计数错配检测（token_count≠token_usage_record，经检测管线注入复核）；结构头时间依赖分层（session_meta/task_started 漏掩蔽时间键翻转；turn_context/thread_settings_applied 的 run 间 variability 纯 UUID——关 UUID 掩蔽即翻转；world_state 的 payload 跨 run 字节相同，其 run 间差异仅行信封 timestamp）；未枚举类型经检测管线报 unknown 不入并集；换槽对表不等 + 同槽精确相等。

## 复算

- `recompute.py --contract codex-ablation-contract.json`：校验绑定 hex、槽命名、union↔face 计数一致、面二分无残留、三态等值不变式、输入三行等值、常量单值、探针、对表 15/15、绑定三链声明、近错声明。`CONTRACT OK`。
- `test_recompute.py`：正常合同接受；10 项变异夹具（sha 非 hex / 缺槽 / header 等值矛盾 / variance 等值矛盾 / 对表破坏 / 输入行破坏 / 常量多值 / 近错声明假 / union 计数不一致 / 绑定三链声明破坏）全部拒绝。该程序核合同内部声明，不独立读取或认证私有原档。
- 合同：`codex-ablation-contract.json`（schema `r1109-codex-type-ablation-v1`，内容无关——任务正文不入公开件）。

## 局限

- 掩蔽等值≠字节级逐字节等值≠服务端实际摄入（自报 usage 复算一致不证摄入，维持[分离账](<../自报usage分离账-2026-11-25/>)口径）。
- 单批 r1109 数据面；掩蔽集以本合同声明为准（时间键类为勘察后补充，如实登记）。
- 属观测口径校准（#17 第 1 条），不覆盖机制干预、读取检测与第三方核验项。

- 本页经非作者独审（PASS-with-notes）：PD1–PD6 独立复算零数字分歧；`world_state` variability 表述订正（run 间差异仅行信封 timestamp，payload 跨 run 字节相同）、raw 全不等值、assistant 计数互异 4/5 限定均出自独审并已并入；绑定三链（rollout==evidence==ledger 15/15）经合同 `binding_triple` 字段承载。
