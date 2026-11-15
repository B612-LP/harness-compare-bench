# WB 重复槽输入与交互量结构（2026-11-16）

**预注册：对 r1109-bw-retest 的 WorkBuddy 六个复测槽（dabstep-payments-10、tb-cargo-plan 各 r1–r3）做纯事后结构分析——输入侧首条 user 消息跨重复字节稳定性，与交互量事件结构登记。** 动机：机制波（v2 序列 / R3 分解 / bird S4 / 工具结果下游性）已覆盖 DSH 与 Codex，A 组第三款 WorkBuddy 的复测槽只有已发布分数（[复测登记-r1109](<../预注册复测选题-2026-11-08/复测登记-r1109.md>)：W dabstep 3/3 reward=0，W tb 3/3 reward=0，tb r1 计划结构门崩塌），输入侧从未测量。若 WB 输入侧跨重复不稳定，teacher 问题③（输入重复性假设）在 A 组内部就不是同质命题。纯算法分析，不新增运行、不判定 WB 门、不改 25 格与任何历史分。

本页冻结于任何槽级数值计算之前；只冻结定义与分支，不预置未经档案核实的槽级事实（bird 教训）。

## 1．范围与数据源（冻结）

- 6 槽：`{dabstep-payments-10, tb-cargo-plan} × {r1, r2, r3}`，私有归档 `launch-r1109/bw-retest/workbuddy/runs/`（与 [r1109-bw-retest 公开现场](<../../3-表现现场/r1109-bw-retest/README.md>)对应）。
- 每槽预期恰一个 session trace jsonl；多于一个或缺失 → exit 2（fail-closed）。
- 槽级常量（trace SHA、字节数）由实现方在建包时从档案读定后作为 fail-closed 常量钉入 verify.py，不由本页预置。

## 2．定义（冻结）

- **W1 输入侧**：每槽恰一条 role=user 的 message 事件；取其 text。跨重复（组内三对两两）比较：
  - 三份 text 逐字节相同 → 该组 `w1_stable`。
  - 存在差异 → 结构定位：text 内 `<system-reminder data-role="user-context">` 信封 span（起止偏移为结构量）；记录逐差异**字节偏移**（不记录差异字节值与任何内容）。全部差异偏移都落在信封 span 内 → `w1_env_volatile`（环境块跨重复不稳定、任务文本稳定）；任一差异偏移在信封 span 外 → `w1_task_text_drift`（任务文本本身跨重复不同——最重发现）。信封标记缺失 → 该组单列 `w1_no_envelope`，只登记不归类。
- **W2 交互量（描述性，不设门）**：每槽按事件型计数（function_call、function_call_result、reasoning、message 按 role 分列、file-history-snapshot、ai-title）；function_call 与 function_call_result 计数相等性登记（结构检查，不做 id 级配对猜测）；canonical 投影 = 顶层去除 `id`、`timestamp`（及显然逐会话易变的外层元数据键）后 sort_keys JSON 的字节数，逐型合计跨重复对比仅登记。
- **W3 分数对齐**：每槽 checker 判分 reward/weighted 与已发布复测登记表值逐槽硬等（常量钉入 verify.py），仅用于把结构事实锚到已判分槽位，不做任何因果表述。
- 内容无关纪律：只记录计数、偏移、span、字节数、SHA；不记录信封或任务文本内容、不记录差异字节值。

## 3．反证分支（冻结）

- **B-W1-STABLE**（两组全 stable）：WB 复测输入侧与 DSH 同质（跨重复逐字节稳定），机制波输入侧结论对 A 组三款方向一致。
- **B-W1-ENV-VOLATILE**（差异全部限信封内）：WB 输入侧存在真实跨重复漂移但限于产品注入的环境块——A 组内输入重复性假设需按产品分列表述，这是对既有「输入稳定性」叙事的**限定**，不是推翻。
- **B-W1-TASK-DRIFT**（任一组出现信封外差异）：最重发现——任务文本跨重复不同，直接冲击 WB 轨道分数可比性前提；只登记证据，不回写任何已发布分数，后续判读留待用户新授权。
- 信封缺失/结构异常 → 相应组降级为结构登记。

## 4．老师反馈对照（Issue #16）

- **P1 机制解释优于加重复数**：零新运行，把输入侧问题③扩展到 A 组第三款的既有归档。
- **P1 观测口径诚实**：W2 明示为描述性结构登记，不冒充统一门（WB trace 形态与 DSH v4/Codex response_item 不同，不可横比门值）。
- **P0 验收**：6 槽、2 组、分析脚本=本包 verify.py；交付含 result.json + test_verify.py + EXECUTION-RECORD.md（执行记录入包，不写任何被钉定公开页）。

## 执行记录（执行完成后写包内 EXECUTION-RECORD.md，不写本页）
