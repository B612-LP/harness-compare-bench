# 豆包输出侧结构分解（bw-retest tb 三重复）— 预注册 v1

- 冻结：2026-11-16T06:56+08:00（任何 result 计算前）。离线纯算法；0 新运行；不改分数/门/25 格；不改既有发布文件。执行记录进包内 EXECUTION-RECORD.md（既有钉定页一律不写）。
- 勘察注记（冻结前事实，可被复算推翻）：豆包 bw-retest 仅 tb-cargo-plan 三槽；trajectory.jsonl 行数 45/37/44（assistant 18/16/19、tool 27/21/25）；三 rep 开场工具名序列前缀相同（Bash,T,Read×3,T,T,T,Read…）；r3 工具集缺 Write/task_create/task_update；纯 assistant 轮 0/1/1；tool_result content 字节 40282/36111/41900。

## 1. 问题
豆包同一 tb 任务三重复的输出侧结构波动是「早期分岔」（分岔点早、随后各自演化）还是「后期收敛」（共享长主干后段分岔）？波动载体是工具调用参数、工具结果还是纯回复轮？与 bird §4.34 的早期分岔结论横向对照（同方法论、不同产品、不作因果/跨产品可比性主张）。

## 2. 冻结判据（内容无关；工具名=可登记标识符，同 §4.34 先例）
- 数据源：bw-retest/doubao/runs/tb-cargo-plan__r{1,2,3}/trace/session/agents/*/system/trajectory.jsonl（每槽恰一 trajectory，多则 exit2）。
- 逐 rep 登记：行数、assistant/tool 行数、tool_call 总数、纯 assistant 轮数（无 tool_calls 的 assistant 行）、逐工具名调用计数表、tool_call function canonical JSON 字节总和（按 name 分列）、tool_result content UTF-8 字节总和、工具名调用序列（assistant 行展开其 tool_calls 顺序，tool 行记 T）。
- 序列比对：三序列两两 LCP、三方 LCP、首分岔 index；首分岔处两侧元素登记（标识符或 T/A，不读值）。
- 计数硬等：三 rep 的 reward=[0,0,0] 与 weighted=[81.48,70.37,81.48] 必须与公开[复测登记-r1109](<../../4-打分细则/预注册复测选题-2026-11-08/复测登记-r1109.md>)该节一致，漂移 exit2；app 版本事实（2.34.12→2.35.19、r1 2400s 帽）仅注记不判定。
- 描述分母与单位逐项登记；字节口径=canonical JSON（sort_keys, ensure_ascii）或 UTF-8 文本，逐项声明。

## 3. 分支
- H-EARLY-DIVERGENCE：三方 LCP < min(序列长)/2（同 §4.34 判据形式）⇒ 结构波动早期分岔型，与 bird 结论同型（登记为同型性观察，非因果、非跨产品规律）。
- H-LATE-CONVERGENCE：LCP ≥ min/2 ⇒ 共享主干后段分岔型。
- 硬等失败或数据不足 ⇒ exit2 / H-INDETERMINATE。

## 4. 交付
verify.py（--root 与 --archive-root 必填，后者=bw-retest/doubao；stdout 摘要；--output 独占创建；双档 stdout 逐字节一致；fail-closed exit2）+ test_verify.py（≥14 双档全绿；真档案 env DOUBAO_STRUCT_ARCHIVE_ROOT 门控拒绝静默跳过；合成用例：早分岔/晚收敛分类、序列展开顺序、逐工具字节表、硬等防篡改、--output 拒绝覆盖）+ result.json（schema doubao-struct-v1，含 prereg sha256、baseline_commit、内容无关声明）+ EXECUTION-RECORD.md。

## 5. 解释边界
n=3 单 case 单产品描述性登记；工具名标识符可比较但参数/结果内容不读值；不外推产品行为规律、不横比 B 组分数面；不构成判卷差异来源分析（checker 未变）；正式 25 行与 bw-retest 判分不变。
