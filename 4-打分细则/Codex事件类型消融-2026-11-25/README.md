# Codex 事件类型消融与输入侧掩蔽等值（2026-11-25）

对 r1109 冻结批次的 **Codex CLI 15 槽 rollout**（5 案例 × 3 run）做事件类型层消融与输入侧掩蔽等值，回答：**Codex 侧跨 run 字节方差能否在类型层完整归因**。这是 [DSH 事件类型消融](<../DSH事件类型消融-2026-11-25/>) 的 Codex 镜像，共同完成 CLI 双侧「真实输入侧差异 vs 日志层差异」的对称归因。

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
| 对称归因 | 面二分完备（恒量 5 型 / 方差 8 型 / 无残留）；并集 13 型中**无 DSH 型后台通知类目**（tool-jobs / subagent-settled 的对应物不存在）——Codex rollout 无「harness 通知混入输入侧」通道 |

**归因结论**：Codex 侧跨 run 字节方差全部落在输出/工具产物/计量记录类型；输入侧经显式掩蔽后恒量。DSH dabstep 旧门 956B 定源为真实输入侧 harness 后台通知的结论不被 Codex 镜像推翻；两侧差异是 harness 事件模型的真实差异，非日志层分类假象。

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
- `test_recompute.py`：正常 + 9 夹具（sha 非 hex / 缺槽 / header 等值矛盾 / variance 等值矛盾 / 对表破坏 / 输入行破坏 / 常量多值 / 近错声明假 / union 计数不一致）全部拒绝。
- 合同：`codex-ablation-contract.json`（schema `r1109-codex-type-ablation-v1`，内容无关——任务正文不入公开件）。

## 局限

- 掩蔽等值≠字节级逐字节等值≠服务端实际摄入（自报 usage 复算一致不证摄入，维持[分离账](<../自报usage分离账-2026-11-25/>)口径）。
- 单批 r1109 数据面；掩蔽集以本合同声明为准（时间键类为勘察后补充，如实登记）。
- 属观测口径校准（#17 第 1 条），不覆盖机制干预、读取检测与第三方核验项。

- 本页经非作者独审（PASS-with-notes）：PD1–PD6 独立复算零数字分歧；`world_state` variability 表述订正（run 间差异仅行信封 timestamp，payload 跨 run 字节相同）、raw 全不等值、assistant 计数互异 4/5 限定均出自独审并已并入；绑定三链（rollout==evidence==ledger 15/15）经合同 `binding_triple` 字段承载。
